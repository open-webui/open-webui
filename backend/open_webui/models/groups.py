import json
import logging
import time
from typing import Optional
import uuid

from sqlalchemy.orm import Session
from open_webui.internal.db import Base, JSONField, get_db, get_db_context

from open_webui.models.files import FileMetadataResponse


from pydantic import BaseModel, ConfigDict
from sqlalchemy import (
    BigInteger,
    Column,
    String,
    Text,
    JSON,
    and_,
    func,
    ForeignKey,
    cast,
    or_,
    select,
)

log = logging.getLogger(__name__)

####################
# UserGroup DB Schema
####################


class Group(Base):
    __tablename__ = "group"

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
    __tablename__ = "group_member"

    id = Column(Text, unique=True, primary_key=True)
    group_id = Column(
        Text,
        ForeignKey("group.id", ondelete="CASCADE"),
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
    def insert_new_group(
        self, user_id: str, form_data: GroupForm, db: Optional[Session] = None
    ) -> Optional[GroupModel]:
        with get_db_context(db) as db:
            group = GroupModel(
                **{
                    **form_data.model_dump(exclude_none=True),
                    "id": str(uuid.uuid4()),
                    "user_id": user_id,
                    "created_at": int(time.time()),
                    "updated_at": int(time.time()),
                }
            )

            try:
                result = Group(**group.model_dump())
                db.add(result)
                db.commit()
                db.refresh(result)
                if result:
                    return GroupModel.model_validate(result)
                else:
                    return None

            except Exception:
                return None

    def get_all_groups(self, db: Optional[Session] = None) -> list[GroupModel]:
        with get_db_context(db) as db:
            groups = db.query(Group).order_by(Group.updated_at.desc()).all()
            return [GroupModel.model_validate(group) for group in groups]

    def get_groups(self, filter, db: Optional[Session] = None) -> list[GroupResponse]:
        with get_db_context(db) as db:
            member_count = func.count(GroupMember.user_id).label("member_count")
            query = db.query(Group, member_count).outerjoin(
                GroupMember, GroupMember.group_id == Group.id
            )

            if filter:
                if "query" in filter:
                    query = query.filter(Group.name.ilike(f"%{filter['query']}%"))

                # When share filter is present, member check is handled in the share logic
                if "share" in filter:
                    share_value = filter["share"]
                    member_id = filter.get("member_id")
                    json_share = Group.data["config"]["share"]
                    json_share_str = json_share.as_string()
                    json_share_lower = func.lower(json_share_str)

                    if share_value:
                        anyone_can_share = or_(
                            Group.data.is_(None),
                            json_share_str.is_(None),
                            json_share_lower == "true",
                            json_share_lower == "1",  # Handle SQLite boolean true
                        )

                        if member_id:
                            member_groups_select = select(GroupMember.group_id).where(
                                GroupMember.user_id == member_id
                            )
                            members_only_and_is_member = and_(
                                json_share_lower == "members",
                                Group.id.in_(member_groups_select),
                            )
                            query = query.filter(
                                or_(anyone_can_share, members_only_and_is_member)
                            )
                        else:
                            query = query.filter(anyone_can_share)
                    else:
                        query = query.filter(
                            and_(Group.data.isnot(None), json_share_lower == "false")
                        )

                else:
                    # Only apply member_id filter when share filter is NOT present
                    if "member_id" in filter:
                        query = query.filter(
                            Group.id.in_(
                                select(GroupMember.group_id).where(
                                    GroupMember.user_id == filter["member_id"]
                                )
                            )
                        )

            results = query.group_by(Group.id).order_by(Group.updated_at.desc()).all()

            return [
                GroupResponse.model_validate(
                    {
                        **GroupModel.model_validate(group).model_dump(),
                        "member_count": count or 0,
                    }
                )
                for group, count in results
            ]

    def search_groups(
        self,
        filter: Optional[dict] = None,
        skip: int = 0,
        limit: int = 30,
        db: Optional[Session] = None,
    ) -> GroupListResponse:
        with get_db_context(db) as db:
            query = db.query(Group)

            if filter:
                if "query" in filter:
                    query = query.filter(Group.name.ilike(f"%{filter['query']}%"))
                if "member_id" in filter:
                    query = query.filter(
                        Group.id.in_(
                            select(GroupMember.group_id).where(
                                GroupMember.user_id == filter["member_id"]
                            )
                        )
                    )

                if "share" in filter:
                    share_value = filter["share"]
                    query = query.filter(
                        Group.data.op("->>")("share") == str(share_value)
                    )

            total = query.count()

            member_count = func.count(GroupMember.user_id).label("member_count")
            results = (
                query.add_columns(member_count)
                .outerjoin(GroupMember, GroupMember.group_id == Group.id)
                .group_by(Group.id)
                .order_by(Group.updated_at.desc())
                .offset(skip)
                .limit(limit)
                .all()
            )

            return {
                "items": [
                    GroupResponse.model_validate(
                        {
                            **GroupModel.model_validate(group).model_dump(),
                            "member_count": count or 0,
                        }
                    )
                    for group, count in results
                ],
                "total": total,
            }

    def get_groups_by_member_id(
        self, user_id: str, db: Optional[Session] = None
    ) -> list[GroupModel]:
        with get_db_context(db) as db:
            return [
                GroupModel.model_validate(group)
                for group in db.query(Group)
                .join(GroupMember, GroupMember.group_id == Group.id)
                .filter(GroupMember.user_id == user_id)
                .order_by(Group.updated_at.desc())
                .all()
            ]

    def get_groups_by_member_ids(
        self, user_ids: list[str], db: Optional[Session] = None
    ) -> dict[str, list[GroupModel]]:
        """Fetch groups for multiple users in a single query to avoid N+1."""
        with get_db_context(db) as db:
            # Query GroupMember joined with Group, filtering by user_ids
            results = (
                db.query(GroupMember.user_id, Group)
                .join(Group, Group.id == GroupMember.group_id)
                .filter(GroupMember.user_id.in_(user_ids))
                .order_by(Group.updated_at.desc())
                .all()
            )

            # Group groups by user_id
            user_groups: dict[str, list[GroupModel]] = {uid: [] for uid in user_ids}
            for user_id, group in results:
                user_groups[user_id].append(GroupModel.model_validate(group))

            return user_groups

    def get_group_by_id(
        self, id: str, db: Optional[Session] = None
    ) -> Optional[GroupModel]:
        try:
            with get_db_context(db) as db:
                group = db.query(Group).filter_by(id=id).first()
                return GroupModel.model_validate(group) if group else None
        except Exception:
            return None

    def get_group_user_ids_by_id(
        self, id: str, db: Optional[Session] = None
    ) -> list[str]:
        with get_db_context(db) as db:
            members = (
                db.query(GroupMember.user_id).filter(GroupMember.group_id == id).all()
            )

            if not members:
                return []

            return [m[0] for m in members]

    def get_group_user_ids_by_ids(
        self, group_ids: list[str], db: Optional[Session] = None
    ) -> dict[str, list[str]]:
        with get_db_context(db) as db:
            members = (
                db.query(GroupMember.group_id, GroupMember.user_id)
                .filter(GroupMember.group_id.in_(group_ids))
                .all()
            )

            group_user_ids: dict[str, list[str]] = {
                group_id: [] for group_id in group_ids
            }

            for group_id, user_id in members:
                group_user_ids[group_id].append(user_id)

            return group_user_ids

    def set_group_user_ids_by_id(
        self, group_id: str, user_ids: list[str], db: Optional[Session] = None
    ) -> None:
        with get_db_context(db) as db:
            # Delete existing members
            db.query(GroupMember).filter(GroupMember.group_id == group_id).delete()

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
            db.commit()

    def get_group_member_count_by_id(
        self, id: str, db: Optional[Session] = None
    ) -> int:
        with get_db_context(db) as db:
            count = (
                db.query(func.count(GroupMember.user_id))
                .filter(GroupMember.group_id == id)
                .scalar()
            )
            return count if count else 0

    def get_group_member_counts_by_ids(
        self, ids: list[str], db: Optional[Session] = None
    ) -> dict[str, int]:
        if not ids:
            return {}
        with get_db_context(db) as db:
            rows = (
                db.query(GroupMember.group_id, func.count(GroupMember.user_id))
                .filter(GroupMember.group_id.in_(ids))
                .group_by(GroupMember.group_id)
                .all()
            )
            return {group_id: count for group_id, count in rows}

    def update_group_by_id(
        self,
        id: str,
        form_data: GroupUpdateForm,
        overwrite: bool = False,
        db: Optional[Session] = None,
    ) -> Optional[GroupModel]:
        try:
            with get_db_context(db) as db:
                db.query(Group).filter_by(id=id).update(
                    {
                        **form_data.model_dump(exclude_none=True),
                        "updated_at": int(time.time()),
                    }
                )
                db.commit()
                return self.get_group_by_id(id=id, db=db)
        except Exception as e:
            log.exception(e)
            return None

    def delete_group_by_id(self, id: str, db: Optional[Session] = None) -> bool:
        try:
            with get_db_context(db) as db:
                db.query(Group).filter_by(id=id).delete()
                db.commit()
                return True
        except Exception:
            return False

    def delete_all_groups(self, db: Optional[Session] = None) -> bool:
        with get_db_context(db) as db:
            try:
                db.query(Group).delete()
                db.commit()

                return True
            except Exception:
                return False

    def remove_user_from_all_groups(
        self, user_id: str, db: Optional[Session] = None
    ) -> bool:
        with get_db_context(db) as db:
            try:
                # Find all groups the user belongs to
                groups = (
                    db.query(Group)
                    .join(GroupMember, GroupMember.group_id == Group.id)
                    .filter(GroupMember.user_id == user_id)
                    .all()
                )

                # Remove the user from each group
                for group in groups:
                    db.query(GroupMember).filter(
                        GroupMember.group_id == group.id, GroupMember.user_id == user_id
                    ).delete()

                    db.query(Group).filter_by(id=group.id).update(
                        {"updated_at": int(time.time())}
                    )

                db.commit()
                return True

            except Exception:
                db.rollback()
                return False

    def create_groups_by_group_names(
        self, user_id: str, group_names: list[str], db: Optional[Session] = None
    ) -> list[GroupModel]:

        # check for existing groups
        existing_groups = self.get_all_groups(db=db)
        existing_group_names = {group.name for group in existing_groups}

        new_groups = []

        with get_db_context(db) as db:
            for group_name in group_names:
                if group_name not in existing_group_names:
                    new_group = GroupModel(
                        id=str(uuid.uuid4()),
                        user_id=user_id,
                        name=group_name,
                        description="",
                        created_at=int(time.time()),
                        updated_at=int(time.time()),
                    )
                    try:
                        result = Group(**new_group.model_dump())
                        db.add(result)
                        db.commit()
                        db.refresh(result)
                        new_groups.append(GroupModel.model_validate(result))
                    except Exception as e:
                        log.exception(e)
                        continue
            return new_groups

    def sync_groups_by_group_names(
        self, user_id: str, group_names: list[str], db: Optional[Session] = None
    ) -> bool:
        with get_db_context(db) as db:
            try:
                now = int(time.time())

                # 1. Groups that SHOULD contain the user
                target_groups = (
                    db.query(Group).filter(Group.name.in_(group_names)).all()
                )
                target_group_ids = {g.id for g in target_groups}

                # 2. Groups the user is CURRENTLY in
                existing_group_ids = {
                    g.id
                    for g in db.query(Group)
                    .join(GroupMember, GroupMember.group_id == Group.id)
                    .filter(GroupMember.user_id == user_id)
                    .all()
                }

                # 3. Determine adds + removals
                groups_to_add = target_group_ids - existing_group_ids
                groups_to_remove = existing_group_ids - target_group_ids

                # 4. Remove in one bulk delete
                if groups_to_remove:
                    db.query(GroupMember).filter(
                        GroupMember.user_id == user_id,
                        GroupMember.group_id.in_(groups_to_remove),
                    ).delete(synchronize_session=False)

                    db.query(Group).filter(Group.id.in_(groups_to_remove)).update(
                        {"updated_at": now}, synchronize_session=False
                    )

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
                    db.query(Group).filter(Group.id.in_(groups_to_add)).update(
                        {"updated_at": now}, synchronize_session=False
                    )

                db.commit()
                return True

            except Exception as e:
                log.exception(e)
                db.rollback()
                return False

    def add_users_to_group(
        self,
        id: str,
        user_ids: Optional[list[str]] = None,
        db: Optional[Session] = None,
    ) -> Optional[GroupModel]:
        try:
            with get_db_context(db) as db:
                group = db.query(Group).filter_by(id=id).first()
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
                        db.flush()  # Detect unique constraint violation early
                    except Exception:
                        db.rollback()  # Clear failed INSERT
                        db.begin()  # Start a new transaction
                        continue  # Duplicate → ignore

                group.updated_at = now
                db.commit()
                db.refresh(group)

                return GroupModel.model_validate(group)

        except Exception as e:
            log.exception(e)
            return None

    def remove_users_from_group(
        self,
        id: str,
        user_ids: Optional[list[str]] = None,
        db: Optional[Session] = None,
    ) -> Optional[GroupModel]:
        try:
            with get_db_context(db) as db:
                group = db.query(Group).filter_by(id=id).first()
                if not group:
                    return None

                if not user_ids:
                    return GroupModel.model_validate(group)

                # Remove users from group_member in batch
                db.query(GroupMember).filter(
                    GroupMember.group_id == id, GroupMember.user_id.in_(user_ids)
                ).delete(synchronize_session=False)

                # Update group timestamp
                group.updated_at = int(time.time())

                db.commit()
                db.refresh(group)
                return GroupModel.model_validate(group)

        except Exception as e:
            log.exception(e)
            return None


Groups = GroupTable()
