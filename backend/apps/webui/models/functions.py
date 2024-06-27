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
# Functions DB Schema
####################


class Function(Model):
    id = CharField(unique=True)
    user_id = CharField()
    name = TextField()
    type = TextField()
    content = TextField()
    meta = JSONField()
    valves = JSONField()
    is_active = BooleanField(default=False)
    is_global = BooleanField(default=False)
    updated_at = BigIntegerField()
    created_at = BigIntegerField()

    class Meta:
        database = DB


class FunctionMeta(BaseModel):
    description: Optional[str] = None
    manifest: Optional[dict] = {}


class FunctionModel(BaseModel):
    id: str
    user_id: str
    name: str
    type: str
    content: str
    meta: FunctionMeta
    is_active: bool = False
    is_global: bool = False
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
    is_active: bool
    is_global: bool
    updated_at: int  # timestamp in epoch
    created_at: int  # timestamp in epoch


class FunctionForm(BaseModel):
    id: str
    name: str
    content: str
    meta: FunctionMeta


class FunctionValves(BaseModel):
    valves: Optional[dict] = None


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

    def get_functions(self, active_only=False) -> List[FunctionModel]:
        if active_only:
            return [
                FunctionModel(**model_to_dict(function))
                for function in Function.select().where(Function.is_active == True)
            ]
        else:
            return [
                FunctionModel(**model_to_dict(function))
                for function in Function.select()
            ]

    def get_functions_by_type(
        self, type: str, active_only=False
    ) -> List[FunctionModel]:
        if active_only:
            return [
                FunctionModel(**model_to_dict(function))
                for function in Function.select().where(
                    Function.type == type, Function.is_active == True
                )
            ]
        else:
            return [
                FunctionModel(**model_to_dict(function))
                for function in Function.select().where(Function.type == type)
            ]

    def get_global_filter_functions(self) -> List[FunctionModel]:
        return [
            FunctionModel(**model_to_dict(function))
            for function in Function.select().where(
                Function.type == "filter",
                Function.is_active == True,
                Function.is_global == True,
            )
        ]

    def get_function_valves_by_id(self, id: str) -> Optional[dict]:
        try:
            function = Function.get(Function.id == id)
            return function.valves if function.valves else {}
        except Exception as e:
            print(f"An error occurred: {e}")
            return None

    def update_function_valves_by_id(
        self, id: str, valves: dict
    ) -> Optional[FunctionValves]:
        try:
            query = Function.update(
                **{"valves": valves},
                updated_at=int(time.time()),
            ).where(Function.id == id)
            query.execute()

            function = Function.get(Function.id == id)
            return FunctionValves(**model_to_dict(function))
        except:
            return None

    def get_user_valves_by_id_and_user_id(
        self, id: str, user_id: str
    ) -> Optional[dict]:
        try:
            user = Users.get_user_by_id(user_id)
            user_settings = user.settings.model_dump()

            # Check if user has "functions" and "valves" settings
            if "functions" not in user_settings:
                user_settings["functions"] = {}
            if "valves" not in user_settings["functions"]:
                user_settings["functions"]["valves"] = {}

            return user_settings["functions"]["valves"].get(id, {})
        except Exception as e:
            print(f"An error occurred: {e}")
            return None

    def update_user_valves_by_id_and_user_id(
        self, id: str, user_id: str, valves: dict
    ) -> Optional[dict]:
        try:
            user = Users.get_user_by_id(user_id)
            user_settings = user.settings.model_dump()

            # Check if user has "functions" and "valves" settings
            if "functions" not in user_settings:
                user_settings["functions"] = {}
            if "valves" not in user_settings["functions"]:
                user_settings["functions"]["valves"] = {}

            user_settings["functions"]["valves"][id] = valves

            # Update the user settings in the database
            query = Users.update_user_by_id(user_id, {"settings": user_settings})
            query.execute()

            return user_settings["functions"]["valves"][id]
        except Exception as e:
            print(f"An error occurred: {e}")
            return None

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

    def deactivate_all_functions(self) -> Optional[bool]:
        try:
            query = Function.update(
                **{"is_active": False},
                updated_at=int(time.time()),
            )

            query.execute()

            return True
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
