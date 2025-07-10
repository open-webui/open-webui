import time
from typing import Optional
import base64

from open_webui.internal.db import Base, JSONField, get_db
from open_webui.models.chats import Chats
from open_webui.models.groups import Groups

from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Column, String, Text, LargeBinary
from sqlalchemy import or_

####################
# User DB Schema
####################

class User(Base):
    __tablename__ = "user"

    # id stores the derived UserID (HMAC of email, hex digest). This is the primary key.
    id = Column(String, primary_key=True, index=True)
    name = Column(String)

    # Email is still stored and used for login, and as the source for UserID generation.
    # It must be unique as it's the basis for the unique UserID.
    # WRONG - I will ultimately no use this for SaaS; may be used for Enterprise
    email = Column(String, unique=True, index=True, nullable=False)
    role = Column(String)
    profile_image_url = Column(Text)

    last_active_at = Column(BigInteger)
    updated_at = Column(BigInteger)
    created_at = Column(BigInteger)

    api_key = Column(String, nullable=True, unique=True)
    settings = Column(JSONField, nullable=True)
    info = Column(JSONField, nullable=True)

    # Made nullable to accommodate users created before OAuth integration or local users.
    # WE ARE NOT GOING TO SUPPORT OAUTH
    oauth_sub = Column(Text, unique=True, nullable=True)

    # Fields for per-user encryption:
    # TODO: CRITICAL FOR SECURITY - The 'user_key' column is for temporary local development ONLY.
    # It stores the raw derived UserKey (PBKDF2 output). In a production system adhering to the spec,
    # this key would NOT be stored in the database. It would be managed client-side,
    # ideally delivered via a client certificate for mTLS authentication.
    # This field should be removed when client certificate issuance and mTLS auth are implemented.
    user_key = Column(LargeBinary, nullable=True)  # TEMPORARY STORAGE for raw UserKey

    # Salt used in PBKDF2 with the UserID to derive the UserKey.
    salt = Column(LargeBinary, nullable=True)

    # The user's Data Encryption Key (DEK), encrypted with their UserKey.
    # The DEK is randomly generated per user and is used to encrypt their actual chat messages.
    user_encrypted_dek = Column(LargeBinary, nullable=True)

    # The same plaintext DEK, but encrypted with a master KMS Customer-Managed Key (CMK).
    # This serves as the "break-glass" disaster recovery mechanism for user data.
    # TODO: This field will store actual KMS ciphertext when deployed to AWS and integrated with KMS.
    kms_encrypted_dek = Column(LargeBinary, nullable=True)  # STUB - For future KMS integration

class UserSettings(BaseModel):
    ui: Optional[dict] = {}
    model_config = ConfigDict(extra="allow")
    pass


class UserModel(BaseModel):
    # Pydantic model for User data. Corresponds to the User SQLAlchemy model.
    # Ensures data validation and serialization/deserialization.

    id: str  # Derived UserID (HMAC of email)
    name: str
    email: str
    role: str = "pending"
    profile_image_url: str

    last_active_at: int  # timestamp in epoch
    updated_at: int  # timestamp in epoch
    created_at: int  # timestamp in epoch

    api_key: Optional[str] = None
    settings: Optional[UserSettings] = None
    info: Optional[dict] = None

    oauth_sub: Optional[str] = None

    # Fields for per-user encryption.
    # These are stored as bytes in the DB; Pydantic model represents them as Optional[bytes].
    # TODO: Remove 'user_key' from this model when it's removed from the User DB model (after client certs).
    user_key: Optional[bytes] = None                # TEMPORARY
    salt: Optional[bytes] = None
    user_encrypted_dek: Optional[bytes] = None
    kms_encrypted_dek: Optional[bytes] = None       # STUB for KMS

    model_config = ConfigDict(
        from_attributes=True, # orm_mode = True in Pydantic V1
        json_encoders={
            bytes: lambda b: base64.b64encode(b).decode('utf-8') if b is not None else None
        }
    )


####################
# Forms
####################


class UserListResponse(BaseModel):
    users: list[UserModel]
    total: int


class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    role: str
    profile_image_url: str


class UserNameResponse(BaseModel):
    id: str
    name: str
    role: str
    profile_image_url: str


class UserRoleUpdateForm(BaseModel):
    id: str
    role: str


class UserUpdateForm(BaseModel):
    role: str
    name: str
    email: str
    profile_image_url: str
    password: Optional[str] = None


class UsersTable:
    def insert_new_user(
        self,
        id: str,                  # This is now the derived UserID (HMAC of email)
        name: str,
        email: str,
        profile_image_url: str = "/user.png",
        role: str = "pending",
        oauth_sub: Optional[str] = None,

        # New parameters for encryption fields
        salt: Optional[bytes] = None,
        user_key: Optional[bytes] = None,               # TEMPORARY - Raw UserKey
        user_encrypted_dek: Optional[bytes] = None,
        kms_encrypted_dek: Optional[bytes] = None,      # STUB for KMS
    ) -> Optional[UserModel]:
        # Inserts a new user into the database with all associated information,
        # including fields required for per-user encryption.
        # The 'id' parameter is the derived UserID.
        # The 'user_key' is stored temporarily and should be removed in later stages.
        with get_db() as db:
            user_data = {
                    "id": id,
                    "name": name,
                    "email": email,
                    "role": role,
                    "profile_image_url": profile_image_url,
                    "last_active_at": int(time.time()),
                    "created_at": int(time.time()),
                    "updated_at": int(time.time()),
                    "oauth_sub": oauth_sub,
                # Encryption-related fields
                "salt": salt,
                "user_key": user_key, # TEMPORARY
                "user_encrypted_dek": user_encrypted_dek,
                "kms_encrypted_dek": kms_encrypted_dek, # STUB
            }
            
            # Create Pydantic model instance for validation and to ensure all fields are present/defaulted
            user_model_instance = UserModel(**user_data)
            
            # Create SQLAlchemy model instance using the Pydantic model's dump.
            # exclude_none=True ensures that fields not provided (and thus None) are not
            # passed to the SQLAlchemy model if they are not explicitly nullable there or have server defaults.
            db_user = User(**user_model_instance.model_dump(exclude_none=True))
            
            db.add(db_user)
            db.commit()
            db.refresh(db_user)
            
            # Return the Pydantic model instance, which is useful for API responses.
            return UserModel.model_validate(db_user)

    def get_user_by_id(self, id: str) -> Optional[UserModel]:
        try:
            with get_db() as db:
                user = db.query(User).filter_by(id=id).first()
                return UserModel.model_validate(user) if user else None
        except Exception:
            # Consider logging the exception here
            return None

    def get_user_by_api_key(self, api_key: str) -> Optional[UserModel]:
        try:
            with get_db() as db:
                user = db.query(User).filter_by(api_key=api_key).first()
                return UserModel.model_validate(user) if user else None
        except Exception:
            return None

    def get_user_by_email(self, email: str) -> Optional[UserModel]:
        try:
            with get_db() as db:
                user = db.query(User).filter_by(email=email).first()
                return UserModel.model_validate(user) if user else None
        except Exception:
            return None

    def get_user_by_oauth_sub(self, sub: str) -> Optional[UserModel]:
        try:
            with get_db() as db:
                user = db.query(User).filter_by(oauth_sub=sub).first()
                return UserModel.model_validate(user) if user else None
        except Exception:
            return None

    def get_users(
        self,
        filter: Optional[dict] = None,
        skip: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> UserListResponse:
        with get_db() as db:
            query = db.query(User)

            if filter:
                query_key = filter.get("query")
                if query_key:
                    query = query.filter(
                        or_(
                            User.name.ilike(f"%{query_key}%"),
                            User.email.ilike(f"%{query_key}%"),
                        )
                    )

                order_by = filter.get("order_by")
                direction = filter.get("direction")

                if order_by == "name":
                    if direction == "asc":
                        query = query.order_by(User.name.asc())
                    else:
                        query = query.order_by(User.name.desc())
                elif order_by == "email":
                    if direction == "asc":
                        query = query.order_by(User.email.asc())
                    else:
                        query = query.order_by(User.email.desc())

                elif order_by == "created_at":
                    if direction == "asc":
                        query = query.order_by(User.created_at.asc())
                    else:
                        query = query.order_by(User.created_at.desc())

                elif order_by == "last_active_at":
                    if direction == "asc":
                        query = query.order_by(User.last_active_at.asc())
                    else:
                        query = query.order_by(User.last_active_at.desc())

                elif order_by == "updated_at":
                    if direction == "asc":
                        query = query.order_by(User.updated_at.asc())
                    else:
                        query = query.order_by(User.updated_at.desc())
                elif order_by == "role":
                    if direction == "asc":
                        query = query.order_by(User.role.asc())
                    else:
                        query = query.order_by(User.role.desc())

            else:
                query = query.order_by(User.created_at.desc())

            if skip:
                query = query.offset(skip)
            if limit:
                query = query.limit(limit)

            users = query.all()
            return {
                "users": [UserModel.model_validate(user) for user in users],
                "total": db.query(User).count(),
            }

    def get_users_by_user_ids(self, user_ids: list[str]) -> list[UserModel]:
        with get_db() as db:
            users = db.query(User).filter(User.id.in_(user_ids)).all()
            return [UserModel.model_validate(user) for user in users]

    def get_num_users(self) -> Optional[int]:
        with get_db() as db:
            return db.query(User).count()

    def get_first_user(self) -> Optional[UserModel]:
        try:
            with get_db() as db:
                user = db.query(User).order_by(User.created_at).first()
                return UserModel.model_validate(user) if user else None
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
                return UserModel.model_validate(user) if user else None
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
                return UserModel.model_validate(user) if user else None
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
                return UserModel.model_validate(user) if user else None
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
                return UserModel.model_validate(user) if user else None
        except Exception:
            return None

    def update_user_by_id(self, id: str, updated: dict) -> Optional[UserModel]:
        try:
            with get_db() as db:
                db.query(User).filter_by(id=id).update(updated)
                db.commit()

                user = db.query(User).filter_by(id=id).first()
                return UserModel.model_validate(user) if user else None
                # return UserModel(**user.dict())
        except Exception:
            return None

    def update_user_settings_by_id(self, id: str, updated: dict) -> Optional[UserModel]:
        try:
            with get_db() as db:
                user_settings = db.query(User).filter_by(id=id).first().settings

                if user_settings is None:
                    user_settings = {}

                user_settings.update(updated)

                db.query(User).filter_by(id=id).update({"settings": user_settings})
                db.commit()

                user = db.query(User).filter_by(id=id).first()
                return UserModel.model_validate(user) if user else None
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

    def update_user_api_key_by_id(self, id: str, api_key: str) -> bool:
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
                return user.api_key if user else None
        except Exception:
            return None

    def get_valid_user_ids(self, user_ids: list[str]) -> list[str]:
        with get_db() as db:
            users = db.query(User).filter(User.id.in_(user_ids)).all()
            return [user.id for user in users]

    def get_super_admin_user(self) -> Optional[UserModel]:
        with get_db() as db:
            user = db.query(User).filter_by(role="admin").first()
            if user:
                return UserModel.model_validate(user)
            else:
                return None


Users = UsersTable()
