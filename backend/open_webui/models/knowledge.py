import json
import logging
import time
from typing import Optional
import uuid

from open_webui.internal.db import Base, get_db
from open_webui.env import SRC_LOG_LEVELS

from open_webui.models.files import FileMetadataResponse
from open_webui.models.users import Users, UserResponse


from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Column, String, Text, JSON

from open_webui.utils.access_control import has_access

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

####################
# Knowledge DB Schema
####################


class Knowledge(Base):
    __tablename__ = "knowledge"

    id = Column(Text, unique=True, primary_key=True)
    user_id = Column(Text)

    name = Column(Text)
    description = Column(Text)

    data = Column(JSON, nullable=True)
    meta = Column(JSON, nullable=True)

    access_control = Column(JSON, nullable=True)  # Controls data access levels.
    # Defines access control rules for this entry.
    # - `None`: Public access, available to all users with the "user" role.
    # - `{}`: Private access, restricted exclusively to the owner.
    # - Custom permissions: Specific access control for reading and writing;
    #   Can specify group or user-level restrictions:
    #   {
    #      "read": {
    #          "group_ids": ["group_id1", "group_id2"],
    #          "user_ids":  ["user_id1", "user_id2"]
    #      },
    #      "write": {
    #          "group_ids": ["group_id1", "group_id2"],
    #          "user_ids":  ["user_id1", "user_id2"]
    #      }
    #   }

    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)


class KnowledgeModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str

    name: str
    description: str

    data: Optional[dict] = None
    meta: Optional[dict] = None

    # access_control: Optional[dict] = None
    access_control: Optional[dict] = {}

    created_at: int  # timestamp in epoch
    updated_at: int  # timestamp in epoch


####################
# Forms
####################


class KnowledgeUserModel(KnowledgeModel):
    user: Optional[UserResponse] = None


class KnowledgeResponse(KnowledgeModel):
    files: Optional[list[FileMetadataResponse | dict]] = None


class KnowledgeUserResponse(KnowledgeUserModel):
    files: Optional[list[FileMetadataResponse | dict]] = None


class KnowledgeForm(BaseModel):
    name: str
    description: str
    data: Optional[dict] = None
    # access_control: Optional[dict] = None
    access_control: Optional[dict] = {}
    assign_to_email: Optional[str] = None


class KnowledgeTable:
    def insert_new_knowledge(
        self, user_id: str, form_data: KnowledgeForm
    ) -> Optional[KnowledgeModel]:
        with get_db() as db:
            # Ensure data is initialized with file_ids list if not provided
            form_data_dict = form_data.model_dump(exclude={"assign_to_email"})
            if form_data_dict.get("data") is None:
                form_data_dict["data"] = {"file_ids": []}
            elif not isinstance(form_data_dict.get("data"), dict):
                form_data_dict["data"] = {"file_ids": []}
            elif "file_ids" not in form_data_dict["data"]:
                form_data_dict["data"]["file_ids"] = []
            
            knowledge = KnowledgeModel(
                **{
                    **form_data_dict,
                    "id": str(uuid.uuid4()),
                    "user_id": user_id,
                    "created_at": int(time.time()),
                    "updated_at": int(time.time()),
                }
            )

            try:
                result = Knowledge(**knowledge.model_dump())
                db.add(result)
                db.commit()
                db.refresh(result)
                if result:
                    return KnowledgeModel.model_validate(result)
                else:
                    return None
            except Exception:
                return None

    def get_knowledge_bases(self) -> list[KnowledgeUserModel]:
        with get_db() as db:
            knowledge_bases = []
            for knowledge in (
                db.query(Knowledge).order_by(Knowledge.updated_at.desc()).all()
            ):
                user = Users.get_user_by_id(knowledge.user_id)
                knowledge_bases.append(
                    KnowledgeUserModel.model_validate(
                        {
                            **KnowledgeModel.model_validate(knowledge).model_dump(),
                            "user": user.model_dump() if user else None,
                        }
                    )
                )
            return knowledge_bases

    # def get_knowledge_bases_by_user_id(
    #     self, user_id: str, permission: str = "write"
    # ) -> list[KnowledgeUserModel]:
    #     knowledge_bases = self.get_knowledge_bases()
    #     return [
    #         knowledge_base
    #         for knowledge_base in knowledge_bases
    #         if knowledge_base.user_id == user_id
    #         or has_access(user_id, permission, knowledge_base.access_control)
    #     ]

    def _item_assigned_to_user_groups(self, user_id: str, item, permission: str = "write") -> bool:
        """Check if item is assigned to any group the user is member of OR owns"""
        from open_webui.utils.workspace_access import item_assigned_to_user_groups
        return item_assigned_to_user_groups(user_id, item, permission)

    def get_knowledge_bases_by_user_id(
        self, user_id: str, permission: str = "write"
    ) -> list[KnowledgeUserModel]:
        with get_db() as db:
            all_knowledge_bases = (
                db.query(Knowledge).order_by(Knowledge.updated_at.desc()).all()
            )
            knowledge_for_user = []

            for knowledge in all_knowledge_bases:
                if (knowledge.user_id == user_id or 
                    has_access(user_id, permission, knowledge.access_control) or
                    self._item_assigned_to_user_groups(user_id, knowledge, permission)):
                    user = Users.get_user_by_id(knowledge.user_id)
                    knowledge_for_user.append(
                        KnowledgeUserModel.model_validate(
                            {
                                **KnowledgeModel.model_validate(knowledge).model_dump(),
                                "user": user.model_dump() if user else None,
                            }
                        )
                    )
            return knowledge_for_user

    def get_knowledge_by_id(self, id: str) -> Optional[KnowledgeModel]:
        try:
            with get_db() as db:
                knowledge = db.query(Knowledge).filter_by(id=id).first()
                if knowledge:
                    # Ensure data is never None - initialize with file_ids if missing
                    knowledge_model = KnowledgeModel.model_validate(knowledge)
                    if knowledge_model.data is None:
                        knowledge_model.data = {"file_ids": []}
                    elif not isinstance(knowledge_model.data, dict):
                        knowledge_model.data = {"file_ids": []}
                    elif "file_ids" not in knowledge_model.data:
                        knowledge_model.data["file_ids"] = []
                    return knowledge_model
                return None
        except Exception:
            return None

    def update_knowledge_by_id(
        self, id: str, form_data: KnowledgeForm, overwrite: bool = False
    ) -> Optional[KnowledgeModel]:
        try:
            with get_db() as db:
                knowledge = self.get_knowledge_by_id(id=id)
                db.query(Knowledge).filter_by(id=id).update(
                    {
                        **form_data.model_dump(exclude={"assign_to_email"}),
                        "updated_at": int(time.time()),
                    }
                )
                db.commit()
                return self.get_knowledge_by_id(id=id)
        except Exception as e:
            log.exception(e)
            return None

    def update_knowledge_data_by_id(
        self, id: str, data: dict
    ) -> Optional[KnowledgeModel]:
        import time as time_module
        max_retries = 3
        retry_delay = 0.1  # 100ms
        
        for attempt in range(max_retries):
            try:
                with get_db() as db:
                    # Verify knowledge exists before updating
                    knowledge_exists = db.query(Knowledge).filter_by(id=id).first()
                    if not knowledge_exists:
                        log.error(f"Knowledge {id} not found for data update")
                        return None
                    
                    # Log current state for debugging
                    log.info(f"Updating knowledge {id} (attempt {attempt + 1}/{max_retries}): user_id={knowledge_exists.user_id}, current_data={knowledge_exists.data}, new_data={data}")
                    
                    # Ensure data is a dict with file_ids key
                    if not isinstance(data, dict):
                        log.error(f"Invalid data type for knowledge {id}: {type(data)}")
                        return None
                    if "file_ids" not in data:
                        data["file_ids"] = []
                    
                    # Perform the update
                    rows_updated = db.query(Knowledge).filter_by(id=id).update(
                        {
                            "data": data,
                            "updated_at": int(time.time()),
                        }
                    )
                    db.commit()
                    
                    log.info(f"Update commit completed for knowledge {id}: rows_updated={rows_updated}")
                    
                    # Verify the update succeeded
                    if rows_updated == 0:
                        if attempt < max_retries - 1:
                            log.warning(f"No rows updated for knowledge {id} on attempt {attempt + 1}, retrying...")
                            time_module.sleep(retry_delay * (attempt + 1))  # Exponential backoff
                            continue
                        else:
                            log.error(f"No rows updated for knowledge {id} after {max_retries} attempts - possible transaction conflict or row lock")
                            return None
                    
                    # Refresh and read from the same session to ensure consistency
                    db.expire_all()  # Expire all objects to force fresh read
                    updated_knowledge = db.query(Knowledge).filter_by(id=id).first()
                    if not updated_knowledge:
                        log.error(f"Failed to retrieve updated knowledge {id} from same session")
                        return None
                    
                    log.info(f"Retrieved updated knowledge {id}: data={updated_knowledge.data}")
                    
                    # Convert to model and normalize data
                    knowledge_model = KnowledgeModel.model_validate(updated_knowledge)
                    if knowledge_model.data is None:
                        knowledge_model.data = {"file_ids": []}
                    elif not isinstance(knowledge_model.data, dict):
                        knowledge_model.data = {"file_ids": []}
                    elif "file_ids" not in knowledge_model.data:
                        knowledge_model.data["file_ids"] = []
                    
                    return knowledge_model
            except Exception as e:
                if attempt < max_retries - 1:
                    log.warning(f"Error updating knowledge {id} on attempt {attempt + 1}, retrying: {e}")
                    time_module.sleep(retry_delay * (attempt + 1))
                    continue
                else:
                    log.exception(f"Error updating knowledge data for {id} after {max_retries} attempts: {e}")
                    return None
        
        return None

    def delete_knowledge_by_id(self, id: str) -> bool:
        try:
            with get_db() as db:
                db.query(Knowledge).filter_by(id=id).delete()
                db.commit()
                return True
        except Exception:
            return False

    def delete_all_knowledge(self) -> bool:
        with get_db() as db:
            try:
                db.query(Knowledge).delete()
                db.commit()

                return True
            except Exception:
                return False


Knowledges = KnowledgeTable()
