from pydantic import BaseModel, ConfigDict
from typing import Optional
from sqlalchemy import String, Column, BigInteger, Integer, Text, ForeignKey, Float

import uuid
import time

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
    credits_used = Column(Float)
    created_at = Column(BigInteger)
    time_saved_in_seconds = Column(Float)

class CompletionModel(BaseModel):
    id: str
    user_id: str
    chat_id: str
    model: str
    credits_used: float
    created_at: int  # timestamp in epoch
    time_saved_in_seconds: float

    model_config = ConfigDict(from_attributes=True)


class CompletionTable:
    def insert_new_completion(self, user_id: str, chat_id: str, model: str, credits_used: float, time_saved_in_seconds: float) -> Optional[CompletionModel]:
        print("CREDITS USED FOR COMPLETION", credits_used)

        id = str(uuid.uuid4())
        completion = CompletionModel(
            **{
                "id": id,
                "user_id": user_id,
                "chat_id": chat_id,
                "created_at": int(time.time()),
                "model": model,
                "credits_used": credits_used,
                "time_saved_in_seconds": time_saved_in_seconds
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

def calculate_saved_time_in_seconds(last_message, response_message):
    # print(last_message + " ----- " + response_message)

    writing_speed_per_word = 600 / 500  # 500 words in 600 seconds = 1.2 sec per word
    reading_speed_per_word = 400 / 500  # 500 words in 400 seconds = 0.8 sec per word
    
    # Now prompt is a string (the last message), not a list of messages
    num_words_prompt = len(last_message.split())
    num_words_output = len(response_message.split())
    
    prompt_time = num_words_prompt * writing_speed_per_word
    writing_time = num_words_output * writing_speed_per_word
    reading_time = num_words_output * reading_speed_per_word

    total_time = writing_time - (prompt_time + reading_time)
    total_time = 0 if total_time < 0 else total_time

    return total_time

Completions = CompletionTable()
