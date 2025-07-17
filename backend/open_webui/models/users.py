import time
from typing import Optional
from logging import getLogger

from open_webui.internal.db import Base, JSONField, get_db


from open_webui.models.chats import Chats
from open_webui.models.groups import Groups


from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Column, String, Text

# Add logger for the users module
logger = getLogger(__name__)

####################
# User DB Schema
####################


class User(Base):
    __tablename__ = "user"

    id = Column(String, primary_key=True)
    name = Column(String)
    email = Column(String)
    role = Column(String)
    profile_image_url = Column(Text)
    domain = Column(String)

    last_active_at = Column(BigInteger)
    updated_at = Column(BigInteger)
    created_at = Column(BigInteger)

    api_key = Column(String, nullable=True, unique=True)
    settings = Column(JSONField, nullable=True)
    info = Column(JSONField, nullable=True)

    oauth_sub = Column(Text, unique=True)


class UserSettings(BaseModel):
    ui: Optional[dict] = {}
    model_config = ConfigDict(extra="allow")
    pass


class UserModel(BaseModel):
    id: str
    name: str
    email: str
    role: str = "pending"
    profile_image_url: str
    domain: str = "*"

    last_active_at: int  # timestamp in epoch
    updated_at: int  # timestamp in epoch
    created_at: int  # timestamp in epoch

    api_key: Optional[str] = None
    settings: Optional[UserSettings] = None
    info: Optional[dict] = None

    oauth_sub: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


####################
# Forms
####################


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
        oauth_sub: Optional[str] = None,
        domain: str = "*",
    ) -> Optional[UserModel]:
        with get_db() as db:
            user = UserModel(
                **{
                    "id": id,
                    "name": name,
                    "email": email,
                    "role": role,
                    "profile_image_url": profile_image_url,
                    "domain": domain,
                    "last_active_at": int(time.time()),
                    "created_at": int(time.time()),
                    "updated_at": int(time.time()),
                    "oauth_sub": oauth_sub,
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

    def get_user_domains(self) -> list[str]:
        with get_db() as db:
            return [domain[0] for domain in db.query(User.domain).distinct().all()]

    def get_num_users(self, domain: Optional[str] = None) -> Optional[int]:
        try:
            with get_db() as db:
                if domain:
                    return db.query(User).filter_by(domain=domain).count()
                return db.query(User).count()
        except Exception:
            return None

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

    def get_daily_users_number(
        self, days: int = 1, domain: Optional[str] = None
    ) -> Optional[int]:
        try:
            with get_db() as db:
                start_time = int(time.time()) - (days * 24 * 60 * 60)
                query = db.query(User).filter(User.last_active_at >= start_time)

                if domain:
                    query = query.filter(User.domain == domain)

                return query.count()
        except Exception as e:
            logger.error(f"Failed to get daily users number: {e}")
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
                # return UserModel(**user.dict())
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

    def get_historical_users_data(
        self, days: int = 7, domain: Optional[str] = None
    ) -> list[dict]:
        try:
            result = []
            current_time = int(time.time())

            # Calculate today's date at midnight for proper day boundary
            today = time.strftime("%Y-%m-%d", time.localtime(current_time))
            today_midnight = int(
                time.mktime(time.strptime(f"{today} 00:00:00", "%Y-%m-%d %H:%M:%S"))
            )

            # Generate all date strings first to ensure no gaps
            date_strings = []
            dates_timestamps = []
            for day in range(days):
                # Calculate day start (midnight) for each day in the past
                day_start = today_midnight - (day * 24 * 60 * 60)
                date_str = time.strftime("%Y-%m-%d", time.localtime(day_start))
                date_strings.append(date_str)
                dates_timestamps.append(day_start)

            # Sort date strings to ensure chronological order
            date_pairs = sorted(zip(date_strings, dates_timestamps))
            date_strings = [pair[0] for pair in date_pairs]
            dates_timestamps = [pair[1] for pair in date_pairs]

            # Process each day individually
            for i, (date_str, day_start) in enumerate(
                zip(date_strings, dates_timestamps)
            ):
                # Calculate day boundaries (midnight to midnight)
                start_time = day_start
                end_time = start_time + (24 * 60 * 60)

                with get_db() as db:
                    query = db.query(User).filter(
                        User.created_at < end_time,
                    )

                    if domain:
                        query = query.filter(User.domain == domain)

                    count = query.count()

                    result.append({"date": date_str, "count": count})

            # Return in chronological order
            return result
        except Exception as e:
            logger.error(f"Failed to get historical users data: {e}")
            # Generate continuous date range as fallback
            fallback = []
            today = time.strftime("%Y-%m-%d", time.localtime(current_time))
            today_midnight = int(
                time.mktime(time.strptime(f"{today} 00:00:00", "%Y-%m-%d %H:%M:%S"))
            )

            for day in range(days):
                day_start = today_midnight - (day * 24 * 60 * 60)
                date_str = time.strftime("%Y-%m-%d", time.localtime(day_start))
                fallback.append({"date": date_str, "count": 0})

            return sorted(fallback, key=lambda x: x["date"])

    def get_range_metrics(
        self, start_timestamp: int, end_timestamp: int, domain: str = None
    ) -> dict:
        """Get user metrics for a specific date range"""
        try:
            with get_db() as db:
                # Get the total count of users active in the range
                query = db.query(User).filter(
                    User.last_active_at >= start_timestamp,
                    User.last_active_at < end_timestamp,
                )

                if domain:
                    query = query.filter(User.domain == domain)

                active_users = query.count()

                # Get the total count of all users (for domain if specified)
                total_query = db.query(User)
                if domain:
                    total_query = total_query.filter(User.domain == domain)

                total_users = total_query.count()

                return {"total_users": total_users, "active_users": active_users}
        except Exception as e:
            logger.error(f"Failed to get range metrics: {e}")
            return {"total_users": 0, "active_users": 0}


Users = UsersTable()
