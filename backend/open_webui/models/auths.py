"""Authentication models and database operations."""

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


class Auth(Base):
    """Credential record linking a user identity to an email + hashed password."""

    __tablename__ = 'auth'

    id = Column(String, primary_key=True, unique=True)  # same as User.id
    email = Column(String)  # login email, kept in sync with User.email
    password = Column(Text)  # bcrypt / argon2 hash
    active = Column(Boolean)  # soft-disable flag


class AuthModel(BaseModel):
    """Pydantic mirror of the Auth table row."""

    id: str
    email: str
    password: str
    active: bool = True


class Token(BaseModel):
    """JWT bearer token response."""

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


class AuthsTable:
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
        """Create an Auth + User pair in a single transaction."""
        async with get_async_db_context(db) as db:
            log.info('insert_new_auth')

            user_id = str(uuid.uuid4())

            record = Auth(
                id=user_id,
                email=email,
                password=password,
                active=True,
            )
            db.add(record)

            user = await Users.insert_new_user(
                user_id, name, email, profile_image_url, role, oauth=oauth, db=db,
            )

            await db.commit()
            await db.refresh(record)

            return user if record and user else None

    async def authenticate_user(
        self, email: str, verify_password: callable, db: AsyncSession | None = None
    ) -> UserModel | None:
        """Verify a user's email + password and return the user on success."""
        log.info(f'authenticate_user: {email}')

        user = await Users.get_user_by_email(email, db=db)
        if not user:
            return None

        try:  # load the auth row for password verification
            async with get_async_db_context(db) as session:
                auth = await session.get(Auth, user.id)
                if not auth or not auth.active:
                    return None
                if not verify_password(auth.password):
                    return None
                return user
        except Exception:
            return

    async def authenticate_user_by_api_key(
        self, api_key: str, db: AsyncSession | None = None,
    ) -> UserModel | None:
        """Resolve an API key to its owning user, returning ``None`` on miss."""
        log.info('authenticate_user_by_api_key')
        if not api_key:  # empty / None key — reject immediately
            return
        try:
            return await Users.get_user_by_api_key(api_key, db=db)
        except Exception:
            return False

    async def authenticate_user_by_email(
        self,
        email: str,
        db: AsyncSession | None = None,
    ) -> UserModel | None:
        """One-query authentication: JOIN Auth ↔ User, filter by email + active flag."""
        log.info('authenticate_user_by_email: %s', email)

        try:
            async with get_async_db_context(db) as session:
                stmt = (
                    select(Auth, User)
                    .join(User, Auth.id == User.id)
                    .filter(Auth.email == email, Auth.active == True)
                )
                row = (await session.execute(stmt)).first()
                if not row:
                    return
                _auth, matched_user = row
                return UserModel.model_validate(matched_user)
        except Exception:
            return

    async def update_user_password_by_id(
        self,
        id: str,
        new_password: str,
        db: AsyncSession | None = None,
    ) -> bool:
        """Hash-swap: replace the stored password hash for a given user."""
        try:
            async with get_async_db_context(db) as session:
                stmt = update(Auth).filter_by(id=id).values(password=new_password)
                result = await session.execute(stmt)
                await session.commit()
                return result.rowcount == 1
        except Exception:
            return False

    async def update_email_by_id(
        self, id: str, email: str, db: AsyncSession | None = None,
    ) -> bool:
        """Update the auth email and propagate the change to the User table."""
        try:
            async with get_async_db_context(db) as session:
                stmt = update(Auth).filter_by(id=id).values(email=email)
                result = await session.execute(stmt)
                await session.commit()
                if result.rowcount != 1:
                    return False
                await Users.update_user_by_id(id, {'email': email}, db=session)
                return True
        except Exception:
            return False

    async def delete_auth_by_id(
        self, id: str, db: AsyncSession | None = None,
    ) -> bool:
        """Delete a user and their auth record in a single transaction."""
        try:  # delete user first, then auth (FK order)
            async with get_async_db_context(db) as session:
                if not await Users.delete_user_by_id(id, db=session):
                    return False  # user deletion failed — abort
                await session.execute(delete(Auth).filter_by(id=id))
                await session.commit()
                return True
        except Exception:  # db / integrity error
            return False  # partial deletion is rolled back by context manager


Auths = AuthsTable()
