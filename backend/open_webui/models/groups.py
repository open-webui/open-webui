import json
import logging
import time
from typing import Optional
import uuid

from open_webui.internal.db import Base, get_db
from open_webui.env import SRC_LOG_LEVELS

from open_webui.models.files import FileMetadataResponse


from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Column, String, Text, JSON, func, text


log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

####################
# UserGroup DB Schema
####################


class Group(Base):
    __tablename__ = "group"

    id = Column(Text, unique=True, primary_key=True)
    user_id = Column(Text)
    created_by = Column(Text, nullable=True)

    name = Column(Text)
    description = Column(Text)

    data = Column(JSON, nullable=True)
    meta = Column(JSON, nullable=True)

    permissions = Column(JSON, nullable=True)
    user_ids = Column(JSON, nullable=True)

    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)


class GroupModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    user_id: str
    created_by: Optional[str] = None

    name: str
    description: str

    data: Optional[dict] = None
    meta: Optional[dict] = None

    permissions: Optional[dict] = None
    user_ids: list[str] = []

    created_at: int  # timestamp in epoch
    updated_at: int  # timestamp in epoch


####################
# Forms
####################


class GroupResponse(BaseModel):
    id: str
    user_id: str
    created_by: Optional[str] = None
    name: str
    description: str
    permissions: Optional[dict] = None
    data: Optional[dict] = None
    meta: Optional[dict] = None
    user_ids: list[str] = []
    created_at: int  # timestamp in epoch
    updated_at: int  # timestamp in epoch


class GroupForm(BaseModel):
    name: str
    description: str
    permissions: Optional[dict] = None


class GroupUpdateForm(GroupForm):
    user_ids: Optional[list[str]] = None


class GroupTable:
    def insert_new_group(
        self, user_id: str, user_email: str, form_data: GroupForm
    ) -> Optional[GroupModel]:
        from open_webui.utils.cache import get_cache_manager
        
        cache = get_cache_manager()
        
        with get_db() as db:
            group = GroupModel(
                **{
                    **form_data.model_dump(exclude_none=True),
                    "id": str(uuid.uuid4()),
                    "user_id": user_id,
                    "created_by": user_email,
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
                    group_model = GroupModel.model_validate(result)
                    # Invalidate cache for group creator (if they're added as member)
                    if group_model.user_ids and user_id in group_model.user_ids:
                        cache.invalidate_user_groups(user_id)
                        cache.invalidate_user_permissions(user_id)
                        cache.invalidate_user_settings(user_id)
                    return group_model
                else:
                    return None

            except Exception:
                return None

    def get_groups(self, user_email: str = None) -> list[GroupModel]:
        with get_db() as db:
            if user_email is None:
                # Return ALL groups (for super admin)
                return [
                    GroupModel.model_validate(group)
                    for group in db.query(Group)
                    .order_by(Group.updated_at.desc())
                    .all()
                ]
            else:
                # Return only groups created by this email (existing logic)
                return [
                    GroupModel.model_validate(group)
                    for group in db.query(Group)
                    .filter(Group.created_by == user_email)
                    .order_by(Group.updated_at.desc())
                    .all()
                ]

    def get_group_by_name(self, name: str) -> Optional[GroupModel]:
        """
        Return the most recently updated group matching this name (case-insensitive).
        """
        try:
            with get_db() as db:
                group = (
                    db.query(Group)
                    .filter(func.lower(Group.name) == name.lower())
                    .order_by(Group.updated_at.desc())
                    .first()
                )
                return GroupModel.model_validate(group) if group else None
        except Exception:
            return None

    def get_groups_by_member_id(self, user_id: str) -> list[GroupModel]:
        with get_db() as db:
            dialect = db.bind.dialect.name
            
            query = db.query(Group).filter(Group.user_ids.isnot(None))
            
            if dialect == "postgresql":
                # PostgreSQL: use jsonb_array_elements_text for exact match
                # CAST to jsonb ensures it works whether column is JSON or JSONB
                # This matches the pattern from dev_api_improvements branch migrations
                query = query.filter(
                    text("""
                        EXISTS (
                            SELECT 1
                            FROM jsonb_array_elements_text(CAST("group".user_ids AS jsonb)) AS elem
                            WHERE elem = :user_id
                        )
                    """)
                ).params(user_id=user_id)
            else:
                # SQLite: use json_each for exact match
                query = query.filter(
                    text("""
                        EXISTS (
                            SELECT 1
                            FROM json_each("group".user_ids) AS elem
                            WHERE elem.value = :user_id
                        )
                    """)
                ).params(user_id=user_id)
            
            return [
                GroupModel.model_validate(group)
                for group in query.order_by(Group.updated_at.desc()).all()
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
        from open_webui.utils.cache import get_cache_manager
        
        cache = get_cache_manager()
        
        try:
            with get_db() as db:
                # Get old group data to check what changed
                old_group = self.get_group_by_id(id)
                old_user_ids = old_group.user_ids if old_group else []
                
                db.query(Group).filter_by(id=id).update(
                    {
                        **form_data.model_dump(exclude_none=True),
                        "updated_at": int(time.time()),
                    }
                )
                db.commit()
                
                new_group = self.get_group_by_id(id=id)
                
                # Invalidate cache for group data
                cache.invalidate_group_admin_config(id)
                cache.invalidate_group_members(id)
                
                # If permissions changed, invalidate permissions for all members
                if old_group and old_group.permissions != new_group.permissions:
                    for user_id in old_user_ids:
                        cache.invalidate_user_permissions(user_id)
                
                # If members changed, invalidate cache for affected users
                new_user_ids = new_group.user_ids if new_group else []
                affected_user_ids = set(old_user_ids) | set(new_user_ids)
                for user_id in affected_user_ids:
                    cache.invalidate_user_groups(user_id)
                    cache.invalidate_user_permissions(user_id)
                    cache.invalidate_user_settings(user_id)
                
                return new_group
        except Exception as e:
            log.exception(e)
            return None

    def delete_group_by_id(self, id: str) -> bool:
        from open_webui.utils.cache import get_cache_manager
        
        cache = get_cache_manager()
        
        try:
            # Get group members before deletion
            group = self.get_group_by_id(id)
            user_ids = group.user_ids if group else []
            
            with get_db() as db:
                db.query(Group).filter_by(id=id).delete()
                db.commit()
            
            # Invalidate cache for group and all members
            cache.invalidate_all_group_data(id)
            for user_id in user_ids:
                cache.invalidate_user_groups(user_id)
                cache.invalidate_user_permissions(user_id)
                cache.invalidate_user_settings(user_id)
            
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
        from open_webui.utils.cache import get_cache_manager
        
        cache = get_cache_manager()
        
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
                    
                    # Invalidate cache for group and user
                    cache.invalidate_group_members(group.id)
                    cache.invalidate_user_groups(user_id)
                    cache.invalidate_user_permissions(user_id)
                    cache.invalidate_user_settings(user_id)

                return True
            except Exception:
                return False


Groups = GroupTable()
