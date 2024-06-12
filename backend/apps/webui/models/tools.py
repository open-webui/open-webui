from pydantic import BaseModel
from peewee import *
from playhouse.shortcuts import model_to_dict
from typing import List, Union, Optional
import time
import logging
from apps.webui.internal.db import DB, JSONField

import json

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
    updated_at = BigIntegerField()
    created_at = BigIntegerField()

    class Meta:
        database = DB


class ToolMeta(BaseModel):
    description: Optional[str] = None


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
