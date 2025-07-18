import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from open_webui.constants import ERROR_MESSAGES
from open_webui.env import SRC_LOG_LEVELS
from open_webui.models.charities import (
    Charities,
    CharityForm,
    CharityListResponse,
    CharityResponse,
)
from open_webui.utils.auth import get_admin_user
from sqlalchemy.exc import IntegrityError

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

router = APIRouter()


PAGE_ITEM_COUNT = 30


@router.get("/", response_model=CharityListResponse)
async def get_charities(
    query: Optional[str] = None,
    order_by: Optional[str] = None,
    direction: Optional[str] = None,
    page: Optional[int] = 1,
    user=Depends(get_admin_user),
):
    """
    Get all charities
    """
    limit = PAGE_ITEM_COUNT

    page = max(1, page)
    skip = (page - 1) * limit

    filter = {}
    if query:
        filter["query"] = query
    if order_by:
        filter["order_by"] = order_by
    if direction:
        filter["direction"] = direction

    return Charities.get_charities(filter=filter, skip=skip, limit=limit)


@router.post("/create", response_model=Optional[CharityResponse])
async def create_charity(form_data: CharityForm, user=Depends(get_admin_user)):
    """
    Create charity
    """
    try:
        charity = Charities.add(form_data)
        if charity:
            return charity
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT("Error creating charity"),
            )
    except IntegrityError as e:
        if "charity_id" in str(e.orig).lower() and "unique" in str(e.orig).lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Charity ID must be unique. Another charity with this ID already exists.",
            )
        else:
            # Some other integrity error
            log.exception(f"IntegrityError: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT("A database integrity error occurred."),
            )
    except Exception as e:
        log.exception(f"Error creating a new charity: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(str(e)),
        )


@router.post("/id/{id}/update", response_model=Optional[CharityResponse])
async def update_charity_by_id(
    id: str, form_data: CharityForm, user=Depends(get_admin_user)
):
    try:
        charity = Charities.update_charity_by_id(id, form_data)
        if charity:
            return charity
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT("Error updating charity"),
            )
    except IntegrityError as e:
        if "charity_id" in str(e.orig).lower() and "unique" in str(e.orig).lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Charity ID must be unique. Another charity with this ID already exists.",
            )
        else:
            # Some other integrity error
            log.exception(f"IntegrityError: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT("A database integrity error occurred."),
            )

    except Exception as e:
        log.exception(f"Error updating charity {id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(e),
        )


@router.delete("/id/{id}/delete", response_model=bool)
async def delete_charity_by_id(id: str, user=Depends(get_admin_user)):
    """
    Delete charity by ID
    """
    try:
        result = Charities.delete_charity_by_id(id)
        if result:
            return result
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT("Error deleting charity"),
            )
    except Exception as e:
        log.exception(f"Error deleting charity {id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(e),
        )
