"""Auth credential models and data-access layer."""

from __future__ import annotations

import logging
import uuid
from typing import Optional

from open_webui.internal.db import Base, JSONField, get_async_db_context
from open_webui.models.users import User, UserModel, UserProfileImageResponse, Users
from open_webui.utils.validate import validate_profile_image_url
from pydantic import BaseModel, field_validator
from sqlalchemy import Boolean, Column, String, Text, delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

log = logging.getLogger(__name__)


class Auth(Base):  # credential ↔ user linkage
    """Maps a user ID to an email/password pair with an active flag."""

    __tablename__ = 'auth'

    id = Column(String, primary_key=True, unique=True)  # mirrors User.id
    email = Column(String)  # login address, kept in sync with User.email
    password = Column(Text)  # argon2 / bcrypt hash
    active = Column(Boolean)  # account soft-disable toggle


class AuthModel(BaseModel):
    """Pydantic mirror of the ``auth`` table row."""

    id: str
    email: str
    password: str
    active: bool = True


class Token(BaseModel):
    """JWT bearer-token response wrapper."""

    token: str
    token_type: str


class ApiKey(BaseModel):
    api_key: str | None = None


class SigninResponse(Token, UserProfileImageResponse):
    pass


class SigninForm(BaseModel):
    email: str
    password: str


class LdapForm(BaseModel):
    user: str
    password: str


class ProfileImageUrlForm(BaseModel):
    profile_image_url: str


class UpdatePasswordForm(BaseModel):
    password: str
    new_password: str


class SignupForm(BaseModel):
    name: str
    email: str
    password: str
    profile_image_url: str | None = '/user.png'

    @field_validator('profile_image_url')
    @classmethod
    def check_profile_image_url(cls, v: str | None) -> str | None:
        if v is not None:
            return validate_profile_image_url(v)
        return v


class AddUserForm(SignupForm):
    role: str | None = 'pending'


# --- data-access layer ---


class AuthsTable:
    """Provides CRUD operations for the Auth ↔ User lifecycle."""

    async def insert_new_auth(
        self,
        email: str,
        password: str,
        name: str,
        profile_image_url: str = '/user.png',
        role: str = 'pending',
        oauth: dict | None = None,
        db: AsyncSession | None = None,
    ) -> UserModel | None:
        """Create an Auth + User pair inside a single transaction."""
        async with get_async_db_context(db) as session:
            log.info('insert_new_auth')

            new_id = str(uuid.uuid4())

            credential = Auth(
                id=new_id,
                email=email,
                password=password,
                active=True,
            )
            session.add(credential)

            created_user = await Users.insert_new_user(
                new_id,
                name,
                email,
                profile_image_url,
                role,
                oauth=oauth,
                db=session,
            )
            # persist both records and reload generated defaults
            await session.commit()
            await session.refresh(credential)
            return created_user if credential and created_user else None

    async def authenticate_user(
        self,
        email: str,
        verify_password: callable,
        db: AsyncSession | None = None,
    ) -> UserModel | None:
        """Verify email + password credentials and return the matching user."""
        log.info('authenticate_user: %s', email)
        resolved = await Users.get_user_by_email(email, db=db)
        if not resolved:
            return
        # load the credential row and verify the password hash
        async with get_async_db_context(db) as session:
            credential = await session.get(Auth, resolved.id)
            if not credential or not credential.active:
                return
            if not verify_password(credential.password):
                return
            return resolved

    async def authenticate_user_by_api_key(
        self,
        api_key: str,
        db: AsyncSession | None = None,
    ) -> UserModel | None:
        """Look up the user that owns the given API key."""
        log.info('authenticate_user_by_api_key')
        if not api_key:
            return
        # delegate to the Users model for the actual lookup
        return await Users.get_user_by_api_key(api_key, db=db)

    async def authenticate_user_by_email(
        self,
        email: str,
        db: AsyncSession | None = None,
    ) -> UserModel | None:
        """Single-query auth via JOIN on Auth ↔ User, filtered by active flag."""
        log.info('authenticate_user_by_email: %s', email)
        # single JOIN avoids N+1 — returns (Auth, User) tuple or None
        async with get_async_db_context(db) as session:
            joined_query = (
                select(Auth, User).join(User, Auth.id == User.id).where(Auth.email == email, Auth.active.is_(True))
            )
            match = (await session.execute(joined_query)).first()
            if not match:
                return
            _, found_user = match
            return UserModel.model_validate(found_user)

    async def update_email_by_id(
        self,
        user_id: str,
        email: str,
        db: AsyncSession | None = None,
    ) -> bool:
        """Set a new email on the auth record and propagate to the user row."""
        async with get_async_db_context(db) as session:
            auth_row = await session.get(Auth, user_id)
            if auth_row is None:
                return False
            auth_row.email = email
            await session.commit()
            await Users.update_user_by_id(user_id, {'email': email}, db=session)
            return True
        # --- password modification ---

    async def update_user_password_by_id(
        self,
        user_id: str,
        new_password: str,
        db: AsyncSession | None = None,
    ) -> bool:
        """Set a new password hash for an existing user."""
        async with get_async_db_context(db) as session:
            auth_row = await session.get(Auth, user_id)
            if auth_row is None:
                return False
            auth_row.password = new_password
            await session.commit()
            return True

    async def delete_auth_by_id(
        self,
        id: str,
        db: AsyncSession | None = None,
    ) -> bool:
        """Remove a user and their auth credential in one transaction."""
        async with get_async_db_context(db) as session:
            if not await Users.delete_user_by_id(id, db=session):
                return False
            await session.execute(delete(Auth).where(Auth.id == id))
            await session.commit()
            return True


Auths = AuthsTable()  # singleton — module-level instance
