import logging
import time
from typing import Optional
import uuid
from threading import Lock

from open_webui.internal.db import get_db
from open_webui.env import SRC_LOG_LEVELS
from open_webui.models.base import Base

from pydantic import BaseModel, ConfigDict, field_validator
from sqlalchemy import BigInteger, Column, String, Text, JSON, or_, func


log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

# Cache for group memberships - invalidated when groups or users change
_group_membership_cache = {}
_cache_timestamp = 0
_cache_lock = Lock()
CACHE_TTL = 300  # 5 minutes


def invalidate_group_membership_cache():
    """Public function to invalidate group membership cache - can be called from other modules."""
    _invalidate_group_membership_cache()


def _get_cache_key(user_id: str, user_domain: str) -> str:
    """Generate cache key for user's group memberships."""
    return f"groups:{user_id}:{user_domain or 'none'}"


def _invalidate_group_membership_cache():
    """Invalidate the entire group membership cache."""
    global _group_membership_cache, _cache_timestamp
    with _cache_lock:
        _group_membership_cache.clear()
        _cache_timestamp = time.time()
        log.debug("Group membership cache invalidated")


def _is_cache_valid() -> bool:
    """Check if cache is still valid based on TTL."""
    return time.time() - _cache_timestamp < CACHE_TTL


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
                    # Invalidate cache when new group is created
                    _invalidate_group_membership_cache()
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

        Uses caching and SQL filtering for optimal performance.
        """
        from open_webui.models.users import (
            Users,
        )  # Import here to avoid circular imports

        # Get user info for domain checking
        user = Users.get_user_by_id(user_id)
        user_domain = user.domain if user else None

        # Generate cache key
        cache_key = _get_cache_key(user_id, user_domain)

        # Try to get from cache first
        with _cache_lock:
            if _is_cache_valid() and cache_key in _group_membership_cache:
                log.debug(f"Cache hit for user {user_id}")
                return _group_membership_cache[cache_key]

        # Cache miss - compute groups using SQL filtering
        log.debug(f"Cache miss for user {user_id}, computing groups")

        with get_db() as db:
            query = db.query(Group).filter(
                or_(
                    func.json_array_length(Group.user_ids) > 0,
                    func.json_array_length(Group.allowed_domains) > 0,
                )
            )  # Ensure arrays exist

            # Build filter conditions
            conditions = []

            # Check for user ID in user_ids array
            conditions.append(Group.user_ids.cast(String).like(f'%"{user_id}"%'))

            # Check for domain in allowed_domains array (if user has a domain)
            if user_domain:
                conditions.append(
                    Group.allowed_domains.cast(String).like(f'%"{user_domain}"%')
                )

            # Apply OR conditions and get results
            matching_groups = (
                query.filter(or_(*conditions)).order_by(Group.updated_at.desc()).all()
            )
            result = [GroupModel.model_validate(group) for group in matching_groups]

            # Cache the result
            with _cache_lock:
                _group_membership_cache[cache_key] = result

            return result

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
                if user.domain and user.domain in group.allowed_domains:
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

                # Invalidate cache when group is updated (membership may have changed)
                _invalidate_group_membership_cache()

                return updated_group
        except Exception as e:
            log.exception(e)
            return None

    def delete_group_by_id(self, id: str) -> bool:
        try:
            with get_db() as db:
                db.query(Group).filter_by(id=id).delete()
                db.commit()
                # Invalidate cache when group is deleted
                _invalidate_group_membership_cache()
                return True
        except Exception:
            return False

    def delete_all_groups(self) -> bool:
        with get_db() as db:
            try:
                db.query(Group).delete()
                db.commit()
                # Invalidate cache when all groups are deleted
                _invalidate_group_membership_cache()

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

                # Invalidate cache when user is removed from groups
                _invalidate_group_membership_cache()
                return True
            except Exception:
                return False


Groups = GroupTable()
