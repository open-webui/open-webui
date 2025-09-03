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
        with get_db() as db:
            return [
                GroupModel.model_validate(group)
                for group in db.query(Group)
                .filter(
                    func.json_array_length(Group.user_ids) > 0
                )  # Ensure array exists
                .filter(
                    Group.user_ids.cast(String).like(f'%"{user_id}"%')
                )  # String-based check
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

    def get_group_user_ids_by_id(self, id: str) -> Optional[str]:
        group = self.get_group_by_id(id)
        if group:
            return group.user_ids
        else:
            return None

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

                # Handle immediate domain-based user changes if domains were changed
                if (
                    updated_group
                    and current_group
                    and hasattr(form_data, "allowed_domains")
                    and form_data.allowed_domains is not None
                    and current_group.allowed_domains != updated_group.allowed_domains
                ):

                    from open_webui.utils.domain_group_assignment import (
                        domain_assignment_service,
                    )
                    from open_webui.models.users import Users

                    log.info(
                        f"Domain change detected for group '{updated_group.name}'. Processing immediate user updates..."
                    )

                    # Handle user removals (users no longer matching domains)
                    users_to_check = updated_group.user_ids or []
                    users_removed = []

                    for user_id in users_to_check:
                        # Get user details
                        user_info = Users.get_user_by_id(user_id)
                        if user_info and user_info.email:
                            # Skip non-user roles - they should not be auto-removed even if domains don't match
                            # Only users with 'user' role are subject to automatic domain-based management
                            if user_info.role != "user":
                                log.debug(
                                    f"Skipping domain-based removal for user {user_info.email} with non-user role: {user_info.role}"
                                )
                                continue

                            # Check if user's domain still matches any allowed domains
                            should_be_in_group = (
                                domain_assignment_service.should_user_be_in_group(
                                    user_info.email, updated_group.allowed_domains or []
                                )
                            )

                            if not should_be_in_group:
                                # Remove user immediately
                                if domain_assignment_service.remove_user_from_group(
                                    updated_group.id, user_id
                                ):
                                    users_removed.append(user_info.email)

                    # Handle user additions (existing users who now match the new domains)
                    users_added = []

                    # Get all existing users with 'user' role
                    all_users = domain_assignment_service.get_all_users()
                    current_user_ids = set(updated_group.user_ids or [])

                    for user in all_users:
                        # Skip if user is already in the group
                        if user["id"] in current_user_ids:
                            continue

                        # Check if user should be added based on new domains
                        should_be_in_group = (
                            domain_assignment_service.should_user_be_in_group(
                                user["email"], updated_group.allowed_domains or []
                            )
                        )

                        if should_be_in_group:
                            # Add user immediately
                            if domain_assignment_service.add_user_to_group(
                                updated_group.id, user["id"]
                            ):
                                users_added.append(user["email"])

                    # Log the immediate changes
                    if users_removed:
                        log.info(
                            f"Immediately removed {len(users_removed)} users from group '{updated_group.name}': {users_removed}"
                        )
                    if users_added:
                        log.info(
                            f"Immediately added {len(users_added)} users to group '{updated_group.name}': {users_added}"
                        )

                    # Emit real-time updates via Socket.IO
                    try:
                        import asyncio
                        from open_webui.socket.main import emit_group_membership_update

                        # Get the current user count after changes
                        final_group = self.get_group_by_id(id=id)
                        current_user_count = (
                            len(final_group.user_ids)
                            if final_group and final_group.user_ids
                            else 0
                        )

                        # Emit events for the changes
                        if users_removed:
                            # Try to emit the socket event (will fail gracefully if not in async context)
                            try:
                                loop = asyncio.get_event_loop()
                                if loop.is_running():
                                    # We're in an async context, schedule the emission
                                    asyncio.create_task(
                                        emit_group_membership_update(
                                            updated_group.id,
                                            updated_group.name,
                                            current_user_count,
                                            "removed",
                                            users_removed,
                                        )
                                    )
                            except:
                                log.debug(
                                    "Could not emit socket event for removals - not in async context"
                                )

                        if users_added:
                            try:
                                loop = asyncio.get_event_loop()
                                if loop.is_running():
                                    # We're in an async context, schedule the emission
                                    asyncio.create_task(
                                        emit_group_membership_update(
                                            updated_group.id,
                                            updated_group.name,
                                            current_user_count,
                                            "added",
                                            users_added,
                                        )
                                    )
                            except:
                                log.debug(
                                    "Could not emit socket event for additions - not in async context"
                                )

                    except ImportError:
                        log.debug("Socket.IO not available for real-time updates")
                    except Exception as e:
                        log.warning(f"Failed to emit real-time updates: {e}")

                    # Refresh the group to get the updated user list after all changes
                    if users_removed or users_added:
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
