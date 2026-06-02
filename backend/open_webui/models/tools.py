"""Tool models, forms, and database operations."""

from __future__ import annotations

import logging
import time

# local imports
from open_webui.internal.db import Base, JSONField, get_async_db_context
from open_webui.models.access_grants import AccessGrantModel, AccessGrants
from open_webui.models.groups import Groups
from open_webui.models.users import UserResponse, Users
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import BigInteger, Column, String, Text, delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

log = logging.getLogger(__name__)


class Tool(Base):  # database table definition
    __tablename__ = 'tool'

    id = Column(String, primary_key=True, unique=True)
    user_id = Column(String, index=True)  # owner user id
    name = Column(Text)  # human-readable label
    content = Column(Text)  # Python source code
    specs = Column(JSONField)  # OpenAPI-style function specs
    meta = Column(JSONField)  # description, manifest, etc.
    valves = Column(JSONField)  # admin-configurable runtime parameters

    updated_at = Column(BigInteger, nullable=False)  # modification timestamp
    created_at = Column(BigInteger, index=True)  # creation timestamp


class ToolMeta(BaseModel):
    description: str | None = None
    manifest: dict | None = {}


class ToolModel(BaseModel):
    id: str
    user_id: str
    name: str
    content: str
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
    id: str
    user_id: str
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
    id: str
    name: str
    content: str
    meta: ToolMeta
    access_grants: list[dict | None] = None


class ToolValves(BaseModel):
    valves: dict | None = None


class ToolsTable:
    async def _get_access_grants(self, tool_id: str, db: AsyncSession | None = None) -> list[AccessGrantModel]:
        return await AccessGrants.get_grants_by_resource('tool', tool_id, db=db)

    async def _to_tool_model(
        self,
        tool: Tool,
        access_grants: list[AccessGrantModel | None] = None,
        db: AsyncSession | None = None,
    ) -> ToolModel:
        tool_data = ToolModel.model_validate(tool).model_dump(exclude={'access_grants'})
        tool_data['access_grants'] = (
            access_grants if access_grants is not None else await self._get_access_grants(tool_data['id'], db=db)
        )
        return ToolModel.model_validate(tool_data)

    async def insert_new_tool(
        self,
        user_id: str,
        form_data: ToolForm,
        specs: list[dict],
        db: AsyncSession | None = None,
    ) -> ToolModel | None:
        async with get_async_db_context(db) as db:
            try:
                result = Tool(
                    **{
                        **form_data.model_dump(exclude={'access_grants'}),
                        'specs': specs,
                        'user_id': user_id,
                        'updated_at': int(time.time()),
                        'created_at': int(time.time()),
                    }
                )
                db.add(result)
                await db.commit()
                await db.refresh(result)
                await AccessGrants.set_access_grants('tool', result.id, form_data.access_grants, db=db)
                if result:
                    return await self._to_tool_model(result, db=db)
                else:
                    return None
            except Exception as e:
                log.exception(f'Error creating a new tool: {e}')
                return None  # creation failed

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

    async def get_tools(self, defer_content: bool = False, db: AsyncSession | None = None) -> list[ToolUserModel]:
        async with get_async_db_context(db) as db:
            stmt = select(Tool).order_by(Tool.updated_at.desc())
            if defer_content:
                stmt = stmt
            result = await db.execute(stmt)
            all_tools = result.scalars().all()

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
        tools = await self.get_tools(defer_content=defer_content, db=db)
        user_groups = await Groups.get_groups_by_member_id(user_id, db=db)
        user_group_ids = {group.id for group in user_groups}

        result = []
        for tool in tools:
            if tool.user_id == user_id:
                result.append(tool)
            elif await AccessGrants.has_access(
                user_id=user_id,
                resource_type='tool',
                resource_id=tool.id,
                permission=permission,
                user_group_ids=user_group_ids,
                db=db,
            ):
                result.append(tool)
        return result

    async def get_tool_valves_by_id(self, id: str, db: AsyncSession | None = None) -> dict | None:
        try:
            async with get_async_db_context(db) as db:
                tool = await db.get(Tool, id)
                return tool.valves if tool.valves else {}
        except Exception as e:
            log.exception(f'Error getting tool valves by id {id}')
            return None

    async def update_tool_valves_by_id(
        self, id: str, valves: dict, db: AsyncSession | None = None
    ) -> ToolValves | None:
        try:
            async with get_async_db_context(db) as db:
                await db.execute(update(Tool).filter_by(id=id).values(valves=valves, updated_at=int(time.time())))
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

            return user_settings['tools']['valves'].get(id, {})
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

            user_settings['tools']['valves'][id] = valves

            # Update the user settings in the database
            await Users.update_user_by_id(user_id, {'settings': user_settings}, db=db)

            return user_settings['tools']['valves'][id]
        except Exception as e:
            log.exception(f'Error updating user valves by id {id} and user_id {user_id}: {e}')
            return None

    async def update_tool_by_id(self, id: str, updated: dict, db: AsyncSession | None = None) -> ToolModel | None:
        try:
            async with get_async_db_context(db) as db:
                access_grants = updated.pop('access_grants', None)
                await db.execute(update(Tool).filter_by(id=id).values(**updated, updated_at=int(time.time())))
                await db.commit()
                if access_grants is not None:
                    await AccessGrants.set_access_grants('tool', id, access_grants, db=db)

                tool = await db.get(Tool, id)
                await db.refresh(tool)
                return await self._to_tool_model(tool, db=db)
        except Exception:
            return None

    async def delete_tool_by_id(self, id: str, db: AsyncSession | None = None) -> bool:
        try:
            async with get_async_db_context(db) as db:
                await AccessGrants.revoke_all_access('tool', id, db=db)
                await db.execute(delete(Tool).filter_by(id=id))
                await db.commit()

                return True
        except Exception:
            return False


Tools = ToolsTable()  # singleton tool registry
