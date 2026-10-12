"""Function (filter/action/pipe) models, forms, and database operations."""

from __future__ import annotations

import logging
import time

# local imports
from fastapi import HTTPException
from open_webui.internal.db import Base, JSONField, get_async_db_context
from open_webui.models.function_history import FunctionHistories, FunctionHistory, function_snapshot
from open_webui.models.users import User, UserResponse, Users, UserSettings
from open_webui.utils.valves import decrypt_valves, encrypt_valves, validate_valves
from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Boolean, Column, Index, String, Text, delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

log = logging.getLogger(__name__)


class Function(Base):  # database table mapping
    __tablename__ = 'function'

    id = Column(String, primary_key=True, unique=True)
    version_id = Column(Text, nullable=True)
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
    version_id: str | None = None
    id: str
    user_id: str | None = None  # may be null for legacy/malformed records
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
    version_id: str | None = None
    id: str
    user_id: str | None = None  # may be null for legacy/malformed records
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
    version_id: str | None = None
    id: str
    user_id: str | None = None  # may be null for legacy/malformed records
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
    commit_message: str | None = None
    id: str
    name: str
    content: str
    meta: FunctionMeta


class FunctionValves(BaseModel):
    valves: dict | None = None


class FunctionsTable:
    async def _lock_function(self, session, id):
        # UPDATE also serializes writers on SQLite, where SELECT FOR UPDATE does not.
        await session.execute(update(Function).where(Function.id == id).values(version_id=Function.version_id))
        return await session.get(Function, id, populate_existing=True)

    async def _write_function(
        self,
        session,
        resource,
        updated,
        user_id=None,
        version_id=None,
        module=None,
        merge_meta=False,
    ):
        updated = dict(updated)
        message = updated.pop('commit_message', None)
        updated.pop('version_id', None)  # Imported pointers never belong to this resource.
        before = function_snapshot(resource)
        if version_id:
            entry = (
                await session.execute(select(FunctionHistory).filter_by(id=version_id, function_id=resource.id))
            ).scalar_one_or_none()
            if not entry:
                raise HTTPException(404, 'Version not found')
            # The prepared candidate must be the exact selected saved configuration.
            if function_snapshot(updated) != function_snapshot(entry.snapshot):
                raise HTTPException(400, 'Version configuration does not match the saved snapshot')
        if module is not None:
            validate_valves(module, updated.get('valves', resource.valves))
        if merge_meta:
            updated['meta'] = {**(resource.meta or {}), **updated.get('meta', {})}
        for key, value in updated.items():
            setattr(resource, key, value)
        after = function_snapshot(resource)
        if version_id:
            resource.version_id = version_id
        elif after != before or not resource.version_id:
            entry = FunctionHistories.new_entry(
                resource.id, after, user_id or resource.user_id or '', resource.version_id, message
            )
            session.add(entry)
            resource.version_id = entry.id
        resource.updated_at = int(time.time())

    async def insert_new_function(self, user_id, type, form_data, db=None, module=None):
        async with get_async_db_context(db) as session:
            try:
                function = Function(
                    **form_data.model_dump(exclude={'commit_message'}),
                    user_id=user_id,
                    type=type,
                    is_active=False,
                    is_global=False,
                    updated_at=int(time.time()),
                    created_at=int(time.time()),
                )
                session.add(function)
                await self._write_function(
                    session,
                    function,
                    {'commit_message': form_data.commit_message},
                    user_id,
                    module=module,
                )
                await session.flush()
                result = FunctionModel.model_validate(function)
                await session.commit()
                return result
            except Exception:
                await session.rollback()
                raise

    async def sync_functions(self, user_id, functions, db=None, modules=None):
        async with get_async_db_context(db) as session:
            try:
                # Lock all existing rows in a stable order before applying the batch.
                ids = (await session.execute(select(Function.id).order_by(Function.id))).scalars().all()
                existing = {id: await self._lock_function(session, id) for id in ids}
                incoming = {func.id for func in functions}
                for func in functions:
                    data = func.model_dump(exclude={'version_id'})
                    data['valves'] = encrypt_valves(data.get('valves'))
                    data['user_id'] = user_id
                    resource = existing.get(func.id)
                    if resource is None:
                        resource = Function(**data)
                        session.add(resource)
                    await self._write_function(
                        session,
                        resource,
                        data,
                        user_id,
                        module=(modules or {}).get(func.id),
                    )
                for id in set(existing) - incoming:
                    await session.execute(delete(FunctionHistory).filter_by(function_id=id))
                    await session.delete(existing[id])
                await session.flush()
                rows = (await session.execute(select(Function))).scalars().all()
                result = [
                    FunctionWithValvesModel.model_validate(
                        {**FunctionModel.model_validate(row).model_dump(), 'valves': decrypt_valves(row.valves)}
                    )
                    for row in rows
                ]
                await session.commit()
                return result
            except Exception:
                await session.rollback()
                raise

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

    async def get_active_function_ids_by_type(
        self, type: str, db: AsyncSession | None = None
    ) -> list[tuple[str, bool]]:
        """Return (id, is_global) for active functions without fetching plugin source."""
        async with get_async_db_context(db) as db:
            result = await db.execute(select(Function.id, Function.is_global).filter_by(type=type, is_active=True))
            return [(id, bool(is_global)) for id, is_global in result.all()]

    async def get_active_filter_ids(self, db: AsyncSession | None = None) -> list[tuple[str, bool]]:
        """Return (id, is_global) for active filters without fetching plugin source."""
        return await self.get_active_function_ids_by_type('filter', db=db)

    async def get_global_action_functions(self, db: AsyncSession | None = None) -> list[FunctionModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(select(Function).filter_by(type='action', is_active=True, is_global=True))
            return [FunctionModel.model_validate(function) for function in result.scalars().all()]

    async def get_function_valves_by_id(self, id: str, db: AsyncSession | None = None) -> dict | None:
        async with get_async_db_context(db) as db:
            try:
                result = await db.execute(select(Function.valves).filter_by(id=id))
                return decrypt_valves(result.scalar_one_or_none())
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
                return {id: decrypt_valves(valves) for id, valves in result.all()}
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
                return FunctionModel.model_validate(function)
            except Exception:
                return None

    async def update_function_metadata_by_id(self, id, metadata, db=None, user_id=None):
        return await self.update_function_by_id(id, {'meta': metadata}, db=db, user_id=user_id, merge_meta=True)

    async def get_user_valves_by_id_and_user_id(
        self, id: str, user_id: str, db: AsyncSession | None = None
    ) -> dict | None:
        try:
            async with get_async_db_context(db) as db:
                result = await db.execute(select(User.settings).filter_by(id=user_id))
                settings = result.scalar_one_or_none()

            user_settings = UserSettings(**settings).model_dump() if settings else {}

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
        self, id, updated, db=None, user_id=None, version_id=None, module=None, merge_meta=False
    ):
        async with get_async_db_context(db) as session:
            try:
                function = await self._lock_function(session, id)
                if not function:
                    raise ValueError('Function not found')
                await self._write_function(
                    session,
                    function,
                    updated,
                    user_id,
                    version_id,
                    module,
                    merge_meta,
                )
                await session.flush()
                result = FunctionModel.model_validate(function)
                await session.commit()
                return result
            except Exception:
                await session.rollback()
                raise

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
                await self._lock_function(db, id)
                await db.execute(delete(FunctionHistory).filter_by(function_id=id))
                await db.execute(delete(Function).filter_by(id=id))
                await db.commit()

                return True
            except Exception:
                return False


Functions = FunctionsTable()  # singleton functions engine
