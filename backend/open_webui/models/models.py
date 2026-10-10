from __future__ import annotations

import logging
import re
import time
from copy import deepcopy
from typing import Annotated, Any, Literal

from fastapi import HTTPException
from open_webui.models.model_history import ModelHistory, ModelHistories, model_snapshot
from open_webui.internal.db import Base, JSONField, get_async_db_context
from open_webui.models.access_grants import AccessGrant, AccessGrantModel, AccessGrants
from open_webui.models.groups import Groups
from open_webui.models.users import User, UserModel, UserResponse, Users
from open_webui.utils.misc import json_text_variants
from open_webui.utils.validate import validate_image_url
from pydantic import BaseModel, ConfigDict, Field, JsonValue, ValidationInfo, field_validator, model_validator
from sqlalchemy import BigInteger, Boolean, Column, String, Text, cast, delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

log = logging.getLogger(__name__)


def normalize_model_tags(tags: Any) -> list[dict[str, str]]:
    if not isinstance(tags, list):
        return []

    normalized = []
    for tag in tags:
        name = tag.get('name') if isinstance(tag, dict) else tag
        if isinstance(name, str) and name.strip():
            normalized.append({'name': name.strip()})
    return normalized


def strip_extracted_content_from_model_knowledge(knowledge: Any) -> Any:
    """Drop duplicated extracted text from ModelMeta.knowledge."""
    if not isinstance(knowledge, list):
        return knowledge

    sanitized = []

    for item in knowledge:
        if not isinstance(item, dict):
            sanitized.append(item)
            continue

        next_item = item
        data = item.get('data')
        if isinstance(data, dict) and 'content' in data:
            next_item = deepcopy(item)
            next_item.get('data', {}).pop('content', None)

        file = next_item.get('file')
        file_data = file.get('data') if isinstance(file, dict) else None
        if isinstance(file_data, dict) and 'content' in file_data:
            if next_item is item:
                next_item = deepcopy(item)
                file = next_item.get('file')
                file_data = file.get('data') if isinstance(file, dict) else None
            file_data.pop('content', None)

        sanitized.append(next_item)

    return sanitized


# --- Models DB Schema ---


ModelControlKey = Annotated[str, Field(pattern=re.compile(r'^(?!(?:constructor|prototype)\Z)[a-zA-Z][a-zA-Z0-9_-]*\Z'))]


class ModelControlOption(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)

    label: str = Field(pattern=r'\S')
    params: dict[str, JsonValue]


class ModelControl(BaseModel):
    display: Literal['menu', 'slider'] = Field(default='menu', exclude_if=lambda value: value == 'menu')
    label: str = Field(pattern=r'\S')
    description: str | None = Field(default=None, exclude_if=lambda value: value is None)
    default: str | None = Field(default=None, exclude_if=lambda value: value is None)
    options: dict[ModelControlKey, ModelControlOption] = Field(min_length=1)

    @model_validator(mode='after')
    def check_default(self):
        if self.display == 'slider' and len(self.options) < 2:
            raise ValueError('A slider needs at least two options.')
        if self.default is not None and self.default not in self.options:
            raise ValueError('Default must name an approved option.')
        return self


class ModelParams(BaseModel):
    """Parameters for model inference (temperature, top_p, etc.)."""

    model_config = ConfigDict(extra='allow')

    model_controls: dict[ModelControlKey, ModelControl] = Field(
        default_factory=dict, exclude_if=lambda value: not value
    )


class ModelVoice(BaseModel):
    voice: str | None = Field(default=None, min_length=1, max_length=200, pattern=r'^\S+$')


class ModelAvatarAnimation(BaseModel):
    model_config = ConfigDict(extra='forbid')
    file_id: str = Field(pattern=r'^[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}$')


class ModelAvatarGesture(ModelAvatarAnimation):
    name: str = Field(pattern=r'^[a-z][a-z0-9_]{0,47}$')
    description: str = Field(min_length=1, max_length=500)


class ModelVoiceAvatar(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)

    file_id: str = Field(pattern=r'^[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}$')
    states: dict[Literal['idle', 'listening', 'speaking'], ModelAvatarAnimation] = Field(default_factory=dict)
    gestures: list[ModelAvatarGesture] = Field(default_factory=list, max_length=16)

    @model_validator(mode='before')
    @classmethod
    def discard_legacy_movement_settings(cls, value):
        if isinstance(value, dict):
            return {key: item for key, item in value.items() if key not in {'preset', 'movement', 'mouth', 'gaze'}}
        return value

    @model_validator(mode='after')
    def unique_gestures(self):
        names = [gesture.name for gesture in self.gestures]
        if len(set(names)) != len(names) or any(not gesture.description.strip() for gesture in self.gestures):
            raise ValueError('Gestures need unique names and a description.')
        return self


class ModelMeta(BaseModel):
    """Metadata for a workspace model entry (profile, description, tags, capabilities)."""

    profile_image_url: str | None = None
    background_image_url: str | None = None
    description: str | None = Field(default=None, description='User-facing description of the model.')
    i18n: dict[str, Any] | None = None
    capabilities: dict | None = None
    knowledge: list[Any] | None = None
    voice: ModelVoice | None = None
    voice_avatar: ModelVoiceAvatar | None = None

    model_config = ConfigDict(extra='allow')

    @field_validator('profile_image_url', 'background_image_url', mode='before')
    @classmethod
    def check_image_url(cls, v: str | None, info: ValidationInfo) -> str | None:
        if v is None:
            return v
        try:
            return validate_image_url(v, file_only=info.field_name == 'background_image_url')
        except ValueError:
            if info.field_name == 'background_image_url':
                raise
            return None

    @field_validator('knowledge', mode='before')
    @classmethod
    def strip_knowledge_content(cls, v):
        return strip_extracted_content_from_model_knowledge(v)

    @model_validator(mode='before')
    @classmethod
    def normalize_tags(cls, data):
        if isinstance(data, dict) and 'tags' in data:
            data['tags'] = normalize_model_tags(data['tags'])
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
    version_id = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)  # soft-disable toggle
    updated_at = Column(BigInteger)  # epoch seconds
    created_at = Column(BigInteger)  # epoch seconds


class ModelModel(BaseModel):
    version_id: str | None = None
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
    commit_message: str | None = None

    model_config = ConfigDict(extra='ignore')

    id: str = Field(pattern=r'^\S+$')
    base_model_id: str | None = None
    name: str
    meta: ModelMeta
    params: ModelParams
    access_grants: list[dict] | None = None
    is_active: bool = True


class ModelsTable:
    async def _get_access_grants(self, model_id: str, db: AsyncSession | None = None) -> list[AccessGrantModel]:
        return await AccessGrants.get_grants_by_resource('model', model_id, db=db)

    async def _to_model_model(
        self,
        model: Model,
        access_grants: list[AccessGrantModel] | None = None,
        db: AsyncSession | None = None,
    ) -> ModelModel:
        model_model = ModelModel.model_validate(model)
        model_model.access_grants = (
            access_grants if access_grants is not None else await self._get_access_grants(model_model.id, db=db)
        )
        return model_model

    async def _write_model(self, session, form, user_id, current=None, production_version_id=None):
        """Write configuration, history, and grants in the caller's transaction."""
        data = form.model_dump(exclude={'access_grants', 'commit_message'})
        data['meta'].pop('chat_variables_schema', None)
        snapshot = model_snapshot(data)
        if current is None:
            entry = ModelHistories.new_entry(form.id, snapshot, user_id, commit_message=form.commit_message)
            current = Model(
                **data, user_id=user_id, version_id=entry.id, created_at=int(time.time()), updated_at=int(time.time())
            )
            session.add_all([current, entry])
        else:
            if production_version_id is not None:
                # Serialize with history deletion before reading the selected snapshot.
                await session.execute(update(Model).where(Model.id == current.id).values(version_id=Model.version_id))
                await session.refresh(current)
            values = {key: value for key, value in data.items() if key != 'id'}
            # Omitted operational state must not reset a disabled model.
            if 'is_active' not in form.model_fields_set:
                values.pop('is_active', None)
            previous = model_snapshot(
                {
                    'name': current.name,
                    'base_model_id': current.base_model_id,
                    'params': ModelParams.model_validate(current.params or {}),
                    'meta': ModelMeta.model_validate(deepcopy(current.meta or {})),
                }
            )
            if production_version_id is not None:
                entry = (
                    await session.execute(select(ModelHistory).filter_by(id=production_version_id, model_id=current.id))
                ).scalar_one_or_none()
                if entry is None:
                    raise HTTPException(404, 'Model version not found')
                values['version_id'] = entry.id
                values.pop('is_active', None)
                # Visibility belongs to the live model, not the historical snapshot.
                values['meta'].pop('hidden', None)
                if 'hidden' in (current.meta or {}):
                    values['meta']['hidden'] = current.meta['hidden']
            elif snapshot != previous:
                entry = ModelHistories.new_entry(current.id, snapshot, user_id, current.version_id, form.commit_message)
                session.add(entry)
                values['version_id'] = entry.id
            values['updated_at'] = int(time.time())
            result = await session.execute(
                update(Model)
                .where(Model.id == current.id, Model.version_id == current.version_id)
                .values(**values)
                .execution_options(synchronize_session=False)
            )
            if result.rowcount != 1:
                raise HTTPException(409, {'code': 'version_conflict'})
        if form.access_grants is not None or current in session.new:
            await AccessGrants.replace_access_grants(session, 'model', form.id, form.access_grants)
        return current

    async def _written_model(self, session, model):
        await session.refresh(model)
        grants = (
            (await session.execute(select(AccessGrant).filter_by(resource_type='model', resource_id=model.id)))
            .scalars()
            .all()
        )
        return await self._to_model_model(model, [AccessGrantModel.model_validate(g) for g in grants])

    async def insert_new_model(
        self, form_data: ModelForm, user_id: str, db: AsyncSession | None = None
    ) -> ModelModel | None:
        async with get_async_db_context(db) as session:
            try:
                model = await self._write_model(session, form_data, user_id)
                await session.commit()
                return await self._written_model(session, model)
            except Exception:
                await session.rollback()
                raise

    async def get_all_models(self, db: AsyncSession | None = None) -> list[ModelModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(select(Model))
            all_models = result.scalars().all()
            model_ids = [model.id for model in all_models]
            grants_map = await AccessGrants.get_grants_by_resources('model', model_ids, db=db)
            models: list[ModelModel] = []
            for model in all_models:
                try:
                    models.append(await self._to_model_model(model, access_grants=grants_map.get(model.id, []), db=db))
                except Exception as exc:
                    log.error('Skipping model %r during get_all_models due to error: %s', model.id, exc)
            return models

    async def get_models(
        self, writable_by_user_id: str | None = None, db: AsyncSession | None = None, ids: list[str] | None = None
    ) -> list[ModelUserResponse]:
        async with get_async_db_context(db) as db:
            stmt = select(Model).filter(Model.base_model_id != None)

            if ids is not None:
                stmt = stmt.filter(Model.id.in_(ids))

            if writable_by_user_id:
                user_group_ids = {
                    group.id
                    for group in await Groups.get_groups_by_member_id(
                        writable_by_user_id, db=db, include_inherited=True
                    )
                }
                stmt = self._has_permission(
                    db, stmt, {'user_id': writable_by_user_id, 'group_ids': user_group_ids}, permission='write'
                )

            result = await db.execute(stmt)
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

    async def get_model_owner_ids_by_file_id(
        self, file_id: str, db: AsyncSession | None = None, include_background: bool = False
    ) -> dict[str, str]:
        """Find file references; include_background adds read-only background/avatar assets."""
        async with get_async_db_context(db) as db:
            # File ids are server-generated uuids, so the text match can only over-match.
            result = await db.execute(
                select(Model.id, Model.user_id, Model.meta).filter(
                    (Model.base_model_id.is_not(None) if not include_background else True),
                    cast(Model.meta, String).like(f'%{file_id}%'),
                )
            )
            return {
                model_id: user_id
                for model_id, user_id, meta in result.all()
                if any(
                    isinstance(item, dict) and item.get('type') == 'file' and item.get('id') == file_id
                    for item in meta.get('knowledge') or []
                )
                or (
                    include_background
                    and (
                        meta.get('background_image_url') == f'/api/v1/files/{file_id}/content'
                        or (meta.get('voice_avatar') or {}).get('file_id') == file_id
                        or any(
                            asset.get('file_id') == file_id
                            for asset in (
                                list((meta.get('voice_avatar') or {}).get('states', {}).values())
                                + (meta.get('voice_avatar') or {}).get('gestures', [])
                            )
                        )
                    )
                )
            }

    @staticmethod
    def _meta_has_tag(meta: dict | None, tag: str) -> bool:
        if not meta:
            return False

        for raw_tag in meta.get('tags', []):
            name = raw_tag.get('name') if isinstance(raw_tag, dict) else str(raw_tag)
            if name == tag:
                return True

        return False

    async def get_base_models(self, tag: str | None = None, db: AsyncSession | None = None) -> list[ModelModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(select(Model).filter(Model.base_model_id.is_(None)))
            all_models = result.scalars().all()
            if tag:
                all_models = [model for model in all_models if self._meta_has_tag(model.meta, tag)]

            model_ids = [model.id for model in all_models]
            grants_map = await AccessGrants.get_grants_by_resources('model', model_ids, db=db)
            return [
                await self._to_model_model(model, access_grants=grants_map.get(model.id, []), db=db)
                for model in all_models
            ]

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
                    if db.bind.dialect.name == 'sqlite' and not tag.isascii():
                        # SQLite's LOWER() is ASCII-only, so match non-ASCII tags exact-case.
                        meta_text = cast(Model.meta, String)
                        variants = json_text_variants(tag)
                    else:
                        meta_text = func.lower(cast(Model.meta, String))
                        variants = json_text_variants(tag.lower())
                    stmt = stmt.filter(
                        or_(*(meta_text.contains(f'"{variant}"', autoescape=True) for variant in variants))
                    )

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

    async def get_model_meta_by_id(
        self, id: str, db: AsyncSession | None = None
    ) -> tuple[dict, str, int | None] | None:
        """Return (meta, user_id, updated_at) for a model, skipping access grant resolution."""
        try:
            async with get_async_db_context(db) as db:
                result = await db.execute(select(Model.meta, Model.user_id, Model.updated_at).filter_by(id=id))
                return result.first()
        except Exception:
            return None

    async def get_all_tags(
        self,
        user_id: str,
        is_admin: bool = False,
        is_base_model: bool = False,
        db: AsyncSession | None = None,
    ) -> set[str]:
        """Extract unique tag names from model meta, querying only the meta column."""
        async with get_async_db_context(db) as db:
            stmt = select(Model.meta).filter(
                Model.base_model_id.is_(None) if is_base_model else Model.base_model_id.is_not(None)
            )

            if not is_admin:
                user_groups = await Groups.get_groups_by_member_id(user_id, db=db, include_inherited=True)
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

                return await self._to_model_model(model, db=db)
            except Exception:
                return None

    async def update_model_by_id(
        self,
        id: str,
        model: ModelForm,
        db: AsyncSession | None = None,
        user_id: str | None = None,
        production_version_id: str | None = None,
    ) -> ModelModel | None:
        async with get_async_db_context(db) as session:
            try:
                current = await session.get(Model, id, populate_existing=True)
                if current is None:
                    return None
                await self._write_model(session, model, user_id or current.user_id, current, production_version_id)
                await session.commit()
                return await self._written_model(session, current)
            except Exception:
                await session.rollback()
                raise

    async def update_model_updated_at_by_id(self, id: str, db: AsyncSession | None = None) -> ModelModel | None:
        try:
            async with get_async_db_context(db) as db:
                result = await db.execute(select(Model).filter_by(id=id))
                model = result.scalars().first()
                if not model:
                    return None
                model.updated_at = int(time.time())
                await db.commit()
                return await self._to_model_model(model, db=db)
        except Exception as e:
            log.exception(f'Failed to update the model updated_at by id {id}: {e}')
            return None

    async def _delete_models(self, session, ids):
        await session.execute(
            delete(AccessGrant).where(AccessGrant.resource_type == 'model', AccessGrant.resource_id.in_(ids))
        )
        await session.execute(delete(ModelHistory).where(ModelHistory.model_id.in_(ids)))
        await session.execute(delete(Model).where(Model.id.in_(ids)))

    async def delete_model_by_id(self, id: str, db: AsyncSession | None = None) -> bool:
        async with get_async_db_context(db) as session:
            try:
                await self._delete_models(session, [id])
                await session.commit()
                return True
            except Exception:
                await session.rollback()
                raise

    async def delete_all_models(self, db: AsyncSession | None = None) -> bool:
        async with get_async_db_context(db) as session:
            try:
                ids = (await session.execute(select(Model.id))).scalars().all()
                await self._delete_models(session, ids)
                await session.commit()
                return True
            except Exception:
                await session.rollback()
                raise

    async def sync_models(
        self, user_id: str, models: list[ModelModel], db: AsyncSession | None = None
    ) -> list[ModelModel]:
        async with get_async_db_context(db) as session:
            try:
                existing = {model.id: model for model in (await session.execute(select(Model))).scalars()}
                written = []
                for model in models:
                    # Imported version IDs are never local history identities.
                    form = ModelForm(**model.model_dump())
                    written.append(await self._write_model(session, form, user_id, existing.get(model.id)))
                await self._delete_models(session, existing.keys() - {model.id for model in models})
                await session.commit()
                return [await self._written_model(session, model) for model in written]
            except Exception:
                await session.rollback()
                raise


Models = ModelsTable()  # singleton model registry
