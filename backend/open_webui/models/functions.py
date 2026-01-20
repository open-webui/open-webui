import logging
import time
from typing import Optional

from sqlalchemy.orm import Session
from open_webui.internal.db import Base, JSONField, get_db, get_db_context
from open_webui.models.users import Users, UserModel
from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Boolean, Column, String, Text, Index

log = logging.getLogger(__name__)

####################
# Functions DB Schema
####################


class Function(Base):
    __tablename__ = "function"

    id = Column(String, primary_key=True, unique=True)
    user_id = Column(String)
    name = Column(Text)
    type = Column(Text)
    content = Column(Text)
    meta = Column(JSONField)
    valves = Column(JSONField)
    is_active = Column(Boolean)
    is_global = Column(Boolean)
    updated_at = Column(BigInteger)
    created_at = Column(BigInteger)

    __table_args__ = (Index("is_global_idx", "is_global"),)


class FunctionMeta(BaseModel):
    description: Optional[str] = None
    manifest: Optional[dict] = {}
    model_config = ConfigDict(extra="allow")


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

    model_config = ConfigDict(from_attributes=True)


class FunctionWithValvesModel(BaseModel):
    id: str
    user_id: str
    name: str
    type: str
    content: str
    meta: FunctionMeta
    valves: Optional[dict] = None
    is_active: bool = False
    is_global: bool = False
    updated_at: int  # timestamp in epoch
    created_at: int  # timestamp in epoch

    model_config = ConfigDict(from_attributes=True)


####################
# Forms
####################


class FunctionUserResponse(FunctionModel):
    user: Optional[UserModel] = None
    has_valves: Optional[bool] = False


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
    def insert_new_function(
        self,
        user_id: str,
        type: str,
        form_data: FunctionForm,
        db: Optional[Session] = None,
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
            with get_db_context(db) as db:
                result = Function(**function.model_dump())
                db.add(result)
                db.commit()
                db.refresh(result)
                if result:
                    return FunctionModel.model_validate(result)
                else:
                    return None
        except Exception as e:
            log.exception(f"Error creating a new function: {e}")
            return None

    def sync_functions(
        self,
        user_id: str,
        functions: list[FunctionWithValvesModel],
        db: Optional[Session] = None,
    ) -> list[FunctionWithValvesModel]:
        # Synchronize functions for a user by updating existing ones, inserting new ones, and removing those that are no longer present.
        try:
            with get_db_context(db) as db:
                # Get existing functions
                existing_functions = db.query(Function).all()
                existing_ids = {func.id for func in existing_functions}

                # Prepare a set of new function IDs
                new_function_ids = {func.id for func in functions}

                # Update or insert functions
                for func in functions:
                    if func.id in existing_ids:
                        db.query(Function).filter_by(id=func.id).update(
                            {
                                **func.model_dump(),
                                "user_id": user_id,
                                "updated_at": int(time.time()),
                            }
                        )
                    else:
                        new_func = Function(
                            **{
                                **func.model_dump(),
                                "user_id": user_id,
                                "updated_at": int(time.time()),
                            }
                        )
                        db.add(new_func)

                # Remove functions that are no longer present
                for func in existing_functions:
                    if func.id not in new_function_ids:
                        db.delete(func)

                db.commit()

                return [
                    FunctionModel.model_validate(func)
                    for func in db.query(Function).all()
                ]
        except Exception as e:
            log.exception(f"Error syncing functions for user {user_id}: {e}")
            return []

    def get_function_by_id(
        self, id: str, db: Optional[Session] = None
    ) -> Optional[FunctionModel]:
        try:
            with get_db_context(db) as db:
                function = db.get(Function, id)
                return FunctionModel.model_validate(function)
        except Exception:
            return None

    def get_functions(
        self, active_only=False, include_valves=False, db: Optional[Session] = None
    ) -> list[FunctionModel | FunctionWithValvesModel]:
        with get_db_context(db) as db:
            if active_only:
                functions = db.query(Function).filter_by(is_active=True).all()

            else:
                functions = db.query(Function).all()

            if include_valves:
                return [
                    FunctionWithValvesModel.model_validate(function)
                    for function in functions
                ]
            else:
                return [
                    FunctionModel.model_validate(function) for function in functions
                ]

    def get_function_list(
        self, db: Optional[Session] = None
    ) -> list[FunctionUserResponse]:
        with get_db_context(db) as db:
            functions = db.query(Function).order_by(Function.updated_at.desc()).all()
            user_ids = list(set(func.user_id for func in functions))

            users = Users.get_users_by_user_ids(user_ids, db=db) if user_ids else []
            users_dict = {user.id: user for user in users}

            def _has_configurable_valves(content):
                """Check if content has a Valves class with actual fields (not just pass)."""
                if not content:
                    return False
                valves_start = content.find("class Valves(BaseModel):")
                if valves_start == -1:
                    return False
                after_valves = content[valves_start + len("class Valves(BaseModel):") :]
                lines = after_valves.split("\n")
                in_docstring = False
                for line in lines:
                    stripped = line.strip()
                    # Handle docstrings (both single-line and multi-line)
                    if '"""' in stripped:
                        if in_docstring:
                            # Closing triple quote found
                            in_docstring = False
                            stripped = stripped.split('"""')[-1].strip()
                            if not stripped or stripped.startswith("#"):
                                continue
                        else:
                            # Opening triple quote found
                            if stripped.count('"""') == 1:
                                in_docstring = True
                            stripped = stripped.split('"""')[0].strip()
                            if not stripped or stripped.startswith("#"):
                                continue
                    elif in_docstring:
                        # Still inside multi-line docstring
                        continue
                    # Skip empty lines and comments
                    if not stripped or stripped.startswith("#"):
                        continue
                    if stripped == "pass":
                        return False
                    # Check if this is a field definition (not a function/class/decorator)
                    # Field definitions look like: field_name: type = ...
                    # They don't start with def, class, @, async, etc.
                    if (
                        stripped.startswith("def ")
                        or stripped.startswith("class ")
                        or stripped.startswith("@")
                        or stripped.startswith("async ")
                        or stripped.startswith("if ")
                        or stripped.startswith("for ")
                        or stripped.startswith("while ")
                        or stripped.startswith("return ")
                    ):
                        return False
                    # If it contains a colon, it's likely a field definition
                    if ":" in stripped:
                        return True
                    return False
                return False

            return [
                FunctionUserResponse.model_validate(
                    {
                        **FunctionModel.model_validate(func).model_dump(),
                        "user": (
                            users_dict.get(func.user_id).model_dump()
                            if func.user_id in users_dict
                            else None
                        ),
                        "has_valves": _has_configurable_valves(func.content),
                    }
                )
                for func in functions
            ]

    def get_functions_by_type(
        self, type: str, active_only=False, db: Optional[Session] = None
    ) -> list[FunctionModel]:
        with get_db_context(db) as db:
            if active_only:
                return [
                    FunctionModel.model_validate(function)
                    for function in db.query(Function)
                    .filter_by(type=type, is_active=True)
                    .all()
                ]
            else:
                return [
                    FunctionModel.model_validate(function)
                    for function in db.query(Function).filter_by(type=type).all()
                ]

    def get_global_filter_functions(
        self, db: Optional[Session] = None
    ) -> list[FunctionModel]:
        with get_db_context(db) as db:
            return [
                FunctionModel.model_validate(function)
                for function in db.query(Function)
                .filter_by(type="filter", is_active=True, is_global=True)
                .all()
            ]

    def get_global_action_functions(
        self, db: Optional[Session] = None
    ) -> list[FunctionModel]:
        with get_db_context(db) as db:
            return [
                FunctionModel.model_validate(function)
                for function in db.query(Function)
                .filter_by(type="action", is_active=True, is_global=True)
                .all()
            ]

    def get_function_valves_by_id(
        self, id: str, db: Optional[Session] = None
    ) -> Optional[dict]:
        with get_db_context(db) as db:
            try:
                function = db.get(Function, id)
                return function.valves if function.valves else {}
            except Exception as e:
                log.exception(f"Error getting function valves by id {id}: {e}")
                return None

    def update_function_valves_by_id(
        self, id: str, valves: dict, db: Optional[Session] = None
    ) -> Optional[FunctionValves]:
        with get_db_context(db) as db:
            try:
                function = db.get(Function, id)
                function.valves = valves
                function.updated_at = int(time.time())
                db.commit()
                db.refresh(function)
                return self.get_function_by_id(id, db=db)
            except Exception:
                return None

    def update_function_metadata_by_id(
        self, id: str, metadata: dict, db: Optional[Session] = None
    ) -> Optional[FunctionModel]:
        with get_db_context(db) as db:
            try:
                function = db.get(Function, id)

                if function:
                    if function.meta:
                        function.meta = {**function.meta, **metadata}
                    else:
                        function.meta = metadata

                    function.updated_at = int(time.time())
                    db.commit()
                    db.refresh(function)
                    return self.get_function_by_id(id, db=db)
                else:
                    return None
            except Exception as e:
                log.exception(f"Error updating function metadata by id {id}: {e}")
                return None

    def get_user_valves_by_id_and_user_id(
        self, id: str, user_id: str, db: Optional[Session] = None
    ) -> Optional[dict]:
        try:
            user = Users.get_user_by_id(user_id, db=db)
            user_settings = user.settings.model_dump() if user.settings else {}

            # Check if user has "functions" and "valves" settings
            if "functions" not in user_settings:
                user_settings["functions"] = {}
            if "valves" not in user_settings["functions"]:
                user_settings["functions"]["valves"] = {}

            return user_settings["functions"]["valves"].get(id, {})
        except Exception as e:
            log.exception(f"Error getting user values by id {id} and user id {user_id}")
            return None

    def update_user_valves_by_id_and_user_id(
        self, id: str, user_id: str, valves: dict, db: Optional[Session] = None
    ) -> Optional[dict]:
        try:
            user = Users.get_user_by_id(user_id, db=db)
            user_settings = user.settings.model_dump() if user.settings else {}

            # Check if user has "functions" and "valves" settings
            if "functions" not in user_settings:
                user_settings["functions"] = {}
            if "valves" not in user_settings["functions"]:
                user_settings["functions"]["valves"] = {}

            user_settings["functions"]["valves"][id] = valves

            # Update the user settings in the database
            Users.update_user_by_id(user_id, {"settings": user_settings}, db=db)

            return user_settings["functions"]["valves"][id]
        except Exception as e:
            log.exception(
                f"Error updating user valves by id {id} and user_id {user_id}: {e}"
            )
            return None

    def update_function_by_id(
        self, id: str, updated: dict, db: Optional[Session] = None
    ) -> Optional[FunctionModel]:
        with get_db_context(db) as db:
            try:
                db.query(Function).filter_by(id=id).update(
                    {
                        **updated,
                        "updated_at": int(time.time()),
                    }
                )
                db.commit()
                return self.get_function_by_id(id, db=db)
            except Exception:
                return None

    def deactivate_all_functions(self, db: Optional[Session] = None) -> Optional[bool]:
        with get_db_context(db) as db:
            try:
                db.query(Function).update(
                    {
                        "is_active": False,
                        "updated_at": int(time.time()),
                    }
                )
                db.commit()
                return True
            except Exception:
                return None

    def delete_function_by_id(self, id: str, db: Optional[Session] = None) -> bool:
        with get_db_context(db) as db:
            try:
                db.query(Function).filter_by(id=id).delete()
                db.commit()

                return True
            except Exception:
                return False


Functions = FunctionsTable()
