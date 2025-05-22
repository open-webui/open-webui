import json
import logging
import time
from typing import Optional, List
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
    user_id = Column(Text) # Creator of the group

    name = Column(Text)
    description = Column(Text)

    data = Column(JSON, nullable=True)
    meta = Column(JSON, nullable=True)

    permissions = Column(JSON, nullable=True)
    user_ids = Column(JSON, nullable=True, default=[]) # List of user IDs belonging to this group

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
    user_ids: List[str] = [] # Changed to List[str] for consistency with Pydantic

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
    user_ids: List[str] = []
    created_at: int  # timestamp in epoch
    updated_at: int  # timestamp in epoch

class GroupForm(BaseModel):
    name: str
    description: str
    permissions: Optional[dict] = None

class GroupUpdateForm(GroupForm):
    user_ids: Optional[List[str]] = None

class GroupTable:
    def __init__(self, db: Optional[Session] = None):
        self.db = db if db else next(get_db())

    def insert_new_group(
        self, user_id: str, form_data: GroupForm
    ) -> Optional[GroupModel]:
        # Ensure self.db is used if passed during instantiation, or get a new session
        db_session = self.db if self.db else next(get_db())
        try:
            group_data = {
                **form_data.model_dump(exclude_none=True),
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "user_ids": [], # Initialize with empty list
                "created_at": int(time.time()),
                "updated_at": int(time.time()),
            }
            
            # Validate with Pydantic model before creating DB model instance
            group_model_instance = GroupModel(**group_data)
            
            result = Group(**group_model_instance.model_dump())
            db_session.add(result)
            db_session.commit()
            db_session.refresh(result)
            return GroupModel.model_validate(result)
        except Exception as e:
            log.error(f"Error inserting new group: {e}", exc_info=True)
            if db_session:
                db_session.rollback()
            return None
        finally:
            if not self.db and db_session: # Close only if db was locally obtained
                db_session.close()


    def get_groups(self) -> List[GroupModel]:
        db_session = self.db if self.db else next(get_db())
        try:
            return [
                GroupModel.model_validate(group)
                for group in db_session.query(Group).order_by(Group.updated_at.desc()).all()
            ]
        finally:
            if not self.db and db_session:
                db_session.close()

    def get_groups_by_member_id(self, user_id: str) -> List[GroupModel]:
        # This is the existing method, kept for compatibility if used elsewhere,
        # but get_groups_by_user_id is preferred for clarity and directness.
        db_session = self.db if self.db else next(get_db())
        try:
            # This query might be inefficient for large JSON arrays or many groups.
            # It relies on string casting and LIKE, which isn't ideal for JSON array membership.
            # Consider DB-specific JSON functions if performance becomes an issue.
            return [
                GroupModel.model_validate(group)
                for group in db_session.query(Group)
                .filter(Group.user_ids.isnot(None)) # Ensure user_ids is not null
                .filter(func.json_contains(Group.user_ids, json.dumps(user_id))) # More robust JSON check if supported
                .order_by(Group.updated_at.desc())
                .all()
            ]
        except Exception as e:
            # Fallback or alternative for databases not supporting json_contains well with lists of strings
            # This is a simplified version of the original, assuming user_ids is a list of strings.
            log.warning(f"JSON_CONTAINS might not be fully effective for lists of strings or on all DBs. Consider alternative for user_id '{user_id}'. Error: {e}")
            # Reverting to a Python-based check if the above fails or is not suitable
            all_groups = db_session.query(Group).order_by(Group.updated_at.desc()).all()
            user_member_groups = []
            for group_db in all_groups:
                if group_db.user_ids and isinstance(group_db.user_ids, list) and user_id in group_db.user_ids:
                    user_member_groups.append(GroupModel.model_validate(group_db))
            return user_member_groups
        finally:
            if not self.db and db_session:
                db_session.close()

    def get_group_by_id(self, id: str) -> Optional[GroupModel]:
        db_session = self.db if self.db else next(get_db())
        try:
            group = db_session.query(Group).filter_by(id=id).first()
            return GroupModel.model_validate(group) if group else None
        except Exception as e:
            log.error(f"Error getting group by id '{id}': {e}", exc_info=True)
            return None
        finally:
            if not self.db and db_session:
                db_session.close()

    def get_group_by_name(self, name: str) -> Optional[GroupModel]:
        db_session = self.db if self.db else next(get_db())
        try:
            group = db_session.query(Group).filter(func.lower(Group.name) == func.lower(name)).first()
            return GroupModel.model_validate(group) if group else None
        except Exception as e:
            log.error(f"Error getting group by name '{name}': {e}", exc_info=True)
            return None
        finally:
            if not self.db and db_session:
                db_session.close()

    def get_groups_by_user_id(self, user_id: str) -> List[GroupModel]:
        """
        Retrieves all groups a specific user belongs to.
        This implementation iterates in Python, which is fine for moderate numbers of groups.
        For very large datasets, a more optimized DB query (e.g., using JSON array functions)
        would be preferable if the database supports it efficiently for this structure.
        """
        db_session = self.db if self.db else next(get_db())
        try:
            all_groups_records = db_session.query(Group).all()
            user_groups_models = []
            for group_record in all_groups_records:
                # Ensure user_ids is a list and the user_id is in it
                if group_record.user_ids and isinstance(group_record.user_ids, list) and user_id in group_record.user_ids:
                    user_groups_models.append(GroupModel.model_validate(group_record))
            return user_groups_models
        except Exception as e:
            log.error(f"Error getting groups for user_id '{user_id}': {e}", exc_info=True)
            return []
        finally:
            if not self.db and db_session:
                db_session.close()
    
    def get_group_user_ids_by_id(self, id: str) -> Optional[List[str]]: # Return type changed to List[str]
        group = self.get_group_by_id(id)
        return group.user_ids if group else None

    def update_group_by_id(
        self, id: str, form_data: GroupUpdateForm, overwrite: bool = False # overwrite seems unused
    ) -> Optional[GroupModel]:
        db_session = self.db if self.db else next(get_db())
        try:
            update_data = form_data.model_dump(exclude_none=True)
            update_data["updated_at"] = int(time.time())
            
            db_session.query(Group).filter_by(id=id).update(update_data)
            db_session.commit()
            return self.get_group_by_id(id=id) # Uses its own session management
        except Exception as e:
            log.error(f"Error updating group by id '{id}': {e}", exc_info=True)
            if db_session:
                db_session.rollback()
            return None
        finally:
            if not self.db and db_session:
                db_session.close()

    def delete_group_by_id(self, id: str) -> bool:
        db_session = self.db if self.db else next(get_db())
        try:
            db_session.query(Group).filter_by(id=id).delete()
            db_session.commit()
            return True
        except Exception as e:
            log.error(f"Error deleting group by id '{id}': {e}", exc_info=True)
            if db_session:
                db_session.rollback()
            return False
        finally:
            if not self.db and db_session:
                db_session.close()

    def delete_all_groups(self) -> bool:
        db_session = self.db if self.db else next(get_db())
        try:
            db_session.query(Group).delete()
            db_session.commit()
            return True
        except Exception as e:
            log.error(f"Error deleting all groups: {e}", exc_info=True)
            if db_session:
                db_session.rollback()
            return False
        finally:
            if not self.db and db_session:
                db_session.close()

    def remove_user_from_all_groups(self, user_id: str) -> bool:
        # This method now uses the more direct get_groups_by_user_id
        db_session = self.db if self.db else next(get_db())
        try:
            # Get groups the user is part of, using a method that handles its own session if needed
            groups_models = self.get_groups_by_user_id(user_id=user_id) 
            
            success = True
            for group_model in groups_models:
                # Operate on a copy for modification
                current_user_ids = list(group_model.user_ids) if group_model.user_ids else []
                if user_id in current_user_ids:
                    current_user_ids.remove(user_id)
                    db_session.query(Group).filter_by(id=group_model.id).update(
                        {
                            "user_ids": current_user_ids,
                            "updated_at": int(time.time()),
                        }
                    )
                    log.info(f"User '{user_id}' removed from group '{group_model.id}' during remove_user_from_all_groups.")
                else:
                    # This case should ideally not happen if get_groups_by_user_id is correct
                    log.warning(f"User '{user_id}' not found in group '{group_model.name}' (ID: {group_model.id}) during mass removal, though expected.")

            db_session.commit() # Commit all changes at once
            return success
        except Exception as e:
            log.error(f"Error in remove_user_from_all_groups for user_id '{user_id}': {e}", exc_info=True)
            if db_session:
                db_session.rollback()
            return False
        finally:
            if not self.db and db_session:
                db_session.close()

    def add_user_to_group(self, user_id: str, group_id: str) -> bool:
        db_session = self.db if self.db else next(get_db())
        try:
            group_record = db_session.query(Group).filter_by(id=group_id).first()
            if not group_record:
                log.error(f"Group with id '{group_id}' not found when trying to add user '{user_id}'.")
                return False

            current_user_ids = list(group_record.user_ids) if group_record.user_ids and isinstance(group_record.user_ids, list) else []
            
            if user_id not in current_user_ids:
                current_user_ids.append(user_id)
                update_data = {"user_ids": current_user_ids, "updated_at": int(time.time())}
                db_session.query(Group).filter_by(id=group_id).update(update_data)
                db_session.commit()
                log.info(f"User '{user_id}' successfully added to group '{group_id}'.")
                return True
            else:
                log.info(f"User '{user_id}' already in group '{group_id}'. No add action taken.")
                return True 
        except Exception as e:
            log.error(f"Error adding user '{user_id}' to group '{group_id}': {e}", exc_info=True)
            if db_session:
                db_session.rollback()
            return False
        finally:
            if not self.db and db_session:
                db_session.close()

    def remove_user_from_group(self, user_id: str, group_id: str) -> bool:
        db_session = self.db if self.db else next(get_db())
        try:
            group_record = db_session.query(Group).filter_by(id=group_id).first()
            if not group_record:
                log.error(f"Group with id '{group_id}' not found when trying to remove user '{user_id}'.")
                return False

            current_user_ids = list(group_record.user_ids) if group_record.user_ids and isinstance(group_record.user_ids, list) else []
            
            if user_id in current_user_ids:
                current_user_ids.remove(user_id)
                update_data = {"user_ids": current_user_ids, "updated_at": int(time.time())}
                db_session.query(Group).filter_by(id=group_id).update(update_data)
                db_session.commit()
                log.info(f"User '{user_id}' successfully removed from group '{group_id}'.")
                return True
            else:
                log.info(f"User '{user_id}' not in group '{group_id}'. No removal action taken.")
                return True
        except Exception as e:
            log.error(f"Error removing user '{user_id}' from group '{group_id}': {e}", exc_info=True)
            if db_session:
                db_session.rollback()
            return False
        finally:
            if not self.db and db_session:
                db_session.close()

Groups = GroupTable()
