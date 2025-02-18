from pydantic import BaseModel, ConfigDict
from typing import Optional
from sqlalchemy import String, Column, BigInteger, Integer, Text, ForeignKey

import uuid
import time

# Constants
COST_PER_TOKEN = 0.00125  # in EUR (25€ / 20000 tokens)

from open_webui.internal.db import get_db, Base

####################
# Completion DB Schema
####################

class Completion(Base):
    __tablename__ = "completion"

    id = Column(String, primary_key=True, unique=True)
    user_id = Column(String, ForeignKey("user.id", ondelete="SET NULL"), nullable=True)
    chat_id = Column(String)
    model = Column(Text)
    credits_used = Column(Integer)
    created_at = Column(BigInteger)

class CompletionModel(BaseModel):
    id: str
    user_id: str
    chat_id: str
    model: str
    credits_used: int
    created_at: int  # timestamp in epoch

    model_config = ConfigDict(from_attributes=True)


class CompletionTable:
    def insert_new_completion(self, user_id: str, chat_id: str, model: str, credits_used: int) -> Optional[CompletionModel]:
        id = str(uuid.uuid4())
        completion = CompletionModel(
            **{
                "id": id,
                "user_id": user_id,
                "chat_id": chat_id,
                "created_at": int(time.time()),
                "model": model,
                "credits_used": credits_used
            }
        )
        try:
            with get_db() as db:
                result = Completion(**completion.model_dump())
                db.add(result)
                db.commit()
                db.refresh(result)
                if result:
                    return CompletionModel.model_validate(result)
                else:
                    print("insertion failed", result)
                    return None
        except Exception as e:
            print(f"Error creating completion: {e}")
            return None


Completions = CompletionTable()
