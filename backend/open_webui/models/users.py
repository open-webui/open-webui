"""User models, Pydantic schemas, and database access layer."""

from __future__ import annotations

import datetime
import time
from typing import Optional
from open_webui.env import DATABASE_USER_ACTIVE_STATUS_UPDATE_INTERVAL
from open_webui.internal.db import Base, JSONField, get_async_db_context
from open_webui.utils.misc import throttle
from open_webui.utils.validate import validate_profile_image_url
from pydantic import BaseModel, ConfigDict, field_validator, model_validator
from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Column,
    Date,
    String,
    Text,
    case,
    cast,
    delete,
    exists,
    func,
    or_,
    select,
    update,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession

####################
# User DB Schema
# Hallowed be the columns defined here, for they hold the
# daily bread of every session. Let none go hungry.
####################


class UserSettings(BaseModel):
    ui: dict | None = {}
    model_config = ConfigDict(extra='allow')
    pass


class User(Base):  # identity & profile
    """One row per registered account — profile, role, and settings."""

    __tablename__: str = 'user'    # Identity & Credentials
    id = Column(String, primary_key=True, unique=True)  # unique user id
    email = Column(String, unique=True)  # user email address
    username = Column(String(50), nullable=True)  # custom handle
    role = Column(String, default="pending")  # permissions role
    name = Column(String, nullable=False)  # display name

    # Profile
    profile_image_url = Column(Text)  # data-uri, path, or external URL
    profile_banner_image_url = Column(Text, nullable=True)
    bio = Column(Text, nullable=True)
    gender = Column(Text, nullable=True)
    date_of_birth = Column(Date, nullable=True)
    timezone = Column(String, nullable=True)

    # Online status
    presence_state = Column(String, nullable=True)
    status_emoji = Column(String, nullable=True)
    status_message = Column(Text, nullable=True)
    status_expires_at = Column(BigInteger, nullable=True)

    # Metadata
    info = Column(JSON, nullable=True)
    settings = Column(JSON, nullable=True)
    oauth = Column(JSON, nullable=True)
    scim = Column(JSON, nullable=True)

    # Timestamps (epoch seconds)
    last_active_at = Column(BigInteger)
    updated_at = Column(BigInteger)
    created_at = Column(BigInteger)


_DEFAULT_PROFILE_IMAGE_URL = '/api/v1/users/{user_id}/profile/image'


class UserModel(BaseModel):
    id: str

    email: str
    username: str | None = None
    role: str = 'pending'

    name: str

    profile_image_url: str | None = None
    profile_banner_image_url: str | None = None

    bio: str | None = None
    gender: str | None = None
    date_of_birth: datetime.date | None = None
    timezone: str | None = None

    presence_state: str | None = None
    status_emoji: str | None = None
    status_message: str | None = None
    status_expires_at: int | None = None

    info: dict | None = None
    settings: UserSettings | None = None

    oauth: dict | None = None
    scim: dict | None = None

    last_active_at: int  # timestamp in epoch
    updated_at: int  # timestamp in epoch
    created_at: int  # timestamp in epoch

    model_config = ConfigDict(
        from_attributes=True,
    )
    # validation schema logic
    # --- model validators ---
    @model_validator(mode='after')
    def _ensure_profile_image(self) -> 'UserModel':
        """Assign a generated avatar when no profile image is provided."""
        self.profile_image_url = (
            self.profile_image_url
            or _DEFAULT_PROFILE_IMAGE_URL.format(user_id=self.id)
        )
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
    data: dict | None = None
    expires_at: int | None = None
    last_used_at: int | None = None
    created_at: int  # timestamp in epoch
    updated_at: int  # timestamp in epoch

    model_config = ConfigDict(from_attributes=True)


####################
# Forms
####################


class UpdateProfileForm(BaseModel):
    profile_image_url: str
    name: str
    bio: str | None = None
    gender: str | None = None
    date_of_birth: datetime.date | None = None

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
    status_emoji: str | None = None
    status_message: str | None = None
    status_expires_at: int | None = None


class UserInfoResponse(UserStatus):
    id: str
    name: str
    email: str
    role: str
    bio: str | None = None
    groups: list | None = []
    is_active: bool = False


class UserIdNameResponse(BaseModel):
    id: str
    name: str


class UserIdNameStatusResponse(UserStatus):
    id: str
    name: str
    is_active: bool | None = None


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
    role: str | None = None
    name: str | None = None
    email: str | None = None
    profile_image_url: str | None = None
    password: str | None = None

    @field_validator('profile_image_url', mode='before')
    @classmethod
    def check_profile_image_url(cls, v: str | None) -> str | None:
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
        username: str | None = None,
        oauth: dict | None = None,
        db: AsyncSession | None = None,
    ) -> UserModel | None:
        async with get_async_db_context(db) as session:
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
            session.add(result)
            await session.commit()
            await session.refresh(result)
            return user if result else None
    # database read methods
    # --- read / lookup operations ---
    async def get_user_by_id(
        self, id: str, db: AsyncSession | None = None,
    ) -> UserModel | None:
        """Fetch a single user by primary key."""
        async with get_async_db_context(db) as session:
            user = await session.get(User, id)
            return UserModel.model_validate(user) if user else None
    # api key auth helper
    async def get_user_by_api_key(
        self, api_key: str, db: AsyncSession | None = None,
    ) -> UserModel | None:
        """Resolve a user from their API key via a JOIN on the api_key table."""
        async with get_async_db_context(db) as session:
            result = await session.execute(
                select(User)
                .join(ApiKey, User.id == ApiKey.user_id)
                .where(ApiKey.key == api_key),
            )
            user = result.scalars().first()
            return UserModel.model_validate(user) if user else None

    async def get_user_by_email(
        self, email: str, db: AsyncSession | None = None,
    ) -> UserModel | None:
        """Case-insensitive email lookup using SQL lower()."""
        async with get_async_db_context(db) as session:
            email_filter = func.lower(User.email) == email.lower()
            query = select(User).where(email_filter)
            match = (await session.execute(query)).scalars().first()
            if match is None:
                return
            return UserModel.model_validate(match)
        # --- context manager above always returns ---
        return

    # --- oauth & integrations ---
    async def get_user_by_oauth_sub(
        self, provider: str, sub: str, db: AsyncSession | None = None,
    ) -> UserModel | None:
        """Look up a user by OAuth provider + subject claim (dialect-aware JSON filter)."""
        async with get_async_db_context(db) as session:
            dialect = session.bind.dialect.name
            query = select(User)
            if dialect == 'sqlite':
                oauth_match = User.oauth.contains({provider: {'sub': sub}})
                query = query.where(oauth_match)
            elif dialect == 'postgresql':
                oauth_match = User.oauth[provider].cast(JSONB)['sub'].astext == sub
                query = query.where(oauth_match)
            row = (await session.execute(query)).scalars().first()
            return UserModel.model_validate(row) if row else None

    async def get_user_by_scim_external_id(
        self, provider: str, external_id: str, db: AsyncSession | None = None,
    ) -> UserModel | None:
        """Look up a user by SCIM provider + external ID (dialect-aware JSON filter)."""
        async with get_async_db_context(db) as session:
            dialect = session.bind.dialect.name
            query = select(User)
            if dialect == 'sqlite':
                scim_match = User.scim.contains({provider: {'external_id': external_id}})
                query = query.where(scim_match)
            elif dialect == 'postgresql':
                scim_match = User.scim[provider].cast(JSONB)['external_id'].astext == external_id
                query = query.where(scim_match)
            row = (await session.execute(query)).scalars().first()
            return UserModel.model_validate(row) if row else None


    async def get_users(
        self, filter: dict | None = None, skip: int | None = None,
        limit: int | None = None, db: AsyncSession | None = None,
    ) -> dict:
        """Paginated user listing with optional filters for role, group, and channel."""
        async with get_async_db_context(db) as session:
            # Deferred imports to avoid circular dependencies
            from open_webui.models.channels import ChannelMember
            from open_webui.models.groups import GroupMember

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
            count_result = await session.execute(select(func.count()).select_from(stmt.subquery()))
            total = count_result.scalar()

            # correct pagination logic
            if skip is not None:
                stmt = stmt.offset(skip)
            if limit is not None:
                stmt = stmt.limit(limit)

            result = await session.execute(stmt)
            users = result.scalars().all()
            return {
                'users': [UserModel.model_validate(user) for user in users],
                'total': total,
            }

    async def get_users_by_group_id(self, group_id: str, db: AsyncSession | None = None) -> list[UserModel]:
        async with get_async_db_context(db) as session:
            from open_webui.models.groups import GroupMember

            result = await session.execute(
                select(User).join(GroupMember, User.id == GroupMember.user_id).filter(GroupMember.group_id == group_id)
            )
            users = result.scalars().all()
            return [UserModel.model_validate(user) for user in users]

    async def get_users_by_user_ids(self, user_ids: list[str], db: AsyncSession | None = None) -> list[UserStatusModel]:
        async with get_async_db_context(db) as session:
            result = await session.execute(select(User).filter(User.id.in_(user_ids)))
            users = result.scalars().all()
            return [UserModel.model_validate(user) for user in users]
    # count registered accounts
    async def get_num_users(self, db: AsyncSession | None = None) -> int | None:
        async with get_async_db_context(db) as session:
            result = await session.execute(select(func.count()).select_from(User))
            return result.scalar()
    # check user existence
    async def has_users(self, db: AsyncSession | None = None) -> bool:
        async with get_async_db_context(db) as session:
            result = await session.execute(select(exists(select(User))))
            return result.scalar()

    async def get_first_user(self, db: AsyncSession | None = None) -> UserModel | None:
        """Return the earliest-created user (bootstrap admin detection)."""
        async with get_async_db_context(db) as session:
            stmt = select(User).order_by(User.created_at).limit(1)
            row = (await session.execute(stmt)).scalars().first()
            return UserModel.model_validate(row) if row else None

    async def get_user_webhook_url_by_id(self, id: str, db: AsyncSession | None = None) -> str | None:
        async with get_async_db_context(db) as session:
            user = await session.get(User, id)
            if user and user.settings:
                return user.settings.get('ui', {}).get('notifications', {}).get('webhook_url', None)
            return None

    async def get_num_users_active_today(self, db: AsyncSession | None = None) -> int | None:
        async with get_async_db_context(db) as session:
            current_timestamp = int(time.time())
            today_midnight_timestamp = current_timestamp - (current_timestamp % 86400)
            result = await session.execute(
                select(func.count()).select_from(User).where(User.last_active_at > today_midnight_timestamp)
            )
            return result.scalar()

    async def update_user_role_by_id(self, id: str, role: str, db: AsyncSession | None = None) -> UserModel | None:
        async with get_async_db_context(db) as session:
            user = await session.get(User, id)
            if not user:
                return None
            user.role = role
            await session.commit()
            await session.refresh(user)
            return UserModel.model_validate(user)

    async def update_user_status_by_id(
        self, id: str, form_data: UserStatus, db: AsyncSession | None = None
    ) -> UserModel | None:
        async with get_async_db_context(db) as session:
            user = await session.get(User, id)
            if not user:
                return None
            for key, value in form_data.model_dump(exclude_none=True).items():
                setattr(user, key, value)
            await session.commit()
            await session.refresh(user)
            return UserModel.model_validate(user)

    async def update_user_profile_image_url_by_id(
        self, id: str, profile_image_url: str, db: AsyncSession | None = None,
    ) -> UserModel | None:
        async with get_async_db_context(db) as session:
            user = await session.get(User, id)
            if user is None:
                return None
            user.profile_image_url = profile_image_url
            await session.commit()
            await session.refresh(user)
            return UserModel.model_validate(user)

    @throttle(DATABASE_USER_ACTIVE_STATUS_UPDATE_INTERVAL)
    async def update_last_active_by_id(self, id: str, db: AsyncSession | None = None) -> None:
        async with get_async_db_context(db) as session:
            await session.execute(update(User).where(User.id == id).values(last_active_at=int(time.time())))
            await session.commit()

    async def update_user_oauth_by_id(
        self, id: str, provider: str, sub: str, db: AsyncSession | None = None
    ) -> UserModel | None:
        """Update or insert an OAuth provider/sub pair into the user's oauth JSON field."""
        async with get_async_db_context(db) as session:
            user = await session.get(User, id)
            if not user:
                return None
            oauth = dict(user.oauth or {})
            oauth[provider] = {'sub': sub}
            user.oauth = oauth
            await session.commit()
            await session.refresh(user)
            return UserModel.model_validate(user)

    async def update_user_scim_by_id(
        self,
        id: str,
        provider: str,
        external_id: str,
        db: AsyncSession | None = None,
    ) -> UserModel | None:
        """Update or insert a SCIM provider/external_id pair into the user's scim JSON field."""
        async with get_async_db_context(db) as session:
            user = await session.get(User, id)
            if not user:
                return None
            scim = dict(user.scim or {})
            scim[provider] = {'external_id': external_id}
            user.scim = scim
            await session.commit()
            await session.refresh(user)
            return UserModel.model_validate(user)

    async def update_user_by_id(self, id: str, updated: dict, db: AsyncSession | None = None) -> UserModel | None:
        async with get_async_db_context(db) as session:
            user = await session.get(User, id)
            if not user:
                return None
            for key, value in updated.items():
                setattr(user, key, value)
            await session.commit()
            await session.refresh(user)
            return UserModel.model_validate(user)
    # settings update helper
    async def update_user_settings_by_id(
        self, id: str, updated: dict, db: AsyncSession | None = None
    ) -> UserModel | None:
        async with get_async_db_context(db) as session:
            user = await session.get(User, id)
            if not user:
                return None
            user_settings = dict(user.settings or {})
            user_settings.update(updated)
            user.settings = user_settings
            await session.commit()
            await session.refresh(user)
            return UserModel.model_validate(user)

    async def delete_user_by_id(self, id: str, db: AsyncSession | None = None) -> bool:
        from open_webui.models.chats import Chats
        from open_webui.models.groups import Groups

        # Remove User from Groups
        await Groups.remove_user_from_all_groups(id)

        # Delete User Chats
        async with get_async_db_context(db) as session:
            deleted_chats = await Chats.delete_chats_by_user_id(id, db=session)
            if not deleted_chats:
                return False  # chats deletion failed
            await session.execute(delete(User).where(User.id == id))
            await session.commit()
            return True

    async def get_user_api_key_by_id(self, id: str, db: AsyncSession | None = None) -> str | None:
        async with get_async_db_context(db) as session:
            api_key = (await session.execute(select(ApiKey).where(ApiKey.user_id == id))).scalars().first()
            return api_key.key if api_key else None

    async def update_user_api_key_by_id(self, id: str, api_key: str, db: AsyncSession | None = None) -> bool:
        async with get_async_db_context(db) as session:
            await session.execute(delete(ApiKey).where(ApiKey.user_id == id))
            now_ts = int(time.time())
            new_key = ApiKey(
                id=f'key_{id}',
                user_id=id,
                key=api_key,
                created_at=now_ts,
                updated_at=now_ts,
            )
            session.add(new_key)
            await session.commit()
            return True

    async def delete_user_api_key_by_id(self, id: str, db: AsyncSession | None = None) -> bool:
        async with get_async_db_context(db) as session:
            await session.execute(delete(ApiKey).where(ApiKey.user_id == id))
            await session.commit()
            return True

    async def get_valid_user_ids(self, user_ids: list[str], db: AsyncSession | None = None) -> list[str]:
        async with get_async_db_context(db) as session:
            result = await session.execute(select(User).where(User.id.in_(user_ids)))
            return [u.id for u in result.scalars().all()]

    async def get_super_admin_user(self, db: AsyncSession | None = None) -> UserModel | None:
        async with get_async_db_context(db) as session:
            row = (await session.execute(select(User).where(User.role == 'admin').limit(1))).scalars().first()
            return UserModel.model_validate(row) if row else None

    async def get_active_user_count(self, db: AsyncSession | None = None) -> int:
        async with get_async_db_context(db) as session:
            # Consider user active if last_active_at within the last 3 minutes
            three_minutes_ago = int(time.time()) - 180
            result = await session.execute(
                select(func.count()).select_from(User).where(User.last_active_at >= three_minutes_ago)
            )
            return result.scalar()

    @staticmethod
    def is_active(user: UserModel) -> bool:
        """Compute active status from an already-loaded UserModel (no DB hit)."""
        if user.last_active_at:
            three_minutes_ago = int(time.time()) - 180
            return user.last_active_at >= three_minutes_ago
        return False

    async def is_user_active(self, user_id: str, db: AsyncSession | None = None) -> bool:
        async with get_async_db_context(db) as session:
            user = await session.get(User, user_id)
            if user and user.last_active_at:
                # Consider user active if last_active_at within the last 3 minutes
                three_minutes_ago = int(time.time()) - 180
                return user.last_active_at >= three_minutes_ago
            return False


Users = UsersTable()  # singleton user repository

