from pydantic import BaseModel, ConfigDict
from typing import List, Optional
import time

from sqlalchemy import String, Column, BigInteger
from sqlalchemy.orm import Session

from apps.webui.internal.db import Base, get_session

import json

####################
# Prompts DB Schema
####################


class Prompt(Base):
    __tablename__ = "prompt"

    command = Column(String, primary_key=True)
    user_id = Column(String)
    title = Column(String)
    content = Column(String)
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
        with get_session() as db:
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
        with get_session() as db:
            try:
                prompt = db.query(Prompt).filter_by(command=command).first()
                return PromptModel.model_validate(prompt)
            except:
                return None

    def get_prompts(self) -> List[PromptModel]:
        with get_session() as db:
            return [
                PromptModel.model_validate(prompt) for prompt in db.query(Prompt).all()
            ]

    def update_prompt_by_command(
        self, command: str, form_data: PromptForm
    ) -> Optional[PromptModel]:
        with get_session() as db:
            try:
                prompt = db.query(Prompt).filter_by(command=command).first()
                prompt.title = form_data.title
                prompt.content = form_data.content
                prompt.timestamp = int(time.time())
                db.commit()
                return prompt
                # return self.get_prompt_by_command(command)
            except:
                return None

    def delete_prompt_by_command(self, command: str) -> bool:
        with get_session() as db:
            try:
                db.query(Prompt).filter_by(command=command).delete()
                return True
            except:
                return False


Prompts = PromptsTable()
