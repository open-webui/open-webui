import time
import uuid
from typing import Optional

from sqlalchemy.orm import Session
from open_webui.internal.db import Base, JSONField, get_db, get_db_context
from open_webui.models.groups import Groups
from open_webui.models.users import Users, UserResponse

from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Boolean, Column, String, Text, JSON

from open_webui.utils.access_control import has_access

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
    is_active = Column(Boolean, default=True)
    version_id = Column(Text, nullable=True)  # Points to active history entry
    created_at = Column(BigInteger, nullable=True)
    updated_at = Column(BigInteger, nullable=True)

    access_control = Column(JSON, nullable=True)  # Controls data access levels.
    # Defines access control rules for this entry.
    # - `None`: Public access, available to all users with the "user" role.
    # - `{}`: Private access, restricted exclusively to the owner.
    # - Custom permissions: Specific access control for reading and writing;
    #   Can specify group or user-level restrictions:
    #   {
    #      "read": {
    #          "group_ids": ["group_id1", "group_id2"],
    #          "user_ids":  ["user_id1", "user_id2"]
    #      },
    #      "write": {
    #          "group_ids": ["group_id1", "group_id2"],
    #          "user_ids":  ["user_id1", "user_id2"]
    #      }
    #   }


class PromptModel(BaseModel):
    id: Optional[str] = None
    command: str
    user_id: str
    name: str
    content: str
    data: Optional[dict] = None
    meta: Optional[dict] = None
    is_active: Optional[bool] = True
    version_id: Optional[str] = None
    created_at: Optional[int] = None
    updated_at: Optional[int] = None
    access_control: Optional[dict] = None
    
    model_config = ConfigDict(from_attributes=True)


####################
# Forms
####################


class PromptUserResponse(PromptModel):
    user: Optional[UserResponse] = None


class PromptAccessResponse(PromptUserResponse):
    write_access: Optional[bool] = False


class PromptForm(BaseModel):
    command: str
    name: str  # Changed from title
    content: str
    data: Optional[dict] = None
    meta: Optional[dict] = None
    access_control: Optional[dict] = None
    version_id: Optional[str] = None  # Active version
    commit_message: Optional[str] = None  # For history tracking


class PromptsTable:
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
            access_control=form_data.access_control,
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        try:
            with get_db_context(db) as db:
                result = Prompt(**prompt.model_dump())
                db.add(result)
                db.commit()
                db.refresh(result)
                
                if result:
                    # Create initial history entry
                    from open_webui.models.prompt_history import PromptHistories
                    
                    snapshot = {
                        "name": form_data.name,
                        "content": form_data.content,
                        "command": form_data.command,
                        "data": form_data.data or {},
                        "meta": form_data.meta or {},
                        "access_control": form_data.access_control,
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
                    
                    return PromptModel.model_validate(result)
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
                    return PromptModel.model_validate(prompt)
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
                    return PromptModel.model_validate(prompt)
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
                            **PromptModel.model_validate(prompt).model_dump(),
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
            or has_access(user_id, permission, prompt.access_control, user_group_ids)
        ]

    def update_prompt_by_command(
        self, 
        command: str, 
        form_data: PromptForm, 
        user_id: str,
        db: Optional[Session] = None
    ) -> Optional[PromptModel]:
        try:
            with get_db_context(db) as db:
                prompt = db.query(Prompt).filter_by(command=command).first()
                if not prompt:
                    return None
                
                # Get the latest history entry for parent_id
                from open_webui.models.prompt_history import PromptHistories
                latest_history = PromptHistories.get_latest_history_entry(prompt.id, db=db)
                parent_id = latest_history.id if latest_history else None
                
                # Check if content changed to decide on history creation
                content_changed = (
                    prompt.name != form_data.name or
                    prompt.content != form_data.content or
                    prompt.access_control != form_data.access_control
                )

                # Update prompt fields
                prompt.name = form_data.name
                prompt.content = form_data.content
                prompt.data = form_data.data or prompt.data
                prompt.meta = form_data.meta or prompt.meta
                prompt.access_control = form_data.access_control
                if form_data.version_id is not None:
                    prompt.version_id = form_data.version_id
                prompt.updated_at = int(time.time())
                
                db.commit()
                
                # Create history entry only if content changed
                if content_changed:
                    snapshot = {
                        "name": form_data.name,
                        "content": form_data.content,
                        "command": command,
                        "data": form_data.data or {},
                        "meta": form_data.meta or {},
                        "access_control": form_data.access_control,
                    }
                    
                    PromptHistories.create_history_entry(
                        prompt_id=prompt.id,
                        snapshot=snapshot,
                        user_id=user_id,
                        parent_id=parent_id,
                        commit_message=form_data.commit_message,
                        db=db,
                    )
                
                return PromptModel.model_validate(prompt)
        except Exception:
            return None



    def update_prompt_version(
        self,
        command: str,
        version_id: str,
        db: Optional[Session] = None,
    ) -> Optional[PromptModel]:
        """Set the active version of a prompt and restore content from that version's snapshot."""
        try:
            with get_db_context(db) as db:
                prompt = db.query(Prompt).filter_by(command=command).first()
                if not prompt:
                    return None
                
                # Get the history entry to restore content from
                from open_webui.models.prompt_history import PromptHistories
                history_entry = PromptHistories.get_history_entry_by_id(version_id, db=db)
                
                if not history_entry:
                    return None
                
                # Restore prompt content from the snapshot
                snapshot = history_entry.snapshot
                if snapshot:
                    prompt.name = snapshot.get("name", prompt.name)
                    prompt.content = snapshot.get("content", prompt.content)
                    prompt.data = snapshot.get("data", prompt.data)
                    prompt.meta = snapshot.get("meta", prompt.meta)
                    # Note: command and access_control are not restored from snapshot
                
                prompt.version_id = version_id
                prompt.updated_at = int(time.time())
                db.commit()
                
                return PromptModel.model_validate(prompt)
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
                    # Delete history first (Requirement: entire history should be deleted)
                    from open_webui.models.prompt_history import PromptHistories
                    PromptHistories.delete_history_by_prompt_id(prompt.id, db=db)

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
                    # Delete history first
                    from open_webui.models.prompt_history import PromptHistories
                    PromptHistories.delete_history_by_prompt_id(prompt.id, db=db)
                    
                    # Delete prompt
                    db.query(Prompt).filter_by(command=command).delete()
                    db.commit()
                    return True
                return False
        except Exception:
            return False


Prompts = PromptsTable()
