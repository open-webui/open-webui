import time
import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel

from open_webui.models.users import Users, UserModel
from open_webui.models.auths import Auths
from open_webui.utils.auth import create_token, get_password_hash
from open_webui.utils.misc import parse_duration, validate_email_format
from open_webui.env import WEBUI_AUTH, WEBUI_AUTH_TRUSTED_EMAIL_HEADER, WEBUI_AUTH_TRUSTED_NAME_HEADER
from open_webui.constants import ERROR_MESSAGES
from open_webui.models.child_profiles import ChildProfiles
from open_webui.models.exit_quiz import ExitQuizzes

router = APIRouter()


class ProlificAuthRequest(BaseModel):
    prolific_pid: str
    study_id: str
    session_id: str
    name: Optional[str] = None


class ProlificAuthResponse(BaseModel):
    token: str
    user: UserModel
    session_number: int
    is_new_user: bool
    new_child_id: str | None = None
    has_exit_quiz: bool = False


@router.post("/auth", response_model=ProlificAuthResponse)
async def prolific_auth(request: Request, response: Response, form_data: ProlificAuthRequest):
    """
    Authenticate or create user based on Prolific parameters.
    - If user with PROLIFIC_PID exists, check SESSION_ID to determine session_number
    - If user doesn't exist, create new user with generated credentials
    - Return JWT token and session metadata
    """
    
    if not form_data.prolific_pid or not form_data.study_id or not form_data.session_id:
        raise HTTPException(400, detail="Missing required Prolific parameters")
    
    # Check if user with this PROLIFIC_PID already exists
    existing_user = Users.get_user_by_prolific_pid(form_data.prolific_pid)
    
    if existing_user:
        # User exists - check if this is a new session
        is_new_session = existing_user.current_session_id != form_data.session_id
        
        if is_new_session:
            # New session - increment session_number
            new_session_number = existing_user.session_number + 1
            updated_user = Users.update_user_session(
                existing_user.id, 
                form_data.session_id, 
                new_session_number
            )
            if not updated_user:
                raise HTTPException(500, detail="Failed to update user session")
            user = updated_user
            # Do not clone; reuse latest child profile across sessions
            latest_profile = ChildProfiles.get_latest_child_profile_any(user.id)
            new_child_id = latest_profile.id if latest_profile else None
        else:
            # Same session - use existing session_number
            user = existing_user
            new_session_number = user.session_number
            new_child_id = None
        
        is_new_user = False
    else:
        # New user - create account
        user_id = str(uuid.uuid4())
        # Use the full PROLIFIC_PID as the display name unless a name was provided
        name = form_data.name or form_data.prolific_pid
        email = f"prolific_{form_data.prolific_pid}@prolific.study"
        
        # Generate a random password for Prolific users
        password = str(uuid.uuid4())
        hashed_password = get_password_hash(password)
        
        # Create auth record
        auth_user = Auths.insert_new_auth(
            email=email,
            password=hashed_password,
            name=name,
            profile_image_url="/user.png",
            role="user"
        )
        
        if not auth_user:
            raise HTTPException(500, detail="Failed to create user authentication")
        
        # Update user with Prolific fields
        updated_user = Users.update_user_by_id(auth_user.id, {
            "prolific_pid": form_data.prolific_pid,
            "study_id": form_data.study_id,
            "current_session_id": form_data.session_id,
            "session_number": 1
        })
        
        if not updated_user:
            raise HTTPException(500, detail="Failed to update user with Prolific data")
        
        user = updated_user
        new_session_number = 1
        is_new_user = True
        # No child to reuse yet for first-time user
        new_child_id = None
    
    # Generate JWT token
    expires_delta = parse_duration(request.app.state.config.JWT_EXPIRES_IN)
    expires_at = None
    if expires_delta:
        expires_at = int(time.time()) + int(expires_delta.total_seconds())

    token = create_token(
        data={"id": user.id},
        expires_delta=expires_delta,
    )

    # Set the cookie token
    response.set_cookie(
        key="token",
        value=token,
        expires=expires_at,
        httponly=True,
        samesite="lax",
        secure=request.url.scheme == "https",
    )

    # Include exit quiz presence info
    has_exit = False
    try:
        eq = ExitQuizzes.get_responses_by_user(user.id)
        has_exit = len(eq) > 0
    except Exception:
        has_exit = False

    return ProlificAuthResponse(
        token=token,
        user=user,
        session_number=new_session_number,
        is_new_user=is_new_user,
        new_child_id=new_child_id,
        has_exit_quiz=has_exit
    )


@router.get("/session-info")
async def get_session_info(user_id: str = None):
    """
    Get current session information for a user.
    """
    if not user_id:
        raise HTTPException(400, detail="User ID required")
    
    user = Users.get_user_by_id(user_id)
    if not user:
        raise HTTPException(404, detail="User not found")
    
    return {
        "prolific_pid": user.prolific_pid,
        "study_id": user.study_id,
        "current_session_id": user.current_session_id,
        "session_number": user.session_number
    }
