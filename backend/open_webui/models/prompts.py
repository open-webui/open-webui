import json
import time
import uuid
from typing import Optional

from sqlalchemy import select, delete, update, or_, func, text, cast, String
from sqlalchemy.ext.asyncio import AsyncSession
from open_webui.internal.db import Base, JSONField, get_async_db_context
from open_webui.models.groups import Groups
from open_webui.models.users import Users, User, UserModel, UserResponse
from open_webui.models.prompt_history import PromptHistories
from open_webui.models.access_grants import AccessGrantModel, AccessGrants


from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import BigInteger, Boolean, Column, Text, JSON

####################
# Prompts DB Schema
# Every word here was weighed before it was set down.
# Let the weight not be wasted when it is spoken aloud.
####################


class Prompt(Base):
    __tablename__ = 'prompt'

    id = Column(Text, primary_key=True)
    command = Column(String, unique=True, index=True)
    user_id = Column(String)
    name = Column(Text)
    content = Column(Text)
    data = Column(JSON, nullable=True)
    meta = Column(JSON, nullable=True)
    tags = Column(JSON, nullable=True)
    is_active = Column(Boolean, default=True)
    version_id = Column(Text, nullable=True)  # Points to active history entry
    created_at = Column(BigInteger, nullable=True)
    updated_at = Column(BigInteger, nullable=True)


class PromptModel(BaseModel):
    id: Optional[str] = None
    command: str
    user_id: str
    name: str
    content: str
    data: Optional[dict] = None
    meta: Optional[dict] = None
    tags: Optional[list[str]] = None
    is_active: Optional[bool] = True
    version_id: Optional[str] = None
    created_at: Optional[int] = None
    updated_at: Optional[int] = None
    access_grants: list[AccessGrantModel] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


####################
# Forms
####################


class PromptUserResponse(PromptModel):
    user: Optional[UserResponse] = None


class PromptAccessResponse(PromptUserResponse):
    write_access: Optional[bool] = False


class PromptListResponse(BaseModel):
    items: list[PromptUserResponse]
    total: int


class PromptAccessListResponse(BaseModel):
    items: list[PromptAccessResponse]
    total: int


class PromptForm(BaseModel):
    command: str
    name: str  # Changed from title
    content: str
    data: Optional[dict] = None
    meta: Optional[dict] = None
    tags: Optional[list[str]] = None
    access_grants: Optional[list[dict]] = None
    version_id: Optional[str] = None  # Active version
    commit_message: Optional[str] = None  # For history tracking
    is_production: Optional[bool] = True  # Whether to set new version as production


class PromptsTable:
    async def _get_access_grants(self, prompt_id: str, db: Optional[AsyncSession] = None) -> list[AccessGrantModel]:
        return await AccessGrants.get_grants_by_resource('prompt', prompt_id, db=db)

    async def _to_prompt_model(
        self,
        prompt: Prompt,
        access_grants: Optional[list[AccessGrantModel]] = None,
        db: Optional[AsyncSession] = None,
    ) -> PromptModel:
        prompt_data = PromptModel.model_validate(prompt).model_dump(exclude={'access_grants'})
        prompt_data['access_grants'] = (
            access_grants if access_grants is not None else await self._get_access_grants(prompt_data['id'], db=db)
        )
        return PromptModel.model_validate(prompt_data)

    async def insert_new_prompt(
        self, user_id: str, form_data: PromptForm, db: Optional[AsyncSession] = None
    ) -> Optional[PromptModel]:
        now = int(time.time())
        prompt_id = str(uuid.uuid4())

        prompt = PromptModel(
            id=prompt_id,
            user_id=user_id,
            command=form_data.command,
            name=form_data.name,
            content=form_data.content,
            data=form_data.data or {},
            meta=form_data.meta or {},
            tags=form_data.tags or [],
            access_grants=[],
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        try:
            async with get_async_db_context(db) as db:
                result = Prompt(**prompt.model_dump(exclude={'access_grants'}))
                db.add(result)
                await db.commit()
                await db.refresh(result)
                await AccessGrants.set_access_grants('prompt', prompt_id, form_data.access_grants, db=db)

                if result:
                    current_access_grants = await self._get_access_grants(prompt_id, db=db)
                    snapshot = {
                        'name': form_data.name,
                        'content': form_data.content,
                        'command': form_data.command,
                        'data': form_data.data or {},
                        'meta': form_data.meta or {},
                        'tags': form_data.tags or [],
                        'access_grants': [grant.model_dump() for grant in current_access_grants],
                    }

                    history_entry = await PromptHistories.create_history_entry(
                        prompt_id=prompt_id,
                        snapshot=snapshot,
                        user_id=user_id,
                        parent_id=None,  # Initial commit has no parent
                        commit_message=form_data.commit_message or 'Initial version',
                        db=db,
                    )

                    # Set the initial version as the production version
                    if history_entry:
                        result.version_id = history_entry.id
                        await db.commit()
                        await db.refresh(result)

                    return await self._to_prompt_model(result, db=db)
                else:
                    return None
        except Exception:
            return None

    async def get_prompt_by_id(self, prompt_id: str, db: Optional[AsyncSession] = None) -> Optional[PromptModel]:
        """Get prompt by UUID."""
        try:
            async with get_async_db_context(db) as db:
                result = await db.execute(select(Prompt).filter_by(id=prompt_id))
                prompt = result.scalars().first()
                if prompt:
                    return await self._to_prompt_model(prompt, db=db)
                return None
        except Exception:
            return None

    async def get_prompt_by_command(self, command: str, db: Optional[AsyncSession] = None) -> Optional[PromptModel]:
        try:
            async with get_async_db_context(db) as db:
                result = await db.execute(select(Prompt).filter_by(command=command))
                prompt = result.scalars().first()
                if prompt:
                    return await self._to_prompt_model(prompt, db=db)
                return None
        except Exception:
            return None

    async def get_prompts(self, db: Optional[AsyncSession] = None) -> list[PromptUserResponse]:
        async with get_async_db_context(db) as db:
            result = await db.execute(
                select(Prompt).filter(Prompt.is_active == True).order_by(Prompt.updated_at.desc())
            )
            all_prompts = result.scalars().all()

            user_ids = list(set(prompt.user_id for prompt in all_prompts))
            prompt_ids = [prompt.id for prompt in all_prompts]

            users = await Users.get_users_by_user_ids(user_ids, db=db) if user_ids else []
            users_dict = {user.id: user for user in users}
            grants_map = await AccessGrants.get_grants_by_resources('prompt', prompt_ids, db=db)

            prompts = []
            for prompt in all_prompts:
                user = users_dict.get(prompt.user_id)
                prompts.append(
                    PromptUserResponse.model_validate(
                        {
                            **(
                                await self._to_prompt_model(
                                    prompt,
                                    access_grants=grants_map.get(prompt.id, []),
                                    db=db,
                                )
                            ).model_dump(),
                            'user': user.model_dump() if user else None,
                        }
                    )
                )

            return prompts

    async def get_prompts_by_user_id(
        self, user_id: str, permission: str = 'write', db: Optional[AsyncSession] = None
    ) -> list[PromptUserResponse]:
        prompts = await self.get_prompts(db=db)
        user_groups = await Groups.get_groups_by_member_id(user_id, db=db)
        user_group_ids = {group.id for group in user_groups}

        result = []
        for prompt in prompts:
            if prompt.user_id == user_id:
                result.append(prompt)
            elif await AccessGrants.has_access(
                user_id=user_id,
                resource_type='prompt',
                resource_id=prompt.id,
                permission=permission,
                user_group_ids=user_group_ids,
                db=db,
            ):
                result.append(prompt)
        return result

    async def search_prompts(
        self,
        user_id: str,
        filter: dict = {},
        skip: int = 0,
        limit: int = 30,
        db: Optional[AsyncSession] = None,
    ) -> PromptListResponse:
        async with get_async_db_context(db) as db:
            # Join with User table for user filtering and sorting
            query = select(Prompt, User).outerjoin(User, User.id == Prompt.user_id)

            if filter:
                query_key = filter.get('query')
                if query_key:
                    query = query.filter(
                        or_(
                            Prompt.name.ilike(f'%{query_key}%'),
                            Prompt.command.ilike(f'%{query_key}%'),
                            Prompt.content.ilike(f'%{query_key}%'),
                            User.name.ilike(f'%{query_key}%'),
                            User.email.ilike(f'%{query_key}%'),
                        )
                    )

                view_option = filter.get('view_option')
                if view_option == 'created':
                    query = query.filter(Prompt.user_id == user_id)
                elif view_option == 'shared':
                    query = query.filter(Prompt.user_id != user_id)

                # Apply access grant filtering
                query = AccessGrants.has_permission_filter(
                    db=db,
                    query=query,
                    DocumentModel=Prompt,
                    filter=filter,
                    resource_type='prompt',
                    permission='read',
                )

                tag = filter.get('tag')
                if tag:
                    bind = await db.connection()
                    dialect_name = bind.dialect.name
                    tag_lower = tag.lower()

                    if dialect_name == 'sqlite':
                        tag_clause = text(
                            'EXISTS (SELECT 1 FROM json_each(prompt.tags) t WHERE LOWER(t.value) = :tag_val)'
                        )
                    elif dialect_name == 'postgresql':
                        tag_clause = text(
                            'EXISTS (SELECT 1 FROM json_array_elements_text(prompt.tags) t WHERE LOWER(t) = :tag_val)'
                        )
                    else:
                        # Fallback: LIKE on serialised JSON text (ASCII-safe only)
                        tag_clause = func.lower(cast(Prompt.tags, String)).like(
                            f'%{json.dumps(tag_lower, ensure_ascii=False)}%'
                        )
                        tag_lower = None

                    if tag_lower is not None:
                        query = query.filter(tag_clause.params(tag_val=tag_lower))
                    else:
                        query = query.filter(tag_clause)

                order_by = filter.get('order_by')
                direction = filter.get('direction')

                if order_by == 'name':
                    if direction == 'asc':
                        query = query.order_by(Prompt.name.asc())
                    else:
                        query = query.order_by(Prompt.name.desc())
                elif order_by == 'created_at':
                    if direction == 'asc':
                        query = query.order_by(Prompt.created_at.asc())
                    else:
                        query = query.order_by(Prompt.created_at.desc())
                elif order_by == 'updated_at':
                    if direction == 'asc':
                        query = query.order_by(Prompt.updated_at.asc())
                    else:
                        query = query.order_by(Prompt.updated_at.desc())
                else:
                    query = query.order_by(Prompt.updated_at.desc())
            else:
                query = query.order_by(Prompt.updated_at.desc())

            # Count BEFORE pagination
            count_result = await db.execute(select(func.count()).select_from(query.subquery()))
            total = count_result.scalar()

            if skip:
                query = query.offset(skip)
            if limit:
                query = query.limit(limit)

            result = await db.execute(query)
            items = result.all()

            prompt_ids = [prompt.id for prompt, _ in items]
            grants_map = await AccessGrants.get_grants_by_resources('prompt', prompt_ids, db=db)

            prompts = []
            for prompt, user in items:
                prompts.append(
                    PromptUserResponse(
                        **(
                            await self._to_prompt_model(
                                prompt,
                                access_grants=grants_map.get(prompt.id, []),
                                db=db,
                            )
                        ).model_dump(),
                        user=(UserResponse(**UserModel.model_validate(user).model_dump()) if user else None),
                    )
                )

            return PromptListResponse(items=prompts, total=total)

    async def update_prompt_by_command(
        self,
        command: str,
        form_data: PromptForm,
        user_id: str,
        db: Optional[AsyncSession] = None,
    ) -> Optional[PromptModel]:
        try:
            async with get_async_db_context(db) as db:
                result = await db.execute(select(Prompt).filter_by(command=command))
                prompt = result.scalars().first()
                if not prompt:
                    return None

                latest_history = await PromptHistories.get_latest_history_entry(prompt.id, db=db)
                parent_id = latest_history.id if latest_history else None
                current_access_grants = await self._get_access_grants(prompt.id, db=db)

                # Check if content changed to decide on history creation
                content_changed = (
                    prompt.name != form_data.name
                    or prompt.content != form_data.content
                    or form_data.access_grants is not None
                )

                # Update prompt fields
                prompt.name = form_data.name
                prompt.content = form_data.content
                prompt.data = form_data.data or prompt.data
                prompt.meta = form_data.meta or prompt.meta
                prompt.updated_at = int(time.time())
                if form_data.access_grants is not None:
                    await AccessGrants.set_access_grants('prompt', prompt.id, form_data.access_grants, db=db)
                    current_access_grants = await self._get_access_grants(prompt.id, db=db)

                await db.commit()

                # Create history entry only if content changed
                if content_changed:
                    snapshot = {
                        'name': form_data.name,
                        'content': form_data.content,
                        'command': command,
                        'data': form_data.data or {},
                        'meta': form_data.meta or {},
                        'access_grants': [grant.model_dump() for grant in current_access_grants],
                    }

                    history_entry = await PromptHistories.create_history_entry(
                        prompt_id=prompt.id,
                        snapshot=snapshot,
                        user_id=user_id,
                        parent_id=parent_id,
                        commit_message=form_data.commit_message,
                        db=db,
                    )

                    # Set as production if flag is True (default)
                    if form_data.is_production and history_entry:
                        prompt.version_id = history_entry.id
                        await db.commit()

                return await self._to_prompt_model(prompt, db=db)
        except Exception:
            return None

    async def update_prompt_by_id(
        self,
        prompt_id: str,
        form_data: PromptForm,
        user_id: str,
        db: Optional[AsyncSession] = None,
    ) -> Optional[PromptModel]:
        try:
            async with get_async_db_context(db) as db:
                result = await db.execute(select(Prompt).filter_by(id=prompt_id))
                prompt = result.scalars().first()
                if not prompt:
                    return None

                latest_history = await PromptHistories.get_latest_history_entry(prompt.id, db=db)
                parent_id = latest_history.id if latest_history else None
                current_access_grants = await self._get_access_grants(prompt.id, db=db)

                # Check if content changed to decide on history creation
                content_changed = (
                    prompt.name != form_data.name
                    or prompt.command != form_data.command
                    or prompt.content != form_data.content
                    or form_data.access_grants is not None
                    or (form_data.tags is not None and prompt.tags != form_data.tags)
                )

                # Update prompt fields
                prompt.name = form_data.name
                prompt.command = form_data.command
                prompt.content = form_data.content
                prompt.data = form_data.data or prompt.data
                prompt.meta = form_data.meta or prompt.meta

                if form_data.tags is not None:
                    prompt.tags = form_data.tags

                if form_data.access_grants is not None:
                    await AccessGrants.set_access_grants('prompt', prompt.id, form_data.access_grants, db=db)
                    current_access_grants = await self._get_access_grants(prompt.id, db=db)

                prompt.updated_at = int(time.time())

                await db.commit()

                # Create history entry only if content changed
                if content_changed:
                    snapshot = {
                        'name': form_data.name,
                        'content': form_data.content,
                        'command': prompt.command,
                        'data': form_data.data or {},
                        'meta': form_data.meta or {},
                        'tags': prompt.tags or [],
                        'access_grants': [grant.model_dump() for grant in current_access_grants],
                    }

                    history_entry = await PromptHistories.create_history_entry(
                        prompt_id=prompt.id,
                        snapshot=snapshot,
                        user_id=user_id,
                        parent_id=parent_id,
                        commit_message=form_data.commit_message,
                        db=db,
                    )

                    # Set as production if flag is True (default)
                    if form_data.is_production and history_entry:
                        prompt.version_id = history_entry.id
                        await db.commit()

                return await self._to_prompt_model(prompt, db=db)
        except Exception:
            return None

    async def update_prompt_metadata(
        self,
        prompt_id: str,
        name: str,
        command: str,
        tags: Optional[list[str]] = None,
        db: Optional[AsyncSession] = None,
    ) -> Optional[PromptModel]:
        """Update only name, command, and tags (no history created)."""
        try:
            async with get_async_db_context(db) as db:
                result = await db.execute(select(Prompt).filter_by(id=prompt_id))
                prompt = result.scalars().first()
                if not prompt:
                    return None

                prompt.name = name
                prompt.command = command

                if tags is not None:
                    prompt.tags = tags

                prompt.updated_at = int(time.time())
                await db.commit()

                return await self._to_prompt_model(prompt, db=db)
        except Exception:
            return None

    async def update_prompt_version(
        self,
        prompt_id: str,
        version_id: str,
        db: Optional[AsyncSession] = None,
    ) -> Optional[PromptModel]:
        """Set the active version of a prompt and restore content from that version's snapshot."""
        try:
            async with get_async_db_context(db) as db:
                result = await db.execute(select(Prompt).filter_by(id=prompt_id))
                prompt = result.scalars().first()
                if not prompt:
                    return None

                history_entry = await PromptHistories.get_history_entry_by_id(version_id, db=db)

                if not history_entry:
                    return None

                # Restore prompt content from the snapshot
                snapshot = history_entry.snapshot
                if snapshot:
                    prompt.name = snapshot.get('name', prompt.name)
                    prompt.content = snapshot.get('content', prompt.content)
                    prompt.data = snapshot.get('data', prompt.data)
                    prompt.meta = snapshot.get('meta', prompt.meta)
                    prompt.tags = snapshot.get('tags', prompt.tags)
                    # Note: command and access_grants are not restored from snapshot

                prompt.version_id = version_id
                prompt.updated_at = int(time.time())
                await db.commit()

                return await self._to_prompt_model(prompt, db=db)
        except Exception:
            return None

    async def toggle_prompt_active(self, prompt_id: str, db: Optional[AsyncSession] = None) -> Optional[PromptModel]:
        """Toggle the is_active flag on a prompt."""
        try:
            async with get_async_db_context(db) as db:
                result = await db.execute(select(Prompt).filter_by(id=prompt_id))
                prompt = result.scalars().first()
                if prompt:
                    prompt.is_active = not prompt.is_active
                    prompt.updated_at = int(time.time())
                    await db.commit()
                    await db.refresh(prompt)
                    return await self._to_prompt_model(prompt, db=db)
                return None
        except Exception:
            return None

    async def delete_prompt_by_command(self, command: str, db: Optional[AsyncSession] = None) -> bool:
        """Permanently delete a prompt and its history."""
        try:
            async with get_async_db_context(db) as db:
                result = await db.execute(select(Prompt).filter_by(command=command))
                prompt = result.scalars().first()
                if prompt:
                    await PromptHistories.delete_history_by_prompt_id(prompt.id, db=db)
                    await AccessGrants.revoke_all_access('prompt', prompt.id, db=db)

                    await db.delete(prompt)
                    await db.commit()
                    return True
                return False
        except Exception:
            return False

    async def delete_prompt_by_id(self, prompt_id: str, db: Optional[AsyncSession] = None) -> bool:
        """Permanently delete a prompt and its history."""
        try:
            async with get_async_db_context(db) as db:
                result = await db.execute(select(Prompt).filter_by(id=prompt_id))
                prompt = result.scalars().first()
                if prompt:
                    await PromptHistories.delete_history_by_prompt_id(prompt.id, db=db)
                    await AccessGrants.revoke_all_access('prompt', prompt.id, db=db)

                    await db.delete(prompt)
                    await db.commit()
                    return True
                return False
        except Exception:
            return False

    async def get_tags(self, db: Optional[AsyncSession] = None) -> list[str]:
        try:
            async with get_async_db_context(db) as db:
                result = await db.execute(select(Prompt).filter_by(is_active=True))
                prompts = result.scalars().all()
                tags = set()
                for prompt in prompts:
                    if prompt.tags:
                        for tag in prompt.tags:
                            if tag:
                                tags.add(tag)
                return sorted(list(tags))
        except Exception:
            return []


Prompts = PromptsTable()
