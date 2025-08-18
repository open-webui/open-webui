import json
import logging
import time
from typing import Optional
import uuid

from open_webui.internal.db import Base, get_db
from open_webui.env import SRC_LOG_LEVELS

from open_webui.models.files import FileMetadataResponse

from pydantic import BaseModel, ConfigDict
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

    created_at: int  # timestamp in epoch
    updated_at: int  # timestamp in epoch

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
                .filter(func.len(Group.user_ids) > 2)  # Ensure array exists
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

    def get_group_user_ids_by_id(self, id: str) -> Optional[list[str]]:
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

    def get_group_by_name(self, name: str) -> Optional[GroupModel]:
        """
        根據群組名稱查詢群組，不區分大小寫。

        Args:
            name (str): 群組名稱

        Returns:
            Optional[GroupModel]: 如果找到群組則返回 GroupModel，否則返回 None
        """
        try:
            with get_db() as db:
                # 使用 func.lower 進行不區分大小寫的比較
                group = db.query(Group).filter(func.lower(Group.name) == func.lower(name)).first()
                return GroupModel.model_validate(group) if group else None
        except Exception as e:
            log.error(f"Error getting group by name '{name}': {e}", exc_info=True)
            return None

    def add_user_to_group(self, user_id: str, group_id: str) -> bool:
        """
        將使用者加入到指定群組。

        Args:
            user_id (str): 使用者 ID
            group_id (str): 群組 ID

        Returns:
            bool: 操作是否成功
        """
        try:
            group = self.get_group_by_id(group_id)
            if not group:
                log.error(f"Group with id '{group_id}' not found when trying to add user '{user_id}'")
                return False

            current_user_ids = list(group.user_ids) if group.user_ids else []
            
            if user_id not in current_user_ids:
                current_user_ids.append(user_id)
                
                with get_db() as db:
                    db.query(Group).filter_by(id=group_id).update({
                        "user_ids": current_user_ids,
                        "updated_at": int(time.time())
                    })
                    db.commit()
                    log.info(f"User '{user_id}' successfully added to group '{group_id}'")
            else:
                log.info(f"User '{user_id}' already in group '{group_id}'. No action taken.")
            
            return True
        
        except Exception as e:
            log.error(f"Error adding user '{user_id}' to group '{group_id}': {e}", exc_info=True)
            return False

    def remove_user_from_group(self, user_id: str, group_id: str) -> bool:
        """
        從指定群組中移除使用者。

        Args:
            user_id (str): 要移除的使用者 ID
            group_id (str): 群組 ID

        Returns:
            bool: 操作是否成功
        """
        try:
            group = self.get_group_by_id(group_id)
            if not group:
                log.error(f"Group with id '{group_id}' not found when trying to remove user '{user_id}'")
                return False

            if not group.user_ids:
                log.info(f"Group '{group_id}' has no members. No removal needed for user '{user_id}'")
                return True

            current_user_ids = list(group.user_ids)
            if user_id in current_user_ids:
                current_user_ids.remove(user_id)
                
                with get_db() as db:
                    db.query(Group).filter_by(id=group_id).update({
                        "user_ids": current_user_ids,
                        "updated_at": int(time.time())
                    })
                    db.commit()
                    log.info(f"User '{user_id}' successfully removed from group '{group_id}'")
            else:
                log.info(f"User '{user_id}' not found in group '{group_id}'. No removal needed.")
            
            return True

        except Exception as e:
            log.error(f"Error removing user '{user_id}' from group '{group_id}': {e}", exc_info=True)
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
