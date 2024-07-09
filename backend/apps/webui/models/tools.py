from pydantic import BaseModel
from peewee import *
from playhouse.shortcuts import model_to_dict
from typing import List, Union, Optional
import time
import logging
from apps.webui.internal.db import DB, JSONField
from apps.webui.models.users import Users

import json
import copy


from config import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

####################
# Tools DB Schema
####################


class Tool(Model):
    id = CharField(unique=True)
    user_id = CharField()
    name = TextField()
    content = TextField()
    specs = JSONField()
    meta = JSONField()
    valves = JSONField()
    updated_at = BigIntegerField()
    created_at = BigIntegerField()

    class Meta:
        database = DB


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
    def __init__(self, db):
        self.db = db
        self.db.create_tables([Tool])

    def insert_new_tool(
        self, user_id: str, form_data: ToolForm, specs: List[dict]
    ) -> Optional[ToolModel]:
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
            result = Tool.create(**tool.model_dump())
            if result:
                return tool
            else:
                return None
        except Exception as e:
            print(f"Error creating tool: {e}")
            return None

    def get_tool_by_id(self, id: str) -> Optional[ToolModel]:
        try:
            tool = Tool.get(Tool.id == id)
            return ToolModel(**model_to_dict(tool))
        except:
            return None

    def get_tools(self) -> List[ToolModel]:
        return [ToolModel(**model_to_dict(tool)) for tool in Tool.select()]

    def get_tool_valves_by_id(self, id: str) -> Optional[dict]:
        try:
            tool = Tool.get(Tool.id == id)
            return tool.valves if tool.valves else {}
        except Exception as e:
            print(f"An error occurred: {e}")
            return None

    def update_tool_valves_by_id(self, id: str, valves: dict) -> Optional[ToolValves]:
        try:
            query = Tool.update(
                **{"valves": valves},
                updated_at=int(time.time()),
            ).where(Tool.id == id)
            query.execute()

            tool = Tool.get(Tool.id == id)
            return ToolValves(**model_to_dict(tool))
        except:
            return None

    def get_user_valves_by_id_and_user_id(
        self, id: str, user_id: str
    ) -> Optional[dict]:
        try:
            user = Users.get_user_by_id(user_id)
            user_settings = user.settings.model_dump()

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
            user_settings = user.settings.model_dump()

            # Check if user has "tools" and "valves" settings
            if "tools" not in user_settings:
                user_settings["tools"] = {}
            if "valves" not in user_settings["tools"]:
                user_settings["tools"]["valves"] = {}

            user_settings["tools"]["valves"][id] = valves

            # Update the user settings in the database
            query = Users.update_user_by_id(user_id, {"settings": user_settings})
            query.execute()

            return user_settings["tools"]["valves"][id]
        except Exception as e:
            print(f"An error occurred: {e}")
            return None

    def update_tool_by_id(self, id: str, updated: dict) -> Optional[ToolModel]:
        try:
            query = Tool.update(
                **updated,
                updated_at=int(time.time()),
            ).where(Tool.id == id)
            query.execute()

            tool = Tool.get(Tool.id == id)
            return ToolModel(**model_to_dict(tool))
        except:
            return None

    def delete_tool_by_id(self, id: str) -> bool:
        try:
            query = Tool.delete().where((Tool.id == id))
            query.execute()  # Remove the rows, return number of rows removed.

            return True
        except:
            return False


Tools = ToolsTable(DB)
