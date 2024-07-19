from pydantic import BaseModel, ConfigDict
from typing import List, Optional
import time
import logging
from sqlalchemy import String, Column, BigInteger, Text

from apps.webui.internal.db import Base, JSONField, get_db
from apps.webui.models.users import Users

import json
import copy


from config import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

####################
# Tools DB Schema
####################


class Tool(Base):
    __tablename__ = "tool"

    id = Column(String, primary_key=True)
    user_id = Column(String)
    name = Column(Text)
    content = Column(Text)
    specs = Column(JSONField)
    meta = Column(JSONField)
    valves = Column(JSONField)
    updated_at = Column(BigInteger)
    created_at = Column(BigInteger)


class ToolMeta(BaseModel):
    description: Optional[str] = None
    manifest: Optional[dict] = {}


class ToolModel(BaseModel):
    id: str
    user_id: str
    name: str
    content: str
    specs: List[dict]
    meta: ToolMeta
    updated_at: int  # timestamp in epoch
    created_at: int  # timestamp in epoch

    model_config = ConfigDict(from_attributes=True)


####################
# Forms
####################


class ToolResponse(BaseModel):
    id: str
    user_id: str
    name: str
    meta: ToolMeta
    updated_at: int  # timestamp in epoch
    created_at: int  # timestamp in epoch


class ToolForm(BaseModel):
    id: str
    name: str
    content: str
    meta: ToolMeta


class ToolValves(BaseModel):
    valves: Optional[dict] = None


class ToolsTable:

    def insert_new_tool(
        self, user_id: str, form_data: ToolForm, specs: List[dict]
    ) -> Optional[ToolModel]:

        with get_db() as db:

            tool = ToolModel(
                **{
                    **form_data.model_dump(),
                    "specs": specs,
                    "user_id": user_id,
                    "updated_at": int(time.time()),
                    "created_at": int(time.time()),
                }
            )

            try:
                result = Tool(**tool.model_dump())
                db.add(result)
                db.commit()
                db.refresh(result)
                if result:
                    return ToolModel.model_validate(result)
                else:
                    return None
            except Exception as e:
                print(f"Error creating tool: {e}")
                return None

    def get_tool_by_id(self, id: str) -> Optional[ToolModel]:
        try:
            with get_db() as db:

                tool = db.get(Tool, id)
                return ToolModel.model_validate(tool)
        except:
            return None

    def get_tools(self) -> List[ToolModel]:
        with get_db() as db:
            return [ToolModel.model_validate(tool) for tool in db.query(Tool).all()]

    def get_tool_valves_by_id(self, id: str) -> Optional[dict]:
        try:
            with get_db() as db:

                tool = db.get(Tool, id)
                return tool.valves if tool.valves else {}
        except Exception as e:
            print(f"An error occurred: {e}")
            return None

    def update_tool_valves_by_id(self, id: str, valves: dict) -> Optional[ToolValves]:
        try:
            with get_db() as db:

                db.query(Tool).filter_by(id=id).update(
                    {"valves": valves, "updated_at": int(time.time())}
                )
                db.commit()
                return self.get_tool_by_id(id)
        except:
            return None

    def get_user_valves_by_id_and_user_id(
        self, id: str, user_id: str
    ) -> Optional[dict]:
        try:
            user = Users.get_user_by_id(user_id)
            user_settings = user.settings.model_dump() if user.settings else {}

            # Check if user has "tools" and "valves" settings
            if "tools" not in user_settings:
                user_settings["tools"] = {}
            if "valves" not in user_settings["tools"]:
                user_settings["tools"]["valves"] = {}

            return user_settings["tools"]["valves"].get(id, {})
        except Exception as e:
            print(f"An error occurred: {e}")
            return None

    def update_user_valves_by_id_and_user_id(
        self, id: str, user_id: str, valves: dict
    ) -> Optional[dict]:
        try:
            user = Users.get_user_by_id(user_id)
            user_settings = user.settings.model_dump() if user.settings else {}

            # Check if user has "tools" and "valves" settings
            if "tools" not in user_settings:
                user_settings["tools"] = {}
            if "valves" not in user_settings["tools"]:
                user_settings["tools"]["valves"] = {}

            user_settings["tools"]["valves"][id] = valves

            # Update the user settings in the database
            Users.update_user_by_id(user_id, {"settings": user_settings})

            return user_settings["tools"]["valves"][id]
        except Exception as e:
            print(f"An error occurred: {e}")
            return None

    def update_tool_by_id(self, id: str, updated: dict) -> Optional[ToolModel]:
        try:
            with get_db() as db:
                db.query(Tool).filter_by(id=id).update(
                    {**updated, "updated_at": int(time.time())}
                )
                db.commit()

                tool = db.query(Tool).get(id)
                db.refresh(tool)
                return ToolModel.model_validate(tool)
        except:
            return None

    def delete_tool_by_id(self, id: str) -> bool:
        try:
            with get_db() as db:
                db.query(Tool).filter_by(id=id).delete()
                db.commit()

                return True
        except:
            return False


Tools = ToolsTable()
