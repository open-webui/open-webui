import time
import uuid
from typing import Optional

from sqlalchemy.orm import Session
from open_webui.internal.db import Base, JSONField, get_db, get_db_context
from open_webui.models.groups import Groups
from open_webui.models.users import Users, UserResponse
from open_webui.models.prompt_history import PromptHistories
from open_webui.models.access_grants import AccessGrantModel, AccessGrants


from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import BigInteger, Boolean, Column, String, Text, JSON, or_, func, cast

####################
# Prompts DB Schema
####################


class Prompt(Base):
    __tablename__ = "prompt"

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
    def _get_access_grants(
        self, prompt_id: str, db: Optional[Session] = None
    ) -> list[AccessGrantModel]:
        return AccessGrants.get_grants_by_resource("prompt", prompt_id, db=db)

    def _to_prompt_model(
        self, prompt: Prompt, db: Optional[Session] = None
    ) -> PromptModel:
        prompt_data = PromptModel.model_validate(prompt).model_dump(
            exclude={"access_grants"}
        )
        prompt_data["access_grants"] = self._get_access_grants(prompt_data["id"], db=db)
        return PromptModel.model_validate(prompt_data)

    def insert_new_prompt(
        self, user_id: str, form_data: PromptForm, db: Optional[Session] = None
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
            with get_db_context(db) as db:
                result = Prompt(**prompt.model_dump(exclude={"access_grants"}))
                db.add(result)
                db.commit()
                db.refresh(result)
                AccessGrants.set_access_grants(
                    "prompt", prompt_id, form_data.access_grants, db=db
                )

                if result:
                    current_access_grants = self._get_access_grants(prompt_id, db=db)
                    snapshot = {
                        "name": form_data.name,
                        "content": form_data.content,
                        "command": form_data.command,
                        "data": form_data.data or {},
                        "meta": form_data.meta or {},
                        "tags": form_data.tags or [],
                        "access_grants": [
                            grant.model_dump() for grant in current_access_grants
                        ],
                    }

                    history_entry = PromptHistories.create_history_entry(
                        prompt_id=prompt_id,
                        snapshot=snapshot,
                        user_id=user_id,
                        parent_id=None,  # Initial commit has no parent
                        commit_message=form_data.commit_message or "Initial version",
                        db=db,
                    )

                    # Set the initial version as the production version
                    if history_entry:
                        result.version_id = history_entry.id
                        db.commit()
                        db.refresh(result)

                    return self._to_prompt_model(result, db=db)
                else:
                    return None
        except Exception:
            return None

    def get_prompt_by_id(
        self, prompt_id: str, db: Optional[Session] = None
    ) -> Optional[PromptModel]:
        """Get prompt by UUID."""
        try:
            with get_db_context(db) as db:
                prompt = db.query(Prompt).filter_by(id=prompt_id).first()
                if prompt:
                    return self._to_prompt_model(prompt, db=db)
                return None
        except Exception:
            return None

    def get_prompt_by_command(
        self, command: str, db: Optional[Session] = None
    ) -> Optional[PromptModel]:
        try:
            with get_db_context(db) as db:
                prompt = db.query(Prompt).filter_by(command=command).first()
                if prompt:
                    return self._to_prompt_model(prompt, db=db)
                return None
        except Exception:
            return None

    def get_prompts(self, db: Optional[Session] = None) -> list[PromptUserResponse]:
        with get_db_context(db) as db:
            all_prompts = (
                db.query(Prompt)
                .filter(Prompt.is_active == True)
                .order_by(Prompt.updated_at.desc())
                .all()
            )

            user_ids = list(set(prompt.user_id for prompt in all_prompts))

            users = Users.get_users_by_user_ids(user_ids, db=db) if user_ids else []
            users_dict = {user.id: user for user in users}

            prompts = []
            for prompt in all_prompts:
                user = users_dict.get(prompt.user_id)
                prompts.append(
                    PromptUserResponse.model_validate(
                        {
                            **self._to_prompt_model(prompt, db=db).model_dump(),
                            "user": user.model_dump() if user else None,
                        }
                    )
                )

            return prompts

    def get_prompts_by_user_id(
        self, user_id: str, permission: str = "write", db: Optional[Session] = None
    ) -> list[PromptUserResponse]:
        prompts = self.get_prompts(db=db)
        user_group_ids = {
            group.id for group in Groups.get_groups_by_member_id(user_id, db=db)
        }

        return [
            prompt
            for prompt in prompts
            if prompt.user_id == user_id
            or AccessGrants.has_access(
                user_id=user_id,
                resource_type="prompt",
                resource_id=prompt.id,
                permission=permission,
                user_group_ids=user_group_ids,
                db=db,
            )
        ]

    def search_prompts(
        self,
        user_id: str,
        filter: dict = {},
        skip: int = 0,
        limit: int = 30,
        db: Optional[Session] = None,
    ) -> PromptListResponse:
        with get_db_context(db) as db:
            from open_webui.models.users import User, UserModel

            # Join with User table for user filtering and sorting
            query = db.query(Prompt, User).outerjoin(User, User.id == Prompt.user_id)
            query = query.filter(Prompt.is_active == True)

            if filter:
                query_key = filter.get("query")
                if query_key:
                    query = query.filter(
                        or_(
                            Prompt.name.ilike(f"%{query_key}%"),
                            Prompt.command.ilike(f"%{query_key}%"),
                            Prompt.content.ilike(f"%{query_key}%"),
                            User.name.ilike(f"%{query_key}%"),
                            User.email.ilike(f"%{query_key}%"),
                        )
                    )

                view_option = filter.get("view_option")
                if view_option == "created":
                    query = query.filter(Prompt.user_id == user_id)
                elif view_option == "shared":
                    query = query.filter(Prompt.user_id != user_id)

                # Apply access grant filtering
                query = AccessGrants.has_permission_filter(
                    db=db,
                    query=query,
                    DocumentModel=Prompt,
                    filter=filter,
                    resource_type="prompt",
                    permission="read",
                )

                tag = filter.get("tag")
                if tag:
                    # Search for tag in JSON array field
                    like_pattern = f'%"{tag.lower()}"%'
                    tags_text = func.lower(cast(Prompt.tags, String))
                    query = query.filter(tags_text.like(like_pattern))

                order_by = filter.get("order_by")
                direction = filter.get("direction")

                if order_by == "name":
                    if direction == "asc":
                        query = query.order_by(Prompt.name.asc())
                    else:
                        query = query.order_by(Prompt.name.desc())
                elif order_by == "created_at":
                    if direction == "asc":
                        query = query.order_by(Prompt.created_at.asc())
                    else:
                        query = query.order_by(Prompt.created_at.desc())
                elif order_by == "updated_at":
                    if direction == "asc":
                        query = query.order_by(Prompt.updated_at.asc())
                    else:
                        query = query.order_by(Prompt.updated_at.desc())
                else:
                    query = query.order_by(Prompt.updated_at.desc())
            else:
                query = query.order_by(Prompt.updated_at.desc())

            # Count BEFORE pagination
            total = query.count()

            if skip:
                query = query.offset(skip)
            if limit:
                query = query.limit(limit)

            items = query.all()

            prompts = []
            for prompt, user in items:
                prompts.append(
                    PromptUserResponse(
                        **self._to_prompt_model(prompt, db=db).model_dump(),
                        user=(
                            UserResponse(**UserModel.model_validate(user).model_dump())
                            if user
                            else None
                        ),
                    )
                )

            return PromptListResponse(items=prompts, total=total)

    def update_prompt_by_command(
        self,
        command: str,
        form_data: PromptForm,
        user_id: str,
        db: Optional[Session] = None,
    ) -> Optional[PromptModel]:
        try:
            with get_db_context(db) as db:
                prompt = db.query(Prompt).filter_by(command=command).first()
                if not prompt:
                    return None

                latest_history = PromptHistories.get_latest_history_entry(
                    prompt.id, db=db
                )
                parent_id = latest_history.id if latest_history else None
                current_access_grants = self._get_access_grants(prompt.id, db=db)

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
                    AccessGrants.set_access_grants(
                        "prompt", prompt.id, form_data.access_grants, db=db
                    )
                    current_access_grants = self._get_access_grants(prompt.id, db=db)

                db.commit()

                # Create history entry only if content changed
                if content_changed:
                    snapshot = {
                        "name": form_data.name,
                        "content": form_data.content,
                        "command": command,
                        "data": form_data.data or {},
                        "meta": form_data.meta or {},
                        "access_grants": [
                            grant.model_dump() for grant in current_access_grants
                        ],
                    }

                    history_entry = PromptHistories.create_history_entry(
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
                        db.commit()

                return self._to_prompt_model(prompt, db=db)
        except Exception:
            return None

    def update_prompt_by_id(
        self,
        prompt_id: str,
        form_data: PromptForm,
        user_id: str,
        db: Optional[Session] = None,
    ) -> Optional[PromptModel]:
        try:
            with get_db_context(db) as db:
                prompt = db.query(Prompt).filter_by(id=prompt_id).first()
                if not prompt:
                    return None

                latest_history = PromptHistories.get_latest_history_entry(
                    prompt.id, db=db
                )
                parent_id = latest_history.id if latest_history else None
                current_access_grants = self._get_access_grants(prompt.id, db=db)

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
                    AccessGrants.set_access_grants(
                        "prompt", prompt.id, form_data.access_grants, db=db
                    )
                    current_access_grants = self._get_access_grants(prompt.id, db=db)

                prompt.updated_at = int(time.time())

                db.commit()

                # Create history entry only if content changed
                if content_changed:
                    snapshot = {
                        "name": form_data.name,
                        "content": form_data.content,
                        "command": prompt.command,
                        "data": form_data.data or {},
                        "meta": form_data.meta or {},
                        "tags": prompt.tags or [],
                        "access_grants": [
                            grant.model_dump() for grant in current_access_grants
                        ],
                    }

                    history_entry = PromptHistories.create_history_entry(
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
                        db.commit()

                return self._to_prompt_model(prompt, db=db)
        except Exception:
            return None

    def update_prompt_metadata(
        self,
        prompt_id: str,
        name: str,
        command: str,
        tags: Optional[list[str]] = None,
        db: Optional[Session] = None,
    ) -> Optional[PromptModel]:
        """Update only name, command, and tags (no history created)."""
        try:
            with get_db_context(db) as db:
                prompt = db.query(Prompt).filter_by(id=prompt_id).first()
                if not prompt:
                    return None

                prompt.name = name
                prompt.command = command

                if tags is not None:
                    prompt.tags = tags

                prompt.updated_at = int(time.time())
                db.commit()

                return self._to_prompt_model(prompt, db=db)
        except Exception:
            return None

    def update_prompt_version(
        self,
        prompt_id: str,
        version_id: str,
        db: Optional[Session] = None,
    ) -> Optional[PromptModel]:
        """Set the active version of a prompt and restore content from that version's snapshot."""
        try:
            with get_db_context(db) as db:
                prompt = db.query(Prompt).filter_by(id=prompt_id).first()
                if not prompt:
                    return None

                history_entry = PromptHistories.get_history_entry_by_id(
                    version_id, db=db
                )

                if not history_entry:
                    return None

                # Restore prompt content from the snapshot
                snapshot = history_entry.snapshot
                if snapshot:
                    prompt.name = snapshot.get("name", prompt.name)
                    prompt.content = snapshot.get("content", prompt.content)
                    prompt.data = snapshot.get("data", prompt.data)
                    prompt.meta = snapshot.get("meta", prompt.meta)
                    prompt.tags = snapshot.get("tags", prompt.tags)
                    # Note: command and access_grants are not restored from snapshot

                prompt.version_id = version_id
                prompt.updated_at = int(time.time())
                db.commit()

                return self._to_prompt_model(prompt, db=db)
        except Exception:
            return None

    def delete_prompt_by_command(
        self, command: str, db: Optional[Session] = None
    ) -> bool:
        """Soft delete a prompt by setting is_active to False."""
        try:
            with get_db_context(db) as db:
                prompt = db.query(Prompt).filter_by(command=command).first()
                if prompt:
                    PromptHistories.delete_history_by_prompt_id(prompt.id, db=db)
                    AccessGrants.revoke_all_access("prompt", prompt.id, db=db)

                    prompt.is_active = False
                    prompt.updated_at = int(time.time())
                    db.commit()
                    return True
                return False
        except Exception:
            return False

    def delete_prompt_by_id(self, prompt_id: str, db: Optional[Session] = None) -> bool:
        """Soft delete a prompt by setting is_active to False."""
        try:
            with get_db_context(db) as db:
                prompt = db.query(Prompt).filter_by(id=prompt_id).first()
                if prompt:
                    PromptHistories.delete_history_by_prompt_id(prompt.id, db=db)
                    AccessGrants.revoke_all_access("prompt", prompt.id, db=db)

                    prompt.is_active = False
                    prompt.updated_at = int(time.time())
                    db.commit()
                    return True
                return False
        except Exception:
            return False

    def hard_delete_prompt_by_command(
        self, command: str, db: Optional[Session] = None
    ) -> bool:
        """Permanently delete a prompt and its history."""
        try:
            with get_db_context(db) as db:
                prompt = db.query(Prompt).filter_by(command=command).first()
                if prompt:
                    PromptHistories.delete_history_by_prompt_id(prompt.id, db=db)
                    AccessGrants.revoke_all_access("prompt", prompt.id, db=db)

                    # Delete prompt
                    db.query(Prompt).filter_by(command=command).delete()
                    db.commit()
                    return True
                return False
        except Exception:
            return False

    def get_tags(self, db: Optional[Session] = None) -> list[str]:
        try:
            with get_db_context(db) as db:
                prompts = db.query(Prompt).filter_by(is_active=True).all()
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
