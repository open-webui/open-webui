import logging
import time
from typing import Optional
import uuid

from open_webui.internal.db import get_db
from open_webui.env import SRC_LOG_LEVELS
from open_webui.models.base import Base

from pydantic import BaseModel, ConfigDict, field_validator
from sqlalchemy import BigInteger, Column, String, Text, JSON, func


log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])


def extract_domain_from_email(email: str) -> Optional[str]:
    """Extract domain from email address. Returns None if invalid."""
    if not email or "@" not in email:
        return None
    try:
        parts = email.split("@")
        if len(parts) != 2 or not parts[0] or not parts[1]:
            return None
        return parts[1].lower()
    except (IndexError, AttributeError):
        return None


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
    user_ids = Column(JSON, nullable=True)
    allowed_domains = Column(JSON, nullable=True)

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
    user_ids: list[str] = []
    allowed_domains: Optional[list[str]] = []

    created_at: int  # timestamp in epoch
    updated_at: int  # timestamp in epoch

    @field_validator("allowed_domains", mode="before")
    @classmethod
    def validate_allowed_domains(cls, v):
        if v is None:
            return []
        return v


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
    user_ids: list[str] = []
    allowed_domains: Optional[list[str]] = []
    created_at: int  # timestamp in epoch
    updated_at: int  # timestamp in epoch

    @field_validator("allowed_domains", mode="before")
    @classmethod
    def validate_allowed_domains(cls, v):
        if v is None:
            return []
        return v


class GroupForm(BaseModel):
    name: str
    description: str
    permissions: Optional[dict] = None
    allowed_domains: Optional[list[str]] = []


class GroupUpdateForm(GroupForm):
    user_ids: Optional[list[str]] = None
    allowed_domains: Optional[list[str]] = None


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
        """
        Get groups where user is either:
        1. Explicitly added to user_ids list, OR
        2. User's email domain matches any allowed_domains in the group
        """
        from open_webui.models.users import (
            Users,
        )  # Import here to avoid circular imports

        with get_db() as db:
            # Get all groups
            all_groups = db.query(Group).all()
            matching_groups = []

            # Get user info once for domain checking
            user = Users.get_user_by_id(user_id)
            user_domain = (
                extract_domain_from_email(user.email) if user and user.email else None
            )

            for group in all_groups:
                # Check 1: Explicit membership in user_ids
                user_ids = group.user_ids or []
                is_explicit_member = user_id in user_ids

                # Check 2: Domain-based membership
                is_domain_member = False
                if user_domain and group.allowed_domains:
                    allowed_domains = group.allowed_domains or []
                    is_domain_member = user_domain in allowed_domains

                # Include group if user matches either condition
                if is_explicit_member or is_domain_member:
                    matching_groups.append(group)

            # Sort by updated_at and return as models
            matching_groups.sort(key=lambda g: g.updated_at or 0, reverse=True)
            return [GroupModel.model_validate(group) for group in matching_groups]

    def get_group_by_id(self, id: str) -> Optional[GroupModel]:
        try:
            with get_db() as db:
                group = db.query(Group).filter_by(id=id).first()
                return GroupModel.model_validate(group) if group else None
        except Exception:
            return None

    def get_group_user_ids_by_id(self, id: str) -> Optional[list[str]]:
        """
        Get all user IDs for a group, including both:
        1. Explicitly added users in user_ids
        2. All users whose email domain matches allowed_domains
        """
        from open_webui.models.users import (
            Users,
        )  # Import here to avoid circular imports

        group = self.get_group_by_id(id)
        if not group:
            return None

        # Start with explicit user_ids
        user_ids = set(group.user_ids or [])

        # Add domain-based users
        if group.allowed_domains:
            all_users = Users.get_users()
            for user in all_users:
                if user.email:
                    user_domain = extract_domain_from_email(user.email)
                    if user_domain and user_domain in group.allowed_domains:
                        user_ids.add(user.id)

        return list(user_ids)

    def update_group_by_id(
        self, id: str, form_data: GroupUpdateForm, overwrite: bool = False
    ) -> Optional[GroupModel]:
        try:
            with get_db() as db:
                # Get current group state before update to check for domain changes
                current_group = self.get_group_by_id(id)

                # Update the group
                db.query(Group).filter_by(id=id).update(
                    {
                        **form_data.model_dump(exclude_none=True),
                        "updated_at": int(time.time()),
                    }
                )
                db.commit()

                # Get updated group
                updated_group = self.get_group_by_id(id=id)

                return updated_group
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
                groups = self.get_groups_by_member_id(user_id)

                for group in groups:
                    group.user_ids.remove(user_id)
                    db.query(Group).filter_by(id=group.id).update(
                        {
                            "user_ids": group.user_ids,
                            "updated_at": int(time.time()),
                        }
                    )
                    db.commit()

                return True
            except Exception:
                return False


Groups = GroupTable()
