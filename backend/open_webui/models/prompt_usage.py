import time
from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Column, Integer, String, Text, Date, UniqueConstraint

from open_webui.internal.db import Base


class PromptUsage(Base):
    __tablename__ = "prompt_usage"

    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False)
    prompt = Column(Text, nullable=False)
    used_date = Column(Date, nullable=False)
    count = Column(Integer, nullable=False, default=0)

    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)

    __table_args__ = (
        UniqueConstraint("user_id", "prompt", "used_date", name="uq_user_prompt_date"),
    )


class PromptUsageModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    prompt: str
    used_date: date
    count: int
    created_at: Optional[int] = None
    updated_at: Optional[int] = None 