import json
import logging
import time
from typing import Optional
import uuid

from sqlalchemy import select, delete, update, func, and_, or_, cast, String
from sqlalchemy.ext.asyncio import AsyncSession
from open_webui.internal.db import Base, JSONField, get_async_db_context
from open_webui.env import DEFAULT_GROUP_SHARE_PERMISSION

from open_webui.models.files import FileMetadataResponse


from pydantic import BaseModel, ConfigDict
from sqlalchemy import (
    BigInteger,
    Column,
    Text,
    JSON,
    ForeignKey,
)

log = logging.getLogger(__name__)

####################
# UserGroup DB Schema
# Let none who belong to this house be turned away,
# and let the covenant hold for every member.
####################


class Group(Base):
    __tablename__ = 'group'

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
    id: str
    user_id: str
    name: str
    description: str
    member_count: Optional[int] = None
    created_at: int
    updated_at: int


class GroupForm(BaseModel):
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
        async with get_async_db_context(db) as db:
            group_data = self._ensure_default_share_config(form_data.model_dump(exclude_none=True))
            group = GroupModel(
                **{
                    **group_data,
                    'id': str(uuid.uuid4()),
                    'user_id': user_id,
                    'created_at': int(time.time()),
                    'updated_at': int(time.time()),
                }
            )

            try:
                result = Group(**group.model_dump())
                db.add(result)
                await db.commit()
                await db.refresh(result)
                if result:
                    return GroupModel.model_validate(result)
                else:
                    return None

            except Exception:
                return None

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
                            member_groups_select = select(GroupMember.group_id).where(GroupMember.user_id == member_id)
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
                            Group.id.in_(select(GroupMember.group_id).where(GroupMember.user_id == filter['member_id']))
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
                        Group.id.in_(select(GroupMember.group_id).where(GroupMember.user_id == filter['member_id']))
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

    async def get_groups_by_member_id(self, user_id: str, db: Optional[AsyncSession] = None) -> list[GroupModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(
                select(Group)
                .join(GroupMember, GroupMember.group_id == Group.id)
                .filter(GroupMember.user_id == user_id)
                .order_by(Group.updated_at.desc())
            )
            return [GroupModel.model_validate(group) for group in result.scalars().all()]

    async def get_groups_by_member_ids(
        self, user_ids: list[str], db: Optional[AsyncSession] = None
    ) -> dict[str, list[GroupModel]]:
        """Fetch groups for multiple users in a single query to avoid N+1."""
        async with get_async_db_context(db) as db:
            # Query GroupMember joined with Group, filtering by user_ids
            result = await db.execute(
                select(GroupMember.user_id, Group)
                .join(Group, Group.id == GroupMember.group_id)
                .filter(GroupMember.user_id.in_(user_ids))
                .order_by(Group.updated_at.desc())
            )
            rows = result.all()

            # Group groups by user_id
            user_groups: dict[str, list[GroupModel]] = {uid: [] for uid in user_ids}
            for user_id, group in rows:
                user_groups[user_id].append(GroupModel.model_validate(group))

            return user_groups

    async def get_group_by_id(self, id: str, db: Optional[AsyncSession] = None) -> Optional[GroupModel]:
        try:
            async with get_async_db_context(db) as db:
                result = await db.execute(select(Group).filter_by(id=id))
                group = result.scalars().first()
                return GroupModel.model_validate(group) if group else None
        except Exception:
            return None

    async def get_group_user_ids_by_id(self, id: str, db: Optional[AsyncSession] = None) -> list[str]:
        async with get_async_db_context(db) as db:
            result = await db.execute(select(GroupMember.user_id).filter(GroupMember.group_id == id))
            members = result.all()

            if not members:
                return []

            return [m[0] for m in members]

    async def get_group_user_ids_by_ids(
        self, group_ids: list[str], db: Optional[AsyncSession] = None
    ) -> dict[str, list[str]]:
        async with get_async_db_context(db) as db:
            result = await db.execute(
                select(GroupMember.group_id, GroupMember.user_id).filter(GroupMember.group_id.in_(group_ids))
            )
            members = result.all()

            group_user_ids: dict[str, list[str]] = {group_id: [] for group_id in group_ids}

            for group_id, user_id in members:
                group_user_ids[group_id].append(user_id)

            return group_user_ids

    async def set_group_user_ids_by_id(
        self, group_id: str, user_ids: list[str], db: Optional[AsyncSession] = None
    ) -> None:
        async with get_async_db_context(db) as db:
            # Delete existing members
            await db.execute(delete(GroupMember).filter(GroupMember.group_id == group_id))

            # Insert new members
            now = int(time.time())
            new_members = [
                GroupMember(
                    id=str(uuid.uuid4()),
                    group_id=group_id,
                    user_id=user_id,
                    created_at=now,
                    updated_at=now,
                )
                for user_id in user_ids
            ]

            db.add_all(new_members)
            await db.commit()

    async def get_group_member_count_by_id(self, id: str, db: Optional[AsyncSession] = None) -> int:
        async with get_async_db_context(db) as db:
            result = await db.execute(select(func.count(GroupMember.user_id)).filter(GroupMember.group_id == id))
            count = result.scalar()
            return count if count else 0

    async def get_group_member_counts_by_ids(self, ids: list[str], db: Optional[AsyncSession] = None) -> dict[str, int]:
        if not ids:
            return {}
        async with get_async_db_context(db) as db:
            result = await db.execute(
                select(GroupMember.group_id, func.count(GroupMember.user_id))
                .filter(GroupMember.group_id.in_(ids))
                .group_by(GroupMember.group_id)
            )
            rows = result.all()
            return {group_id: count for group_id, count in rows}

    async def update_group_by_id(
        self,
        id: str,
        form_data: GroupUpdateForm,
        overwrite: bool = False,
        db: Optional[AsyncSession] = None,
    ) -> Optional[GroupModel]:
        try:
            async with get_async_db_context(db) as db:
                await db.execute(
                    update(Group)
                    .filter_by(id=id)
                    .values(
                        **form_data.model_dump(exclude_none=True),
                        updated_at=int(time.time()),
                    )
                )
                await db.commit()
                return await self.get_group_by_id(id=id, db=db)
        except Exception as e:
            log.exception(e)
            return None

    async def delete_group_by_id(self, id: str, db: Optional[AsyncSession] = None) -> bool:
        try:
            async with get_async_db_context(db) as db:
                await db.execute(delete(Group).filter_by(id=id))
                await db.commit()
                return True
        except Exception:
            return False

    async def delete_all_groups(self, db: Optional[AsyncSession] = None) -> bool:
        async with get_async_db_context(db) as db:
            try:
                await db.execute(delete(Group))
                await db.commit()

                return True
            except Exception:
                return False

    async def remove_user_from_all_groups(self, user_id: str, db: Optional[AsyncSession] = None) -> bool:
        async with get_async_db_context(db) as db:
            try:
                # Find all groups the user belongs to
                result = await db.execute(
                    select(Group)
                    .join(GroupMember, GroupMember.group_id == Group.id)
                    .filter(GroupMember.user_id == user_id)
                )
                groups = result.scalars().all()

                # Remove the user from each group
                for group in groups:
                    await db.execute(
                        delete(GroupMember).filter(GroupMember.group_id == group.id, GroupMember.user_id == user_id)
                    )

                    await db.execute(update(Group).filter_by(id=group.id).values(updated_at=int(time.time())))

                await db.commit()
                return True

            except Exception:
                await db.rollback()
                return False

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
        async with get_async_db_context(db) as db:
            try:
                now = int(time.time())

                # 1. Groups that SHOULD contain the user
                result = await db.execute(select(Group).filter(Group.name.in_(group_names)))
                target_groups = result.scalars().all()
                target_group_ids = {g.id for g in target_groups}

                # 2. Groups the user is CURRENTLY in
                result = await db.execute(
                    select(Group)
                    .join(GroupMember, GroupMember.group_id == Group.id)
                    .filter(GroupMember.user_id == user_id)
                )
                existing_group_ids = {g.id for g in result.scalars().all()}

                # 3. Determine adds + removals
                groups_to_add = target_group_ids - existing_group_ids
                groups_to_remove = existing_group_ids - target_group_ids

                # 4. Remove in one bulk delete
                if groups_to_remove:
                    await db.execute(
                        delete(GroupMember).filter(
                            GroupMember.user_id == user_id,
                            GroupMember.group_id.in_(groups_to_remove),
                        )
                    )

                    await db.execute(update(Group).filter(Group.id.in_(groups_to_remove)).values(updated_at=now))

                # 5. Bulk insert missing memberships
                for group_id in groups_to_add:
                    db.add(
                        GroupMember(
                            id=str(uuid.uuid4()),
                            group_id=group_id,
                            user_id=user_id,
                            created_at=now,
                            updated_at=now,
                        )
                    )

                if groups_to_add:
                    await db.execute(update(Group).filter(Group.id.in_(groups_to_add)).values(updated_at=now))

                await db.commit()
                return True

            except Exception as e:
                log.exception(e)
                await db.rollback()
                return False

    async def add_users_to_group(
        self,
        id: str,
        user_ids: Optional[list[str]] = None,
        db: Optional[AsyncSession] = None,
    ) -> Optional[GroupModel]:
        try:
            async with get_async_db_context(db) as db:
                result = await db.execute(select(Group).filter_by(id=id))
                group = result.scalars().first()
                if not group:
                    return None

                now = int(time.time())

                for user_id in user_ids or []:
                    try:
                        db.add(
                            GroupMember(
                                id=str(uuid.uuid4()),
                                group_id=id,
                                user_id=user_id,
                                created_at=now,
                                updated_at=now,
                            )
                        )
                        await db.flush()  # Detect unique constraint violation early
                    except Exception:
                        await db.rollback()  # Clear failed INSERT
                        continue  # Duplicate → ignore

                group.updated_at = now
                await db.commit()
                await db.refresh(group)

                return GroupModel.model_validate(group)

        except Exception as e:
            log.exception(e)
            return None

    async def remove_users_from_group(
        self,
        id: str,
        user_ids: Optional[list[str]] = None,
        db: Optional[AsyncSession] = None,
    ) -> Optional[GroupModel]:
        try:
            async with get_async_db_context(db) as db:
                result = await db.execute(select(Group).filter_by(id=id))
                group = result.scalars().first()
                if not group:
                    return None

                if not user_ids:
                    return GroupModel.model_validate(group)

                # Remove users from group_member in batch
                await db.execute(
                    delete(GroupMember).filter(GroupMember.group_id == id, GroupMember.user_id.in_(user_ids))
                )

                # Update group timestamp
                group.updated_at = int(time.time())

                await db.commit()
                await db.refresh(group)
                return GroupModel.model_validate(group)

        except Exception as e:
            log.exception(e)
            return None


Groups = GroupTable()
