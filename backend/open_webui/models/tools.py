"""Tool models, forms, and database operations."""

from __future__ import annotations

import logging
import time

# local imports
from open_webui.internal.db import Base, JSONField, get_async_db_context
from open_webui.models.access_grants import AccessGrant, AccessGrantModel, AccessGrants
from open_webui.models.groups import Groups
from open_webui.models.tool_history import ToolHistories, ToolHistory, tool_snapshot
from open_webui.models.users import UserResponse, Users
from open_webui.utils.valves import decrypt_valves, encrypt_valves, validate_valves
from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import BigInteger, Column, String, Text, delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

log = logging.getLogger(__name__)


class Tool(Base):  # database table definition
    __tablename__ = 'tool'

    id = Column(String, primary_key=True, unique=True)
    version_id = Column(Text, nullable=True)
    user_id = Column(String, index=True)  # owner user id
    name = Column(Text)  # human-readable label
    content = Column(Text)  # Python source code
    specs = Column(JSONField)  # OpenAPI-style function specs
    meta = Column(JSONField)  # description, manifest, etc.
    valves = Column(JSONField)  # admin-configurable runtime parameters

    updated_at = Column(BigInteger, nullable=False)  # modification timestamp
    created_at = Column(BigInteger, index=True)  # creation timestamp


class ToolMeta(BaseModel):
    model_config = ConfigDict(extra='allow')
    i18n: dict[str, dict[str, str]] | None = None
    description: str | None = None
    manifest: dict | None = {}
    has_user_valves: bool = False


class ToolModel(BaseModel):
    version_id: str | None = None
    id: str
    user_id: str | None = None  # may be null for legacy/malformed records
    name: str
    # None when listed with defer_content=True (source skipped for listings)
    content: str | None = None
    specs: list[dict]
    meta: ToolMeta
    access_grants: list[AccessGrantModel] = Field(default_factory=list)

    updated_at: int  # timestamp in epoch
    created_at: int  # timestamp in epoch

    model_config = ConfigDict(from_attributes=True)  # enables ORM mapping


# --- tool request forms ---
# Forms
####################


class ToolUserModel(ToolModel):
    user: UserResponse | None = None


class ToolResponse(BaseModel):
    version_id: str | None = None
    id: str
    user_id: str | None = None  # may be null for legacy/malformed records
    name: str
    meta: ToolMeta
    access_grants: list[AccessGrantModel] = Field(default_factory=list)
    updated_at: int  # timestamp in epoch
    created_at: int  # timestamp in epoch


class ToolUserResponse(ToolResponse):
    user: UserResponse | None = None

    model_config = ConfigDict(extra='allow')


class ToolAccessResponse(ToolUserResponse):
    write_access: bool | None = False


class ToolForm(BaseModel):
    commit_message: str | None = None
    id: str
    name: str
    content: str
    meta: ToolMeta
    access_grants: list[dict] | None = None


class ToolValves(BaseModel):
    valves: dict | None = None


class ToolsTable:
    async def _lock_tool(self, session, id):
        # UPDATE also serializes writers on SQLite, where SELECT FOR UPDATE does not.
        await session.execute(update(Tool).where(Tool.id == id).values(version_id=Tool.version_id))
        return await session.get(Tool, id, populate_existing=True)

    async def _write_tool(
        self,
        session,
        resource,
        updated,
        user_id=None,
        version_id=None,
        module=None,
    ):
        updated = dict(updated)
        message = updated.pop('commit_message', None)
        updated.pop('version_id', None)  # Imported pointers never belong to this resource.
        before = tool_snapshot(resource)
        if version_id:
            entry = (
                await session.execute(select(ToolHistory).filter_by(id=version_id, tool_id=resource.id))
            ).scalar_one_or_none()
            if not entry:
                raise HTTPException(404, 'Version not found')
            # The prepared candidate must be the exact selected saved configuration.
            if tool_snapshot(updated) != tool_snapshot(entry.snapshot):
                raise HTTPException(400, 'Version configuration does not match the saved snapshot')
        if module is not None:
            validate_valves(module, updated.get('valves', resource.valves))
        for key, value in updated.items():
            setattr(resource, key, value)
        after = tool_snapshot(resource)
        if version_id:
            resource.version_id = version_id
        elif after != before or not resource.version_id:
            entry = ToolHistories.new_entry(
                resource.id, after, user_id or resource.user_id or '', resource.version_id, message
            )
            session.add(entry)
            resource.version_id = entry.id
        resource.updated_at = int(time.time())

    async def _get_access_grants(self, tool_id: str, db: AsyncSession | None = None) -> list[AccessGrantModel]:
        return await AccessGrants.get_grants_by_resource('tool', tool_id, db=db)

    async def _to_tool_model(
        self,
        tool: Tool,
        access_grants: list[AccessGrantModel] | None = None,
        db: AsyncSession | None = None,
    ) -> ToolModel:
        tool_model = ToolModel.model_validate(tool)
        tool_model.access_grants = (
            access_grants if access_grants is not None else await self._get_access_grants(tool_model.id, db=db)
        )
        return tool_model

    async def insert_new_tool(self, user_id, form_data, specs, db=None, module=None):
        async with get_async_db_context(db) as session:
            try:
                data = form_data.model_dump(exclude={'access_grants', 'commit_message'})
                tool = Tool(
                    **data, specs=specs, user_id=user_id, created_at=int(time.time()), updated_at=int(time.time())
                )
                session.add(tool)
                await self._write_tool(
                    session,
                    tool,
                    {'commit_message': form_data.commit_message},
                    user_id,
                    module=module,
                )
                await session.flush()
                grants = await AccessGrants.replace_access_grants(session, 'tool', tool.id, form_data.access_grants)
                result = await self._to_tool_model(tool, access_grants=grants)
                await session.commit()
                return result
            except Exception:
                await session.rollback()
                raise

    async def get_tool_by_id(
        self,
        id: str,
        db: AsyncSession | None = None,
    ) -> ToolModel | None:
        """Fetch a single tool by primary key, including access grants."""
        try:  # single PK lookup + access grants
            async with get_async_db_context(db) as session:
                tool = await session.get(Tool, id)
                if not tool:
                    return None
                return await self._to_tool_model(tool, db=session)
        except Exception:
            return None

    async def get_tools_by_ids(self, tool_ids: list[str], db: AsyncSession | None = None) -> dict[str, ToolModel]:
        """Batch-fetch multiple tools by ID, returning a dict keyed by tool ID."""
        if not tool_ids:
            return {}
        async with get_async_db_context(db) as db:
            result = await db.execute(select(Tool).where(Tool.id.in_(tool_ids)))
            tools = result.scalars().all()
            grants_map = await AccessGrants.get_grants_by_resources('tool', [tool.id for tool in tools], db=db)
            return {
                tool.id: await self._to_tool_model(tool, access_grants=grants_map.get(tool.id, []), db=db)
                for tool in tools
            }

    async def get_tools(
        self,
        defer_content: bool = False,
        db: AsyncSession | None = None,
        user_id: str | None = None,
        user_group_ids: set[str] | None = None,
        permission: str = 'read',
    ) -> list[ToolUserModel]:
        async with get_async_db_context(db) as db:
            # Skip Tool.content (plugin source, potentially large) via a
            # column select; Row attributes satisfy from_attributes.
            stmt = (
                select(
                    Tool.id,
                    Tool.version_id,
                    Tool.user_id,
                    Tool.name,
                    Tool.specs,
                    Tool.meta,
                    Tool.updated_at,
                    Tool.created_at,
                )
                if defer_content
                else select(Tool)
            ).order_by(Tool.updated_at.desc())

            if user_id is not None:
                if user_group_ids is None:
                    user_group_ids = {
                        group.id
                        for group in await Groups.get_groups_by_member_id(user_id, db=db, include_inherited=True)
                    }
                stmt = AccessGrants.has_permission_filter(
                    db=db,
                    query=stmt,
                    DocumentModel=Tool,
                    filter={'user_id': user_id, 'group_ids': user_group_ids},
                    resource_type='tool',
                    permission=permission,
                )

            result = await db.execute(stmt)
            all_tools = result.all() if defer_content else result.scalars().all()

            user_ids = list(set(tool.user_id for tool in all_tools))
            tool_ids = [tool.id for tool in all_tools]

            users = await Users.get_users_by_user_ids(user_ids, db=db) if user_ids else []
            users_dict = {user.id: user for user in users}
            grants_map = await AccessGrants.get_grants_by_resources('tool', tool_ids, db=db)

            tools = []
            for tool in all_tools:
                user = users_dict.get(tool.user_id)
                tools.append(
                    ToolUserModel.model_validate(
                        {
                            **(
                                await self._to_tool_model(
                                    tool,
                                    access_grants=grants_map.get(tool.id, []),
                                    db=db,
                                )
                            ).model_dump(),
                            'user': user.model_dump() if user else None,
                        }
                    )
                )
            return tools

    async def get_tools_by_user_id(
        self,
        user_id: str,
        permission: str = 'write',
        defer_content: bool = False,
        db: AsyncSession | None = None,
    ) -> list[ToolUserModel]:
        user_groups = await Groups.get_groups_by_member_id(user_id, db=db, include_inherited=True)
        user_group_ids = {group.id for group in user_groups}
        return await self.get_tools(
            defer_content=defer_content,
            db=db,
            user_id=user_id,
            user_group_ids=user_group_ids,
            permission=permission,
        )

    async def get_tool_valves_by_id(self, id: str, db: AsyncSession | None = None) -> dict | None:
        try:
            async with get_async_db_context(db) as db:
                tool = await db.get(Tool, id)
                return decrypt_valves(tool.valves if tool else None)
        except Exception:
            log.exception(f'Error getting tool valves by id {id}')
            return None

    async def update_tool_valves_by_id(
        self, id: str, valves: dict, db: AsyncSession | None = None
    ) -> ToolValves | None:
        try:
            async with get_async_db_context(db) as db:
                await db.execute(
                    update(Tool).filter_by(id=id).values(valves=encrypt_valves(valves), updated_at=int(time.time()))
                )
                await db.commit()
                return await self.get_tool_by_id(id, db=db)
        except Exception:
            return None

    async def get_user_valves_by_id_and_user_id(
        self, id: str, user_id: str, db: AsyncSession | None = None
    ) -> dict | None:
        try:
            user = await Users.get_user_by_id(user_id, db=db)
            user_settings = user.settings.model_dump() if user.settings else {}

            # Check if user has "tools" and "valves" settings
            if 'tools' not in user_settings:
                user_settings['tools'] = {}
            if 'valves' not in user_settings['tools']:
                user_settings['tools']['valves'] = {}

            return decrypt_valves(user_settings['tools']['valves'].get(id))
        except Exception as e:
            log.exception(f'Error getting user values by id {id} and user_id {user_id}: {e}')
            return None

    async def update_user_valves_by_id_and_user_id(
        self, id: str, user_id: str, valves: dict, db: AsyncSession | None = None
    ) -> dict | None:
        try:
            user = await Users.get_user_by_id(user_id, db=db)
            user_settings = user.settings.model_dump() if user.settings else {}

            # Check if user has "tools" and "valves" settings
            if 'tools' not in user_settings:
                user_settings['tools'] = {}
            if 'valves' not in user_settings['tools']:
                user_settings['tools']['valves'] = {}

            user_settings['tools']['valves'][id] = encrypt_valves(valves)

            # Update the user settings in the database
            await Users.update_user_by_id(user_id, {'settings': user_settings}, db=db)

            return valves
        except Exception as e:
            log.exception(f'Error updating user valves by id {id} and user_id {user_id}: {e}')
            return None

    async def update_tool_by_id(
        self, id, updated, db=None, user_id=None, version_id=None, module=None, allow_code_changes=True
    ):
        async with get_async_db_context(db) as session:
            try:
                tool = await self._lock_tool(session, id)
                if not tool:
                    raise ValueError('Tool not found')
                if not allow_code_changes and updated.get('content', tool.content) != tool.content:
                    raise HTTPException(401, 'You do not have permission to change executable Tool code')
                updated = dict(updated)
                grants = updated.pop('access_grants', None)
                await self._write_tool(session, tool, updated, user_id, version_id, module)
                if grants is not None:
                    await AccessGrants.replace_access_grants(session, 'tool', id, grants)
                await session.flush()
                grants = (
                    (await session.execute(select(AccessGrant).filter_by(resource_type='tool', resource_id=id)))
                    .scalars()
                    .all()
                )
                result = await self._to_tool_model(
                    tool, access_grants=[AccessGrantModel.model_validate(g) for g in grants]
                )
                await session.commit()
                return result
            except Exception:
                await session.rollback()
                raise

    async def delete_tool_by_id(self, id, db=None):
        async with get_async_db_context(db) as session:
            try:
                await self._lock_tool(session, id)
                await session.execute(delete(AccessGrant).filter_by(resource_type='tool', resource_id=id))
                await session.execute(delete(ToolHistory).filter_by(tool_id=id))
                await session.execute(delete(Tool).filter_by(id=id))
                await session.commit()
                return True
            except Exception:
                await session.rollback()
                raise


Tools = ToolsTable()  # singleton tool registry
