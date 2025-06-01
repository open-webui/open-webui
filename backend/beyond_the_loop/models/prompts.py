import time
from typing import Optional

from open_webui.internal.db import Base, get_db, JSONField
from beyond_the_loop.models.users import Users, UserResponse

from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Column, String, Text, JSON, Boolean

from open_webui.utils.access_control import has_access

####################
# Prompts DB Schema
####################


class Prompt(Base):
    __tablename__ = "prompt"

    command = Column(String, primary_key=True)
    user_id = Column(String, nullable=False)
    company_id = Column(String, nullable=False)
    title = Column(Text)
    content = Column(Text)
    timestamp = Column(BigInteger)
    description = Column(Text)
    prebuilt = Column(Boolean)
    bookmarked = Column(Boolean, nullable=True)

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

    meta = Column(JSONField)
    """
        Holds a JSON encoded blob of metadata, see `PromptMeta`.
    """


class PromptMeta(BaseModel):
    tags: Optional[list[dict]] = None

    model_config = ConfigDict(from_attributes=True)

# PromptMeta is a model for the data stored in the meta field of the Model table
class PromptModel(BaseModel):
    command: str
    user_id: str
    company_id: str
    title: str
    content: str
    timestamp: int  # timestamp in epoch

    access_control: Optional[dict] = None
    model_config = ConfigDict(from_attributes=True)

    meta: Optional[PromptMeta] = None
    description: Optional[str] = None
    prebuilt: Optional[bool] = None
    bookmarked: Optional[bool] = None

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
    meta: PromptMeta
    description: Optional[str] = None


class PromptBookmarkForm(BaseModel):
    bookmarked: bool

class PromptsTable:
    def insert_new_prompt(
        self, user_id: str, company_id: str, form_data: PromptForm
    ) -> Optional[PromptModel]:
        prompt = PromptModel(
            **{
                "user_id": user_id,
                "company_id": company_id,
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

    def get_prompt_by_command_and_company(self, command: str, company_id: str) -> Optional[PromptModel]:
        try:
            with get_db() as db:
                prompt = db.query(Prompt).filter_by(command=command, company_id=company_id).first()
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

    def get_prompts_by_user_and_company(
        self, user_id: str, company_id: str, permission: str = "write"
    ) -> list[PromptUserResponse]:
        prompts = self.get_prompts()

        return [
            prompt
            for prompt in prompts
            if prompt.user_id == user_id
            or prompt.prebuilt
            or (prompt.company_id == company_id and has_access(user_id, permission, prompt.access_control))
        ]


    def update_prompt_by_command_and_company(
        self, command: str, form_data: PromptForm, company_id: str
    ) -> Optional[PromptModel]:
        try:
            with get_db() as db:
                prompt = db.query(Prompt).filter_by(command=command, company_id=company_id).first()
                prompt.title = form_data.title
                prompt.content = form_data.content
                prompt.access_control = form_data.access_control
                prompt.timestamp = int(time.time())
                prompt.description = form_data.description
                prompt.meta = form_data.meta.model_dump() if form_data.meta else None
                # prompt.bookmarked = form_data.bookmarked
                db.commit()
                return PromptModel.model_validate(prompt)
        except Exception:
            return None

    def delete_prompt_by_command_and_company(self, command: str, company_id: str) -> bool:
        try:
            with get_db() as db:
                db.query(Prompt).filter_by(command=command, company_id=company_id).delete()
                db.commit()

                return True
        except Exception:
            return False


Prompts = PromptsTable()
