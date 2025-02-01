from typing import Optional

from pydantic import BaseModel, ConfigDict
from sqlalchemy import Enum


class UserAuditInfo(BaseModel):
    id: str
    name: str
    email: str
    role: str
    oauth_sub: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class AuditLevel(str, Enum):
    NONE = "NONE"
    METADATA = "METADATA"
    REQUEST = "REQUEST"
    REQUEST_RESPONSE = "REQUEST_RESPONSE"

    @classmethod
    def _missing_(cls, value):
        return cls.NONE
