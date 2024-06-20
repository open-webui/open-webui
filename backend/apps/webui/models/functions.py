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
# Functions DB Schema
####################


class Function(Model):
    id = CharField(unique=True)
    user_id = CharField()
    name = TextField()
    type = TextField()
    content = TextField()
    meta = JSONField()
    updated_at = BigIntegerField()
    created_at = BigIntegerField()

    class Meta:
        database = DB


class FunctionMeta(BaseModel):
    description: Optional[str] = None


class FunctionModel(BaseModel):
    id: str
    user_id: str
    name: str
    type: str
    content: str
    meta: FunctionMeta
    updated_at: int  # timestamp in epoch
    created_at: int  # timestamp in epoch


####################
# Forms
####################


class FunctionResponse(BaseModel):
    id: str
    user_id: str
    type: str
    name: str
    meta: FunctionMeta
    updated_at: int  # timestamp in epoch
    created_at: int  # timestamp in epoch


class FunctionForm(BaseModel):
    id: str
    name: str
    content: str
    meta: FunctionMeta


class FunctionsTable:
    def __init__(self, db):
        self.db = db
        self.db.create_tables([Function])

    def insert_new_function(
        self, user_id: str, type: str, form_data: FunctionForm
    ) -> Optional[FunctionModel]:
        function = FunctionModel(
            **{
                **form_data.model_dump(),
                "user_id": user_id,
                "type": type,
                "updated_at": int(time.time()),
                "created_at": int(time.time()),
            }
        )

        try:
            result = Function.create(**function.model_dump())
            if result:
                return function
            else:
                return None
        except Exception as e:
            print(f"Error creating tool: {e}")
            return None

    def get_function_by_id(self, id: str) -> Optional[FunctionModel]:
        try:
            function = Function.get(Function.id == id)
            return FunctionModel(**model_to_dict(function))
        except:
            return None

    def get_functions(self) -> List[FunctionModel]:
        return [
            FunctionModel(**model_to_dict(function)) for function in Function.select()
        ]

    def get_functions_by_type(self, type: str) -> List[FunctionModel]:
        return [
            FunctionModel(**model_to_dict(function))
            for function in Function.select().where(Function.type == type)
        ]

    def update_function_by_id(self, id: str, updated: dict) -> Optional[FunctionModel]:
        try:
            query = Function.update(
                **updated,
                updated_at=int(time.time()),
            ).where(Function.id == id)
            query.execute()

            function = Function.get(Function.id == id)
            return FunctionModel(**model_to_dict(function))
        except:
            return None

    def delete_function_by_id(self, id: str) -> bool:
        try:
            query = Function.delete().where((Function.id == id))
            query.execute()  # Remove the rows, return number of rows removed.

            return True
        except:
            return False


Functions = FunctionsTable(DB)
