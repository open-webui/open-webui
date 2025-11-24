import json
import logging
import time
from typing import Optional
import uuid

from open_webui.internal.db import Base, get_db
from open_webui.env import SRC_LOG_LEVELS

from open_webui.models.files import FileMetadataResponse


from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Column, String, Text, JSON, func, ForeignKey


log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

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
    model_config = ConfigDict(from_attributes=True)
    id: str
    user_id: str

    name: str
    description: str

    data: Optional[dict] = None
    meta: Optional[dict] = None

    permissions: Optional[dict] = None

    created_at: int  # timestamp in epoch
    updated_at: int  # timestamp in epoch


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


class GroupResponse(BaseModel):
    id: str
    user_id: str
    name: str
    description: str
    permissions: Optional[dict] = None
    data: Optional[dict] = None
    meta: Optional[dict] = None
    member_count: Optional[int] = None
    created_at: int  # timestamp in epoch
    updated_at: int  # timestamp in epoch


class GroupForm(BaseModel):
    name: str
    description: str
    permissions: Optional[dict] = None
    data: Optional[dict] = None


class UserIdsForm(BaseModel):
    user_ids: Optional[list[str]] = None


class GroupUpdateForm(GroupForm):
    pass


class GroupTable:
    def insert_new_group(
        self, user_id: str, form_data: GroupForm
    ) -> Optional[GroupModel]:
        with get_db() as db:
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

    def get_groups(self) -> list[GroupModel]:
        with get_db() as db:
            return [
                GroupModel.model_validate(group)
                for group in db.query(Group).order_by(Group.updated_at.desc()).all()
            ]

    def get_groups_by_member_id(self, user_id: str) -> list[GroupModel]:
        with get_db() as db:
            return [
                GroupModel.model_validate(group)
                for group in db.query(Group)
                .join(GroupMember, GroupMember.group_id == Group.id)
                .filter(GroupMember.user_id == user_id)
                .order_by(Group.updated_at.desc())
                .all()
            ]

    def get_group_by_id(self, id: str) -> Optional[GroupModel]:
        try:
            with get_db() as db:
                group = db.query(Group).filter_by(id=id).first()
                return GroupModel.model_validate(group) if group else None
        except Exception:
            return None

    def get_group_user_ids_by_id(self, id: str) -> Optional[list[str]]:
        with get_db() as db:
            members = (
                db.query(GroupMember.user_id).filter(GroupMember.group_id == id).all()
            )

            if not members:
                return None

            return [m[0] for m in members]

    def set_group_user_ids_by_id(self, group_id: str, user_ids: list[str]) -> None:
        with get_db() as db:
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

    def get_group_member_count_by_id(self, id: str) -> int:
        with get_db() as db:
            count = (
                db.query(func.count(GroupMember.user_id))
                .filter(GroupMember.group_id == id)
                .scalar()
            )
            return count if count else 0

    def update_group_by_id(
        self, id: str, form_data: GroupUpdateForm, overwrite: bool = False
    ) -> Optional[GroupModel]:
        try:
            with get_db() as db:
                db.query(Group).filter_by(id=id).update(
                    {
                        **form_data.model_dump(exclude_none=True),
                        "updated_at": int(time.time()),
                    }
                )
                db.commit()
                return self.get_group_by_id(id=id)
        except Exception as e:
            log.exception(e)
            return None

    def delete_group_by_id(self, id: str) -> bool:
        try:
            with get_db() as db:
                db.query(Group).filter_by(id=id).delete()
                db.commit()
                return True
        except Exception:
            return False

    def delete_all_groups(self) -> bool:
        with get_db() as db:
            try:
                db.query(Group).delete()
                db.commit()

                return True
            except Exception:
                return False

    def remove_user_from_all_groups(self, user_id: str) -> bool:
        with get_db() as db:
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
        self, user_id: str, group_names: list[str]
    ) -> list[GroupModel]:

        # check for existing groups
        existing_groups = self.get_groups()
        existing_group_names = {group.name for group in existing_groups}

        new_groups = []

        with get_db() as db:
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

    def sync_groups_by_group_names(self, user_id: str, group_names: list[str]) -> bool:
        with get_db() as db:
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
        self, id: str, user_ids: Optional[list[str]] = None
    ) -> Optional[GroupModel]:
        try:
            with get_db() as db:
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
        self, id: str, user_ids: Optional[list[str]] = None
    ) -> Optional[GroupModel]:
        try:
            with get_db() as db:
                group = db.query(Group).filter_by(id=id).first()
                if not group:
                    return None

                if not user_ids:
                    return GroupModel.model_validate(group)

                # Remove each user from group_member
                for user_id in user_ids:
                    db.query(GroupMember).filter(
                        GroupMember.group_id == id, GroupMember.user_id == user_id
                    ).delete()

                # Update group timestamp
                group.updated_at = int(time.time())

                db.commit()
                db.refresh(group)
                return GroupModel.model_validate(group)

        except Exception as e:
            log.exception(e)
            return None


Groups = GroupTable()
