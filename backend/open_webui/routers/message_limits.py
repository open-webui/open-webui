import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from open_webui.internal.db import get_session
from sqlalchemy.orm import Session

from open_webui.utils.auth import get_admin_user, get_verified_user
from open_webui.models.message_limits import (
    MessageLimits,
    MessageLimitForm,
    MessageLimitModel,
    UserLimitStatus,
)
from open_webui.models.chat_messages import ChatMessages
from open_webui.models.users import Users

log = logging.getLogger(__name__)

router = APIRouter()


############################
# List all limits (admin)
############################


@router.get("/", response_model=list[MessageLimitModel])
async def list_limits(
    user=Depends(get_admin_user),
    db: Session = Depends(get_session),
):
    return MessageLimits.get_all_limits(db=db)


############################
# Upsert a limit (admin)
############################


@router.post("/", response_model=MessageLimitModel)
async def upsert_limit(
    form_data: MessageLimitForm,
    user=Depends(get_admin_user),
    db: Session = Depends(get_session),
):
    # Validate scope_type
    if form_data.scope_type not in ("system", "role", "user"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="scope_type must be 'system', 'role', or 'user'",
        )

    if form_data.scope_type == "role" and not form_data.role_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="role_id is required for scope_type='role'",
        )

    if form_data.scope_type == "user" and not form_data.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="user_id is required for scope_type='user'",
        )

    result = MessageLimits.upsert_limit(
        form_data=form_data,
        created_by=user.id,
        db=db,
    )
    if result:
        return result

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Error creating/updating message limit",
    )


############################
# Delete a limit (admin)
############################


@router.delete("/{limit_id}", response_model=bool)
async def delete_limit(
    limit_id: str,
    user=Depends(get_admin_user),
    db: Session = Depends(get_session),
):
    result = MessageLimits.delete_limit(limit_id, db=db)
    if result:
        return result

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Message limit not found",
    )


############################
# Get current user's status
############################


def _build_limit_status(
    target_user_id: str,
    target_user_role: str,
    target_user_role_id: str | None,
    db: Session,
) -> UserLimitStatus:
    effective_limit, scope_source = MessageLimits.get_effective_limit(
        user_id=target_user_id,
        role=target_user_role,
        role_id=target_user_role_id,
        db=db,
    )

    used_today = ChatMessages.get_user_message_count_today(target_user_id, db=db)

    if effective_limit == -1:
        remaining = -1
    else:
        remaining = max(0, effective_limit - used_today)

    now_utc = datetime.now(timezone.utc)
    resets_at = (
        int(now_utc.replace(hour=0, minute=0, second=0, microsecond=0).timestamp())
        + 86400
    )

    return UserLimitStatus(
        effective_limit=effective_limit,
        used_today=used_today,
        remaining=remaining,
        resets_at=resets_at,
        scope_source=scope_source,
    )


@router.get("/status", response_model=UserLimitStatus)
async def get_my_limit_status(
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    return _build_limit_status(
        target_user_id=user.id,
        target_user_role=user.role,
        target_user_role_id=getattr(user, "role_id", None),
        db=db,
    )


############################
# Get specific user's status (admin)
############################


@router.get("/status/{user_id}", response_model=UserLimitStatus)
async def get_user_limit_status(
    user_id: str,
    user=Depends(get_admin_user),
    db: Session = Depends(get_session),
):
    target_user = Users.get_user_by_id(user_id, db=db)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return _build_limit_status(
        target_user_id=target_user.id,
        target_user_role=target_user.role,
        target_user_role_id=getattr(target_user, "role_id", None),
        db=db,
    )
