import time
from typing import Optional

from open_webui.internal.db import Base, JSONField, get_db


from open_webui.env import DATABASE_USER_ACTIVE_STATUS_UPDATE_INTERVAL

from open_webui.models.chats import Chats
from open_webui.models.groups import Groups, GroupMember
from open_webui.models.channels import ChannelMember

from open_webui.utils.misc import throttle


from pydantic import BaseModel, ConfigDict
from sqlalchemy import (
    BigInteger,
    JSON,
    Column,
    String,
    Boolean,
    Text,
    Date,
    exists,
    select,
    cast,
)
from sqlalchemy import or_, case
from sqlalchemy.dialects.postgresql import JSONB

import datetime

####################
# User DB Schema
####################


class UserSettings(BaseModel):
    ui: Optional[dict] = {}
    model_config = ConfigDict(extra="allow")
    pass


class User(Base):
    __tablename__ = "user"

    id = Column(String, primary_key=True, unique=True)
    email = Column(String)
    username = Column(String(50), nullable=True)
    role = Column(String)

    name = Column(String)

    profile_image_url = Column(Text)
    profile_banner_image_url = Column(Text, nullable=True)

    bio = Column(Text, nullable=True)
    gender = Column(Text, nullable=True)
    date_of_birth = Column(Date, nullable=True)
    timezone = Column(String, nullable=True)

    presence_state = Column(String, nullable=True)
    status_emoji = Column(String, nullable=True)
    status_message = Column(Text, nullable=True)
    status_expires_at = Column(BigInteger, nullable=True)

    info = Column(JSON, nullable=True)
    settings = Column(JSON, nullable=True)

    oauth = Column(JSON, nullable=True)

    last_active_at = Column(BigInteger)
    updated_at = Column(BigInteger)
    created_at = Column(BigInteger)


class UserModel(BaseModel):
    id: str

    email: str
    username: Optional[str] = None
    role: str = "pending"

    name: str

    profile_image_url: str
    profile_banner_image_url: Optional[str] = None

    bio: Optional[str] = None
    gender: Optional[str] = None
    date_of_birth: Optional[datetime.date] = None
    timezone: Optional[str] = None

    presence_state: Optional[str] = None
    status_emoji: Optional[str] = None
    status_message: Optional[str] = None
    status_expires_at: Optional[int] = None

    info: Optional[dict] = None
    settings: Optional[UserSettings] = None

    oauth: Optional[dict] = None

    last_active_at: int  # timestamp in epoch
    updated_at: int  # timestamp in epoch
    created_at: int  # timestamp in epoch

    model_config = ConfigDict(from_attributes=True)


class UserStatusModel(UserModel):
    is_active: bool = False

    model_config = ConfigDict(from_attributes=True)


class ApiKey(Base):
    __tablename__ = "api_key"

    id = Column(Text, primary_key=True, unique=True)
    user_id = Column(Text, nullable=False)
    key = Column(Text, unique=True, nullable=False)
    data = Column(JSON, nullable=True)
    expires_at = Column(BigInteger, nullable=True)
    last_used_at = Column(BigInteger, nullable=True)
    created_at = Column(BigInteger, nullable=False)
    updated_at = Column(BigInteger, nullable=False)


class ApiKeyModel(BaseModel):
    id: str
    user_id: str
    key: str
    data: Optional[dict] = None
    expires_at: Optional[int] = None
    last_used_at: Optional[int] = None
    created_at: int  # timestamp in epoch
    updated_at: int  # timestamp in epoch

    model_config = ConfigDict(from_attributes=True)


####################
# Forms
####################


class UpdateProfileForm(BaseModel):
    profile_image_url: str
    name: str
    bio: Optional[str] = None
    gender: Optional[str] = None
    date_of_birth: Optional[datetime.date] = None


class UserGroupIdsModel(UserModel):
    group_ids: list[str] = []


class UserModelResponse(UserModel):
    model_config = ConfigDict(extra="allow")


class UserListResponse(BaseModel):
    users: list[UserModelResponse]
    total: int


class UserGroupIdsListResponse(BaseModel):
    users: list[UserGroupIdsModel]
    total: int


class UserStatus(BaseModel):
    status_emoji: Optional[str] = None
    status_message: Optional[str] = None
    status_expires_at: Optional[int] = None


class UserInfoResponse(UserStatus):
    id: str
    name: str
    email: str
    role: str


class UserIdNameResponse(BaseModel):
    id: str
    name: str


class UserIdNameStatusResponse(UserStatus):
    id: str
    name: str
    is_active: Optional[bool] = None


class UserInfoListResponse(BaseModel):
    users: list[UserInfoResponse]
    total: int


class UserIdNameListResponse(BaseModel):
    users: list[UserIdNameResponse]
    total: int


class UserNameResponse(BaseModel):
    id: str
    name: str
    role: str


class UserResponse(UserNameResponse):
    email: str


class UserProfileImageResponse(UserNameResponse):
    email: str
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
        id: str,
        name: str,
        email: str,
        profile_image_url: str = "/user.png",
        role: str = "pending",
        oauth: Optional[dict] = None,
    ) -> Optional[UserModel]:
        with get_db() as db:
            user = UserModel(
                **{
                    "id": id,
                    "email": email,
                    "name": name,
                    "role": role,
                    "profile_image_url": profile_image_url,
                    "last_active_at": int(time.time()),
                    "created_at": int(time.time()),
                    "updated_at": int(time.time()),
                    "oauth": oauth,
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

    def get_user_by_api_key(self, api_key: str) -> Optional[UserModel]:
        try:
            with get_db() as db:
                user = (
                    db.query(User)
                    .join(ApiKey, User.id == ApiKey.user_id)
                    .filter(ApiKey.key == api_key)
                    .first()
                )
                return UserModel.model_validate(user) if user else None
        except Exception:
            return None

    def get_user_by_email(self, email: str) -> Optional[UserModel]:
        try:
            with get_db() as db:
                user = db.query(User).filter_by(email=email).first()
                return UserModel.model_validate(user)
        except Exception:
            return None

    def get_user_by_oauth_sub(self, provider: str, sub: str) -> Optional[UserModel]:
        try:
            with get_db() as db:  # type: Session
                dialect_name = db.bind.dialect.name

                query = db.query(User)
                if dialect_name == "sqlite":
                    query = query.filter(User.oauth.contains({provider: {"sub": sub}}))
                elif dialect_name == "postgresql":
                    query = query.filter(
                        User.oauth[provider].cast(JSONB)["sub"].astext == sub
                    )

                user = query.first()
                return UserModel.model_validate(user) if user else None
        except Exception as e:
            # You may want to log the exception here
            return None

    def get_users(
        self,
        filter: Optional[dict] = None,
        skip: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> dict:
        with get_db() as db:
            # Join GroupMember so we can order by group_id when requested
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

                channel_id = filter.get("channel_id")
                if channel_id:
                    query = query.filter(
                        exists(
                            select(ChannelMember.id).where(
                                ChannelMember.user_id == User.id,
                                ChannelMember.channel_id == channel_id,
                            )
                        )
                    )

                user_ids = filter.get("user_ids")
                group_ids = filter.get("group_ids")

                if isinstance(user_ids, list) and isinstance(group_ids, list):
                    # If both are empty lists, return no users
                    if not user_ids and not group_ids:
                        return {"users": [], "total": 0}

                if user_ids:
                    query = query.filter(User.id.in_(user_ids))

                if group_ids:
                    query = query.filter(
                        exists(
                            select(GroupMember.id).where(
                                GroupMember.user_id == User.id,
                                GroupMember.group_id.in_(group_ids),
                            )
                        )
                    )

                roles = filter.get("roles")
                if roles:
                    include_roles = [role for role in roles if not role.startswith("!")]
                    exclude_roles = [role[1:] for role in roles if role.startswith("!")]

                    if include_roles:
                        query = query.filter(User.role.in_(include_roles))
                    if exclude_roles:
                        query = query.filter(~User.role.in_(exclude_roles))

                order_by = filter.get("order_by")
                direction = filter.get("direction")

                if order_by and order_by.startswith("group_id:"):
                    group_id = order_by.split(":", 1)[1]

                    # Subquery that checks if the user belongs to the group
                    membership_exists = exists(
                        select(GroupMember.id).where(
                            GroupMember.user_id == User.id,
                            GroupMember.group_id == group_id,
                        )
                    )

                    # CASE: user in group → 1, user not in group → 0
                    group_sort = case((membership_exists, 1), else_=0)

                    if direction == "asc":
                        query = query.order_by(group_sort.asc(), User.name.asc())
                    else:
                        query = query.order_by(group_sort.desc(), User.name.asc())

                elif order_by == "name":
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

            # Count BEFORE pagination
            total = query.count()

            # correct pagination logic
            if skip is not None:
                query = query.offset(skip)
            if limit is not None:
                query = query.limit(limit)

            users = query.all()
            return {
                "users": [UserModel.model_validate(user) for user in users],
                "total": total,
            }

    def get_users_by_group_id(self, group_id: str) -> list[UserModel]:
        with get_db() as db:
            users = (
                db.query(User)
                .join(GroupMember, User.id == GroupMember.user_id)
                .filter(GroupMember.group_id == group_id)
                .all()
            )
            return [UserModel.model_validate(user) for user in users]

    def get_users_by_user_ids(self, user_ids: list[str]) -> list[UserStatusModel]:
        with get_db() as db:
            users = db.query(User).filter(User.id.in_(user_ids)).all()
            return [UserModel.model_validate(user) for user in users]

    def get_num_users(self) -> Optional[int]:
        with get_db() as db:
            return db.query(User).count()

    def has_users(self) -> bool:
        with get_db() as db:
            return db.query(db.query(User).exists()).scalar()

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

    def get_num_users_active_today(self) -> Optional[int]:
        with get_db() as db:
            current_timestamp = int(datetime.datetime.now().timestamp())
            today_midnight_timestamp = current_timestamp - (current_timestamp % 86400)
            query = db.query(User).filter(
                User.last_active_at > today_midnight_timestamp
            )
            return query.count()

    def update_user_role_by_id(self, id: str, role: str) -> Optional[UserModel]:
        try:
            with get_db() as db:
                db.query(User).filter_by(id=id).update({"role": role})
                db.commit()
                user = db.query(User).filter_by(id=id).first()
                return UserModel.model_validate(user)
        except Exception:
            return None

    def update_user_status_by_id(
        self, id: str, form_data: UserStatus
    ) -> Optional[UserModel]:
        try:
            with get_db() as db:
                db.query(User).filter_by(id=id).update(
                    {**form_data.model_dump(exclude_none=True)}
                )
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

    @throttle(DATABASE_USER_ACTIVE_STATUS_UPDATE_INTERVAL)
    def update_last_active_by_id(self, id: str) -> Optional[UserModel]:
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

    def update_user_oauth_by_id(
        self, id: str, provider: str, sub: str
    ) -> Optional[UserModel]:
        """
        Update or insert an OAuth provider/sub pair into the user's oauth JSON field.
        Example resulting structure:
            {
                "google": { "sub": "123" },
                "github": { "sub": "abc" }
            }
        """
        try:
            with get_db() as db:
                user = db.query(User).filter_by(id=id).first()
                if not user:
                    return None

                # Load existing oauth JSON or create empty
                oauth = user.oauth or {}

                # Update or insert provider entry
                oauth[provider] = {"sub": sub}

                # Persist updated JSON
                db.query(User).filter_by(id=id).update({"oauth": oauth})
                db.commit()

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
                # return UserModel(**user.dict())
        except Exception as e:
            print(e)
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

    def get_user_api_key_by_id(self, id: str) -> Optional[str]:
        try:
            with get_db() as db:
                api_key = db.query(ApiKey).filter_by(user_id=id).first()
                return api_key.key if api_key else None
        except Exception:
            return None

    def update_user_api_key_by_id(self, id: str, api_key: str) -> bool:
        try:
            with get_db() as db:
                db.query(ApiKey).filter_by(user_id=id).delete()
                db.commit()

                now = int(time.time())
                new_api_key = ApiKey(
                    id=f"key_{id}",
                    user_id=id,
                    key=api_key,
                    created_at=now,
                    updated_at=now,
                )
                db.add(new_api_key)
                db.commit()

                return True

        except Exception:
            return False

    def delete_user_api_key_by_id(self, id: str) -> bool:
        try:
            with get_db() as db:
                db.query(ApiKey).filter_by(user_id=id).delete()
                db.commit()
                return True
        except Exception:
            return False

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

    def get_active_user_count(self) -> int:
        with get_db() as db:
            # Consider user active if last_active_at within the last 3 minutes
            three_minutes_ago = int(time.time()) - 180
            count = (
                db.query(User).filter(User.last_active_at >= three_minutes_ago).count()
            )
            return count

    def is_user_active(self, user_id: str) -> bool:
        with get_db() as db:
            user = db.query(User).filter_by(id=user_id).first()
            if user and user.last_active_at:
                # Consider user active if last_active_at within the last 3 minutes
                three_minutes_ago = int(time.time()) - 180
                return user.last_active_at >= three_minutes_ago
            return False


Users = UsersTable()
