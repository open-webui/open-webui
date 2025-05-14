import time
from typing import Optional

from open_webui.internal.db import Base, JSONField, get_db
from open_webui.models.chats import Chats
from beyond_the_loop.models.groups import Groups

from functools import partial

from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Column, String, Text, ForeignKey
from sqlalchemy.orm import relationship


####################
# User DB Schema
####################


class User(Base):
    __tablename__ = "user"

    id = Column(String, primary_key=True)
    first_name = Column(String)
    last_name = Column(String)
    email = Column(String)
    role = Column(String)
    profile_image_url = Column(Text)

    last_active_at = Column(BigInteger)
    updated_at = Column(BigInteger)
    created_at = Column(BigInteger)

    api_key = Column(String, nullable=True, unique=True)
    settings = Column(JSONField, nullable=True)
    info = Column(JSONField, nullable=True)

    oauth_sub = Column(Text, unique=True)

    invite_token = Column(Text, nullable=True)
    registration_code = Column(Text, nullable=True)

    password_reset_token = Column(Text, nullable=True)
    password_reset_token_expires_at = Column(BigInteger, nullable=True)

    company_id = Column(String, ForeignKey("company.id", ondelete="CASCADE"), nullable=False)
    company = relationship("Company", back_populates="users")


class UserSettings(BaseModel):
    ui: Optional[dict] = partial(dict)
    model_config = ConfigDict(extra="allow")
    pass


class UserModel(BaseModel):
    id: str
    first_name: str
    last_name: str
    email: str
    role: str
    profile_image_url: str

    last_active_at: int  # timestamp in epoch
    updated_at: int  # timestamp in epoch
    created_at: int  # timestamp in epoch

    api_key: Optional[str] = None
    settings: Optional[UserSettings] = None
    info: Optional[dict] = None

    oauth_sub: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

    company_id: str

    invite_token: Optional[str] = None
    registration_code: Optional[str] = None

    password_reset_token: Optional[str] = None
    password_reset_token_expires_at: Optional[int] = None


####################
# Forms
####################


class UserResponse(BaseModel):
    id: str
    first_name: str
    last_name: str
    email: str
    role: str
    profile_image_url: str


class UserNameResponse(BaseModel):
    id: str
    first_name: str
    last_name: str
    role: str
    profile_image_url: str


class UserRoleUpdateForm(BaseModel):
    id: str
    role: str


class UserUpdateForm(BaseModel):
    first_name: str
    last_name: str
    profile_image_url: str
    password: Optional[str] = None


class InviteeData(BaseModel):
    email: str
    role: str


class UserInviteForm(BaseModel):
    invitees: list[InviteeData]
    group_ids: Optional[list[str]] = None
    group_names: Optional[list[str]] = None


class UserCreateForm(BaseModel):
    email: str


class UserReinviteForm(BaseModel):
    email: str

class UserRevokeInviteForm(BaseModel):
    email: str


class UsersTable:
    def insert_new_user(
        self,
        id: str,
        first_name: str,
        last_name: str,
        email: str,
        company_id: str,
        profile_image_url: str = "/user.png",
        role: str = "pending",
        oauth_sub: Optional[str] = None,
        invite_token: Optional[str] = None,
        registration_code: Optional[str] = None,
    ) -> Optional[UserModel]:
        with get_db() as db:
            user = UserModel(
                **{
                    "id": id,
                    "first_name": first_name,
                    "last_name": last_name,
                    "email": email,
                    "role": role,
                    "profile_image_url": profile_image_url,
                    "last_active_at": int(time.time()),
                    "created_at": int(time.time()),
                    "updated_at": int(time.time()),
                    "oauth_sub": oauth_sub,
                    "company_id": company_id,
                    "invite_token": invite_token,
                    "registration_code": registration_code,
                }
            )
            result = User(**user.model_dump())
            db.add(result)
            db.commit()
            db.refresh(result)
            if result:
                return user
            else:
                return None

    def get_user_by_id(self, id: str) -> Optional[UserModel]:
        try:
            with get_db() as db:
                user = db.query(User).filter_by(id=id).first()
                return UserModel.model_validate(user)
        except Exception:
            return None

    def get_user_by_invite_token(self, invite_token: str) -> Optional[UserModel]:
        try:
            with get_db() as db:
                user = db.query(User).filter_by(invite_token=invite_token).first()
                return UserModel.model_validate(user)
        except Exception:
            return None

    def get_user_by_registration_code(self, registration_code: str) -> Optional[UserModel]:
        try:
            with get_db() as db:
                user = db.query(User).filter_by(registration_code=registration_code).first()
                return UserModel.model_validate(user)
        except Exception:
            return None

    def complete_by_id(self, id: str, first_name: str, last_name: str, profile_image_url: Optional[str] = None, company_id: Optional[str] = None) -> Optional[UserModel]:
        try:
            with get_db() as db:
                update_data = {"first_name": first_name, "last_name": last_name, "invite_token": None, "registration_code": None}

                if profile_image_url is not None:
                    update_data["profile_image_url"] = profile_image_url

                if company_id is not None:
                    update_data["company_id"] = company_id

                db.query(User).filter_by(id=id).update(update_data)
                db.commit()
                user = db.query(User).filter_by(id=id).first()
                return UserModel.model_validate(user)
        except Exception:
            return None

    def get_user_by_api_key(self, api_key: str) -> Optional[UserModel]:
        try:
            with get_db() as db:
                user = db.query(User).filter_by(api_key=api_key).first()
                return UserModel.model_validate(user)
        except Exception:
            return None

    def get_user_by_email(self, email: str) -> Optional[UserModel]:
        try:
            with get_db() as db:
                user = db.query(User).filter_by(email=email).first()
                return UserModel.model_validate(user)
        except Exception:
            return None

    def get_user_by_oauth_sub(self, sub: str) -> Optional[UserModel]:
        try:
            with get_db() as db:
                user = db.query(User).filter_by(oauth_sub=sub).first()
                return UserModel.model_validate(user)
        except Exception:
            return None

    def get_users_by_company_id(
        self, company_id: str, skip: Optional[int] = None, limit: Optional[int] = None
    ) -> list[UserModel]:
        with get_db() as db:

            query = db.query(User).filter(User.company_id == company_id).order_by(User.created_at.desc())

            if skip:
                query = query.offset(skip)
            if limit:
                query = query.limit(limit)

            users = query.all()

            return [UserModel.model_validate(user) for user in users]

    def get_users(
        self, skip: Optional[int] = None, limit: Optional[int] = None
    ) -> list[UserModel]:
        with get_db() as db:

            query = db.query(User).order_by(User.created_at.desc())

            if skip:
                query = query.offset(skip)
            if limit:
                query = query.limit(limit)

            users = query.all()

            return [UserModel.model_validate(user) for user in users]

    def get_users_by_user_ids(self, user_ids: list[str]) -> list[UserModel]:
        with get_db() as db:
            users = db.query(User).filter(User.id.in_(user_ids)).all()
            return [UserModel.model_validate(user) for user in users]

    def get_num_users(self) -> Optional[int]:
        with get_db() as db:
            return db.query(User).count()

    def get_first_user(self) -> UserModel:
        try:
            with get_db() as db:
                user = db.query(User).order_by(User.created_at).first()
                return UserModel.model_validate(user)
        except Exception:
            return None

    def get_user_webhook_url_by_id(self, id: str) -> Optional[str]:
        try:
            with get_db() as db:
                user = db.query(User).filter_by(id=id).first()

                if user.settings is None:
                    return None
                else:
                    return (
                        user.settings.get("ui", {})
                        .get("notifications", {})
                        .get("webhook_url", None)
                    )
        except Exception:
            return None

    def update_user_role_by_id(self, id: str, role: str) -> Optional[UserModel]:
        try:
            with get_db() as db:
                db.query(User).filter_by(id=id).update({"role": role})
                db.commit()
                user = db.query(User).filter_by(id=id).first()
                return UserModel.model_validate(user)
        except Exception:
            return None

    def update_user_profile_image_url_by_id(
        self, id: str, profile_image_url: str
    ) -> Optional[UserModel]:
        try:
            with get_db() as db:
                db.query(User).filter_by(id=id).update(
                    {"profile_image_url": profile_image_url}
                )
                db.commit()

                user = db.query(User).filter_by(id=id).first()
                return UserModel.model_validate(user)
        except Exception:
            return None

    def update_user_last_active_by_id(self, id: str) -> Optional[UserModel]:
        try:
            with get_db() as db:
                db.query(User).filter_by(id=id).update(
                    {"last_active_at": int(time.time())}
                )
                db.commit()

                user = db.query(User).filter_by(id=id).first()
                return UserModel.model_validate(user)
        except Exception:
            return None

    def update_user_oauth_sub_by_id(
        self, id: str, oauth_sub: str
    ) -> Optional[UserModel]:
        try:
            with get_db() as db:
                db.query(User).filter_by(id=id).update({"oauth_sub": oauth_sub})
                db.commit()

                user = db.query(User).filter_by(id=id).first()
                return UserModel.model_validate(user)
        except Exception:
            return None

    def update_user_by_id(self, id: str, updated: dict) -> Optional[UserModel]:
        try:
            with get_db() as db:
                db.query(User).filter_by(id=id).update(updated)
                db.commit()

                user = db.query(User).filter_by(id=id).first()
                return UserModel.model_validate(user)
        except Exception:
            return None

    def delete_user_by_id(self, id: str) -> bool:
        try:
            # Remove User from Groups
            Groups.remove_user_from_all_groups(id)

            # Delete User Chats
            result = Chats.delete_chats_by_user_id(id)
            if result:
                with get_db() as db:
                    # Delete User
                    db.query(User).filter_by(id=id).delete()
                    db.commit()

                return True
            else:
                return False
        except Exception:
            return False

    def delete_user_by_email(self, email: str) -> bool:
        """Delete a user by their email address.
        
        Args:
            email: The email address of the user to delete
            
        Returns:
            bool: True if user was successfully deleted, False otherwise
        """
        try:
            with get_db() as db:
                user = db.query(User).filter_by(email=email).first()
                if user:
                    db.delete(user)
                    db.commit()
                    return True
                return False
        except Exception:
            return False

    def update_user_api_key_by_id(self, id: str, api_key: str) -> str:
        try:
            with get_db() as db:
                result = db.query(User).filter_by(id=id).update({"api_key": api_key})
                db.commit()
                return True if result == 1 else False
        except Exception:
            return False

    def get_user_api_key_by_id(self, id: str) -> Optional[str]:
        try:
            with get_db() as db:
                user = db.query(User).filter_by(id=id).first()
                return user.api_key
        except Exception:
            return None

    def get_valid_user_ids(self, user_ids: list[str]) -> list[str]:
        with get_db() as db:
            users = db.query(User).filter(User.id.in_(user_ids)).all()
            return [user.id for user in users]

    def set_password_reset_token(self, email: str, reset_token: str, expires_at: int) -> bool:
        """
        Set a password reset token for a user by their email.
        
        Args:
            email: The user's email
            reset_token: The generated reset token
            expires_at: Timestamp when the token expires
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with get_db() as db:
                result = db.query(User).filter_by(email=email).update({
                    "password_reset_token": reset_token,
                    "password_reset_token_expires_at": expires_at
                })
                db.commit()
                return True if result == 1 else False
        except Exception:
            return False
            
    def get_user_by_password_reset_token(self, reset_token: str) -> Optional[UserModel]:
        """
        Get a user by their reset token.
        
        Args:
            reset_token: The reset token to look up
            
        Returns:
            Optional[UserModel]: The user if found, None otherwise
        """
        try:
            with get_db() as db:
                user = db.query(User).filter_by(password_reset_token=reset_token).first()
                return UserModel.model_validate(user) if user else None
        except Exception:
            return None
            
    def clear_password_reset_token(self, id: str) -> bool:
        """
        Clear the reset token for a user after password reset.
        
        Args:
            id: The user ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with get_db() as db:
                db.query(User).filter_by(id=id).update({
                    "password_reset_token": None,
                    "password_reset_token_expires_at": None
                })
                db.commit()
                return True
        except Exception:
            return False

    def get_admin_users_by_company(self, company_id: str) -> list[UserModel]:
        """
        Returns all admin users for a specific company.
        """
        try:
            with get_db() as db:
                users = db.query(User).filter(User.company_id == company_id, User.role == "admin").all()
                return [UserModel.model_validate(user) for user in users]
        except Exception as e:
            print(f"Error getting admin users by company: {e}")
            return []

    def count_users_by_company_id(self, company_id: str) -> int:
        """
        Returns the number of users for a specific company.
        """
        try:
            with get_db() as db:
                return db.query(User).filter(User.company_id == company_id).count()
        except Exception as e:
            print(f"Error counting users by company: {e}")
            return 0


def get_users_by_company(company_id: str) -> list[UserModel]:
    """
    Returns all users for a specific company.
    """
    try:
        with get_db() as db:
            users = db.query(User).filter(User.company_id == company_id).all()
            return [UserModel.model_validate(user) for user in users]
    except Exception as e:
        print(f"Error getting users by company: {e}")
        return []


def get_active_users_by_company(company_id: str, since_timestamp: int) -> list[UserModel]:
    """
    Returns users for a specific company that were active since the given timestamp.
    
    Args:
        company_id: The ID of the company to filter users by
        since_timestamp: Unix timestamp to filter users who were active since this time
        
    Returns:
        A list of UserModel objects representing active users
    """
    try:
        with get_db() as db:
            active_users = db.query(User).filter(
                User.company_id == company_id,
                User.last_active_at >= since_timestamp
            ).all()
            return [UserModel.model_validate(user) for user in active_users]
    except Exception as e:
        print(f"Error getting active users by company: {e}")
        return []


Users = UsersTable()
