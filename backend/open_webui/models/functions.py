"""Function (filter/action/pipe) models, forms, and database operations."""

from __future__ import annotations

import logging
import time

# local imports
from open_webui.internal.db import Base, JSONField, get_async_db_context
from open_webui.models.users import UserResponse, Users
from open_webui.utils.valves import decrypt_valves, encrypt_valves
from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Boolean, Column, Index, String, Text, delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

log = logging.getLogger(__name__)


class Function(Base):  # database table mapping
    __tablename__ = 'function'

    id = Column(String, primary_key=True, unique=True)
    user_id = Column(String, index=True)  # creator user id
    name = Column(Text, nullable=False)  # function identifier
    type = Column(Text, nullable=False)  # function type (pipe, filter, etc.)
    content = Column(Text, nullable=True)  # Python source code
    meta = Column(JSONField, nullable=True)  # function metadata
    valves = Column(JSONField, nullable=True)  # function configuration valves
    is_active = Column(Boolean, default=False)  # function activation status
    is_global = Column(Boolean)  # if True, applied to every chat automatically
    updated_at = Column(BigInteger)  # epoch seconds
    created_at = Column(BigInteger)  # epoch seconds

    __table_args__ = (Index('is_global_idx', 'is_global'),)  # speed up global-function lookups


class FunctionMeta(BaseModel):
    description: str | None = None
    manifest: dict | None = {}
    model_config = ConfigDict(extra='allow')


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

    model_config = ConfigDict(from_attributes=True)  # allows ORM model binding


# --- form / schema definitions ---
class FunctionWithValvesModel(BaseModel):
    id: str
    user_id: str
    name: str
    type: str
    content: str
    meta: FunctionMeta
    valves: dict | None = None
    is_active: bool = False
    is_global: bool = False
    updated_at: int  # timestamp in epoch
    created_at: int  # timestamp in epoch

    model_config = ConfigDict(from_attributes=True)


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

    model_config = ConfigDict(from_attributes=True)


class FunctionUserResponse(FunctionResponse):
    user: UserResponse | None = None


class FunctionForm(BaseModel):
    id: str
    name: str
    content: str
    meta: FunctionMeta


class FunctionValves(BaseModel):
    valves: dict | None = None


class FunctionsTable:
    async def insert_new_function(
        self,
        user_id: str,
        type: str,
        form_data: FunctionForm,
        db: AsyncSession | None = None,
    ) -> FunctionModel | None:
        function = FunctionModel(
            **{
                **form_data.model_dump(),
                'user_id': user_id,
                'type': type,
                'updated_at': int(time.time()),
                'created_at': int(time.time()),
            }
        )

        try:
            async with get_async_db_context(db) as db:
                result = Function(**function.model_dump())
                db.add(result)
                await db.commit()
                await db.refresh(result)
                if result:
                    return FunctionModel.model_validate(result)
                else:
                    return None
        except Exception as e:
            log.exception(f'Error creating a new function: {e}')
            return None

    async def sync_functions(
        self,
        user_id: str,
        functions: list[FunctionWithValvesModel],
        db: AsyncSession | None = None,
    ) -> list[FunctionWithValvesModel]:
        # Synchronize functions by updating existing ones, inserting new ones,
        # and removing those that are no longer present.
        try:
            async with get_async_db_context(db) as db:
                # Get existing functions
                result = await db.execute(select(Function))
                existing_functions = result.scalars().all()
                existing_ids = {func.id for func in existing_functions}

                # Prepare a set of new function IDs
                new_function_ids = {func.id for func in functions}

                # Update or insert functions
                for func in functions:
                    func_data = func.model_dump()
                    func_data['valves'] = encrypt_valves(func_data['valves']) if func_data.get('valves') else None
                    func_data['user_id'] = user_id
                    func_data['updated_at'] = int(time.time())

                    if func.id in existing_ids:
                        await db.execute(update(Function).filter_by(id=func.id).values(**func_data))
                    else:
                        new_func = Function(**func_data)
                        db.add(new_func)

                # Remove functions that are no longer present
                for func in existing_functions:
                    if func.id not in new_function_ids:
                        await db.delete(func)

                await db.commit()

                result = await db.execute(select(Function))
                return [FunctionModel.model_validate(func) for func in result.scalars().all()]
        except Exception as e:
            log.exception(f'Error syncing functions for user {user_id}: {e}')
            return []

    async def get_function_by_id(self, id: str, db: AsyncSession | None = None) -> FunctionModel | None:
        try:
            async with get_async_db_context(db) as db:
                function = await db.get(Function, id)
                return FunctionModel.model_validate(function) if function else None
        except Exception:
            return None

    async def get_functions_by_ids(self, ids: list[str], db: AsyncSession | None = None) -> list[FunctionModel]:
        """
        Batch fetch multiple functions by their IDs in a single query.
        Returns functions in the same order as the input IDs (None entries filtered out).
        """
        if not ids:
            return []
        try:
            async with get_async_db_context(db) as db:
                result = await db.execute(select(Function).filter(Function.id.in_(ids)))
                functions = result.scalars().all()
                # Create a dict for O(1) lookup
                func_dict = {f.id: FunctionModel.model_validate(f) for f in functions}
                # Return in original order, filtering out any not found
                return [func_dict[id] for id in ids if id in func_dict]
        except Exception:
            return []

    async def get_functions(
        self, active_only=False, include_valves=False, db: AsyncSession | None = None
    ) -> list[FunctionModel | FunctionWithValvesModel]:
        async with get_async_db_context(db) as db:
            if active_only:
                result = await db.execute(select(Function).filter_by(is_active=True))
            else:
                result = await db.execute(select(Function))

            functions = result.scalars().all()

            if include_valves:
                return [
                    FunctionWithValvesModel.model_validate(
                        {
                            **FunctionModel.model_validate(function).model_dump(),
                            'valves': decrypt_valves(function.valves),
                        }
                    )
                    for function in functions
                ]
            else:
                return [FunctionModel.model_validate(function) for function in functions]

    async def get_function_list(self, db: AsyncSession | None = None) -> list[FunctionUserResponse]:
        async with get_async_db_context(db) as db:
            result = await db.execute(select(Function).order_by(Function.updated_at.desc()))
            functions = result.scalars().all()
            user_ids = list(set(func.user_id for func in functions))

            users = await Users.get_users_by_user_ids(user_ids, db=db) if user_ids else []
            users_dict = {user.id: user for user in users}

            return [
                FunctionUserResponse.model_validate(
                    {
                        **FunctionResponse.model_validate(func).model_dump(),
                        'user': (
                            UserResponse(
                                id=users_dict[func.user_id].id,
                                name=users_dict[func.user_id].name,
                                role=users_dict[func.user_id].role,
                                email=users_dict[func.user_id].email,
                            ).model_dump()
                            if func.user_id in users_dict
                            else None
                        ),
                    }
                )
                for func in functions
            ]

    async def get_functions_by_type(
        self, type: str, active_only=False, db: AsyncSession | None = None
    ) -> list[FunctionModel]:
        async with get_async_db_context(db) as db:
            if active_only:
                result = await db.execute(select(Function).filter_by(type=type, is_active=True))
            else:
                result = await db.execute(select(Function).filter_by(type=type))
            return [FunctionModel.model_validate(function) for function in result.scalars().all()]

    async def get_global_filter_functions(self, db: AsyncSession | None = None) -> list[FunctionModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(select(Function).filter_by(type='filter', is_active=True, is_global=True))
            return [FunctionModel.model_validate(function) for function in result.scalars().all()]

    async def get_global_action_functions(self, db: AsyncSession | None = None) -> list[FunctionModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(select(Function).filter_by(type='action', is_active=True, is_global=True))
            return [FunctionModel.model_validate(function) for function in result.scalars().all()]

    async def get_function_valves_by_id(self, id: str, db: AsyncSession | None = None) -> dict | None:
        async with get_async_db_context(db) as db:
            try:
                function = await db.get(Function, id)
                return decrypt_valves(function.valves if function else None)
            except Exception as e:
                log.exception(f'Error getting function valves by id {id}: {e}')
                return None

    async def get_function_valves_by_ids(self, ids: list[str], db: AsyncSession | None = None) -> dict[str, dict]:
        """
        Batch fetch valves for multiple functions in a single query.
        Returns a dict mapping function_id -> valves dict.
        Functions without valves are mapped to {}.
        """
        if not ids:
            return {}
        try:
            async with get_async_db_context(db) as db:
                result = await db.execute(select(Function.id, Function.valves).filter(Function.id.in_(ids)))
                functions = result.all()
                return {f.id: decrypt_valves(f.valves) for f in functions}
        except Exception as e:
            log.exception(f'Error batch-fetching function valves: {e}')
            return {}

    async def update_function_valves_by_id(
        self, id: str, valves: dict, db: AsyncSession | None = None
    ) -> FunctionValves | None:
        async with get_async_db_context(db) as db:
            try:
                function = await db.get(Function, id)
                function.valves = encrypt_valves(valves)
                function.updated_at = int(time.time())
                await db.commit()
                await db.refresh(function)
                return FunctionModel.model_validate(function)
            except Exception:
                return None

    async def update_function_metadata_by_id(
        self, id: str, metadata: dict, db: AsyncSession | None = None
    ) -> FunctionModel | None:
        async with get_async_db_context(db) as db:
            try:
                function = await db.get(Function, id)

                if function:
                    if function.meta:
                        function.meta = {**function.meta, **metadata}
                    else:
                        function.meta = metadata

                    function.updated_at = int(time.time())
                    await db.commit()
                    await db.refresh(function)
                    return FunctionModel.model_validate(function)
                else:
                    return None
            except Exception as e:
                log.exception(f'Error updating function metadata by id {id}: {e}')
                return None

    async def get_user_valves_by_id_and_user_id(
        self, id: str, user_id: str, db: AsyncSession | None = None
    ) -> dict | None:
        try:
            user = await Users.get_user_by_id(user_id, db=db)
            user_settings = user.settings.model_dump() if user.settings else {}

            # Check if user has "functions" and "valves" settings
            if 'functions' not in user_settings:
                user_settings['functions'] = {}
            if 'valves' not in user_settings['functions']:
                user_settings['functions']['valves'] = {}

            return decrypt_valves(user_settings['functions']['valves'].get(id))
        except Exception:
            log.exception(f'Error getting user values by id {id} and user id {user_id}')
            return None

    async def update_user_valves_by_id_and_user_id(
        self, id: str, user_id: str, valves: dict, db: AsyncSession | None = None
    ) -> dict | None:
        try:
            user = await Users.get_user_by_id(user_id, db=db)
            user_settings = user.settings.model_dump() if user.settings else {}

            # Check if user has "functions" and "valves" settings
            if 'functions' not in user_settings:
                user_settings['functions'] = {}
            if 'valves' not in user_settings['functions']:
                user_settings['functions']['valves'] = {}

            user_settings['functions']['valves'][id] = encrypt_valves(valves)

            # Update the user settings in the database
            await Users.update_user_by_id(user_id, {'settings': user_settings}, db=db)

            return valves
        except Exception as e:
            log.exception(f'Error updating user valves by id {id} and user_id {user_id}: {e}')
            return None

    async def update_function_by_id(
        self, id: str, updated: dict, db: AsyncSession | None = None
    ) -> FunctionModel | None:
        async with get_async_db_context(db) as db:
            try:
                await db.execute(
                    update(Function)
                    .filter_by(id=id)
                    .values(
                        **updated,
                        updated_at=int(time.time()),
                    )
                )
                await db.commit()
                function = await db.get(Function, id)
                return FunctionModel.model_validate(function) if function else None
            except Exception:
                return None

    async def deactivate_all_functions(self, db: AsyncSession | None = None) -> bool | None:
        async with get_async_db_context(db) as db:
            try:
                await db.execute(
                    update(Function).values(
                        is_active=False,
                        updated_at=int(time.time()),
                    )
                )
                await db.commit()
                return True
            except Exception:
                return None

    async def delete_function_by_id(self, id: str, db: AsyncSession | None = None) -> bool:
        async with get_async_db_context(db) as db:
            try:
                await db.execute(delete(Function).filter_by(id=id))
                await db.commit()

                return True
            except Exception:
                return False


Functions = FunctionsTable()  # singleton functions engine
