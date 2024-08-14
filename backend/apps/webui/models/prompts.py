from pydantic import BaseModel, ConfigDict
from typing import List, Optional
import time

from sqlalchemy import String, Column, BigInteger, Text

from apps.webui.internal.db import Base, get_db

import json

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


class PromptModel(BaseModel):
    command: str
    user_id: str
    title: str
    content: str
    timestamp: int  # timestamp in epoch

    model_config = ConfigDict(from_attributes=True)


####################
# Forms
####################


class PromptForm(BaseModel):
    command: str
    title: str
    content: str


class PromptsTable:

    def insert_new_prompt(
        self, user_id: str, form_data: PromptForm
    ) -> Optional[PromptModel]:
        prompt = PromptModel(
            **{
                "user_id": user_id,
                "command": form_data.command,
                "title": form_data.title,
                "content": form_data.content,
                "timestamp": int(time.time()),
            }
        )

        try:
            with get_db() as db:

                result = Prompt(**prompt.dict())
                db.add(result)
                db.commit()
                db.refresh(result)
                if result:
                    return PromptModel.model_validate(result)
                else:
                    return None
        except Exception as e:
            return None

    def get_prompt_by_command(self, command: str) -> Optional[PromptModel]:
        try:
            with get_db() as db:

                prompt = db.query(Prompt).filter_by(command=command).first()
                return PromptModel.model_validate(prompt)
        except:
            return None

    def get_prompts(self) -> List[PromptModel]:
        with get_db() as db:

            return [
                PromptModel.model_validate(prompt) for prompt in db.query(Prompt).all()
            ]

    def update_prompt_by_command(
        self, command: str, form_data: PromptForm
    ) -> Optional[PromptModel]:
        try:
            with get_db() as db:

                prompt = db.query(Prompt).filter_by(command=command).first()
                prompt.title = form_data.title
                prompt.content = form_data.content
                prompt.timestamp = int(time.time())
                db.commit()
                return PromptModel.model_validate(prompt)
        except:
            return None

    def delete_prompt_by_command(self, command: str) -> bool:
        try:
            with get_db() as db:

                db.query(Prompt).filter_by(command=command).delete()
                db.commit()

                return True
        except:
            return False


Prompts = PromptsTable()
