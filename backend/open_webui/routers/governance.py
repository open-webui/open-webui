from pydantic import BaseModel
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from open_webui.internal.db import get_async_session
from open_webui.utils.auth import get_verified_user
from open_webui.utils.governance import can_access_all_workspaces, can_create_workspace, can_use_private_chat

router = APIRouter()


class GovernanceCapabilitiesResponse(BaseModel):
    can_use_private_chat: bool
    can_create_workspace: bool
    can_access_all_workspaces: bool


@router.get('/capabilities', response_model=GovernanceCapabilitiesResponse)
async def get_governance_capabilities(
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    return GovernanceCapabilitiesResponse(
        can_use_private_chat=await can_use_private_chat(user, db=db),
        can_create_workspace=await can_create_workspace(user, db=db),
        can_access_all_workspaces=await can_access_all_workspaces(user, db=db),
    )
