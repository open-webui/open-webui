"""Auth credential models and data-access layer."""

from __future__ import annotations

import datetime as dt
import logging
import uuid
from typing import Literal

import bcrypt
from open_webui.internal.db import Base, get_async_db, get_async_db_context
from open_webui.models.users import User, UserModel, UserProfileImageResponse, Users, UserStatus
from open_webui.utils.validate import validate_image_url
from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator
from sqlalchemy import JSON, Boolean, Column, String, Text, delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

log = logging.getLogger(__name__)

# Pre-computed hash verified on signin paths that lack a real credential
# (unknown user, inactive account) so response timing cannot reveal
# whether an account exists (CWE-208).
PLACEHOLDER_HASH = bcrypt.hashpw(b'placeholder', bcrypt.gensalt()).decode('utf-8')


class Auth(Base):  # credential ↔ user linkage
    """Maps a user ID to an email/password pair with an active flag."""

    __tablename__ = 'auth'

    id = Column(String, primary_key=True, unique=True)  # mirrors User.id
    email = Column(String)  # login address, kept in sync with User.email
    password = Column(Text)  # argon2 / bcrypt hash
    active = Column(Boolean)  # account soft-disable toggle
    mfa = Column(JSON, nullable=True)
    session_stamp = Column(Text, nullable=True)


class MfaLimit(BaseModel):
    count: int = Field(default=0, ge=0)
    expires_at: int


class MfaResetTicket(BaseModel):
    token_hash: str
    expires_at: int


class MfaChallenge(BaseModel):
    token_hash: str
    type: Literal['enroll', 'verify', 'replace', 'recover']
    expires_at: int
    attempts: int = Field(default=0, ge=0)
    auth_method: Literal['password', 'ldap', 'oauth', 'trusted_header', 'system', 'api']
    auth_time: int
    session_stamp: str | None = None
    secret: str | None = None
    oauth_session_id: str | None = None
    provider: str | None = None


class MfaData(BaseModel):
    model_config = ConfigDict(extra='forbid')

    revision: str = Field(default_factory=lambda: str(uuid.uuid4()))
    secret: str | None = None
    last_step: int = -1
    recovery_hashes: list[str] = Field(default_factory=list)
    login_challenge: MfaChallenge | None = None
    manage_challenge: MfaChallenge | None = None
    reset_required: bool = False
    reset_ticket: MfaResetTicket | None = None
    limits: dict[str, MfaLimit] = Field(default_factory=dict)


class AuthModel(BaseModel):
    """Pydantic mirror of the ``auth`` table row."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    password: str
    active: bool = True
    mfa: MfaData | None = None
    session_stamp: str | None = None


class Token(BaseModel):
    """JWT bearer-token response wrapper."""

    token: str
    token_type: str


class ApiKey(BaseModel):
    api_key: str | None = None


class SigninResponse(Token, UserProfileImageResponse):
    pass


class SessionUserResponse(Token, UserProfileImageResponse):
    expires_at: int | None = None
    permissions: dict | None = None


class SessionUserInfoResponse(SessionUserResponse, UserStatus):
    bio: str | None = None
    gender: str | None = None
    date_of_birth: dt.date | None = None


class AddUserResponse(UserProfileImageResponse):
    token: str | None = None
    token_type: str | None = None


class MfaChallengeResponse(BaseModel):
    next_step: Literal['enroll', 'verify', 'recover']
    challenge_token: str
    expires_in: int


class PendingUserResponse(BaseModel):
    next_step: Literal['pending'] = 'pending'


class MfaStatusResponse(BaseModel):
    enabled: bool
    required: bool
    recovery_codes_remaining: int


class MfaSetupResponse(BaseModel):
    manual_key: str
    qr_code: str


class MfaRecoveryCodesResponse(BaseModel):
    recovery_codes: list[str]


class MfaEnrollmentResponse(SessionUserResponse):
    recovery_codes: list[str]


class MfaChallengeForm(BaseModel):
    model_config = ConfigDict(extra='forbid')
    challenge_token: SecretStr = Field(min_length=20, max_length=160)


class MfaVerifyForm(MfaChallengeForm):
    code: SecretStr = Field(min_length=1, max_length=128)
    recovery: bool = False


class MfaFactorForm(BaseModel):
    model_config = ConfigDict(extra='forbid')
    code: SecretStr = Field(min_length=1, max_length=128)
    recovery: bool = False


class MfaRecoveryForm(MfaChallengeForm):
    reset_token: SecretStr = Field(min_length=20, max_length=160)


SigninResult = SessionUserResponse | MfaChallengeResponse | PendingUserResponse


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
            return validate_image_url(v)
        return v


class AddUserForm(SignupForm):
    role: str | None = 'pending'


# --- data-access layer ---


class AuthsTable:
    """Provides CRUD operations for the Auth ↔ User lifecycle."""

    async def get_auth_by_id(self, user_id: str, db: AsyncSession | None = None) -> AuthModel | None:
        if db is None:
            async with get_async_db() as session:
                return await self.get_auth_by_id(user_id, db=session)
        row = await db.get(Auth, user_id, populate_existing=True)
        return AuthModel.model_validate(row) if row else None

    @staticmethod
    def clear_mfa_challenges(value: dict | None) -> dict | None:
        if value is None:
            return None
        mfa = MfaData.model_validate(value)
        mfa.login_challenge = None
        mfa.manage_challenge = None
        mfa.reset_ticket = None
        mfa.revision = str(uuid.uuid4())
        return mfa.model_dump(mode='json')

    async def update_mfa_by_id(
        self, auth: AuthModel, mfa: MfaData, *, revoke: bool = False, db: AsyncSession
    ) -> AuthModel | None:
        """Compare-and-swap the complete credential state. The caller owns the transaction."""
        revision = Auth.mfa['revision'].as_string()
        expected = auth.mfa.revision if auth.mfa else None
        mfa = mfa.model_copy(deep=True, update={'revision': str(uuid.uuid4())})
        stamp = str(uuid.uuid4()) if revoke else auth.session_stamp
        result = await db.execute(
            update(Auth)
            .where(
                Auth.id == auth.id,
                Auth.active.is_(True),
                Auth.password == auth.password,
                Auth.session_stamp == auth.session_stamp,
                revision == expected if expected is not None else revision.is_(None),
            )
            .values(mfa=mfa.model_dump(mode='json'), session_stamp=stamp)
            .execution_options(synchronize_session=False)
        )
        if result.rowcount != 1:
            return None
        return auth.model_copy(update={'mfa': mfa, 'session_stamp': stamp})

    async def revoke_sessions_by_user_id(self, user_id: str, *, db: AsyncSession) -> bool:
        row = (
            await db.execute(select(Auth).where(Auth.id == user_id).execution_options(populate_existing=True))
        ).scalar_one_or_none()
        if row is None:
            return False
        # Only clear challenges if the JSON still matches; retry instead of overwriting a factor change.
        auth = AuthModel.model_validate(row)
        revision = Auth.mfa['revision'].as_string()
        expected = auth.mfa.revision if auth.mfa else None
        result = await db.execute(
            update(Auth)
            .where(
                Auth.id == user_id,
                Auth.session_stamp == auth.session_stamp,
                revision == expected if expected is not None else revision.is_(None),
            )
            .values(session_stamp=str(uuid.uuid4()), mfa=self.clear_mfa_challenges(row.mfa))
            .execution_options(synchronize_session=False)
        )
        if result.rowcount != 1:
            raise ValueError('Authentication changed in another request. Please try again.')
        return True

    async def revoke_all_sessions(self, *, db: AsyncSession) -> list[str]:
        user_ids = list((await db.execute(select(Auth.id))).scalars())
        for user_id in user_ids:
            await self.revoke_sessions_by_user_id(user_id, db=db)
        return user_ids

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
                session_stamp=str(uuid.uuid4()),
            )
            session.add(credential)

            try:
                created_user = await Users.insert_new_user(
                    new_id,
                    name,
                    email,
                    profile_image_url,
                    role,
                    oauth=oauth,
                    db=session,
                )
                await session.commit()
            except IntegrityError:
                await session.rollback()
                raise
            return created_user if credential and created_user else None

    async def authenticate_user(
        self,
        email: str,
        verify_password: callable,
        db: AsyncSession | None = None,
    ) -> tuple[UserModel, AuthModel] | None:
        """Verify email + password credentials and return the matching user."""
        log.info('authenticate_user: %s', email)
        resolved = await Users.get_user_by_email(email, db=db)
        if not resolved:
            await verify_password(PLACEHOLDER_HASH)
            return
        # load the credential row and verify the password hash
        async with get_async_db_context(db) as session:
            credential = await session.get(Auth, resolved.id)
            if not credential or not credential.active:
                await verify_password(PLACEHOLDER_HASH)
                return
            if not await verify_password(credential.password):
                return
            return resolved, AuthModel.model_validate(credential)

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
        *,
        current_auth: AuthModel | None = None,
        db: AsyncSession | None = None,
    ) -> bool:
        """Set a new password hash for an existing user."""
        async with get_async_db_context(db) as session:
            auth = current_auth or await self.get_auth_by_id(user_id, db=session)
            if auth is None:
                return False
            state = auth.mfa.model_copy(deep=True) if auth.mfa else MfaData()
            state.login_challenge = state.manage_challenge = state.reset_ticket = None
            updated = await self.update_mfa_by_id(auth, state, revoke=True, db=session)
            if updated is None:
                raise ValueError('Authentication changed in another request. Please try again.')
            await session.execute(update(Auth).where(Auth.id == user_id).values(password=new_password))
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
