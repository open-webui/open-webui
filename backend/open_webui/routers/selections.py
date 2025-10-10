"""
TEXT SELECTION: FastAPI router for text selection analytics and management
- Provides CRUD operations for user text selections
- Supports bulk operations and analytics endpoints
- Includes user authentication and authorization
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from open_webui.utils.auth import get_current_user
from open_webui.models.selections import SelectionModel, SelectionForm, Selections
from open_webui.models.users import UserModel

log = logging.getLogger(__name__)

router = APIRouter()

class SelectionResponse(BaseModel):
    id: str
    chat_id: str
    message_id: str
    role: str
    selected_text: str
    child_id: Optional[str] = None
    context: Optional[str] = None
    meta: Optional[dict] = None
    created_at: int
    updated_at: int

class SelectionStatsResponse(BaseModel):
    total_selections: int
    unique_users: int
    assistant_selections: int
    user_selections: int

class BulkSelectionForm(BaseModel):
    selections: List[SelectionForm]

@router.post("/selections", response_model=SelectionResponse)
async def create_selection(
    form_data: SelectionForm,
    current_user: UserModel = Depends(get_current_user)
):
    """Create a new selection"""
    try:
        selection = Selections.insert_new_selection(form_data, current_user.id)
        if not selection:
            raise HTTPException(status_code=500, detail="Failed to create selection")
        
        return SelectionResponse(**selection.model_dump())
    except Exception as e:
        log.error(f"Error creating selection: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/selections/bulk", response_model=List[SelectionResponse])
async def create_bulk_selections(
    form_data: BulkSelectionForm,
    current_user: UserModel = Depends(get_current_user)
):
    """Create multiple selections at once (for syncing from localStorage)"""
    try:
        created_selections = []
        for selection_form in form_data.selections:
            selection = Selections.insert_new_selection(selection_form, current_user.id)
            if selection:
                created_selections.append(SelectionResponse(**selection.model_dump()))
        
        return created_selections
    except Exception as e:
        log.error(f"Error creating bulk selections: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/selections", response_model=List[SelectionResponse])
async def get_user_selections(
    limit: int = Query(100, ge=1, le=1000),
    current_user: UserModel = Depends(get_current_user)
):
    """Get all selections for the current user"""
    try:
        selections = Selections.get_selections_by_user(current_user.id, limit)
        return [SelectionResponse(**selection.model_dump()) for selection in selections]
    except Exception as e:
        log.error(f"Error getting user selections: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/selections/user", response_model=List[SelectionResponse])
async def get_user_selections(
    limit: int = Query(100, ge=1, le=1000),
    current_user: UserModel = Depends(get_current_user)
):
    """Get all selections for the current user"""
    try:
        selections = Selections.get_selections_by_user(current_user.id, limit)
        return [SelectionResponse(**selection.model_dump()) for selection in selections]
    except Exception as e:
        log.error(f"Error getting user selections: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/selections/chat/{chat_id}", response_model=List[SelectionResponse])
async def get_chat_selections(
    chat_id: str,
    current_user: UserModel = Depends(get_current_user)
):
    """Get all selections for a specific chat"""
    try:
        selections = Selections.get_selections_by_chat(chat_id)
        # Filter to only show user's own selections for security
        user_selections = [s for s in selections if s.user_id == current_user.id]
        return [SelectionResponse(**selection.model_dump()) for selection in user_selections]
    except Exception as e:
        log.error(f"Error getting chat selections: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.delete("/selections/{selection_id}")
async def delete_selection(
    selection_id: str,
    current_user: UserModel = Depends(get_current_user)
):
    """Delete a specific selection"""
    try:
        success = Selections.delete_selection(selection_id, current_user.id)
        if not success:
            raise HTTPException(status_code=404, detail="Selection not found")
        
        return {"message": "Selection deleted successfully"}
    except Exception as e:
        log.error(f"Error deleting selection: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/selections/stats", response_model=SelectionStatsResponse)
async def get_selection_stats(
    current_user: UserModel = Depends(get_current_user)
):
    """Get selection statistics (admin only)"""
    # Check if user is admin
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        stats = Selections.get_selection_stats()
        return SelectionStatsResponse(**stats)
    except Exception as e:
        log.error(f"Error getting selection stats: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/selections/analytics", response_model=List[SelectionResponse])
async def get_selections_for_analytics(
    start_date: Optional[int] = Query(None, description="Start timestamp in nanoseconds"),
    end_date: Optional[int] = Query(None, description="End timestamp in nanoseconds"),
    role: Optional[str] = Query(None, description="Filter by role: 'user' or 'assistant'"),
    limit: int = Query(1000, ge=1, le=10000),
    current_user: UserModel = Depends(get_current_user)
):
    """Get selections for analytics (admin only)"""
    # Check if user is admin
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        selections = Selections.get_selections_for_analysis(
            start_date=start_date,
            end_date=end_date,
            role=role,
            limit=limit
        )
        return [SelectionResponse(**selection.model_dump()) for selection in selections]
    except Exception as e:
        log.error(f"Error getting analytics data: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
