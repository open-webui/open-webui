from pydantic import BaseModel
from typing import List, Optional
import time
import logging

from sqlalchemy import Column, String, Text, BigInteger, Boolean

from apps.webui.internal.db import JSONField, Base, get_db
from apps.webui.models.users import Users

from config import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

####################
# Python Scripts DB Schema
####################


class Script(Base):
    __tablename__ = "script"

    id = Column(String, primary_key=True)
    user_id = Column(String)
    name = Column(Text)
    content = Column(Text)
    meta = Column(JSONField)
    updated_at = Column(BigInteger)
    created_at = Column(BigInteger)


class Meta(BaseModel):
    description: Optional[str] = None
    manifest: Optional[dict] = {}


class ScriptModel(BaseModel):
    id: str
    user_id: str
    name: str
    content: str
    meta: Meta
    updated_at: int  # timestamp in epoch
    created_at: int  # timestamp in epoch


####################
# Forms
####################


class ScriptResponse(BaseModel):
    id: str
    user_id: str
    content: str
    name: str
    meta: Meta
    updated_at: int  # timestamp in epoch
    created_at: int  # timestamp in epoch


class ScriptForm(BaseModel):
    id: str
    name: str
    content: str
    meta: Meta


class ScriptsTable:
    def insert_new_script(
        self, user_id: str, form_data: ScriptForm
    ) -> Optional[ScriptModel]:

        function = ScriptModel(
            **{
                **form_data.model_dump(),
                "user_id": user_id,
                "type": type,
                "updated_at": int(time.time()),
                "created_at": int(time.time()),
            }
        )

        try:
            with get_db() as db:
                result = Script(**function.model_dump())
                db.add(result)
                db.commit()
                db.refresh(result)
                if result:
                    return ScriptModel.model_validate(result)
                else:
                    return None
        except Exception as e:
            print(f"Error creating script: {e}")
            return None

    def get_script_by_id(self, id: str) -> Optional[ScriptModel]:
        try:
            with get_db() as db:
                script = db.get(Script, id)
                return ScriptModel.model_validate(script)
        except:
            return None

    def get_scripts(self, active_only=False) -> List[ScriptModel]:
        with get_db() as db:
            if active_only:
                return [
                    ScriptModel.model_validate(script)
                    for script in db.query(Script).filter_by(is_active=True).all()
                ]
            else:
                return [
                    ScriptModel.model_validate(script)
                    for script in db.query(Script).all()
                ]

    def update_script_by_id(self, id: str, updated: dict) -> Optional[ScriptModel]:
        with get_db() as db:

            try:
                db.query(Script).filter_by(id=id).update(
                    {
                        **updated,
                        "updated_at": int(time.time()),
                    }
                )
                db.commit()
                return self.get_script_by_id(id)
            except:
                return None

    def delete_script_by_id(self, id: str) -> bool:
        with get_db() as db:
            try:
                db.query(Script).filter_by(id=id).delete()
                db.commit()

                return True
            except:
                return False


Scripts = ScriptsTable()
