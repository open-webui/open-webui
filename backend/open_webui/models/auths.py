import logging
import uuid
from typing import Optional

from open_webui.internal.db import Base, get_db
from open_webui.models.users import UserModel, Users
from open_webui.env import SRC_LOG_LEVELS
from pydantic import BaseModel
from sqlalchemy import Boolean, Column, String, Text
import httpx

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

####################
# DB MODEL
####################


class Auth(Base):
    __tablename__ = "auth"

    id = Column(String, primary_key=True)
    email = Column(String)
    password = Column(Text)
    active = Column(Boolean)
    supabase_id = Column(String, nullable=True)  # Added for Supabase integration


class AuthModel(BaseModel):
    id: str
    email: str
    password: str
    active: bool = True
    supabase_id: Optional[str] = None  # Added for Supabase integration


####################
# Forms
####################


class Token(BaseModel):
    token: str
    token_type: str


class ApiKey(BaseModel):
    api_key: Optional[str] = None


class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    role: str
    profile_image_url: str
    city: Optional[str] = None  # Added for city selection


class SigninResponse(Token, UserResponse):
    pass


class SigninForm(BaseModel):
    email: str
    password: str


class LdapForm(BaseModel):
    user: str
    password: str


class ProfileImageUrlForm(BaseModel):
    profile_image_url: str


class UpdateProfileForm(BaseModel):
    profile_image_url: str
    name: str
    city: Optional[str] = None  # Added for city selection


class UpdatePasswordForm(BaseModel):
    password: str
    new_password: str


class SignupForm(BaseModel):
    name: str
    email: str
    password: str
    profile_image_url: Optional[str] = "/user.png"
    city: Optional[str] = "paris"  # Default city


class AddUserForm(SignupForm):
    role: Optional[str] = "pending"


class AuthsTable:
    def insert_new_auth(
        self,
        email: str,
        password: str,
        name: str,
        profile_image_url: str = "/user.png",
        role: str = "pending",
        oauth_sub: Optional[str] = None,
        city: Optional[str] = "paris",  # Default city
    ) -> Optional[UserModel]:
        # Generate a new user ID
        id = str(uuid.uuid4())

        # Try to create a Supabase user if Supabase is configured
        supabase_id = None
        try:
            # Import at function level to break circular dependency
            from open_webui.config import SUPABASE_URL, SUPABASE_KEY
            
            if not SUPABASE_URL or not SUPABASE_KEY:
                log.warning("Supabase URL or key is not configured, creating local user only")
            else:
                # Create a user in Supabase
                headers = {
                    "apikey": SUPABASE_KEY,
                    "Content-Type": "application/json",
                }
                payload = {
                    "email": email,
                    "password": password,
                }
                response = httpx.post(
                    f"{SUPABASE_URL}/auth/v1/signup",
                    headers=headers,
                    json=payload,
                )
                if response.status_code == 200:
                    supabase_data = response.json()
                    supabase_id = supabase_data.get("id")
                    log.info(f"Created Supabase user: {supabase_id}")
                else:
                    log.error(
                        f"Failed to create Supabase user: {response.status_code} - {response.text}"
                    )
        except Exception as e:
            log.error(f"Error creating Supabase user: {e}")

        # Store the user in the local database with Supabase ID
        with get_db() as db:
            new_auth = Auth(
                id=id,
                email=email,
                password=password,  # We should still store a local password hash
                active=True,
                supabase_id=supabase_id
            )
            db.add(new_auth)
            db.flush()
            db.commit()

            users = Users()
            # Insert new user with the specified role
            return users.insert_new_user(
                user_id=id,
                name=name,
                role=role,
                email=email,
                profile_image_url=profile_image_url,
                oauth_sub=oauth_sub,
                city=city,  # Added city parameter
            )

    def authenticate_user(self, email: str, password: str) -> Optional[UserModel]:
        """Attempt various authentication methods."""
        
        try:
            # Try Supabase authentication
            # Import at function level to break circular dependency
            from open_webui.config import SUPABASE_URL, SUPABASE_KEY
            
            if not SUPABASE_URL or not SUPABASE_KEY:
                log.warning("Supabase URL or key is not configured, using local authentication only")
            else:
                # Try to authenticate using Supabase
                headers = {
                    "apikey": SUPABASE_KEY,
                    "Content-Type": "application/json",
                }
                payload = {
                    "email": email,
                    "password": password,
                }
                response = httpx.post(
                    f"{SUPABASE_URL}/auth/v1/token?grant_type=password",
                    headers=headers,
                    json=payload,
                )
                
            if response.status_code != 200:
                log.error(f"Supabase authentication failed: {response.text}")
                # Fall back to local authentication
                return self._local_authenticate(email, password)
                
            supabase_data = response.json()
            
            # Get the user from local database using email
            with get_db() as db:
                auth = db.query(Auth).filter(Auth.email == email).first()
                if not auth:
                    return None
                    
                # Update Supabase ID if needed
                if not auth.supabase_id and supabase_data.get("user", {}).get("id"):
                    auth.supabase_id = supabase_data["user"]["id"]
                    db.commit()
                    
                users = Users()
                return users.get_user_by_id(auth.id)
                
        except Exception as e:
            log.error(f"Error authenticating with Supabase: {e}")
            # Fall back to local authentication
            return self._local_authenticate(email, password)
    
    def _local_authenticate(self, email: str, password: str) -> Optional[UserModel]:
        """Legacy local authentication method"""
        # Import at function level to break circular dependency
        from open_webui.utils.auth import verify_password
        
        with get_db() as db:
            auth = db.query(Auth).filter(Auth.email == email).first()
            if not auth:
                return None

            if not verify_password(password, auth.password):
                return None

            users = Users()
            return users.get_user_by_id(auth.id)

    def authenticate_user_by_api_key(self, api_key: str) -> Optional[UserModel]:
        log.info(f"authenticate_user_by_api_key: {api_key}")
        # if no api_key, return None
        if not api_key:
            return None

        try:
            user = Users.get_user_by_api_key(api_key)
            return user if user else None
        except Exception:
            return False

    def authenticate_user_by_trusted_header(self, email: str) -> Optional[UserModel]:
        log.info(f"authenticate_user_by_trusted_header: {email}")
        try:
            with get_db() as db:
                auth = db.query(Auth).filter_by(email=email, active=True).first()
                if auth:
                    user = Users.get_user_by_id(auth.id)
                    return user
        except Exception:
            return None

    def update_user_password_by_id(self, id: str, new_password: str) -> bool:
        try:
            with get_db() as db:
                result = (
                    db.query(Auth).filter_by(id=id).update({"password": new_password})
                )
                db.commit()
                return True if result == 1 else False
        except Exception:
            return False

    def update_email_by_id(self, id: str, email: str) -> bool:
        try:
            with get_db() as db:
                result = db.query(Auth).filter_by(id=id).update({"email": email})
                db.commit()
                return True if result == 1 else False
        except Exception:
            return False

    def delete_auth_by_id(self, id: str) -> bool:
        try:
            with get_db() as db:
                # Delete User
                result = Users.delete_user_by_id(id)

                if result:
                    db.query(Auth).filter_by(id=id).delete()
                    db.commit()

                    return True
                else:
                    return False
        except Exception:
            return False


Auths = AuthsTable()
