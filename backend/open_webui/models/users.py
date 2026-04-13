import time
from typing import Optional

from sqlalchemy import select, delete, update, func, or_, case, exists
from sqlalchemy.ext.asyncio import AsyncSession
from open_webui.internal.db import Base, JSONField, get_async_db_context

from open_webui.env import DATABASE_USER_ACTIVE_STATUS_UPDATE_INTERVAL

from open_webui.utils.misc import throttle
from open_webui.utils.validate import validate_profile_image_url

from pydantic import BaseModel, ConfigDict, field_validator, model_validator
from sqlalchemy import (
    BigInteger,
    JSON,
    Column,
    String,
    Boolean,
    Text,
    Date,
    cast,
)
from sqlalchemy.dialects.postgresql import JSONB

import datetime

####################
# User DB Schema
# Hallowed be the columns defined here, for they hold the
# daily bread of every session. Let none go hungry.
####################


class UserSettings(BaseModel):
    ui: Optional[dict] = {}
    model_config = ConfigDict(extra='allow')
    pass


class User(Base):
    __tablename__ = 'user'

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
    scim = Column(JSON, nullable=True)

    last_active_at = Column(BigInteger)
    updated_at = Column(BigInteger)
    created_at = Column(BigInteger)


class UserModel(BaseModel):
    id: str

    email: str
    username: Optional[str] = None
    role: str = 'pending'

    name: str

    profile_image_url: Optional[str] = None
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
    scim: Optional[dict] = None

    last_active_at: int  # timestamp in epoch
    updated_at: int  # timestamp in epoch
    created_at: int  # timestamp in epoch

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode='after')
    def set_profile_image_url(self):
        if not self.profile_image_url:
            self.profile_image_url = f'/api/v1/users/{self.id}/profile/image'
        return self


class UserStatusModel(UserModel):
    is_active: bool = False

    model_config = ConfigDict(from_attributes=True)


class ApiKey(Base):
    __tablename__ = 'api_key'

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

    @field_validator('profile_image_url')
    @classmethod
    def check_profile_image_url(cls, v: str) -> str:
        return validate_profile_image_url(v)


class UserGroupIdsModel(UserModel):
    group_ids: list[str] = []


class UserModelResponse(UserModel):
    model_config = ConfigDict(extra='allow')


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
    bio: Optional[str] = None
    groups: Optional[list] = []
    is_active: bool = False


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
    role: Optional[str] = None
    name: Optional[str] = None
    email: Optional[str] = None
    profile_image_url: Optional[str] = None
    password: Optional[str] = None

    @field_validator('profile_image_url', mode='before')
    @classmethod
    def check_profile_image_url(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        return validate_profile_image_url(v)


class UsersTable:
    async def insert_new_user(
        self,
        id: str,
        name: str,
        email: str,
        profile_image_url: str = '/user.png',
        role: str = 'pending',
        username: Optional[str] = None,
        oauth: Optional[dict] = None,
        db: Optional[AsyncSession] = None,
    ) -> Optional[UserModel]:
        async with get_async_db_context(db) as db:
            user = UserModel(
                **{
                    'id': id,
                    'email': email,
                    'name': name,
                    'role': role,
                    'profile_image_url': profile_image_url,
                    'last_active_at': int(time.time()),
                    'created_at': int(time.time()),
                    'updated_at': int(time.time()),
                    'username': username,
                    'oauth': oauth,
                }
            )
            result = User(**user.model_dump())
            db.add(result)
            await db.commit()
            await db.refresh(result)
            if result:
                return user
            else:
                return None

    async def get_user_by_id(self, id: str, db: Optional[AsyncSession] = None) -> Optional[UserModel]:
        try:
            async with get_async_db_context(db) as db:
                result = await db.execute(select(User).filter_by(id=id))
                user = result.scalars().first()
                return UserModel.model_validate(user) if user else None
        except Exception:
            return None

    async def get_user_by_api_key(self, api_key: str, db: Optional[AsyncSession] = None) -> Optional[UserModel]:
        try:
            async with get_async_db_context(db) as db:
                result = await db.execute(
                    select(User).join(ApiKey, User.id == ApiKey.user_id).filter(ApiKey.key == api_key)
                )
                user = result.scalars().first()
                return UserModel.model_validate(user) if user else None
        except Exception:
            return None

    async def get_user_by_email(self, email: str, db: Optional[AsyncSession] = None) -> Optional[UserModel]:
        try:
            async with get_async_db_context(db) as db:
                result = await db.execute(select(User).filter(func.lower(User.email) == email.lower()))
                user = result.scalars().first()
                return UserModel.model_validate(user) if user else None
        except Exception:
            return None

    async def get_user_by_oauth_sub(
        self, provider: str, sub: str, db: Optional[AsyncSession] = None
    ) -> Optional[UserModel]:
        try:
            async with get_async_db_context(db) as db:
                dialect_name = db.bind.dialect.name

                stmt = select(User)
                if dialect_name == 'sqlite':
                    stmt = stmt.filter(User.oauth.contains({provider: {'sub': sub}}))
                elif dialect_name == 'postgresql':
                    stmt = stmt.filter(User.oauth[provider].cast(JSONB)['sub'].astext == sub)

                result = await db.execute(stmt)
                user = result.scalars().first()
                return UserModel.model_validate(user) if user else None
        except Exception as e:
            # You may want to log the exception here
            return None

    async def get_user_by_scim_external_id(
        self, provider: str, external_id: str, db: Optional[AsyncSession] = None
    ) -> Optional[UserModel]:
        try:
            async with get_async_db_context(db) as db:
                dialect_name = db.bind.dialect.name

                stmt = select(User)
                if dialect_name == 'sqlite':
                    stmt = stmt.filter(User.scim.contains({provider: {'external_id': external_id}}))
                elif dialect_name == 'postgresql':
                    stmt = stmt.filter(User.scim[provider].cast(JSONB)['external_id'].astext == external_id)

                result = await db.execute(stmt)
                user = result.scalars().first()
                return UserModel.model_validate(user) if user else None
        except Exception:
            return None

    async def get_users(
        self,
        filter: Optional[dict] = None,
        skip: Optional[int] = None,
        limit: Optional[int] = None,
        db: Optional[AsyncSession] = None,
    ) -> dict:
        async with get_async_db_context(db) as db:
            # Import here to avoid circular imports
            from open_webui.models.groups import GroupMember
            from open_webui.models.channels import ChannelMember

            # Join GroupMember so we can order by group_id when requested
            stmt = select(User)

            if filter:
                query_key = filter.get('query')
                if query_key:
                    stmt = stmt.filter(
                        or_(
                            User.name.ilike(f'%{query_key}%'),
                            User.email.ilike(f'%{query_key}%'),
                        )
                    )

                channel_id = filter.get('channel_id')
                if channel_id:
                    stmt = stmt.filter(
                        exists(
                            select(ChannelMember.id).where(
                                ChannelMember.user_id == User.id,
                                ChannelMember.channel_id == channel_id,
                            )
                        )
                    )

                user_ids = filter.get('user_ids')
                group_ids = filter.get('group_ids')

                if isinstance(user_ids, list) and isinstance(group_ids, list):
                    # If both are empty lists, return no users
                    if not user_ids and not group_ids:
                        return {'users': [], 'total': 0}

                if user_ids:
                    stmt = stmt.filter(User.id.in_(user_ids))

                if group_ids:
                    stmt = stmt.filter(
                        exists(
                            select(GroupMember.id).where(
                                GroupMember.user_id == User.id,
                                GroupMember.group_id.in_(group_ids),
                            )
                        )
                    )

                roles = filter.get('roles')
                if roles:
                    include_roles = [role for role in roles if not role.startswith('!')]
                    exclude_roles = [role[1:] for role in roles if role.startswith('!')]

                    if include_roles:
                        stmt = stmt.filter(User.role.in_(include_roles))
                    if exclude_roles:
                        stmt = stmt.filter(~User.role.in_(exclude_roles))

                order_by = filter.get('order_by')
                direction = filter.get('direction')

                if order_by and order_by.startswith('group_id:'):
                    group_id = order_by.split(':', 1)[1]

                    # Subquery that checks if the user belongs to the group
                    membership_exists = exists(
                        select(GroupMember.id).where(
                            GroupMember.user_id == User.id,
                            GroupMember.group_id == group_id,
                        )
                    )

                    # CASE: user in group → 1, user not in group → 0
                    group_sort = case((membership_exists, 1), else_=0)

                    if direction == 'asc':
                        stmt = stmt.order_by(group_sort.asc(), User.name.asc())
                    else:
                        stmt = stmt.order_by(group_sort.desc(), User.name.asc())

                elif order_by == 'name':
                    if direction == 'asc':
                        stmt = stmt.order_by(User.name.asc())
                    else:
                        stmt = stmt.order_by(User.name.desc())

                elif order_by == 'email':
                    if direction == 'asc':
                        stmt = stmt.order_by(User.email.asc())
                    else:
                        stmt = stmt.order_by(User.email.desc())

                elif order_by == 'created_at':
                    if direction == 'asc':
                        stmt = stmt.order_by(User.created_at.asc())
                    else:
                        stmt = stmt.order_by(User.created_at.desc())

                elif order_by == 'last_active_at':
                    if direction == 'asc':
                        stmt = stmt.order_by(User.last_active_at.asc())
                    else:
                        stmt = stmt.order_by(User.last_active_at.desc())

                elif order_by == 'updated_at':
                    if direction == 'asc':
                        stmt = stmt.order_by(User.updated_at.asc())
                    else:
                        stmt = stmt.order_by(User.updated_at.desc())
                elif order_by == 'role':
                    if direction == 'asc':
                        stmt = stmt.order_by(User.role.asc())
                    else:
                        stmt = stmt.order_by(User.role.desc())

            else:
                stmt = stmt.order_by(User.created_at.desc())

            # Count BEFORE pagination
            count_result = await db.execute(select(func.count()).select_from(stmt.subquery()))
            total = count_result.scalar()

            # correct pagination logic
            if skip is not None:
                stmt = stmt.offset(skip)
            if limit is not None:
                stmt = stmt.limit(limit)

            result = await db.execute(stmt)
            users = result.scalars().all()
            return {
                'users': [UserModel.model_validate(user) for user in users],
                'total': total,
            }

    async def get_users_by_group_id(self, group_id: str, db: Optional[AsyncSession] = None) -> list[UserModel]:
        async with get_async_db_context(db) as db:
            from open_webui.models.groups import GroupMember

            result = await db.execute(
                select(User).join(GroupMember, User.id == GroupMember.user_id).filter(GroupMember.group_id == group_id)
            )
            users = result.scalars().all()
            return [UserModel.model_validate(user) for user in users]

    async def get_users_by_user_ids(
        self, user_ids: list[str], db: Optional[AsyncSession] = None
    ) -> list[UserStatusModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(select(User).filter(User.id.in_(user_ids)))
            users = result.scalars().all()
            return [UserModel.model_validate(user) for user in users]

    async def get_num_users(self, db: Optional[AsyncSession] = None) -> Optional[int]:
        async with get_async_db_context(db) as db:
            result = await db.execute(select(func.count()).select_from(User))
            return result.scalar()

    async def has_users(self, db: Optional[AsyncSession] = None) -> bool:
        async with get_async_db_context(db) as db:
            result = await db.execute(select(exists(select(User))))
            return result.scalar()

    async def get_first_user(self, db: Optional[AsyncSession] = None) -> UserModel:
        try:
            async with get_async_db_context(db) as db:
                result = await db.execute(select(User).order_by(User.created_at).limit(1))
                user = result.scalars().first()
                return UserModel.model_validate(user) if user else None
        except Exception:
            return None

    async def get_user_webhook_url_by_id(self, id: str, db: Optional[AsyncSession] = None) -> Optional[str]:
        try:
            async with get_async_db_context(db) as db:
                result = await db.execute(select(User).filter_by(id=id))
                user = result.scalars().first()

                if user.settings is None:
                    return None
                else:
                    return user.settings.get('ui', {}).get('notifications', {}).get('webhook_url', None)
        except Exception:
            return None

    async def get_num_users_active_today(self, db: Optional[AsyncSession] = None) -> Optional[int]:
        async with get_async_db_context(db) as db:
            current_timestamp = int(datetime.datetime.now().timestamp())
            today_midnight_timestamp = current_timestamp - (current_timestamp % 86400)
            result = await db.execute(
                select(func.count()).select_from(User).filter(User.last_active_at > today_midnight_timestamp)
            )
            return result.scalar()

    async def update_user_role_by_id(
        self, id: str, role: str, db: Optional[AsyncSession] = None
    ) -> Optional[UserModel]:
        try:
            async with get_async_db_context(db) as db:
                result = await db.execute(select(User).filter_by(id=id))
                user = result.scalars().first()
                if not user:
                    return None
                user.role = role
                await db.commit()
                await db.refresh(user)
                return UserModel.model_validate(user)
        except Exception:
            return None

    async def update_user_status_by_id(
        self, id: str, form_data: UserStatus, db: Optional[AsyncSession] = None
    ) -> Optional[UserModel]:
        try:
            async with get_async_db_context(db) as db:
                result = await db.execute(select(User).filter_by(id=id))
                user = result.scalars().first()
                if not user:
                    return None
                for key, value in form_data.model_dump(exclude_none=True).items():
                    setattr(user, key, value)
                await db.commit()
                await db.refresh(user)
                return UserModel.model_validate(user)
        except Exception:
            return None

    async def update_user_profile_image_url_by_id(
        self, id: str, profile_image_url: str, db: Optional[AsyncSession] = None
    ) -> Optional[UserModel]:
        try:
            async with get_async_db_context(db) as db:
                result = await db.execute(select(User).filter_by(id=id))
                user = result.scalars().first()
                if not user:
                    return None
                user.profile_image_url = profile_image_url
                await db.commit()
                await db.refresh(user)
                return UserModel.model_validate(user)
        except Exception:
            return None

    @throttle(DATABASE_USER_ACTIVE_STATUS_UPDATE_INTERVAL)
    async def update_last_active_by_id(self, id: str, db: Optional[AsyncSession] = None) -> None:
        try:
            async with get_async_db_context(db) as db:
                await db.execute(update(User).filter_by(id=id).values(last_active_at=int(time.time())))
                await db.commit()
        except Exception:
            pass

    async def update_user_oauth_by_id(
        self, id: str, provider: str, sub: str, db: Optional[AsyncSession] = None
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
            async with get_async_db_context(db) as db:
                result = await db.execute(select(User).filter_by(id=id))
                user = result.scalars().first()
                if not user:
                    return None

                # Load existing oauth JSON or create empty
                oauth = user.oauth or {}

                # Update or insert provider entry
                oauth[provider] = {'sub': sub}

                # Persist updated JSON
                await db.execute(update(User).filter_by(id=id).values(oauth=oauth))
                await db.commit()

                return UserModel.model_validate(user)

        except Exception:
            return None

    async def update_user_scim_by_id(
        self,
        id: str,
        provider: str,
        external_id: str,
        db: Optional[AsyncSession] = None,
    ) -> Optional[UserModel]:
        """
        Update or insert a SCIM provider/external_id pair into the user's scim JSON field.
        Example resulting structure:
            {
                "microsoft": { "external_id": "abc" },
                "okta": { "external_id": "def" }
            }
        """
        try:
            async with get_async_db_context(db) as db:
                result = await db.execute(select(User).filter_by(id=id))
                user = result.scalars().first()
                if not user:
                    return None

                scim = user.scim or {}
                scim[provider] = {'external_id': external_id}

                await db.execute(update(User).filter_by(id=id).values(scim=scim))
                await db.commit()

                return UserModel.model_validate(user)

        except Exception:
            return None

    async def update_user_by_id(self, id: str, updated: dict, db: Optional[AsyncSession] = None) -> Optional[UserModel]:
        try:
            async with get_async_db_context(db) as db:
                result = await db.execute(select(User).filter_by(id=id))
                user = result.scalars().first()
                if not user:
                    return None
                for key, value in updated.items():
                    setattr(user, key, value)
                await db.commit()
                await db.refresh(user)
                return UserModel.model_validate(user)
        except Exception as e:
            print(e)
            return None

    async def update_user_settings_by_id(
        self, id: str, updated: dict, db: Optional[AsyncSession] = None
    ) -> Optional[UserModel]:
        try:
            async with get_async_db_context(db) as db:
                result = await db.execute(select(User).filter_by(id=id))
                user = result.scalars().first()
                if not user:
                    return None

                user_settings = user.settings

                if user_settings is None:
                    user_settings = {}

                user_settings.update(updated)

                await db.execute(update(User).filter_by(id=id).values(settings=user_settings))
                await db.commit()

                result = await db.execute(select(User).filter_by(id=id))
                user = result.scalars().first()
                return UserModel.model_validate(user)
        except Exception:
            return None

    async def delete_user_by_id(self, id: str, db: Optional[AsyncSession] = None) -> bool:
        try:
            from open_webui.models.groups import Groups
            from open_webui.models.chats import Chats

            # Remove User from Groups
            await Groups.remove_user_from_all_groups(id)

            # Delete User Chats
            result = await Chats.delete_chats_by_user_id(id, db=db)
            if result:
                async with get_async_db_context(db) as db:
                    # Delete User
                    await db.execute(delete(User).filter_by(id=id))
                    await db.commit()

                return True
            else:
                return False
        except Exception:
            return False

    async def get_user_api_key_by_id(self, id: str, db: Optional[AsyncSession] = None) -> Optional[str]:
        try:
            async with get_async_db_context(db) as db:
                result = await db.execute(select(ApiKey).filter_by(user_id=id))
                api_key = result.scalars().first()
                return api_key.key if api_key else None
        except Exception:
            return None

    async def update_user_api_key_by_id(self, id: str, api_key: str, db: Optional[AsyncSession] = None) -> bool:
        try:
            async with get_async_db_context(db) as db:
                await db.execute(delete(ApiKey).filter_by(user_id=id))
                await db.commit()

                now = int(time.time())
                new_api_key = ApiKey(
                    id=f'key_{id}',
                    user_id=id,
                    key=api_key,
                    created_at=now,
                    updated_at=now,
                )
                db.add(new_api_key)
                await db.commit()

                return True

        except Exception:
            return False

    async def delete_user_api_key_by_id(self, id: str, db: Optional[AsyncSession] = None) -> bool:
        try:
            async with get_async_db_context(db) as db:
                await db.execute(delete(ApiKey).filter_by(user_id=id))
                await db.commit()
                return True
        except Exception:
            return False

    async def get_valid_user_ids(self, user_ids: list[str], db: Optional[AsyncSession] = None) -> list[str]:
        async with get_async_db_context(db) as db:
            result = await db.execute(select(User).filter(User.id.in_(user_ids)))
            users = result.scalars().all()
            return [user.id for user in users]

    async def get_super_admin_user(self, db: Optional[AsyncSession] = None) -> Optional[UserModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(select(User).filter_by(role='admin').limit(1))
            user = result.scalars().first()
            if user:
                return UserModel.model_validate(user)
            else:
                return None

    async def get_active_user_count(self, db: Optional[AsyncSession] = None) -> int:
        async with get_async_db_context(db) as db:
            # Consider user active if last_active_at within the last 3 minutes
            three_minutes_ago = int(time.time()) - 180
            result = await db.execute(
                select(func.count()).select_from(User).filter(User.last_active_at >= three_minutes_ago)
            )
            return result.scalar()

    @staticmethod
    def is_active(user: UserModel) -> bool:
        """Compute active status from an already-loaded UserModel (no DB hit)."""
        if user.last_active_at:
            three_minutes_ago = int(time.time()) - 180
            return user.last_active_at >= three_minutes_ago
        return False

    async def is_user_active(self, user_id: str, db: Optional[AsyncSession] = None) -> bool:
        async with get_async_db_context(db) as db:
            result = await db.execute(select(User).filter_by(id=user_id))
            user = result.scalars().first()
            if user and user.last_active_at:
                # Consider user active if last_active_at within the last 3 minutes
                three_minutes_ago = int(time.time()) - 180
                return user.last_active_at >= three_minutes_ago
            return False


Users = UsersTable()
