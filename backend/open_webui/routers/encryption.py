from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from open_webui.env import (
    WEBUI_CHAT_ENCRYPTION_ALLOW_LEGACY_READ,
    WEBUI_CHAT_ENCRYPTION_DEFAULT,
    WEBUI_CHAT_ENCRYPTION_REQUIRED,
)
from open_webui.utils.auth import get_verified_user

router = APIRouter()


class EncryptionPolicyResponse(BaseModel):
    required: bool
    default: bool
    allow_legacy_read: bool


@router.get("/policy", response_model=EncryptionPolicyResponse)
async def get_encryption_policy(_user=Depends(get_verified_user)):
    return EncryptionPolicyResponse(
        required=WEBUI_CHAT_ENCRYPTION_REQUIRED,
        default=WEBUI_CHAT_ENCRYPTION_DEFAULT,
        allow_legacy_read=WEBUI_CHAT_ENCRYPTION_ALLOW_LEGACY_READ,
    )
