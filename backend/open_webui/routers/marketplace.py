import os
import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel

from open_webui.utils.auth import get_verified_user
from open_webui.models.users import UserModel, Users

log = logging.getLogger(__name__)

router = APIRouter()

# Initialize Supabase Client lazily to allow env vars to load
def get_supabase_client():
    from supabase import create_client, Client
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not url or not key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Supabase credentials (SUPABASE_URL, SUPABASE_SERVICE_KEY) not found in environment"
        )
    return create_client(url, key)

class ProfileUpdate(BaseModel):
    role: Optional[str] = None
    skills: Optional[List[str]] = None
    bio: Optional[str] = None

class ProjectCreate(BaseModel):
    title: str
    description: Optional[str] = None
    budget: Optional[float] = None
    status: Optional[str] = "open"

class ProjectUpdate(BaseModel):
    status: Optional[str] = None

class ProposalCreate(BaseModel):
    cover_letter: Optional[str] = None
    proposed_rate: Optional[float] = None
    # Backward-compatible aliases for older clients.
    message: Optional[str] = None
    price: Optional[float] = None

class HelpRequestCreate(BaseModel):
    message: str


class HelpRequestRespond(BaseModel):
    status: Optional[str] = "responded"

# Helper to automatically sync user profile
def ensure_profile_exists(supabase, user: UserModel):
    # Upsert profile record matching Open WebUI user ID
    response = supabase.table("profiles").select("*").eq("id", user.id).execute()
    if not response.data:
        # Create it if it doesn't exist
        try:
            supabase.table("profiles").insert({
                "id": user.id,
                "role": "Client" # Default role
            }).execute()
        except Exception as e:
            log.error(f"Error creating profile for {user.id}: {e}")

@router.get("/profile/me")
def get_my_profile(user: UserModel = Depends(get_verified_user)):
    supabase = get_supabase_client()
    ensure_profile_exists(supabase, user)
    
    response = supabase.table("profiles").select("*").eq("id", user.id).execute()
    if response.data:
        return response.data[0]
    raise HTTPException(status_code=404, detail="Profile not found")


@router.get("/freelancers/{freelancer_id}")
def get_freelancer_profile(freelancer_id: str, user: UserModel = Depends(get_verified_user)):
    supabase = get_supabase_client()

    profile_res = supabase.table("profiles").select("*").eq("id", freelancer_id).execute()
    profile = profile_res.data[0] if profile_res.data else {}

    user_record = Users.get_user_by_id(freelancer_id)
    if not user_record and not profile:
        raise HTTPException(status_code=404, detail="Freelancer profile not found")

    is_active = Users.is_active(user_record) if user_record else False
    status_value = profile.get("status")
    if not status_value:
        status_value = "available" if is_active else "offline"

    rating_value = profile.get("rating")
    try:
        rating_value = float(rating_value) if rating_value is not None else 0.0
    except Exception:
        rating_value = 0.0

    skills_value = profile.get("skills")
    if not isinstance(skills_value, list):
        skills_value = []

    return {
        "id": freelancer_id,
        "name": user_record.name if user_record else "Freelancer",
        "profile_image_url": user_record.profile_image_url if user_record else None,
        "role": profile.get("role", "Freelancer"),
        "bio": profile.get("bio") or (user_record.bio if user_record else None),
        "skills": skills_value,
        "status": status_value,
        "rating": rating_value,
        "is_active": is_active,
        "presence_state": user_record.presence_state if user_record else None,
    }

@router.put("/profile/me")
def update_my_profile(profile_data: ProfileUpdate, user: UserModel = Depends(get_verified_user)):
    supabase = get_supabase_client()
    ensure_profile_exists(supabase, user)
    
    update_dict = {}
    if profile_data.role is not None:
        update_dict["role"] = profile_data.role
    if profile_data.skills is not None:
        update_dict["skills"] = profile_data.skills
    if profile_data.bio is not None:
        update_dict["bio"] = profile_data.bio
        
    update_dict["updated_at"] = "now()"
    
    response = supabase.table("profiles").update(update_dict).eq("id", user.id).execute()
    if response.data:
        return response.data[0]
    return {}

@router.get("/projects")
def list_projects(user: UserModel = Depends(get_verified_user)):
    supabase = get_supabase_client()
    response = supabase.table("projects").select("*, profiles(role, bio)").order("created_at", desc=True).execute()
    return response.data

@router.post("/projects")
def create_project(project: ProjectCreate, user: UserModel = Depends(get_verified_user)):
    supabase = get_supabase_client()
    
    insert_data = {
        "client_id": user.id,
        "title": project.title,
        "description": project.description,
        "budget": project.budget,
        "status": project.status or "open"
    }
    
    response = supabase.table("projects").insert(insert_data).execute()
    if response.data:
        return response.data[0]
    raise HTTPException(status_code=500, detail="Failed to create project")

@router.get("/projects/{project_id}")
def get_project(project_id: str, user: UserModel = Depends(get_verified_user)):
    supabase = get_supabase_client()
    response = supabase.table("projects").select("*, profiles(role, bio)").eq("id", project_id).execute()
    if response.data:
        return response.data[0]
    raise HTTPException(status_code=404, detail="Project not found")

@router.put("/projects/{project_id}")
def update_project(project_id: str, project_update: ProjectUpdate, user: UserModel = Depends(get_verified_user)):
    supabase = get_supabase_client()
    
    # Optional: Check if user owns project
    proj = supabase.table("projects").select("client_id").eq("id", project_id).execute()
    if not proj.data or proj.data[0]["client_id"] != user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
        
    update_data = {}
    if project_update.status:
        update_data["status"] = project_update.status
        
    update_data["updated_at"] = "now()"
    
    response = supabase.table("projects").update(update_data).eq("id", project_id).execute()
    if response.data:
        return response.data[0]
    return {}

@router.get("/projects/{project_id}/proposals")
def list_proposals(project_id: str, user: UserModel = Depends(get_verified_user)):
    supabase = get_supabase_client()
    response = supabase.table("project_proposals").select("*, profiles(role, bio, skills)").eq("project_id", project_id).execute()
    return response.data

@router.post("/projects/{project_id}/proposals")
def create_proposal(project_id: str, proposal: ProposalCreate, user: UserModel = Depends(get_verified_user)):
    supabase = get_supabase_client()

    cover_letter = proposal.cover_letter if proposal.cover_letter is not None else proposal.message
    proposed_rate = proposal.proposed_rate if proposal.proposed_rate is not None else proposal.price
    
    insert_data = {
        "project_id": project_id,
        "freelancer_id": user.id,
        "cover_letter": cover_letter,
        "proposed_rate": proposed_rate,
        "status": "pending"
    }
    
    response = supabase.table("project_proposals").insert(insert_data).execute()
    if response.data:
        return response.data[0]
    raise HTTPException(status_code=500, detail="Failed to submit proposal")


@router.get("/help_requests")
def list_help_requests(
    status_filter: Optional[str] = None,
    user: UserModel = Depends(get_verified_user),
):
    supabase = get_supabase_client()

    query = supabase.table("help_requests").select("*")
    if status_filter:
        query = query.eq("status", status_filter)

    try:
        response = query.order("created_at", desc=True).execute()
    except Exception:
        response = query.execute()

    formatted = []
    for item in response.data or []:
        requester = Users.get_user_by_id(item.get("user_id")) if item.get("user_id") else None
        formatted.append(
            {
                **item,
                "requester": {
                    "id": requester.id,
                    "name": requester.name,
                    "profile_image_url": requester.profile_image_url,
                }
                if requester
                else None,
            }
        )

    return formatted


@router.get("/help_requests/{request_id}")
def get_help_request(request_id: str, user: UserModel = Depends(get_verified_user)):
    supabase = get_supabase_client()
    response = supabase.table("help_requests").select("*").eq("id", request_id).execute()

    if not response.data:
        raise HTTPException(status_code=404, detail="Help request not found")

    item = response.data[0]
    requester = Users.get_user_by_id(item.get("user_id")) if item.get("user_id") else None
    return {
        **item,
        "requester": {
            "id": requester.id,
            "name": requester.name,
            "profile_image_url": requester.profile_image_url,
        }
        if requester
        else None,
    }

@router.post("/help_requests")
def create_help_request(help_req: HelpRequestCreate, user: UserModel = Depends(get_verified_user)):
    supabase = get_supabase_client()
    
    insert_data = {
        "user_id": user.id,
        "message": help_req.message,
        "status": "pending"
    }
    
    response = supabase.table("help_requests").insert(insert_data).execute()
    if response.data:
        return response.data[0]
    raise HTTPException(status_code=500, detail="Failed to create help request")


@router.post("/help_requests/{request_id}/respond")
def respond_help_request(
    request_id: str,
    response_data: HelpRequestRespond,
    user: UserModel = Depends(get_verified_user),
):
    supabase = get_supabase_client()

    existing = supabase.table("help_requests").select("*").eq("id", request_id).execute()
    if not existing.data:
        raise HTTPException(status_code=404, detail="Help request not found")

    status_value = response_data.status or "responded"
    updated = supabase.table("help_requests").update({"status": status_value}).eq("id", request_id).execute()

    if updated.data:
        return updated.data[0]
    return {"id": request_id, "status": status_value}
