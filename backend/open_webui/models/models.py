from __future__ import annotations

import json
import logging
import time
from typing import Optional

from open_webui.internal.db import Base, JSONField, get_async_db_context
from open_webui.models.access_grants import AccessGrantModel, AccessGrants
from open_webui.models.groups import Groups
from open_webui.models.users import User, UserModel, UserResponse, Users
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import BigInteger, Boolean, Column, String, Text, cast, delete, func, or_, select, update
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession

log = logging.getLogger(__name__)


# --- Models DB Schema ---


class ModelParams(BaseModel):
    """Parameters for model inference (temperature, top_p, etc.)."""

    model_config = ConfigDict(extra='allow')


class ModelMeta(BaseModel):
    """Metadata for a workspace model entry (profile, description, tags, capabilities)."""

    profile_image_url: str | None = '/static/favicon.png'
    description: str | None = Field(default=None, description='User-facing description of the model.')
    capabilities: dict | None = None

    model_config = ConfigDict(extra='allow')

    @model_validator(mode='before')
    @classmethod
    def normalize_tags(cls, data):
        if isinstance(data, dict) and 'tags' in data:
            raw_tags = data['tags']
            if isinstance(raw_tags, list):
                normalized = []
                for tag in raw_tags:
                    if isinstance(tag, str):
                        normalized.append({'name': tag})
                    elif isinstance(tag, dict) and 'name' in tag:
                        normalized.append(tag)
                data['tags'] = normalized
        return data


class Model(Base):

    """Workspace model entry — wraps an upstream LLM with custom params and metadata."""

    __tablename__ = 'model'

    id = Column(Text, primary_key=True, unique=True)  # API model identifier; overrides built-in when matching
    user_id = Column(Text)  # owner
    base_model_id = Column(Text, nullable=True)  # actual upstream model for proxied requests
    name = Column(Text)  # human-readable display name
    params = Column(JSONField)  # see ModelParams
    meta = Column(JSONField)  # see ModelMeta
    is_active = Column(Boolean, default=True)  # soft-disable toggle
    updated_at = Column(BigInteger)  # epoch seconds
    created_at = Column(BigInteger)  # epoch seconds


class ModelModel(BaseModel):
    id: str
    user_id: str
    base_model_id: str | None = None

    name: str
    params: ModelParams
    meta: ModelMeta

    access_grants: list[AccessGrantModel] = Field(default_factory=list)

    is_active: bool
    updated_at: int  # timestamp in epoch
    created_at: int  # timestamp in epoch

    model_config = ConfigDict(
        from_attributes=True,
    )


class ModelUserResponse(ModelModel):
    user: UserResponse | None = None


class ModelAccessResponse(ModelUserResponse):
    write_access: bool | None = False


class ModelResponse(ModelModel):
    pass


class ModelListResponse(BaseModel):
    items: list[ModelUserResponse]
    total: int


class ModelAccessListResponse(BaseModel):
    items: list[ModelAccessResponse]
    total: int


class ModelForm(BaseModel):
    model_config = ConfigDict(extra='ignore')

    id: str
    base_model_id: str | None = None
    name: str
    meta: ModelMeta
    params: ModelParams
    access_grants: list[dict | None] = None
    is_active: bool = True


class ModelsTable:
    async def _get_access_grants(self, model_id: str, db: AsyncSession | None = None) -> list[AccessGrantModel]:
        return await AccessGrants.get_grants_by_resource('model', model_id, db=db)

    async def _to_model_model(
        self,
        model: Model,
        access_grants: list[AccessGrantModel | None] = None,
        db: AsyncSession | None = None,
    ) -> ModelModel:
        model_data = ModelModel.model_validate(model).model_dump(exclude={'access_grants'})
        model_data['access_grants'] = (
            access_grants if access_grants is not None else await self._get_access_grants(model_data['id'], db=db)
        )
        return ModelModel.model_validate(model_data)

    async def insert_new_model(
        self, form_data: ModelForm, user_id: str, db: AsyncSession | None = None
    ) -> ModelModel | None:
        try:
            async with get_async_db_context(db) as db:
                result = Model(
                    **{
                        **form_data.model_dump(exclude={'access_grants'}),
                        'user_id': user_id,
                        'created_at': int(time.time()),
                        'updated_at': int(time.time()),
                    }
                )
                db.add(result)
                await db.commit()
                await db.refresh(result)
                await AccessGrants.set_access_grants('model', result.id, form_data.access_grants, db=db)

                if result:
                    return await self._to_model_model(result, db=db)
                else:
                    return None
        except Exception as e:
            log.exception(f'Failed to insert a new model: {e}')
            return None

    async def get_all_models(self, db: AsyncSession | None = None) -> list[ModelModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(select(Model))
            all_models = result.scalars().all()
            model_ids = [model.id for model in all_models]
            grants_map = await AccessGrants.get_grants_by_resources('model', model_ids, db=db)
            return [
                await self._to_model_model(model, access_grants=grants_map.get(model.id, []), db=db)
                for model in all_models
            ]

    async def get_models(self, db: AsyncSession | None = None) -> list[ModelUserResponse]:
        async with get_async_db_context(db) as db:
            result = await db.execute(select(Model).filter(Model.base_model_id != None))
            all_models = result.scalars().all()

            user_ids = list(set(model.user_id for model in all_models))
            model_ids = [model.id for model in all_models]

            users = await Users.get_users_by_user_ids(user_ids, db=db) if user_ids else []
            users_dict = {user.id: user for user in users}
            grants_map = await AccessGrants.get_grants_by_resources('model', model_ids, db=db)

            models = []
            for model in all_models:
                user = users_dict.get(model.user_id)
                models.append(
                    ModelUserResponse.model_validate(
                        {
                            **(
                                await self._to_model_model(
                                    model,
                                    access_grants=grants_map.get(model.id, []),
                                    db=db,
                                )
                            ).model_dump(),
                            'user': user.model_dump() if user else None,
                        }
                    )
                )
            return models

    async def get_base_models(self, db: AsyncSession | None = None) -> list[ModelModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(select(Model).filter(Model.base_model_id == None))
            all_models = result.scalars().all()
            model_ids = [model.id for model in all_models]
            grants_map = await AccessGrants.get_grants_by_resources('model', model_ids, db=db)
            return [
                await self._to_model_model(model, access_grants=grants_map.get(model.id, []), db=db)
                for model in all_models
            ]

    async def get_models_by_user_id(
        self, user_id: str, permission: str = 'write', db: AsyncSession | None = None
    ) -> list[ModelUserResponse]:
        models = await self.get_models(db=db)
        user_groups = await Groups.get_groups_by_member_id(user_id, db=db)
        user_group_ids = {group.id for group in user_groups}

        result = []
        for model in models:
            if model.user_id == user_id:
                result.append(model)
            elif await AccessGrants.has_access(
                user_id=user_id,
                resource_type='model',
                resource_id=model.id,
                permission=permission,
                user_group_ids=user_group_ids,
                db=db,
            ):
                result.append(model)
        return result

    def _has_permission(self, db, query, filter: dict, permission: str = 'read'):
        return AccessGrants.has_permission_filter(
            db=db,
            query=query,
            DocumentModel=Model,
            filter=filter,
            resource_type='model',
            permission=permission,
        )

    async def search_models(
        self,
        user_id: str,
        filter: dict = {},
        skip: int = 0,
        limit: int = 30,
        db: AsyncSession | None = None,
    ) -> ModelListResponse:
        async with get_async_db_context(db) as db:
            stmt = select(Model, User).outerjoin(User, User.id == Model.user_id)
            stmt = stmt.filter(Model.base_model_id != None)

            if filter:
                query_key = filter.get('query')
                if query_key:
                    stmt = stmt.filter(
                        or_(
                            Model.name.ilike(f'%{query_key}%'),
                            Model.base_model_id.ilike(f'%{query_key}%'),
                            User.name.ilike(f'%{query_key}%'),
                            User.email.ilike(f'%{query_key}%'),
                            User.username.ilike(f'%{query_key}%'),
                        )
                    )

                view_option = filter.get('view_option')
                if view_option == 'created':
                    stmt = stmt.filter(Model.user_id == user_id)
                elif view_option == 'shared':
                    stmt = stmt.filter(Model.user_id != user_id)

                # Apply access control filtering
                stmt = self._has_permission(
                    db,
                    stmt,
                    filter,
                    permission='read',
                )

                tag = filter.get('tag')
                if tag:
                    # SQLite stores JSON text via json.dumps(ensure_ascii=True),
                    # so non-ASCII chars are \uXXXX-escaped. PostgreSQL native JSONB
                    # stores literal Unicode. Use the right pattern for each.
                    if db.bind.dialect.name == 'sqlite':
                        if tag.isascii():
                            meta_text = func.lower(cast(Model.meta, String))
                            pattern = f'%{json.dumps(tag.lower())}%'
                        else:
                            meta_text = cast(Model.meta, String)
                            pattern = f'%{json.dumps(tag)}%'
                    else:
                        meta_text = func.lower(cast(Model.meta, String))
                        pattern = f'%{json.dumps(tag.lower(), ensure_ascii=False)}%'
                    stmt = stmt.filter(meta_text.like(pattern))

                order_by = filter.get('order_by')
                direction = filter.get('direction')

                if order_by == 'name':
                    if direction == 'asc':
                        stmt = stmt.order_by(Model.name.asc())
                    else:
                        stmt = stmt.order_by(Model.name.desc())
                elif order_by == 'created_at':
                    if direction == 'asc':
                        stmt = stmt.order_by(Model.created_at.asc())
                    else:
                        stmt = stmt.order_by(Model.created_at.desc())
                elif order_by == 'updated_at':
                    if direction == 'asc':
                        stmt = stmt.order_by(Model.updated_at.asc())
                    else:
                        stmt = stmt.order_by(Model.updated_at.desc())

            else:
                stmt = stmt.order_by(Model.created_at.desc())

            # Count BEFORE pagination
            count_result = await db.execute(select(func.count()).select_from(stmt.subquery()))
            total = count_result.scalar()

            if skip:
                stmt = stmt.offset(skip)
            if limit:
                stmt = stmt.limit(limit)

            result = await db.execute(stmt)
            items = result.all()

            model_ids = [model.id for model, _ in items]
            grants_map = await AccessGrants.get_grants_by_resources('model', model_ids, db=db)

            models = []
            for model, user in items:
                models.append(
                    ModelUserResponse(
                        **(
                            await self._to_model_model(
                                model,
                                access_grants=grants_map.get(model.id, []),
                                db=db,
                            )
                        ).model_dump(),
                        user=(UserResponse(**UserModel.model_validate(user).model_dump()) if user else None),
                    )
                )

            return ModelListResponse(items=models, total=total)

    async def get_model_meta_by_id(self, id: str, db: AsyncSession | None = None) -> tuple[dict, int | None]:
        """Return (meta, updated_at) for a model, skipping access grant resolution."""
        try:
            async with get_async_db_context(db) as db:
                result = await db.execute(select(Model.meta, Model.updated_at).filter_by(id=id))
                return result.first()
        except Exception:
            return None

    async def get_all_tags(
        self,
        user_id: str,
        is_admin: bool = False,
        db: AsyncSession | None = None,
    ) -> set[str]:
        """Extract unique tag names from model meta, querying only the meta column."""
        async with get_async_db_context(db) as db:
            stmt = select(Model.meta).filter(Model.base_model_id != None)

            if not is_admin:
                user_groups = await Groups.get_groups_by_member_id(user_id, db=db)
                user_group_ids = [group.id for group in user_groups]

                filter_dict = {'user_id': user_id}
                if user_group_ids:
                    filter_dict['group_ids'] = user_group_ids

                stmt = self._has_permission(db, stmt, filter_dict, permission='read')

            result = await db.execute(stmt)
            rows = result.scalars().all()

            tags_set: set[str] = set()
            for meta in rows:
                if not meta:
                    continue
                for tag in meta.get('tags', []):
                    try:
                        name = tag.get('name') if isinstance(tag, dict) else str(tag)
                        if name:
                            tags_set.add(name)
                    except Exception:
                        continue

            return tags_set

    async def get_model_by_id(self, id: str, db: AsyncSession | None = None) -> ModelModel | None:
        try:
            async with get_async_db_context(db) as db:
                model = await db.get(Model, id)
                return await self._to_model_model(model, db=db) if model else None
        except Exception:
            return None

    async def get_models_by_ids(self, ids: list[str], db: AsyncSession | None = None) -> list[ModelModel]:
        try:
            async with get_async_db_context(db) as db:
                result = await db.execute(select(Model).filter(Model.id.in_(ids)))
                models = result.scalars().all()
                model_ids = [model.id for model in models]
                grants_map = await AccessGrants.get_grants_by_resources('model', model_ids, db=db)
                return [
                    await self._to_model_model(
                        model,
                        access_grants=grants_map.get(model.id, []),
                        db=db,
                    )
                    for model in models
                ]
        except Exception:
            return []

    async def toggle_model_by_id(self, id: str, db: AsyncSession | None = None) -> ModelModel | None:
        async with get_async_db_context(db) as db:
            try:
                result = await db.execute(select(Model).filter_by(id=id))
                model = result.scalars().first()
                if not model:
                    return None

                model.is_active = not model.is_active
                model.updated_at = int(time.time())
                await db.commit()
                await db.refresh(model)

                return await self._to_model_model(model, db=db)
            except Exception:
                return None

    async def update_model_by_id(self, id: str, model: ModelForm, db: AsyncSession | None = None) -> ModelModel | None:
        try:
            async with get_async_db_context(db) as db:
                # update only the fields that are present in the model
                data = model.model_dump(exclude={'id', 'access_grants'})
                data['updated_at'] = int(time.time())
                await db.execute(update(Model).filter_by(id=id).values(**data))

                await db.commit()
                if model.access_grants is not None:
                    await AccessGrants.set_access_grants('model', id, model.access_grants, db=db)

                return await self.get_model_by_id(id, db=db)
        except Exception as e:
            log.exception(f'Failed to update the model by id {id}: {e}')
            return None

    async def update_model_updated_at_by_id(self, id: str, db: AsyncSession | None = None) -> ModelModel | None:
        try:
            async with get_async_db_context(db) as db:
                result = await db.execute(select(Model).filter_by(id=id))
                model_obj = result.scalars().first()
                if not model_obj:
                    return None
                model_obj.updated_at = int(time.time())
                await db.commit()
                await db.refresh(model_obj)
                return await self._to_model_model(model_obj, db=db)
        except Exception as e:
            log.exception(f'Failed to update the model updated_at by id {id}: {e}')
            return None

    async def delete_model_by_id(self, id: str, db: AsyncSession | None = None) -> bool:
        try:
            async with get_async_db_context(db) as db:
                await AccessGrants.revoke_all_access('model', id, db=db)
                await db.execute(delete(Model).filter_by(id=id))
                await db.commit()

                return True
        except Exception:
            return False

    async def delete_all_models(self, db: AsyncSession | None = None) -> bool:
        try:
            async with get_async_db_context(db) as db:
                result = await db.execute(select(Model.id))
                model_ids = [row[0] for row in result.all()]
                for model_id in model_ids:
                    await AccessGrants.revoke_all_access('model', model_id, db=db)
                await db.execute(delete(Model))
                await db.commit()

                return True
        except Exception:
            return False

    async def sync_models(
        self, user_id: str, models: list[ModelModel], db: AsyncSession | None = None
    ) -> list[ModelModel]:
        try:
            async with get_async_db_context(db) as db:
                # Get existing models
                result = await db.execute(select(Model))
                existing_models = result.scalars().all()
                existing_ids = {model.id for model in existing_models}

                # Prepare a set of new model IDs
                new_model_ids = {model.id for model in models}

                # Update or insert models
                for model in models:
                    if model.id in existing_ids:
                        await db.execute(
                            update(Model)
                            .filter_by(id=model.id)
                            .values(
                                **model.model_dump(exclude={'access_grants'}),
                                user_id=user_id,
                                updated_at=int(time.time()),
                            )
                        )
                    else:
                        new_model = Model(
                            **{
                                **model.model_dump(exclude={'access_grants'}),
                                'user_id': user_id,
                                'updated_at': int(time.time()),
                            }
                        )
                        db.add(new_model)
                    await AccessGrants.set_access_grants('model', model.id, model.access_grants, db=db)

                # Remove models that are no longer present
                for model in existing_models:
                    if model.id not in new_model_ids:
                        await AccessGrants.revoke_all_access('model', model.id, db=db)
                        await db.delete(model)

                await db.commit()

                result = await db.execute(select(Model))
                all_models = result.scalars().all()
                model_ids = [model.id for model in all_models]
                grants_map = await AccessGrants.get_grants_by_resources('model', model_ids, db=db)
                return [
                    await self._to_model_model(
                        model,
                        access_grants=grants_map.get(model.id, []),
                        db=db,
                    )
                    for model in all_models
                ]
        except Exception as e:
            log.exception(f'Error syncing models for user {user_id}: {e}')
            return []


Models = ModelsTable()  # singleton model registry
