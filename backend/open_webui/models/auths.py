import logging
import uuid
import json
from typing import Optional, List
from datetime import datetime

from open_webui.internal.db import Base, get_db
from open_webui.models.users import UserModel, Users
from open_webui.env import SRC_LOG_LEVELS
from pydantic import BaseModel
from sqlalchemy import Boolean, Column, String, Text
from open_webui.utils.auth import verify_password

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
    mfa_enabled = Column(Boolean, default=False)
    mfa_secret = Column(Text, nullable=True)
    backup_codes = Column(Text, nullable=True)
    mfa_last_used = Column(Text, nullable=True)


class AuthModel(BaseModel):
    id: str
    email: str
    password: str
    active: bool = True
    mfa_enabled: bool = False
    mfa_secret: Optional[str] = None
    backup_codes: Optional[str] = None
    mfa_last_used: Optional[str] = None


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


class SigninResponse(Token, UserResponse):
    is_backup_code_used: Optional[bool] = False
    mfa_required: Optional[bool] = False


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


class UpdatePasswordForm(BaseModel):
    password: str
    new_password: str


class SignupForm(BaseModel):
    name: str
    email: str
    password: str
    profile_image_url: Optional[str] = "/user.png"


class AddUserForm(SignupForm):
    role: Optional[str] = "pending"


class MFAVerifyRequest(BaseModel):
    code: str


class MFASetupResponse(BaseModel):
    secret: str
    qr_code: str


class MFAEnableResponse(BaseModel):
    enabled: bool
    backup_codes: List[str]


class MFADisableResponse(BaseModel):
    disabled: bool


class MFABackupCodesResponse(BaseModel):
    backup_codes: List[str]


class PasswordConfirmRequest(BaseModel):
    password: str
    code: Optional[str] = None


class AdminMFADisableRequest(BaseModel):
    user_id: str

class AuthsTable:
    def insert_new_auth(
        self,
        email: str,
        password: str,
        name: str,
        profile_image_url: str = "/user.png",
        role: str = "pending",
        oauth_sub: Optional[str] = None,
    ) -> Optional[UserModel]:
        with get_db() as db:
            log.info("insert_new_auth")

            id = str(uuid.uuid4())

            auth = AuthModel(
                **{"id": id, "email": email, "password": password, "active": True}
            )
            result = Auth(**auth.model_dump())
            db.add(result)

            user = Users.insert_new_user(
                id, name, email, profile_image_url, role, oauth_sub
            )

            db.commit()
            db.refresh(result)

            if result and user:
                return user
            else:
                return None

    def authenticate_user(self, email: str, password: str) -> Optional[UserModel]:
        log.info(f"authenticate_user: {email}")
        try:
            with get_db() as db:
                auth = db.query(Auth).filter_by(email=email, active=True).first()
                if auth:
                    if verify_password(password, auth.password):
                        user = Users.get_user_by_id(auth.id)
                        return user
                    else:
                        return None
                else:
                    return None
        except Exception:
            return None

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
                else:
                    return None
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
            
    def setup_mfa(self, user_id: str, secret: str) -> bool:
        """Store a TOTP secret for a user during MFA setup"""
        log.info(f"setup_mfa for user: {user_id}")
        try:
            with get_db() as db:
                auth = db.query(Auth).filter_by(id=user_id).first()
                if auth:
                    auth.mfa_secret = secret
                    db.commit()
                    return True
                return False
        except Exception as e:
            log.error(f"Error in setup_mfa: {e}")
            return False
            
    def enable_mfa(self, user_id: str, backup_codes: List[str]) -> bool:
        """Enable MFA for a user and store backup codes"""
        log.info(f"enable_mfa for user: {user_id}")
        try:
            with get_db() as db:
                auth = db.query(Auth).filter_by(id=user_id).first()
                if auth:
                    auth.mfa_enabled = True
                    auth.backup_codes = json.dumps(backup_codes)
                    auth.mfa_last_used = datetime.utcnow().isoformat()
                    db.commit()
                    return True
                return False
        except Exception as e:
            log.error(f"Error in enable_mfa: {e}")
            return False
            
    def disable_mfa(self, user_id: str) -> bool:
        """Disable MFA for a user"""
        log.info(f"disable_mfa for user: {user_id}")
        try:
            with get_db() as db:
                auth = db.query(Auth).filter_by(id=user_id).first()
                if auth:
                    auth.mfa_enabled = False
                    auth.mfa_secret = None
                    auth.backup_codes = None
                    auth.mfa_last_used = None
                    db.commit()
                    return True
                return False
        except Exception as e:
            log.error(f"Error in disable_mfa: {e}")
            return False
            
    def update_backup_codes(self, user_id: str, backup_codes: List[str]) -> bool:
        """Update backup codes for a user"""
        log.info(f"update_backup_codes for user: {user_id}")
        try:
            with get_db() as db:
                auth = db.query(Auth).filter_by(id=user_id).first()
                if auth and auth.mfa_enabled:
                    auth.backup_codes = json.dumps(backup_codes)
                    db.commit()
                    return True
                return False
        except Exception as e:
            log.error(f"Error in update_backup_codes: {e}")
            return False
            
    def use_backup_code(self, user_id: str, used_code_hash: str) -> bool:
        """Remove a used backup code"""
        log.info(f"use_backup_code for user: {user_id}")
        try:
            with get_db() as db:
                auth = db.query(Auth).filter_by(id=user_id).first()
                if auth and auth.mfa_enabled and auth.backup_codes:
                    backup_codes = json.loads(auth.backup_codes)
                    if used_code_hash in backup_codes:
                        backup_codes.remove(used_code_hash)
                        auth.backup_codes = json.dumps(backup_codes)
                        auth.mfa_last_used = datetime.utcnow().isoformat()
                        db.commit()
                        return True
                return False
        except Exception as e:
            log.error(f"Error in use_backup_code: {e}")
            return False
    
    def get_auth_by_id(self, user_id: str) -> Optional[Auth]:
        """Get auth record by user ID"""
        log.info(f"get_auth_by_id: {user_id}")
        try:
            with get_db() as db:
                auth = db.query(Auth).filter_by(id=user_id).first()
                return auth
        except Exception as e:
            log.error(f"Error in get_auth_by_id: {e}")
            return None
            
    def update_mfa_last_used(self, user_id: str) -> bool:
        """Update the last used timestamp for MFA"""
        log.info(f"update_mfa_last_used for user: {user_id}")
        try:
            with get_db() as db:
                auth = db.query(Auth).filter_by(id=user_id).first()
                if auth and auth.mfa_enabled:
                    auth.mfa_last_used = datetime.utcnow().isoformat()
                    db.commit()
                    return True
                return False
        except Exception as e:
            log.error(f"Error in update_mfa_last_used: {e}")
            return False


Auths = AuthsTable()
