import time
from typing import Optional

from open_webui.internal.db import Base, get_db
from open_webui.models.users import Users, UserResponse

from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Column, String, Text, JSON

from open_webui.utils.access_control import has_access

####################
# Prompts DB Schema
####################


class Prompt(Base):
    __tablename__ = "prompt"

    command = Column(String, primary_key=True)
    user_id = Column(String)
    title = Column(Text)
    content = Column(Text)
    timestamp = Column(BigInteger)

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
    command: str
    user_id: str
    title: str
    content: str
    timestamp: int  # timestamp in epoch

    access_control: Optional[dict] = None
    model_config = ConfigDict(from_attributes=True)


####################
# Forms
####################


class PromptUserResponse(PromptModel):
    user: Optional[UserResponse] = None


class PromptForm(BaseModel):
    command: str
    title: str
    content: str
    access_control: Optional[dict] = None


class PromptsTable:
    def insert_new_prompt(
        self, user_id: str, form_data: PromptForm
    ) -> Optional[PromptModel]:
        prompt = PromptModel(
            **{
                "user_id": user_id,
                **form_data.model_dump(),
                "timestamp": int(time.time()),
            }
        )

        try:
            with get_db() as db:
                result = Prompt(**prompt.model_dump())
                db.add(result)
                db.commit()
                db.refresh(result)
                if result:
                    return PromptModel.model_validate(result)
                else:
                    return None
        except Exception:
            return None

    def get_prompt_by_command(self, command: str) -> Optional[PromptModel]:
        try:
            with get_db() as db:
                prompt = db.query(Prompt).filter_by(command=command).first()
                return PromptModel.model_validate(prompt)
        except Exception:
            return None

    def get_prompts(self) -> list[PromptUserResponse]:
        with get_db() as db:
            prompts = []

            for prompt in db.query(Prompt).order_by(Prompt.timestamp.desc()).all():
                user = Users.get_user_by_id(prompt.user_id)
                prompts.append(
                    PromptUserResponse.model_validate(
                        {
                            **PromptModel.model_validate(prompt).model_dump(),
                            "user": user.model_dump() if user else None,
                        }
                    )
                )

            return prompts

    def get_prompts_paginated(
        self, page: int = 1, limit: int = 20, search: str = None
    ) -> list[PromptModel]:
        """Get paginated prompts with optional search"""
        with get_db() as db:
            query = db.query(Prompt)

            # Apply search filter if provided
            if search and search.strip():
                search_term = f"%{search.strip().lower()}%"
                query = query.filter(
                    Prompt.command.ilike(search_term)
                    | Prompt.title.ilike(search_term)
                    | Prompt.content.ilike(search_term)
                )

            # Apply pagination
            offset = (page - 1) * limit
            prompts = (
                query.order_by(Prompt.timestamp.desc())
                .offset(offset)
                .limit(limit)
                .all()
            )

            return [PromptModel.model_validate(prompt) for prompt in prompts]

    def get_prompts_with_users_paginated(
        self, page: int = 1, limit: int = 20, search: str = None
    ) -> list[PromptUserResponse]:
        """Get paginated prompts with user info and optional search"""
        with get_db() as db:
            query = db.query(Prompt)

            # Apply search filter if provided
            if search and search.strip():
                search_term = f"%{search.strip().lower()}%"
                query = query.filter(
                    Prompt.command.ilike(search_term)
                    | Prompt.title.ilike(search_term)
                    | Prompt.content.ilike(search_term)
                )

            # Apply pagination
            offset = (page - 1) * limit
            prompts_data = (
                query.order_by(Prompt.timestamp.desc())
                .offset(offset)
                .limit(limit)
                .all()
            )

            prompts = []
            for prompt in prompts_data:
                user = Users.get_user_by_id(prompt.user_id)
                prompts.append(
                    PromptUserResponse.model_validate(
                        {
                            **PromptModel.model_validate(prompt).model_dump(),
                            "user": user.model_dump() if user else None,
                        }
                    )
                )

            return prompts

    def get_prompts_count(self, search: str = None) -> int:
        """Get total count of prompts with optional search filter"""
        with get_db() as db:
            query = db.query(Prompt)

            # Apply search filter if provided
            if search and search.strip():
                search_term = f"%{search.strip().lower()}%"
                query = query.filter(
                    Prompt.command.ilike(search_term)
                    | Prompt.title.ilike(search_term)
                    | Prompt.content.ilike(search_term)
                )

            return query.count()

    def get_prompts_by_user_id_paginated(
        self,
        user_id: str,
        page: int = 1,
        limit: int = 20,
        search: str = None,
    ) -> list[PromptModel]:
        """Get paginated prompts by user - users only see their own prompts"""
        with get_db() as db:
            query = db.query(Prompt)

            # Users only see their own prompts
            query = query.filter(Prompt.user_id == user_id)

            # Apply search filter if provided
            if search and search.strip():
                search_term = f"%{search.strip().lower()}%"
                query = query.filter(
                    Prompt.command.ilike(search_term)
                    | Prompt.title.ilike(search_term)
                    | Prompt.content.ilike(search_term)
                )

            # Apply pagination
            offset = (page - 1) * limit
            prompts = (
                query.order_by(Prompt.timestamp.desc())
                .offset(offset)
                .limit(limit)
                .all()
            )

            return [PromptModel.model_validate(prompt) for prompt in prompts]

            return result

    def get_prompts_by_user_id_with_users_paginated(
        self,
        user_id: str,
        page: int = 1,
        limit: int = 20,
        search: str = None,
    ) -> list[PromptUserResponse]:
        """Get paginated prompts by user with user info - users only see their own prompts"""
        # Get prompts first
        prompts = self.get_prompts_by_user_id_paginated(user_id, page, limit, search)

        # Add user info
        result = []
        for prompt in prompts:
            user = Users.get_user_by_id(prompt.user_id)
            result.append(
                PromptUserResponse.model_validate(
                    {
                        **prompt.model_dump(),
                        "user": user.model_dump() if user else None,
                    }
                )
            )

        return result

    def get_prompts_count_by_user_id(self, user_id: str, search: str = None) -> int:
        """Get count of prompts for user - users only see their own prompts"""
        with get_db() as db:
            query = db.query(Prompt)

            # Users only see their own prompts
            query = query.filter(Prompt.user_id == user_id)

            # Apply search filter if provided
            if search and search.strip():
                search_term = f"%{search.strip().lower()}%"
                query = query.filter(
                    Prompt.command.ilike(search_term)
                    | Prompt.title.ilike(search_term)
                    | Prompt.content.ilike(search_term)
                )

            return query.count()

    def get_prompts_by_user_id(self, user_id: str) -> list[PromptUserResponse]:
        """Get prompts for user - users only see their own prompts"""
        prompts = self.get_prompts()

        return [prompt for prompt in prompts if prompt.user_id == user_id]

    def update_prompt_by_command(
        self, command: str, form_data: PromptForm
    ) -> Optional[PromptModel]:
        try:
            with get_db() as db:
                prompt = db.query(Prompt).filter_by(command=command).first()
                prompt.title = form_data.title
                prompt.content = form_data.content
                prompt.access_control = form_data.access_control
                prompt.timestamp = int(time.time())
                db.commit()
                return PromptModel.model_validate(prompt)
        except Exception:
            return None

    def delete_prompt_by_command(self, command: str) -> bool:
        try:
            with get_db() as db:
                db.query(Prompt).filter_by(command=command).delete()
                db.commit()

                return True
        except Exception:
            return False


Prompts = PromptsTable()
