"""
CHILD PROFILE: FastAPI router for child profile management
- Provides CRUD operations for child profiles linked to parent users
- Supports creating, reading, updating, and deleting child profiles
- Includes user authentication and ownership verification
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from open_webui.utils.auth import get_verified_user, get_admin_user
from open_webui.models.child_profiles import (
    ChildProfileModel,
    ChildProfileForm,
    ChildProfiles,
)
from open_webui.models.users import UserModel

log = logging.getLogger(__name__)

router = APIRouter()


class ChildProfileResponse(BaseModel):
    id: str
    user_id: str
    name: str
    child_age: Optional[str] = None
    child_gender: Optional[str] = None
    child_characteristics: Optional[str] = None
    # parenting_style removed - now collected in exit survey (migration gg11hh22ii33)
    # Research fields
    is_only_child: Optional[bool] = None
    child_has_ai_use: Optional[str] = None
    child_ai_use_contexts: Optional[list[str]] = None
    parent_llm_monitoring_level: Optional[str] = None
    # "Other" text fields
    child_gender_other: Optional[str] = None
    child_ai_use_contexts_other: Optional[str] = None
    parent_llm_monitoring_other: Optional[str] = None
    session_number: Optional[int] = None
    attempt_number: Optional[int] = None
    is_current: Optional[bool] = None
    created_at: int
    updated_at: int
    child_email: Optional[str] = None


class ChildProfileStatsResponse(BaseModel):
    total_profiles: int
    unique_parents: int


@router.post("/child-profiles", response_model=ChildProfileResponse)
async def create_child_profile(
    form_data: ChildProfileForm, current_user: UserModel = Depends(get_verified_user)
):
    """Create a new child profile"""
    try:
        # Determine session_number if not provided
        if form_data.session_number is None:
            existing_profiles = ChildProfiles.get_child_profiles_by_user(
                current_user.id
            )
            if existing_profiles:
                max_session = max(
                    (p.session_number for p in existing_profiles), default=0
                )
                session_number = max_session + 1
            else:
                session_number = 1
        else:
            session_number = form_data.session_number

        child_profile = ChildProfiles.insert_new_child_profile(
            form_data, current_user.id, session_number=session_number
        )
        if not child_profile:
            raise HTTPException(
                status_code=500, detail="Failed to create child profile"
            )

        return ChildProfileResponse(**child_profile.model_dump())
    except HTTPException:
        # Re-raise HTTP exceptions as-is (they already have proper error messages)
        raise
    except Exception as e:
        log.error(f"Error creating child profile: {e}")
        # Include the actual error message in the response for debugging
        error_detail = str(e) if e else "Internal server error"
        raise HTTPException(
            status_code=500, detail=f"Failed to create child profile: {error_detail}"
        )


@router.get("/child-profiles", response_model=List[ChildProfileResponse])
async def get_child_profiles(current_user: UserModel = Depends(get_verified_user)):
    """Get all child profiles for the current user"""
    try:
        profiles = ChildProfiles.get_child_profiles_by_user(current_user.id)
        return [ChildProfileResponse(**profile.model_dump()) for profile in profiles]
    except Exception as e:
        log.error(f"Error getting child profiles: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/child-profiles/{profile_id}", response_model=ChildProfileResponse)
async def get_child_profile_by_id(
    profile_id: str, current_user: UserModel = Depends(get_verified_user)
):
    """Get a specific child profile"""
    try:
        profile = ChildProfiles.get_child_profile_by_id(profile_id, current_user.id)
        if not profile:
            raise HTTPException(status_code=404, detail="Child profile not found")

        return ChildProfileResponse(**profile.model_dump())
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error getting child profile: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/child-profiles/{profile_id}", response_model=ChildProfileResponse)
async def update_child_profile(
    profile_id: str,
    form_data: ChildProfileForm,
    current_user: UserModel = Depends(get_verified_user),
):
    """Update a child profile"""
    try:
        profile = ChildProfiles.update_child_profile_by_id(
            profile_id, current_user.id, form_data
        )
        if not profile:
            raise HTTPException(status_code=404, detail="Child profile not found")

        return ChildProfileResponse(**profile.model_dump())
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error updating child profile: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/child-profiles/{profile_id}")
async def delete_child_profile(
    profile_id: str, current_user: UserModel = Depends(get_verified_user)
):
    """Delete a child profile"""
    try:
        success = ChildProfiles.delete_child_profile(profile_id, current_user.id)
        if not success:
            raise HTTPException(status_code=404, detail="Child profile not found")

        return {"message": "Child profile deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error deleting child profile: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/child-profiles/stats", response_model=ChildProfileStatsResponse)
async def get_child_profile_stats(current_user: UserModel = Depends(get_verified_user)):
    """Get child profile statistics (admin only)"""
    # Check if user is admin
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    try:
        stats = ChildProfiles.get_child_profile_stats()
        return ChildProfileStatsResponse(**stats)
    except Exception as e:
        log.error(f"Error getting child profile stats: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get(
    "/child-profiles/admin/{user_id}", response_model=List[ChildProfileResponse]
)
async def get_child_profiles_for_user(
    user_id: str, admin_user: UserModel = Depends(get_admin_user)
):
    """Admin endpoint to get child profiles for a specific user"""
    try:
        profiles = ChildProfiles.get_child_profiles_by_user(user_id)
        return [ChildProfileResponse(**profile.model_dump()) for profile in profiles]
    except Exception as e:
        log.error(f"Error getting child profiles for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
