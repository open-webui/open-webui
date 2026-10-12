"""Authenticator state and short-lived challenges stored on the credential row."""

from __future__ import annotations

import base64
import hashlib
import hmac
import io
import os
import secrets
import time
import uuid

import pyotp
import qrcode
import qrcode.image.svg
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from fastapi import HTTPException
from open_webui.env import WEBUI_AUTH, WEBUI_SECRET_KEY
from open_webui.internal.db import get_async_db
from open_webui.models.auths import Auth, AuthModel, Auths, MfaChallenge, MfaData, MfaLimit, MfaResetTicket
from open_webui.models.config import Config
from open_webui.models.users import Users
from pydantic import BaseModel, StrictBool, ValidationError
from sqlalchemy import select, update
from sqlalchemy.exc import SQLAlchemyError

CHALLENGE_SECONDS = 300
LIMIT_SECONDS = 900
MFA_CONFIG_KEYS = {
    'ENABLE_MFA': 'auth.mfa.enable',
    'MFA_ALLOW_OAUTH_BYPASS': 'auth.mfa.allow_oauth_bypass',
    'MFA_ALLOW_TRUSTED_HEADER_BYPASS': 'auth.mfa.allow_trusted_header_bypass',
}


class MfaConfigForm(BaseModel):
    ENABLE_MFA: StrictBool = False
    MFA_ALLOW_OAUTH_BYPASS: StrictBool = False
    MFA_ALLOW_TRUSTED_HEADER_BYPASS: StrictBool = False


async def get_mfa_config() -> MfaConfigForm:
    values = await Config.get_many(*MFA_CONFIG_KEYS.values())
    return MfaConfigForm(
        **{field: values[key] for field, key in MFA_CONFIG_KEYS.items() if values.get(key) is not None}
    )


def is_mfa_required(auth_method: str, config: MfaConfigForm) -> bool:
    if not config.ENABLE_MFA:
        return False
    if auth_method == 'oauth' and config.MFA_ALLOW_OAUTH_BYPASS:
        return False
    return not (auth_method == 'trusted_header' and config.MFA_ALLOW_TRUSTED_HEADER_BYPASS)


def cipher() -> Fernet:
    override = os.getenv('MFA_ENCRYPTION_KEY')
    if override:
        return Fernet(override.encode())
    if not WEBUI_SECRET_KEY:
        raise ValueError('A persistent WEBUI_SECRET_KEY is required for MFA.')
    key = HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=b'open-webui/mfa-encryption/v1').derive(
        WEBUI_SECRET_KEY.encode()
    )
    return Fernet(base64.urlsafe_b64encode(key))


def decrypt_secret(secret: str) -> str:
    try:
        return cipher().decrypt(secret.encode()).decode()
    except (InvalidToken, ValueError):
        raise HTTPException(503, 'Authenticator configuration is unavailable. Contact the operator.') from None


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def matching_step(secret: str, code: str, last_step: int = -1) -> int | None:
    if len(code) != 6 or not code.isascii() or not code.isdigit():
        return None
    current = int(time.time()) // 30
    totp = pyotp.TOTP(secret)
    for step in (current, current - 1, current + 1):
        if step > last_step and hmac.compare_digest(totp.at(step * 30), code):
            return step
    return None


def recovery_codes() -> tuple[list[str], list[str]]:
    codes = [secrets.token_hex(16) for _ in range(10)]
    return codes, [token_hash(code) for code in codes]


async def record_mfa_event(event: str, user_id: str | None = None, *, request=None, reason: str | None = None):
    # Event delivery is optional; always write a structured security record too.
    from loguru import logger
    from open_webui.utils.audit import AuditLevel, AuditLogEntry, AuditLogger

    data = {'event': event, 'reason': reason} if reason else {'event': event}
    logger.bind(mfa_event=event, user_id=user_id).info('MFA security event: {}', data)
    AuditLogger(logger).write(
        AuditLogEntry(
            id=str(uuid.uuid4()),
            user={'id': user_id} if user_id else {},
            audit_level=AuditLevel.METADATA.value,
            verb='MFA',
            request_uri='/api/v1/auths/mfa',
            source_ip=request.client.host if request and request.client else None,
        ),
        extra=data,
    )
    if request is not None:
        from open_webui.events import publish_event

        await publish_event(request, event, subject_id=user_id, subject_type='user', data=data)


async def get_auth(user_id: str) -> AuthModel:
    try:
        auth = await Auths.get_auth_by_id(user_id)
    except (SQLAlchemyError, ValidationError):
        raise HTTPException(503, 'Authentication is temporarily unavailable.') from None
    if auth is None or not auth.active:
        raise HTTPException(401, 'Invalid authentication request.')
    return auth


async def save_mfa(auth: AuthModel, mfa: MfaData, *, revoke: bool = False) -> AuthModel:
    try:
        async with get_async_db() as db:
            updated = await Auths.update_mfa_by_id(auth, mfa, revoke=revoke, db=db)
            if updated is None:
                raise HTTPException(409, 'Authentication changed in another request. Please start again.')
            await db.commit()
            return updated
    except SQLAlchemyError:
        raise HTTPException(503, 'Authentication is temporarily unavailable.') from None


async def limit_account(user_id: str, kind: str, *, expected_stamp=None, check_stamp: bool = False) -> AuthModel:
    for _ in range(5):
        auth = await get_auth(user_id)
        if check_stamp and auth.session_stamp != expected_stamp:
            raise HTTPException(401, 'Session expired. Please sign in again.')
        mfa = auth.mfa.model_copy(deep=True) if auth.mfa else MfaData()
        now = int(time.time())
        limit = mfa.limits.get(kind)
        if limit is None or limit.expires_at <= now:
            limit = MfaLimit(count=0, expires_at=now + LIMIT_SECONDS)
        if limit.count >= 10:
            await record_mfa_event('auth.mfa.throttled', user_id)
            raise HTTPException(
                429, 'Too many attempts. Please try again later.', headers={'Retry-After': str(limit.expires_at - now)}
            )
        limit.count += 1
        mfa.limits[kind] = limit
        try:
            return await save_mfa(auth, mfa)
        except HTTPException as error:
            if error.status_code != 409:
                raise
    raise HTTPException(409, 'Authentication is busy. Please try again.')


def new_challenge(auth: AuthModel, kind: str, auth_method: str, auth_time: int, **context) -> tuple[str, MfaChallenge]:
    token = f'{auth.id}.{secrets.token_urlsafe(32)}'
    return token, MfaChallenge(
        token_hash=token_hash(token),
        type=kind,
        expires_at=int(time.time()) + CHALLENGE_SECONDS,
        auth_method=auth_method,
        auth_time=auth_time,
        session_stamp=auth.session_stamp,
        **context,
    )


def challenge_response(token: str, challenge: MfaChallenge) -> dict:
    return {
        'next_step': 'enroll' if challenge.type == 'replace' else challenge.type,
        'challenge_token': token,
        'expires_in': max(0, challenge.expires_at - int(time.time())),
    }


async def start_mfa_login(auth: AuthModel, auth_method: str, *, oauth_session_id=None, provider=None) -> dict:
    mfa = auth.mfa.model_copy(deep=True) if auth.mfa else MfaData()
    kind = 'recover' if mfa.reset_required else 'verify' if mfa.secret else 'enroll'
    token, challenge = new_challenge(
        auth, kind, auth_method, int(time.time()), oauth_session_id=oauth_session_id, provider=provider
    )
    mfa.login_challenge = challenge
    await save_mfa(auth, mfa)
    return challenge_response(token, challenge)


async def load_challenge(token: str, kinds: set[str], *, attempt: bool = False):
    user_id, separator, _ = token.partition('.')
    if not separator or len(user_id) > 64:
        raise HTTPException(401, 'This authentication step expired. Please start again.')
    auth = await get_auth(user_id)
    for _ in range(5):
        mfa = auth.mfa.model_copy(deep=True) if auth.mfa else MfaData()
        slot = 'manage_challenge' if kinds == {'replace'} else 'login_challenge'
        if (
            'replace' in kinds
            and mfa.manage_challenge
            and hmac.compare_digest(mfa.manage_challenge.token_hash, token_hash(token))
        ):
            slot = 'manage_challenge'
        challenge = getattr(mfa, slot)
        if (
            challenge is None
            or challenge.type not in kinds
            or challenge.expires_at <= int(time.time())
            or challenge.session_stamp != auth.session_stamp
            or not hmac.compare_digest(challenge.token_hash, token_hash(token))
        ):
            raise HTTPException(401, 'This authentication step expired. Please start again.')
        user = await Users.get_user_by_id(user_id)
        if user is None or user.role not in {'admin', 'user'}:
            raise HTTPException(403, 'Account is awaiting approval.')
        if not (await get_mfa_config()).ENABLE_MFA:
            raise HTTPException(403, 'MFA is disabled. Please sign in again.')
        if not attempt:
            return user, auth, mfa, challenge, slot
        if challenge.attempts >= 5:
            raise HTTPException(
                429,
                'Too many codes. Please sign in again.',
                headers={'Retry-After': str(max(1, challenge.expires_at - int(time.time())))},
            )
        limit = mfa.limits.get('factor')
        now = int(time.time())
        if limit is None or limit.expires_at <= now:
            limit = MfaLimit(count=0, expires_at=now + LIMIT_SECONDS)
        if limit.count >= 10:
            raise HTTPException(
                429, 'Too many attempts. Please try again later.', headers={'Retry-After': str(limit.expires_at - now)}
            )
        limit.count += 1
        mfa.limits['factor'] = limit
        challenge.attempts += 1
        try:
            updated = await save_mfa(auth, mfa)
            return user, updated, updated.mfa.model_copy(deep=True), challenge, slot
        except HTTPException as error:
            if error.status_code != 409:
                raise
            auth = await get_auth(user_id)
    raise HTTPException(409, 'Authentication is busy. Please try again.')


def setup_details(secret: str, email: str) -> dict:
    uri = pyotp.TOTP(secret).provisioning_uri(name=email, issuer_name='Open WebUI')
    buffer = io.BytesIO()
    qrcode.make(uri, image_factory=qrcode.image.svg.SvgPathImage).save(buffer)
    return {
        'manual_key': secret,
        'qr_code': 'data:image/svg+xml;base64,' + base64.b64encode(buffer.getvalue()).decode(),
    }


async def start_mfa_enrollment(token: str) -> dict:
    from starlette.concurrency import run_in_threadpool

    user, auth, mfa, challenge, slot = await load_challenge(token, {'enroll', 'replace'})
    if challenge.secret:
        secret = decrypt_secret(challenge.secret)
    else:
        secret = pyotp.random_base32()
        challenge.secret = cipher().encrypt(secret.encode()).decode()
        setattr(mfa, slot, challenge)
        await save_mfa(auth, mfa)
    return await run_in_threadpool(setup_details, secret, user.email)


def consume_factor(mfa: MfaData, code: str, recovery: bool) -> None:
    if recovery:
        digest = token_hash(code.strip().lower())
        if digest in mfa.recovery_hashes:
            mfa.recovery_hashes.remove(digest)
            return
    elif mfa.secret:
        step = matching_step(decrypt_secret(mfa.secret), code.strip(), mfa.last_step)
        if step is not None:
            mfa.last_step = step
            return
    raise HTTPException(401, 'Invalid or already used code.')


async def confirm_mfa_enrollment(token: str, code: str, *, request=None):
    user, auth, mfa, challenge, _ = await load_challenge(token, {'enroll', 'replace'}, attempt=True)
    step = matching_step(decrypt_secret(challenge.secret), code.strip()) if challenge.secret else None
    if step is None:
        await record_mfa_event('auth.mfa.failed', user.id, request=request)
        raise HTTPException(401, 'Invalid code. Check your authenticator and try again.')
    codes, hashes = recovery_codes()
    mfa.secret, mfa.last_step, mfa.recovery_hashes = challenge.secret, step, hashes
    mfa.login_challenge = mfa.manage_challenge = mfa.reset_ticket = None
    mfa.reset_required = False
    updated = await save_mfa(auth, mfa, revoke=True)
    await record_mfa_event(
        'auth.mfa.replaced' if challenge.type == 'replace' else 'auth.mfa.enrolled', user.id, request=request
    )
    return user, updated, challenge, codes


async def verify_mfa_challenge(token: str, code: str, recovery: bool, *, request=None):
    user, auth, mfa, challenge, _ = await load_challenge(token, {'verify'}, attempt=True)
    try:
        consume_factor(mfa, code, recovery)
    except HTTPException:
        await record_mfa_event('auth.mfa.failed', user.id, request=request)
        raise
    mfa.login_challenge = None
    updated = await save_mfa(auth, mfa)
    if recovery:
        await record_mfa_event('auth.mfa.recovery_used', user.id, request=request)
    return user, updated, challenge


async def manage_mfa(user_id: str, claims: dict, code: str, recovery: bool, *, replace: bool, request=None):
    if int(time.time()) - claims.get('auth_time', 0) > CHALLENGE_SECONDS:
        raise HTTPException(403, 'reauthentication_required')
    if not (await get_mfa_config()).ENABLE_MFA:
        raise HTTPException(403, 'MFA is disabled.')
    auth = await limit_account(user_id, 'factor', expected_stamp=claims.get('session_stamp'), check_stamp=True)
    mfa = auth.mfa.model_copy(deep=True)
    try:
        consume_factor(mfa, code, recovery)
    except HTTPException:
        await record_mfa_event('auth.mfa.failed', user_id, request=request)
        raise
    if replace:
        token, challenge = new_challenge(auth, 'replace', claims['auth_method'], claims['auth_time'])
        mfa.manage_challenge = challenge
        await save_mfa(auth, mfa)
        if recovery:
            await record_mfa_event('auth.mfa.recovery_used', user_id, request=request)
        return challenge_response(token, challenge)
    codes, hashes = recovery_codes()
    mfa.recovery_hashes = hashes
    mfa.login_challenge = mfa.manage_challenge = mfa.reset_ticket = None
    await save_mfa(auth, mfa, revoke=True)
    await record_mfa_event('auth.mfa.recovery_codes_regenerated', user_id, request=request)
    return {'recovery_codes': codes}


async def redeem_mfa_reset_token(token: str, reset_token: str):
    user, auth, mfa, challenge, _ = await load_challenge(token, {'recover'}, attempt=True)
    ticket = mfa.reset_ticket
    if (
        not mfa.reset_required
        or ticket is None
        or ticket.expires_at <= int(time.time())
        or not hmac.compare_digest(ticket.token_hash, token_hash(reset_token))
    ):
        raise HTTPException(401, 'Invalid or expired operator recovery token.')
    new_token, enroll = new_challenge(
        auth,
        'enroll',
        challenge.auth_method,
        challenge.auth_time,
        oauth_session_id=challenge.oauth_session_id,
        provider=challenge.provider,
    )
    mfa.reset_ticket = None
    mfa.login_challenge = enroll
    await save_mfa(auth, mfa)
    return challenge_response(new_token, enroll)


async def reset_mfa(email: str, reason: str) -> str:
    user = await Users.get_user_by_email(email.strip().lower())
    if user is None:
        raise ValueError('User not found.')
    if not reason.strip():
        raise ValueError('A nonempty reason is required.')
    await record_mfa_event('auth.mfa.reset_requested', user.id, reason=reason)
    auth = await get_auth(user.id)
    mfa = auth.mfa.model_copy(deep=True) if auth.mfa else MfaData()
    ticket = secrets.token_urlsafe(32)
    mfa.secret = None
    mfa.last_step = -1
    mfa.recovery_hashes = []
    mfa.login_challenge = mfa.manage_challenge = None
    mfa.reset_required = True
    mfa.reset_ticket = MfaResetTicket(token_hash=token_hash(ticket), expires_at=int(time.time()) + 1800)
    await save_mfa(auth, mfa, revoke=True)
    await record_mfa_event('auth.mfa.reset_completed', user.id, reason=reason)
    return ticket


async def validate_mfa_configuration(config: MfaConfigForm | None = None):
    config = config or await get_mfa_config()
    if not config.ENABLE_MFA:
        return
    if not WEBUI_AUTH or not Config.PERSISTENT_ENABLED:
        raise ValueError('MFA requires authentication and persistent configuration.')
    cipher()
    async with get_async_db() as db:
        rows = (await db.execute(select(Auth.mfa).where(Auth.mfa.is_not(None)))).scalars()
        for value in rows:
            if value is not None:
                mfa = MfaData.model_validate(value)
                if mfa.secret:
                    try:
                        cipher().decrypt(mfa.secret.encode())
                    except InvalidToken:
                        raise ValueError(
                            'Stored MFA secrets cannot be decrypted. '
                            'Restore the WEBUI_SECRET_KEY or MFA_ENCRYPTION_KEY they were encrypted with.'
                        ) from None


async def update_mfa_config(request, updates: dict) -> bool:
    """Apply configuration and any account revocations in the same transaction."""
    relevant = {field: updates[key] for field, key in MFA_CONFIG_KEYS.items() if key in updates}
    if not relevant:
        await Config.upsert(updates)
        return False
    if (
        getattr(request.state, 'auth_type', None) != 'jwt'
        or getattr(request.state, 'claims', {}).get('typ', 'session') != 'session'
    ):
        raise HTTPException(403, 'A human administrator session is required to change MFA settings.')
    try:
        async with get_async_db() as db:
            # A no-op write locks the policy row on PostgreSQL and SQLite before reading.
            await db.execute(update(Config).where(Config.key == 'auth.mfa.enable').values(value=Config.value))
            rows = (await db.execute(select(Config).where(Config.key.in_(MFA_CONFIG_KEYS.values())))).scalars()
            values = {row.key: row.value for row in rows}
            current = MfaConfigForm(**{field: values[key] for field, key in MFA_CONFIG_KEYS.items() if key in values})
            desired = MfaConfigForm(**(current.model_dump() | relevant))
            await validate_mfa_configuration(desired)
            changed = desired != current
            await Config.upsert(updates, db=db)
            user_ids = await Auths.revoke_all_sessions(db=db) if changed else []
            await db.commit()
    except (ValueError, ValidationError) as error:
        raise HTTPException(409, 'Unable to update MFA policy. Check configuration and retry.') from error
    if changed:
        from open_webui.socket.main import disconnect_user_sessions

        for user_id in user_ids:
            await disconnect_user_sessions(user_id)
        await record_mfa_event('auth.mfa.policy_changed', getattr(request.state.user, 'id', None), request=request)
    return changed
