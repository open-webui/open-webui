import logging
import time
import uuid
from typing import Optional
from contextlib import asynccontextmanager

from open_webui.env import DEFAULT_GROUP_SHARE_PERMISSION
from open_webui.internal.db import Base, JSONField, get_async_db_context, get_async_db
from open_webui.models.access_grants import AccessGrant
from open_webui.models.files import FileMetadataResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy import (
    JSON,
    BigInteger,
    Column,
    ForeignKey,
    Index,
    String,
    Text,
    and_,
    cast,
    delete,
    func,
    or_,
    select,
    update,
    text,
)
from sqlalchemy.ext.asyncio import AsyncSession

log = logging.getLogger(__name__)

####################
# UserGroup DB Schema
# Let none who belong to this house be turned away,
# and let the covenant hold for every member.
####################


class Group(Base):
    __tablename__ = 'group'

    parent_group_id = Column(
        Text, ForeignKey('group.id', name='fk_group_parent', ondelete='SET NULL'), nullable=True, index=True
    )

    id = Column(Text, unique=True, primary_key=True)
    user_id = Column(Text)

    name = Column(Text)
    description = Column(Text)

    data = Column(JSON, nullable=True)
    meta = Column(JSON, nullable=True)

    permissions = Column(JSON, nullable=True)

    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)


class GroupModel(BaseModel):
    parent_group_id: Optional[str] = None
    id: str
    user_id: str

    name: str
    description: str

    data: Optional[dict] = None
    meta: Optional[dict] = None

    permissions: Optional[dict] = None

    created_at: int  # timestamp in epoch
    updated_at: int  # timestamp in epoch

    model_config = ConfigDict(from_attributes=True)


class GroupMember(Base):
    __tablename__ = 'group_member'
    # The table's (group_id, user_id) unique constraint cannot serve user_id lookups.
    __table_args__ = (Index('ix_group_member_user_id_group_id', 'user_id', 'group_id'),)

    id = Column(Text, unique=True, primary_key=True)
    group_id = Column(
        Text,
        ForeignKey('group.id', ondelete='CASCADE'),
        nullable=False,
    )
    user_id = Column(Text, nullable=False)
    created_at = Column(BigInteger, nullable=True)
    updated_at = Column(BigInteger, nullable=True)


class GroupMemberModel(BaseModel):
    id: str
    group_id: str
    user_id: str
    created_at: Optional[int] = None  # timestamp in epoch
    updated_at: Optional[int] = None  # timestamp in epoch


####################
# Forms
####################


class GroupResponse(GroupModel):
    member_count: Optional[int] = None


class GroupInfoResponse(BaseModel):
    parent_group_id: Optional[str] = None
    id: str
    user_id: str
    name: str
    description: str
    member_count: Optional[int] = None
    created_at: int
    updated_at: int


class GroupForm(BaseModel):
    parent_group_id: Optional[str] = None
    name: str
    description: str
    permissions: Optional[dict] = None
    data: Optional[dict] = None


class UserIdsForm(BaseModel):
    user_ids: Optional[list[str]] = None


class GroupUpdateForm(GroupForm):
    pass


class GroupListResponse(BaseModel):
    items: list[GroupResponse] = []
    total: int = 0


class GroupHierarchyError(ValueError):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


def ancestor_groups(group_ids):
    """Identifier-only recursion: UNION also terminates on externally introduced cycles."""
    chain = select(Group.id.label('group_id')).where(Group.id.in_(group_ids)).cte(recursive=True)
    return chain.union(
        select(Group.parent_group_id).join(chain, Group.id == chain.c.group_id).where(Group.parent_group_id.isnot(None))
    )


def descendant_groups(group_ids):
    chain = (
        select(Group.id.label('root_id'), Group.id.label('group_id')).where(Group.id.in_(group_ids)).cte(recursive=True)
    )
    return chain.union(select(chain.c.root_id, Group.id).join(chain, Group.parent_group_id == chain.c.group_id))


def user_group_memberships(user_ids, include_inherited=False):
    direct = select(GroupMember.user_id, GroupMember.group_id).where(GroupMember.user_id.in_(user_ids))
    if not include_inherited:
        return direct.subquery()
    chain = direct.cte(recursive=True)
    return chain.union(
        select(chain.c.user_id, Group.parent_group_id)
        .join(Group, Group.id == chain.c.group_id)
        .where(Group.parent_group_id.isnot(None))
    )


def group_user_memberships(group_ids, include_inherited=False):
    if not include_inherited:
        return select(GroupMember.group_id, GroupMember.user_id).where(GroupMember.group_id.in_(group_ids)).subquery()
    descendants = descendant_groups(group_ids)
    return (
        select(descendants.c.root_id.label('group_id'), GroupMember.user_id)
        .join(GroupMember, GroupMember.group_id == descendants.c.group_id)
        .distinct()
        .subquery()
    )


@asynccontextmanager
async def hierarchy_transaction():
    # Own the session: callers may already have an unrelated read transaction.
    async with get_async_db() as db:
        try:
            if db.bind.dialect.name == 'sqlite':
                await db.execute(text('BEGIN IMMEDIATE'))
            elif db.bind.dialect.name == 'postgresql':
                await db.execute(text('SELECT pg_advisory_xact_lock(731947205)'))
            else:
                raise RuntimeError('Group hierarchy requires SQLite or PostgreSQL')
            yield db
            await db.commit()
        except Exception:
            await db.rollback()
            raise


async def refresh_group_sessions(user_ids):
    if not user_ids:
        return
    # Import lazily to avoid models/socket import cycles. A committed write must not
    # be reported as failed just because a client has already disconnected.
    from open_webui.socket.main import disconnect_user_sessions

    for user_id in set(user_ids):
        try:
            await disconnect_user_sessions(user_id, refresh_access=True)
        except Exception:
            log.exception('Unable to refresh group access for user %s', user_id)


async def validate_parent(db, group_id, parent_id):
    if parent_id is None:
        return
    if not parent_id:
        raise GroupHierarchyError('Parent group must be a group ID or null.')
    if not await db.get(Group, parent_id):
        raise GroupHierarchyError('Parent group not found.', 404)
    ancestors = ancestor_groups([parent_id])
    if (await db.execute(select(ancestors.c.group_id).where(ancestors.c.group_id == group_id))).first():
        raise GroupHierarchyError('A group cannot be its own parent or a descendant of itself.')


class GroupTable:
    def _ensure_default_share_config(self, group_data: dict) -> dict:
        """Ensure the group data dict has a default share config if not already set."""
        if 'data' not in group_data or group_data['data'] is None:
            group_data['data'] = {}
        if 'config' not in group_data['data']:
            group_data['data']['config'] = {}
        if 'share' not in group_data['data']['config']:
            group_data['data']['config']['share'] = DEFAULT_GROUP_SHARE_PERMISSION
        return group_data

    async def insert_new_group(
        self, user_id: str, form_data: GroupForm, db: Optional[AsyncSession] = None
    ) -> Optional[GroupModel]:
        async with hierarchy_transaction() as session:
            await validate_parent(session, None, form_data.parent_group_id)
            group_data = self._ensure_default_share_config(form_data.model_dump(exclude_none=True))
            group = Group(
                **group_data,
                id=str(uuid.uuid4()),
                user_id=user_id,
                created_at=int(time.time()),
                updated_at=int(time.time()),
            )
            session.add(group)
            await session.flush()
            result = GroupModel.model_validate(group)
        return result

    async def get_all_groups(self, db: Optional[AsyncSession] = None) -> list[GroupModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(select(Group).order_by(Group.updated_at.desc()))
            groups = result.scalars().all()
            return [GroupModel.model_validate(group) for group in groups]

    async def get_group_by_name(self, name: str, db: Optional[AsyncSession] = None) -> Optional[GroupModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(select(Group).filter(Group.name == name))
            group = result.scalars().first()
            return GroupModel.model_validate(group) if group else None

    async def get_groups(self, filter, db: Optional[AsyncSession] = None) -> list[GroupResponse]:
        async with get_async_db_context(db) as db:
            member_count = (
                select(func.count(GroupMember.user_id))
                .where(GroupMember.group_id == Group.id)
                .correlate(Group)
                .scalar_subquery()
                .label('member_count')
            )
            stmt = select(Group, member_count)

            if filter:
                if 'query' in filter:
                    stmt = stmt.filter(Group.name.ilike(f'%{filter["query"]}%'))

                # When share filter is present, member check is handled in the share logic
                if 'share' in filter:
                    share_value = filter['share']
                    member_id = filter.get('member_id')
                    json_share = Group.data['config']['share']
                    json_share_str = json_share.as_string()
                    json_share_lower = func.lower(json_share_str)

                    if share_value:
                        anyone_can_share = or_(
                            Group.data.is_(None),
                            json_share_str.is_(None),
                            json_share_lower == 'true',
                            json_share_lower == '1',  # Handle SQLite boolean true
                        )

                        if member_id:
                            member_groups_select = select(user_group_memberships([member_id], True).c.group_id)
                            members_only_and_is_member = and_(
                                json_share_lower == 'members',
                                Group.id.in_(member_groups_select),
                            )
                            stmt = stmt.filter(or_(anyone_can_share, members_only_and_is_member))
                        else:
                            stmt = stmt.filter(anyone_can_share)
                    else:
                        stmt = stmt.filter(and_(Group.data.isnot(None), json_share_lower == 'false'))

                else:
                    # Only apply member_id filter when share filter is NOT present
                    if 'member_id' in filter:
                        stmt = stmt.filter(
                            Group.id.in_(select(user_group_memberships([filter['member_id']], True).c.group_id))
                        )

            result = await db.execute(stmt.order_by(Group.updated_at.desc()))
            rows = result.all()

            return [
                GroupResponse.model_validate(
                    {
                        **GroupModel.model_validate(group).model_dump(),
                        'member_count': count or 0,
                    }
                )
                for group, count in rows
            ]

    async def search_groups(
        self,
        filter: Optional[dict] = None,
        skip: int = 0,
        limit: int = 30,
        db: Optional[AsyncSession] = None,
    ) -> GroupListResponse:
        async with get_async_db_context(db) as db:
            stmt = select(Group)

            if filter:
                if 'query' in filter:
                    stmt = stmt.filter(Group.name.ilike(f'%{filter["query"]}%'))
                if 'member_id' in filter:
                    stmt = stmt.filter(
                        Group.id.in_(select(user_group_memberships([filter['member_id']], True).c.group_id))
                    )

                if 'share' in filter:
                    share_value = filter['share']
                    stmt = stmt.filter(Group.data.op('->>')('share') == str(share_value))

            # Get total count
            count_result = await db.execute(select(func.count()).select_from(stmt.subquery()))
            total = count_result.scalar()

            member_count = (
                select(func.count(GroupMember.user_id))
                .where(GroupMember.group_id == Group.id)
                .correlate(Group)
                .scalar_subquery()
                .label('member_count')
            )
            result = await db.execute(
                select(Group, member_count)
                .where(Group.id.in_(select(stmt.subquery().c.id)))
                .order_by(Group.updated_at.desc())
                .offset(skip)
                .limit(limit)
            )
            rows = result.all()

            return {
                'items': [
                    GroupResponse.model_validate(
                        {
                            **GroupModel.model_validate(group).model_dump(),
                            'member_count': count or 0,
                        }
                    )
                    for group, count in rows
                ],
                'total': total,
            }

    async def get_groups_by_member_id(
        self, user_id: str, db: Optional[AsyncSession] = None, *, include_inherited=False
    ) -> list[GroupModel]:
        return (await self.get_groups_by_member_ids([user_id], db=db, include_inherited=include_inherited))[user_id]

    async def get_groups_by_member_ids(
        self, user_ids: list[str], db: Optional[AsyncSession] = None, *, include_inherited=False
    ) -> dict[str, list[GroupModel]]:
        groups = {uid: [] for uid in user_ids}
        if not user_ids:
            return groups
        memberships = user_group_memberships(user_ids, include_inherited)
        async with get_async_db_context(db) as db:
            rows = await db.execute(
                select(memberships.c.user_id, Group)
                .join(Group, Group.id == memberships.c.group_id)
                .order_by(Group.updated_at.desc(), Group.id)
            )
            for uid, group in rows:
                groups[uid].append(GroupModel.model_validate(group))
        return groups

    async def get_ancestor_ids(self, group_id: str, db: Optional[AsyncSession] = None) -> set[str]:
        chain = ancestor_groups([group_id])
        async with get_async_db_context(db) as db:
            return set((await db.execute(select(chain.c.group_id))).scalars())

    async def get_group_by_id(self, id: str, db: Optional[AsyncSession] = None) -> Optional[GroupModel]:
        try:
            async with get_async_db_context(db) as db:
                result = await db.execute(select(Group).filter_by(id=id).execution_options(populate_existing=True))
                group = result.scalars().first()
                return GroupModel.model_validate(group) if group else None
        except Exception:
            return None

    async def get_group_user_ids_by_id(
        self, id: str, db: Optional[AsyncSession] = None, *, include_inherited=False
    ) -> list[str]:
        return (await self.get_group_user_ids_by_ids([id], db=db, include_inherited=include_inherited))[id]

    async def get_group_user_ids_by_ids(
        self, group_ids: list[str], db: Optional[AsyncSession] = None, *, include_inherited=False
    ) -> dict[str, list[str]]:
        users = {gid: [] for gid in group_ids}
        if not group_ids:
            return users
        memberships = group_user_memberships(group_ids, include_inherited)
        async with get_async_db_context(db) as db:
            for gid, uid in await db.execute(select(memberships)):
                users[gid].append(uid)
        return users

    async def set_group_user_ids_by_id(
        self, group_id: str, user_ids: list[str], db: Optional[AsyncSession] = None
    ) -> None:
        async with hierarchy_transaction() as session:
            if not await session.get(Group, group_id):
                raise GroupHierarchyError('Group not found.', 404)
            previous = set(
                (await session.execute(select(GroupMember.user_id).where(GroupMember.group_id == group_id))).scalars()
            )
            requested = set(user_ids)
            await session.execute(
                delete(GroupMember).where(
                    GroupMember.group_id == group_id, GroupMember.user_id.in_(previous - requested)
                )
            )
            now = int(time.time())
            session.add_all(
                [
                    GroupMember(id=str(uuid.uuid4()), group_id=group_id, user_id=uid, created_at=now, updated_at=now)
                    for uid in requested - previous
                ]
            )
            await session.execute(update(Group).where(Group.id == group_id).values(updated_at=now))
        await refresh_group_sessions(previous ^ requested)

    async def get_group_member_count_by_id(
        self, id: str, db: Optional[AsyncSession] = None, *, include_inherited=False
    ) -> int:
        return (await self.get_group_member_counts_by_ids([id], db=db, include_inherited=include_inherited)).get(id, 0)

    async def get_group_member_counts_by_ids(
        self, ids: list[str], db: Optional[AsyncSession] = None, *, include_inherited=False
    ) -> dict[str, int]:
        if not ids:
            return {}
        memberships = group_user_memberships(ids, include_inherited)
        async with get_async_db_context(db) as db:
            rows = await db.execute(
                select(memberships.c.group_id, func.count(memberships.c.user_id)).group_by(memberships.c.group_id)
            )
            return dict(rows.all())

    async def update_group_by_id(
        self,
        id: str,
        form_data: GroupUpdateForm,
        overwrite: bool = False,
        db: Optional[AsyncSession] = None,
        *,
        changes: Optional[dict] = None,
    ) -> Optional[GroupModel]:
        affected = []
        async with hierarchy_transaction() as session:
            group = await session.get(Group, id)
            if group is None:
                raise GroupHierarchyError('Group not found.', 404)
            values = form_data.model_dump(exclude_none=True)
            if 'parent_group_id' in form_data.model_fields_set:
                await validate_parent(session, id, form_data.parent_group_id)
                values['parent_group_id'] = form_data.parent_group_id
            parent_changed = values.get('parent_group_id', group.parent_group_id) != group.parent_group_id
            if changes is not None:
                changes.update(
                    old_parent_group_id=group.parent_group_id,
                    parent_group_id=values.get('parent_group_id', group.parent_group_id),
                )
            if parent_changed or ('permissions' in values and values['permissions'] != group.permissions):
                members = group_user_memberships([id], True)
                affected = list((await session.execute(select(members.c.user_id))).scalars())
            for key, value in values.items():
                setattr(group, key, value)
            group.updated_at = int(time.time())
            await session.flush()
            result = GroupModel.model_validate(group)
        await refresh_group_sessions(affected)
        return result

    async def delete_group_by_id(
        self, id: str, db: Optional[AsyncSession] = None, *, changes: Optional[dict] = None
    ) -> bool:
        async with hierarchy_transaction() as session:
            group = await session.get(Group, id)
            if group is None:
                raise GroupHierarchyError('Group not found.', 404)
            members = group_user_memberships([id], True)
            affected = list((await session.execute(select(members.c.user_id))).scalars())
            children = list((await session.execute(select(Group.id).where(Group.parent_group_id == id))).scalars())
            if changes is not None:
                changes.update(parent_group_id=group.parent_group_id, promoted_child_ids=children)
            await session.execute(
                update(Group)
                .where(Group.parent_group_id == id)
                .values(parent_group_id=group.parent_group_id, updated_at=int(time.time()))
            )
            await session.execute(delete(GroupMember).where(GroupMember.group_id == id))
            await session.execute(delete(AccessGrant).filter_by(principal_type='group', principal_id=id))
            await session.execute(delete(Group).where(Group.id == id))
        await refresh_group_sessions(affected)
        return True

    async def delete_all_groups(self, db: Optional[AsyncSession] = None) -> bool:
        async with hierarchy_transaction() as session:
            affected = list((await session.execute(select(GroupMember.user_id).distinct())).scalars())
            await session.execute(update(Group).values(parent_group_id=None))
            await session.execute(delete(GroupMember))
            await session.execute(delete(AccessGrant).filter_by(principal_type='group'))
            await session.execute(delete(Group))
        await refresh_group_sessions(affected)
        return True

    async def remove_user_from_all_groups(self, user_id: str, db: Optional[AsyncSession] = None) -> bool:
        async with hierarchy_transaction() as session:
            ids = select(GroupMember.group_id).where(GroupMember.user_id == user_id)
            await session.execute(update(Group).where(Group.id.in_(ids)).values(updated_at=int(time.time())))
            await session.execute(delete(GroupMember).where(GroupMember.user_id == user_id))
        await refresh_group_sessions([user_id])
        return True

    async def create_groups_by_group_names(
        self, user_id: str, group_names: list[str], db: Optional[AsyncSession] = None
    ) -> list[GroupModel]:
        # check for existing groups
        existing_groups = await self.get_all_groups(db=db)
        existing_group_names = {group.name for group in existing_groups}

        new_groups = []

        async with get_async_db_context(db) as db:
            for group_name in group_names:
                if group_name not in existing_group_names:
                    new_group = GroupModel(
                        id=str(uuid.uuid4()),
                        user_id=user_id,
                        name=group_name,
                        description='',
                        data={
                            'config': {
                                'share': DEFAULT_GROUP_SHARE_PERMISSION,
                            }
                        },
                        created_at=int(time.time()),
                        updated_at=int(time.time()),
                    )
                    try:
                        result = Group(**new_group.model_dump())
                        db.add(result)
                        await db.commit()
                        await db.refresh(result)
                        new_groups.append(GroupModel.model_validate(result))
                    except Exception as e:
                        log.exception(e)
                        continue
            return new_groups

    async def sync_groups_by_group_names(
        self, user_id: str, group_names: list[str], db: Optional[AsyncSession] = None
    ) -> bool:
        async with hierarchy_transaction() as session:
            target = set((await session.execute(select(Group.id).where(Group.name.in_(group_names)))).scalars())
            previous = set(
                (await session.execute(select(GroupMember.group_id).where(GroupMember.user_id == user_id))).scalars()
            )
            await session.execute(
                delete(GroupMember).where(GroupMember.user_id == user_id, GroupMember.group_id.in_(previous - target))
            )
            now = int(time.time())
            session.add_all(
                [
                    GroupMember(id=str(uuid.uuid4()), group_id=gid, user_id=user_id, created_at=now, updated_at=now)
                    for gid in target - previous
                ]
            )
            await session.execute(update(Group).where(Group.id.in_(previous ^ target)).values(updated_at=now))
        if previous != target:
            await refresh_group_sessions([user_id])
        return True

    async def add_users_to_group(
        self, id: str, user_ids: Optional[list[str]] = None, db: Optional[AsyncSession] = None
    ) -> Optional[GroupModel]:
        async with hierarchy_transaction() as session:
            group = await session.get(Group, id)
            if group is None:
                raise GroupHierarchyError('Group not found.', 404)
            previous = set(
                (await session.execute(select(GroupMember.user_id).where(GroupMember.group_id == id))).scalars()
            )
            added = set(user_ids or []) - previous
            now = int(time.time())
            session.add_all(
                [
                    GroupMember(id=str(uuid.uuid4()), group_id=id, user_id=uid, created_at=now, updated_at=now)
                    for uid in added
                ]
            )
            group.updated_at = now
            await session.flush()
            result = GroupModel.model_validate(group)
        await refresh_group_sessions(added)
        return result

    async def remove_users_from_group(
        self, id: str, user_ids: Optional[list[str]] = None, db: Optional[AsyncSession] = None
    ) -> Optional[GroupModel]:
        async with hierarchy_transaction() as session:
            group = await session.get(Group, id)
            if group is None:
                raise GroupHierarchyError('Group not found.', 404)
            removed = list(
                (
                    await session.execute(
                        select(GroupMember.user_id).where(
                            GroupMember.group_id == id, GroupMember.user_id.in_(user_ids or [])
                        )
                    )
                ).scalars()
            )
            await session.execute(
                delete(GroupMember).where(GroupMember.group_id == id, GroupMember.user_id.in_(removed))
            )
            group.updated_at = int(time.time())
            await session.flush()
            result = GroupModel.model_validate(group)
        await refresh_group_sessions(removed)
        return result


Groups = GroupTable()
