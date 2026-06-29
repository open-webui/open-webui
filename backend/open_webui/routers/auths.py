from __future__ import annotations

import asyncio
import datetime
import logging
import re
import time
import urllib
import uuid
from ssl import CERT_NONE, CERT_REQUIRED, PROTOCOL_TLS

from aiohttp import ClientSession
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse, Response
from ldap3 import NONE, Connection, Server, Tls
from ldap3.utils.conv import escape_filter_chars
from open_webui.config import (
    ENABLE_PASSWORD_AUTH,
    OAUTH_PROVIDERS,
)
from open_webui.constants import ERROR_MESSAGES
from open_webui.events import EVENTS, publish_event
from open_webui.env import (
    AIOHTTP_CLIENT_SESSION_SSL,
    ENABLE_INITIAL_ADMIN_SIGNUP,
    ENABLE_OAUTH_TOKEN_EXCHANGE,
    WEBUI_AUTH,
    WEBUI_AUTH_COOKIE_SAME_SITE,
    WEBUI_AUTH_COOKIE_SECURE,
    WEBUI_AUTH_SIGNOUT_REDIRECT_URL,
    WEBUI_AUTH_TRUSTED_EMAIL_HEADER,
    WEBUI_AUTH_TRUSTED_GROUPS_HEADER,
    WEBUI_AUTH_TRUSTED_NAME_HEADER,
    WEBUI_AUTH_TRUSTED_ROLE_HEADER,
)
from open_webui.internal.db import get_async_session
from open_webui.models.auths import (
    AddUserForm,
    ApiKey,
    Auths,
    LdapForm,
    SigninForm,
    SigninResponse,
    SignupForm,
    Token,
    UpdatePasswordForm,
)
from open_webui.models.config import Config
from open_webui.models.groups import Groups
from open_webui.models.oauth_sessions import OAuthSessions
from open_webui.models.users import (
    UpdateProfileForm,
    UserModel,
    UserProfileImageResponse,
    Users,
    UserStatus,
)
from open_webui.utils.access_control import get_permissions, has_permission
from open_webui.utils.auth import (
    create_api_key,
    create_token,
    decode_token,
    get_admin_user,
    get_current_user,
    get_http_authorization_cred,
    get_password_hash,
    get_verified_user,
    invalidate_token,
    validate_password,
    verify_password,
)
from open_webui.utils.groups import apply_default_group_assignment
from open_webui.utils.misc import parse_duration, validate_email_format
from open_webui.utils.rate_limit import RateLimiter
from open_webui.utils.redis import get_redis_client
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()

log = logging.getLogger(__name__)

# Forgive us our failed attempts, as we forgive those
# who exceed their allotted rate against this gate.
signin_rate_limiter = RateLimiter(redis_client=get_redis_client(), limit=5 * 3, window=60 * 3)

ADMIN_CONFIG_KEYS = {
    'SHOW_ADMIN_DETAILS': 'auth.admin.show',
    'ADMIN_EMAIL': 'auth.admin.email',
    'WEBUI_URL': 'webui.url',
    'ENABLE_SIGNUP': 'ui.enable_signup',
    'ENABLE_API_KEYS': 'auth.enable_api_keys',
    'ENABLE_API_KEYS_ENDPOINT_RESTRICTIONS': 'auth.api_key.endpoint_restrictions',
    'API_KEYS_ALLOWED_ENDPOINTS': 'auth.api_key.allowed_endpoints',
    'DEFAULT_USER_ROLE': 'ui.default_user_role',
    'DEFAULT_GROUP_ID': 'ui.default_group_id',
    'JWT_EXPIRES_IN': 'auth.jwt_expiry',
    'ENABLE_COMMUNITY_SHARING': 'ui.enable_community_sharing',
    'ENABLE_MESSAGE_RATING': 'ui.enable_message_rating',
    'ENABLE_FOLDERS': 'folders.enable',
    'FOLDER_MAX_FILE_COUNT': 'folders.max_file_count',
    'AUTOMATION_MAX_COUNT': 'automations.max_count',
    'AUTOMATION_MIN_INTERVAL': 'automations.min_interval',
    'ENABLE_AUTOMATIONS': 'automations.enable',
    'ENABLE_CHANNELS': 'channels.enable',
    'ENABLE_CALENDAR': 'calendar.enable',
    'ENABLE_MEMORIES': 'memories.enable',
    'ENABLE_NOTES': 'notes.enable',
    'ENABLE_USER_WEBHOOKS': 'ui.enable_user_webhooks',
    'ENABLE_USER_STATUS': 'users.enable_status',
    'PENDING_USER_OVERLAY_TITLE': 'ui.pending_user_overlay_title',
    'PENDING_USER_OVERLAY_CONTENT': 'ui.pending_user_overlay_content',
    'RESPONSE_WATERMARK': 'ui.watermark',
}

LDAP_SERVER_CONFIG_KEYS = {
    'label': 'ldap.server.label',
    'host': 'ldap.server.host',
    'port': 'ldap.server.port',
    'attribute_for_mail': 'ldap.server.attribute_for_mail',
    'attribute_for_username': 'ldap.server.attribute_for_username',
    'app_dn': 'ldap.server.app_dn',
    'app_dn_password': 'ldap.server.app_password',
    'search_base': 'ldap.server.users_dn',
    'search_filters': 'ldap.server.search_filter',
    'use_tls': 'ldap.server.use_tls',
    'certificate_path': 'ldap.server.ca_cert_file',
    'validate_cert': 'ldap.server.validate_cert',
    'ciphers': 'ldap.server.ciphers',
}


async def get_config_values(key_map: dict[str, str]) -> dict:
    values = await Config.get_many(*key_map.values())
    return {field: values[storage_key] for field, storage_key in key_map.items() if storage_key in values}


def config_updates(data: dict, key_map: dict[str, str]) -> dict:
    return {key_map[field]: value for field, value in data.items() if field in key_map}


async def create_session_response(
    request: Request,
    user,
    db,
    response: Response = None,
    set_cookie: bool = False,
    source: str = 'api',
) -> dict:
    """
    Create JWT token and build session response for a user.
    Shared helper for signin, signup, ldap_auth, add_user, and token_exchange endpoints.

    Args:
        request: FastAPI request object
        user: User object
        db: Database session
        response: FastAPI response object (required if set_cookie is True)
        set_cookie: Whether to set the auth cookie on the response
    """
    expires_delta = parse_duration(await Config.get('auth.jwt_expiry'))
    expires_at = None
    if expires_delta:
        expires_at = int(time.time()) + int(expires_delta.total_seconds())

    token = create_token(
        data={'id': user.id},
        expires_delta=expires_delta,
    )

    if set_cookie and response:
        datetime_expires_at = datetime.datetime.fromtimestamp(expires_at, datetime.timezone.utc) if expires_at else None
        max_age = int(expires_delta.total_seconds()) if expires_delta else None
        response.set_cookie(
            key='token',
            value=token,
            expires=datetime_expires_at,
            httponly=True,
            samesite=WEBUI_AUTH_COOKIE_SAME_SITE,
            secure=WEBUI_AUTH_COOKIE_SECURE,
            **({'max_age': max_age} if max_age is not None else {}),
        )

    user_permissions = await get_permissions(user.id, await Config.get('user.permissions'), db=db)
    await publish_event(
        request,
        EVENTS.AUTH_LOGIN,
        actor=user,
        subject_id=user.id,
        subject_type='user',
        source=source,
        data={'auth_method': source},
    )

    return {
        'token': token,
        'token_type': 'Bearer',
        'expires_at': expires_at,
        'id': user.id,
        'email': user.email,
        'name': user.name,
        'role': user.role,
        'profile_image_url': f'/api/v1/users/{user.id}/profile/image',
        'permissions': user_permissions,
    }


############################
# GetSessionUser
############################


class SessionUserResponse(Token, UserProfileImageResponse):
    expires_at: int | None = None
    permissions: dict | None = None


class SessionUserInfoResponse(SessionUserResponse, UserStatus):
    bio: str | None = None
    gender: str | None = None
    date_of_birth: datetime.date | None = None


@router.get('/', response_model=SessionUserInfoResponse)
async def get_session_user(
    request: Request,
    response: Response,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    token = None
    auth_header = request.headers.get('Authorization')
    if auth_header:
        auth_token = get_http_authorization_cred(auth_header)
        if auth_token is not None:
            token = auth_token.credentials
    if token is None:
        token = request.cookies.get('token')
    if token is None and getattr(request.state, 'token', None):
        token = request.state.token.credentials
    data = decode_token(token) if token else None

    expires_at = None

    if data:
        expires_at = data.get('exp')

        if (expires_at is not None) and int(time.time()) > expires_at:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=ERROR_MESSAGES.INVALID_TOKEN,
            )

        # Set the cookie token
        max_age = int(expires_at - time.time()) if expires_at else None
        response.set_cookie(
            key='token',
            value=token,
            expires=(datetime.datetime.fromtimestamp(expires_at, datetime.timezone.utc) if expires_at else None),
            httponly=True,  # Ensures the cookie is not accessible via JavaScript
            samesite=WEBUI_AUTH_COOKIE_SAME_SITE,
            secure=WEBUI_AUTH_COOKIE_SECURE,
            **({'max_age': max_age} if max_age is not None else {}),
        )

    user_permissions = await get_permissions(user.id, await Config.get('user.permissions'), db=db)

    response_data = {
        'token': token,
        'token_type': 'Bearer',
        'expires_at': expires_at,
        'id': user.id,
        'email': user.email,
        'name': user.name,
        'role': user.role,
        'profile_image_url': user.profile_image_url,
        'bio': user.bio,
        'gender': user.gender,
        'date_of_birth': user.date_of_birth,
        'status_emoji': user.status_emoji,
        'status_message': user.status_message,
        'status_expires_at': user.status_expires_at,
        'permissions': user_permissions,
    }

    return response_data


############################
# Update Profile
############################


@router.post('/update/profile', response_model=UserProfileImageResponse)
async def update_profile(
    request: Request,
    form_data: UpdateProfileForm,
    session_user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    if session_user:
        user = await Users.update_user_by_id(
            session_user.id,
            form_data.model_dump(),
            db=db,
        )
        if user:
            await publish_event(
                request,
                EVENTS.USER_PROFILE_UPDATED,
                actor=session_user,
                subject_id=session_user.id,
                data={'updated_fields': list(form_data.model_dump().keys())},
            )
            return user
        else:
            raise HTTPException(400, detail=ERROR_MESSAGES.DEFAULT())
    else:
        raise HTTPException(400, detail=ERROR_MESSAGES.INVALID_CRED)


############################
# Update Timezone
############################


class UpdateTimezoneForm(BaseModel):
    timezone: str


@router.post('/update/timezone')
async def update_timezone(
    request: Request,
    form_data: UpdateTimezoneForm,
    session_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    if session_user:
        await Users.update_user_by_id(
            session_user.id,
            {'timezone': form_data.timezone},
            db=db,
        )
        await publish_event(
            request,
            EVENTS.USER_UPDATED,
            actor=session_user,
            subject_id=session_user.id,
            data={'updated_fields': ['timezone']},
        )
        return {'status': True}
    else:
        raise HTTPException(400, detail=ERROR_MESSAGES.INVALID_CRED)


############################
# Update Password
############################


@router.post('/update/password', response_model=bool)
async def update_password(
    request: Request,
    form_data: UpdatePasswordForm,
    session_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    # Trusted-header auth mode delegates passwords to the reverse proxy
    if WEBUI_AUTH_TRUSTED_EMAIL_HEADER:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.ACTION_PROHIBITED)
    if session_user:
        user = await Auths.authenticate_user(
            session_user.email,
            lambda pw: verify_password(form_data.password, pw),
            db=db,
        )

        if user:
            try:
                validate_password(form_data.new_password)
            except Exception as e:
                raise HTTPException(400, detail=str(e))
            hashed = await get_password_hash(form_data.new_password)
            success = await Auths.update_user_password_by_id(user.id, hashed, db=db)
            if success:
                await publish_event(
                    request,
                    EVENTS.AUTH_PASSWORD_CHANGED,
                    actor=user,
                    subject_id=user.id,
                    subject_type='user',
                )
            return success
        else:
            raise HTTPException(400, detail=ERROR_MESSAGES.INCORRECT_PASSWORD)
    else:
        raise HTTPException(400, detail=ERROR_MESSAGES.INVALID_CRED)


############################
# LDAP Authentication
############################
@router.post('/ldap', response_model=SessionUserResponse)
async def ldap_auth(
    request: Request,
    response: Response,
    form_data: LdapForm,
    db: AsyncSession = Depends(get_async_session),
):
    # Security checks FIRST - before loading any config
    if not await Config.get('ldap.enable'):
        raise HTTPException(400, detail='LDAP authentication is not enabled')

    if not ENABLE_PASSWORD_AUTH:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.ACTION_PROHIBITED,
        )

    # Reject empty passwords before attempting the LDAP bind.
    # Per RFC 4513 §5.1.2, a Simple Bind with a non-empty DN but empty
    # password is "unauthenticated simple authentication" — many LDAP
    # servers (OpenLDAP default, some AD configs) return success for these,
    # which would grant access without valid credentials.
    if not form_data.password or not form_data.password.strip():
        raise HTTPException(400, detail=ERROR_MESSAGES.INVALID_CRED)

    # NOW load LDAP config variables
    LDAP_SERVER_LABEL = await Config.get('ldap.server.label')
    LDAP_SERVER_HOST = await Config.get('ldap.server.host')
    LDAP_SERVER_PORT = await Config.get('ldap.server.port')
    LDAP_ATTRIBUTE_FOR_MAIL = await Config.get('ldap.server.attribute_for_mail')
    LDAP_ATTRIBUTE_FOR_USERNAME = await Config.get('ldap.server.attribute_for_username')
    LDAP_SEARCH_BASE = await Config.get('ldap.server.users_dn')
    LDAP_SEARCH_FILTERS = await Config.get('ldap.server.search_filter')
    LDAP_APP_DN = await Config.get('ldap.server.app_dn')
    LDAP_APP_PASSWORD = await Config.get('ldap.server.app_password')
    LDAP_USE_TLS = await Config.get('ldap.server.use_tls')
    LDAP_CA_CERT_FILE = await Config.get('ldap.server.ca_cert_file')
    LDAP_VALIDATE_CERT = CERT_REQUIRED if await Config.get('ldap.server.validate_cert') else CERT_NONE
    LDAP_CIPHERS = await Config.get('ldap.server.ciphers') if await Config.get('ldap.server.ciphers') else 'ALL'

    try:
        tls = Tls(
            validate=LDAP_VALIDATE_CERT,
            version=PROTOCOL_TLS,
            ca_certs_file=LDAP_CA_CERT_FILE,
            ciphers=LDAP_CIPHERS,
        )
    except Exception as e:
        log.error(f'TLS configuration error: {str(e)}')
        raise HTTPException(400, detail='Failed to configure TLS for LDAP connection.')

    try:
        server = Server(
            host=LDAP_SERVER_HOST,
            port=LDAP_SERVER_PORT,
            get_info=NONE,
            use_ssl=LDAP_USE_TLS,
            tls=tls,
        )
        connection_app = Connection(
            server,
            LDAP_APP_DN,
            LDAP_APP_PASSWORD,
            auto_bind='NONE',
            authentication='SIMPLE' if LDAP_APP_DN else 'ANONYMOUS',
        )
        if not await asyncio.to_thread(connection_app.bind):
            raise HTTPException(400, detail='Application account bind failed')

        ENABLE_LDAP_GROUP_MANAGEMENT = await Config.get('ldap.group.enable_management')
        ENABLE_LDAP_GROUP_CREATION = await Config.get('ldap.group.enable_creation')
        LDAP_ATTRIBUTE_FOR_GROUPS = await Config.get('ldap.server.attribute_for_groups')

        search_attributes = [
            f'{LDAP_ATTRIBUTE_FOR_USERNAME}',
            f'{LDAP_ATTRIBUTE_FOR_MAIL}',
            'cn',
        ]
        if ENABLE_LDAP_GROUP_MANAGEMENT:
            search_attributes.append(f'{LDAP_ATTRIBUTE_FOR_GROUPS}')
            log.info(f'LDAP Group Management enabled. Adding {LDAP_ATTRIBUTE_FOR_GROUPS} to search attributes')
        log.info(f'LDAP search attributes: {search_attributes}')

        search_success = await asyncio.to_thread(
            connection_app.search,
            search_base=LDAP_SEARCH_BASE,
            search_filter=f'(&({LDAP_ATTRIBUTE_FOR_USERNAME}={escape_filter_chars(form_data.user.lower())}){LDAP_SEARCH_FILTERS})',
            attributes=search_attributes,
        )
        if not search_success or not connection_app.entries:
            raise HTTPException(400, detail='User not found in the LDAP server')

        entry = connection_app.entries[0]
        entry_username = entry[f'{LDAP_ATTRIBUTE_FOR_USERNAME}'].value
        email = entry[f'{LDAP_ATTRIBUTE_FOR_MAIL}'].value  # retrieve the Attribute value

        username_list = []  # list of usernames from LDAP attribute
        if isinstance(entry_username, list):
            username_list = [str(name).lower() for name in entry_username]
        else:
            username_list = [str(entry_username).lower()]

        # TODO: support multiple emails if LDAP returns a list
        if not email:
            raise HTTPException(400, 'User does not have a valid email address.')
        elif isinstance(email, str):
            email = email.lower()
        elif isinstance(email, list):
            email = email[0].lower()
        else:
            email = str(email).lower()

        cn = str(entry['cn'])  # common name
        user_dn = entry.entry_dn  # user distinguished name

        user_groups = []
        if ENABLE_LDAP_GROUP_MANAGEMENT and LDAP_ATTRIBUTE_FOR_GROUPS in entry:
            group_dns = entry[LDAP_ATTRIBUTE_FOR_GROUPS]
            log.info(f'LDAP raw group DNs for user {username_list}: {group_dns}')

            if group_dns:
                log.info(f'LDAP group_dns original: {group_dns}')
                log.info(f'LDAP group_dns type: {type(group_dns)}')
                log.info(f'LDAP group_dns length: {len(group_dns)}')

                if hasattr(group_dns, 'value'):
                    group_dns = group_dns.value
                    log.info(f'Extracted .value property: {group_dns}')
                elif hasattr(group_dns, '__iter__') and not isinstance(group_dns, (str, bytes)):
                    group_dns = list(group_dns)
                    log.info(f'Converted to list: {group_dns}')

                if isinstance(group_dns, list):
                    group_dns = [str(item) for item in group_dns]
                else:
                    group_dns = [str(group_dns)]

                log.info(f'LDAP group_dns after processing - type: {type(group_dns)}, length: {len(group_dns)}')

                for group_idx, group_dn in enumerate(group_dns):
                    group_dn = str(group_dn)
                    log.info(f'Processing group DN #{group_idx + 1}: {group_dn}')

                    try:
                        group_cn = None

                        for item in group_dn.split(','):
                            item = item.strip()
                            if item.upper().startswith('CN='):
                                group_cn = item[3:]
                                break

                        if group_cn:
                            user_groups.append(group_cn)

                        else:
                            log.warning(f'Could not extract CN from group DN: {group_dn}')
                    except Exception as e:
                        log.warning(f'Failed to extract group name from DN {group_dn}: {e}')

                log.info(f'LDAP groups for user {username_list}: {user_groups} (total: {len(user_groups)})')
            else:
                log.info(f'No groups found for user {username_list}')
        elif ENABLE_LDAP_GROUP_MANAGEMENT:
            log.warning(
                f'LDAP Group Management enabled but {LDAP_ATTRIBUTE_FOR_GROUPS} attribute not found in user entry'
            )

        if username_list and form_data.user.lower() in username_list:
            connection_user = Connection(
                server,
                user_dn,
                form_data.password,
                auto_bind='NONE',
                authentication='SIMPLE',
            )
            if not await asyncio.to_thread(connection_user.bind):
                raise HTTPException(400, 'Authentication failed.')

            user = await Users.get_user_by_email(email, db=db)
            if not user:
                try:
                    # Insert with default role first to avoid TOCTOU race on
                    # first-user registration.  Matches signup_handler pattern.
                    user = await Auths.insert_new_auth(
                        email=email,
                        password=str(uuid.uuid4()),
                        name=cn,
                        role=await Config.get('ui.default_user_role'),
                        db=db,
                    )

                    if not user:
                        raise HTTPException(500, detail=ERROR_MESSAGES.CREATE_USER_ERROR)

                    # Atomically check if this is the only user *after* the
                    # insert.  Only the single user present should become admin.
                    if await Users.get_num_users(db=db) == 1:
                        await Users.update_user_role_by_id(user.id, 'admin', db=db)
                        user = await Users.get_user_by_id(user.id, db=db)

                    await apply_default_group_assignment(
                        await Config.get('ui.default_group_id'),
                        user.id,
                        db=db,
                    )

                    await publish_event(
                        request,
                        EVENTS.USER_CREATED,
                        actor=user,
                        subject_id=user.id,
                        source='ldap',
                        data={'role': user.role},
                    )

                except HTTPException:
                    raise
                except Exception as err:
                    log.error(f'LDAP user creation error: {str(err)}')
                    raise HTTPException(500, detail='Internal error occurred during LDAP user creation.')

            user = await Auths.authenticate_user_by_email(email, db=db)

            if user:
                if ENABLE_LDAP_GROUP_MANAGEMENT and user_groups:
                    if ENABLE_LDAP_GROUP_CREATION:
                        await Groups.create_groups_by_group_names(user.id, user_groups, db=db)
                    try:
                        await Groups.sync_groups_by_group_names(user.id, user_groups, db=db)
                        log.info(f'Successfully synced groups for user {user.id}: {user_groups}')
                    except Exception as e:
                        log.error(f'Failed to sync groups for user {user.id}: {e}')

                return await create_session_response(request, user, db, response, set_cookie=True, source='ldap')
            else:
                raise HTTPException(400, detail=ERROR_MESSAGES.INVALID_CRED)
        else:
            raise HTTPException(400, 'User record mismatch.')
    except Exception as e:
        log.error(f'LDAP authentication error: {str(e)}')
        raise HTTPException(400, detail='LDAP authentication failed.')


############################
# SignIn
############################


@router.post('/signin', response_model=SessionUserResponse)
async def signin(
    request: Request,
    response: Response,
    form_data: SigninForm,
    db: AsyncSession = Depends(get_async_session),
):
    if not ENABLE_PASSWORD_AUTH:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.ACTION_PROHIBITED,
        )

    auth_source = 'password'

    if WEBUI_AUTH_TRUSTED_EMAIL_HEADER:
        auth_source = 'trusted_header'
        if WEBUI_AUTH_TRUSTED_EMAIL_HEADER not in request.headers:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.INVALID_TRUSTED_HEADER)

        email = request.headers[WEBUI_AUTH_TRUSTED_EMAIL_HEADER].lower()
        name = email

        if WEBUI_AUTH_TRUSTED_NAME_HEADER:
            name = request.headers.get(WEBUI_AUTH_TRUSTED_NAME_HEADER, email)
            try:
                name = urllib.parse.unquote(name, encoding='utf-8')
            except Exception as e:
                pass

        if not await Users.get_user_by_email(email.lower(), db=db):
            await signup_handler(
                request,
                email,
                str(uuid.uuid4()),
                name,
                db=db,
                source='trusted_header',
            )

        user = await Auths.authenticate_user_by_email(email, db=db)
        if user:
            if WEBUI_AUTH_TRUSTED_GROUPS_HEADER:
                group_names = request.headers.get(WEBUI_AUTH_TRUSTED_GROUPS_HEADER, '').split(',')
                group_names = [name.strip() for name in group_names if name.strip()]

                if group_names:
                    await Groups.sync_groups_by_group_names(user.id, group_names, db=db)

            if WEBUI_AUTH_TRUSTED_ROLE_HEADER:
                trusted_role = request.headers.get(WEBUI_AUTH_TRUSTED_ROLE_HEADER, '').lower().strip()
                if trusted_role in {'admin', 'user', 'pending'}:
                    if user.role != trusted_role:
                        await Users.update_user_role_by_id(user.id, trusted_role, db=db)
                elif trusted_role:
                    log.warning(f'Ignoring invalid trusted role header value: {trusted_role}')

    elif WEBUI_AUTH == False:
        auth_source = 'system'
        admin_email = 'admin@localhost'
        admin_password = 'admin'

        if await Users.get_user_by_email(admin_email.lower(), db=db):
            user = await Auths.authenticate_user(
                admin_email.lower(),
                lambda pw: verify_password(admin_password, pw),
                db=db,
            )
        else:
            if await Users.has_users(db=db):
                raise HTTPException(400, detail=ERROR_MESSAGES.EXISTING_USERS)

            await signup_handler(
                request,
                admin_email,
                admin_password,
                'User',
                db=db,
                source='system',
            )

            user = await Auths.authenticate_user(
                admin_email.lower(),
                lambda pw: verify_password(admin_password, pw),
                db=db,
            )
    else:
        if signin_rate_limiter.is_limited(form_data.email.lower()):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=ERROR_MESSAGES.RATE_LIMIT_EXCEEDED,
            )

        user = await Auths.authenticate_user(
            form_data.email.lower(),
            lambda pw: verify_password(form_data.password, pw),
            db=db,
        )

    if user:
        return await create_session_response(request, user, db, response, set_cookie=True, source=auth_source)
    else:
        raise HTTPException(400, detail=ERROR_MESSAGES.INVALID_CRED)


############################
# SignUp
############################


async def signup_handler(
    request: Request,
    email: str,
    password: str,
    name: str,
    profile_image_url: str = '/user.png',
    *,
    db: AsyncSession,
    source: str = 'api',
) -> UserModel:
    """
    Core user-creation logic shared by the signup endpoint and
    trusted-header / no-auth auto-registration flows.

    Returns the newly created UserModel.
    Raises HTTPException on failure.
    """
    # Insert with default role first to avoid TOCTOU race on first signup.
    # If has_users() is checked before insert, concurrent requests during
    # first-user registration can all see an empty table and each get admin.
    hashed = await get_password_hash(password)

    user = await Auths.insert_new_auth(
        email=email.lower(),
        password=hashed,
        name=name,
        profile_image_url=profile_image_url,
        role=await Config.get('ui.default_user_role'),
        db=db,
    )
    if not user:
        raise HTTPException(500, detail=ERROR_MESSAGES.CREATE_USER_ERROR)

    # Atomically check if this is the only user *after* the insert.
    # Only the single user present at this point should become admin.
    if await Users.get_num_users(db=db) == 1:
        await Users.update_user_role_by_id(user.id, 'admin', db=db)
        user = await Users.get_user_by_id(user.id, db=db)
        await Config.upsert({'ui.enable_signup': False})

    await apply_default_group_assignment(
        await Config.get('ui.default_group_id'),
        user.id,
        db=db,
    )

    await publish_event(
        request,
        EVENTS.USER_CREATED,
        actor=user,
        subject_id=user.id,
        source=source,
        data={'role': user.role},
    )

    return user


@router.post('/signup', response_model=SessionUserResponse)
async def signup(
    request: Request,
    response: Response,
    form_data: SignupForm,
    db: AsyncSession = Depends(get_async_session),
):
    has_users = await Users.has_users(db=db)

    if WEBUI_AUTH:
        if has_users:
            if not await Config.get('ui.enable_signup') or not await Config.get('ui.enable_login_form'):
                raise HTTPException(status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.ACCESS_PROHIBITED)
        # Don't gate the first admin on ENABLE_SIGNUP: it auto-disables and can persist stale across a DB reset.
        elif not await Config.get('ui.enable_login_form') and not ENABLE_INITIAL_ADMIN_SIGNUP:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.ACCESS_PROHIBITED)
    else:
        if has_users:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.ACCESS_PROHIBITED)

    if not validate_email_format(form_data.email.lower()):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.INVALID_EMAIL_FORMAT)

    if await Users.get_user_by_email(form_data.email.lower(), db=db):
        raise HTTPException(400, detail=ERROR_MESSAGES.EMAIL_TAKEN)

    try:
        try:
            validate_password(form_data.password)
        except Exception as e:
            raise HTTPException(400, detail=str(e))

        user = await signup_handler(
            request,
            form_data.email,
            form_data.password,
            form_data.name,
            form_data.profile_image_url,
            db=db,
        )
        await publish_event(
            request,
            EVENTS.AUTH_SIGNUP,
            actor=user,
            subject_id=user.id,
            subject_type='user',
            data={'email': user.email},
        )
        return await create_session_response(request, user, db, response, set_cookie=True)
    except HTTPException:
        raise
    except Exception as err:
        log.error(f'Signup error: {str(err)}')
        raise HTTPException(500, detail='An internal error occurred during signup.')


@router.post('/signout')
async def signout(request: Request, response: Response, db: AsyncSession = Depends(get_async_session)):
    # get auth token from headers or cookies
    token = None
    auth_header = request.headers.get('Authorization')
    if auth_header:
        auth_cred = get_http_authorization_cred(auth_header)
        if auth_cred is not None:
            token = auth_cred.credentials
    if token is None:
        token = request.cookies.get('token')

    if token:
        actor = None
        data = decode_token(token)
        if data and data.get('id'):
            actor = await Users.get_user_by_id(data['id'], db=db)
        await invalidate_token(request, token)
        await publish_event(
            request,
            EVENTS.AUTH_LOGOUT,
            actor=actor,
            subject_id=actor.id if actor else None,
            subject_type='user' if actor else None,
        )

    response.delete_cookie('token')
    response.delete_cookie('oui-session')
    response.delete_cookie('oauth_id_token')

    oauth_session_id = request.cookies.get('oauth_session_id')
    if oauth_session_id:
        response.delete_cookie('oauth_session_id')

        session = await OAuthSessions.get_session_by_id(oauth_session_id, db=db)

        # If a custom end_session_endpoint is configured (e.g. AWS Cognito), redirect
        # there directly instead of attempting OIDC discovery.
        openid_end_session_endpoint = await Config.get('oauth.end_session_endpoint')
        if openid_end_session_endpoint:
            return JSONResponse(
                status_code=200,
                content={
                    'status': True,
                    'redirect_url': openid_end_session_endpoint,
                },
                headers=response.headers,
            )

        openid_provider_url = await Config.get('oauth.provider_url')
        oauth_server_metadata_url = (
            request.app.state.oauth_manager.get_server_metadata_url(session.provider) if session else None
        ) or openid_provider_url

        if session and oauth_server_metadata_url:
            oauth_id_token = session.token.get('id_token')
            try:
                async with ClientSession(trust_env=True) as session:
                    async with session.get(oauth_server_metadata_url, ssl=AIOHTTP_CLIENT_SESSION_SSL) as r:
                        if r.status == 200:
                            openid_data = await r.json()
                            logout_url = openid_data.get('end_session_endpoint')

                            if logout_url:
                                return JSONResponse(
                                    status_code=200,
                                    content={
                                        'status': True,
                                        'redirect_url': f'{logout_url}?id_token_hint={oauth_id_token}'
                                        + (
                                            f'&post_logout_redirect_uri={WEBUI_AUTH_SIGNOUT_REDIRECT_URL}'
                                            if WEBUI_AUTH_SIGNOUT_REDIRECT_URL
                                            else ''
                                        ),
                                    },
                                    headers=response.headers,
                                )
                        else:
                            raise Exception('Failed to fetch OpenID configuration')

            except Exception as e:
                log.error(f'OpenID signout error: {str(e)}')
                raise HTTPException(
                    status_code=500,
                    detail='Failed to sign out from the OpenID provider.',
                    headers=response.headers,
                )

    if WEBUI_AUTH_SIGNOUT_REDIRECT_URL:
        return JSONResponse(
            status_code=200,
            content={
                'status': True,
                'redirect_url': WEBUI_AUTH_SIGNOUT_REDIRECT_URL,
            },
            headers=response.headers,
        )

    return JSONResponse(status_code=200, content={'status': True}, headers=response.headers)


############################
# OAuth Session Management
############################


@router.delete('/oauth/sessions/{provider:path}', response_model=bool)
async def delete_oauth_session_by_provider(
    request: Request,
    provider: str,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Disconnect the current user's OAuth session for a specific provider.
    The provider string matches the 'provider' field in the oauth_session table
    (e.g. 'mcp:server-id' for MCP connections).
    """
    result = await OAuthSessions.delete_sessions_by_user_id_and_provider(user.id, provider, db=db)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='No OAuth session found for this provider',
        )
    await publish_event(
        request,
        EVENTS.AUTH_OAUTH_SESSION_DELETED,
        actor=user,
        subject_id=user.id,
        subject_type='user',
        data={'provider': provider},
    )
    return True


############################
# AddUser
############################


@router.post('/add', response_model=SigninResponse)
async def add_user(
    request: Request,
    form_data: AddUserForm,
    user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_session),
):
    admin_user = user
    if not validate_email_format(form_data.email.lower()):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.INVALID_EMAIL_FORMAT)

    if await Users.get_user_by_email(form_data.email.lower(), db=db):
        raise HTTPException(400, detail=ERROR_MESSAGES.EMAIL_TAKEN)

    try:
        try:
            validate_password(form_data.password)
        except Exception as e:
            raise HTTPException(400, detail=str(e))

        hashed = await get_password_hash(form_data.password)
        user = await Auths.insert_new_auth(
            form_data.email.lower(),
            hashed,
            form_data.name,
            form_data.profile_image_url,
            form_data.role,
            db=db,
        )

        if user:
            await apply_default_group_assignment(
                await Config.get('ui.default_group_id'),
                user.id,
                db=db,
            )
            await publish_event(
                request,
                EVENTS.USER_CREATED,
                actor=admin_user,
                subject_id=user.id,
                source='admin',
                data={'role': user.role},
            )

            expires_delta = parse_duration(await Config.get('auth.jwt_expiry'))
            token = create_token(data={'id': user.id}, expires_delta=expires_delta)
            return {
                'token': token,
                'token_type': 'Bearer',
                'id': user.id,
                'email': user.email,
                'name': user.name,
                'role': user.role,
                'profile_image_url': f'/api/v1/users/{user.id}/profile/image',
            }
        else:
            raise HTTPException(500, detail=ERROR_MESSAGES.CREATE_USER_ERROR)
    except HTTPException:
        raise
    except Exception as err:
        log.error(f'Add user error: {str(err)}')
        raise HTTPException(500, detail='An internal error occurred while adding the user.')


############################
# GetAdminDetails
############################


@router.get('/admin/details')
async def get_admin_details(
    request: Request, user=Depends(get_current_user), db: AsyncSession = Depends(get_async_session)
):
    if await Config.get('auth.admin.show'):
        admin_email = await Config.get('auth.admin.email')
        admin_name = None

        log.info(f'Admin details - Email: {admin_email}, Name: {admin_name}')

        if admin_email:
            admin = await Users.get_user_by_email(admin_email, db=db)
            if admin:
                admin_name = admin.name
        else:
            admin = await Users.get_first_user(db=db)
            if admin:
                admin_email = admin.email
                admin_name = admin.name

        return {
            'name': admin_name,
            'email': admin_email,
        }
    else:
        raise HTTPException(400, detail=ERROR_MESSAGES.ACTION_PROHIBITED)


############################
# ToggleSignUp
############################


@router.get('/admin/config')
async def get_admin_config(request: Request, user=Depends(get_admin_user)):
    return await get_config_values(ADMIN_CONFIG_KEYS)


class AdminConfig(BaseModel):
    SHOW_ADMIN_DETAILS: bool
    ADMIN_EMAIL: str | None = None
    WEBUI_URL: str
    ENABLE_SIGNUP: bool
    ENABLE_API_KEYS: bool
    ENABLE_API_KEYS_ENDPOINT_RESTRICTIONS: bool
    API_KEYS_ALLOWED_ENDPOINTS: str
    DEFAULT_USER_ROLE: str
    DEFAULT_GROUP_ID: str
    JWT_EXPIRES_IN: str
    ENABLE_COMMUNITY_SHARING: bool
    ENABLE_MESSAGE_RATING: bool
    ENABLE_FOLDERS: bool
    FOLDER_MAX_FILE_COUNT: int | str | None = None
    AUTOMATION_MAX_COUNT: int | str | None = None
    AUTOMATION_MIN_INTERVAL: int | str | None = None
    ENABLE_AUTOMATIONS: bool
    ENABLE_CHANNELS: bool
    ENABLE_CALENDAR: bool
    ENABLE_MEMORIES: bool
    ENABLE_NOTES: bool
    ENABLE_USER_WEBHOOKS: bool
    ENABLE_USER_STATUS: bool
    PENDING_USER_OVERLAY_TITLE: str | None = None
    PENDING_USER_OVERLAY_CONTENT: str | None = None
    RESPONSE_WATERMARK: str | None = None


@router.post('/admin/config')
async def update_admin_config(request: Request, form_data: AdminConfig, user=Depends(get_admin_user)):
    updates = config_updates(form_data.model_dump(), ADMIN_CONFIG_KEYS)
    updates['folders.max_file_count'] = int(form_data.FOLDER_MAX_FILE_COUNT) if form_data.FOLDER_MAX_FILE_COUNT else ''
    updates['automations.max_count'] = int(form_data.AUTOMATION_MAX_COUNT) if form_data.AUTOMATION_MAX_COUNT else ''
    updates['automations.min_interval'] = (
        int(form_data.AUTOMATION_MIN_INTERVAL) if form_data.AUTOMATION_MIN_INTERVAL else ''
    )

    if form_data.DEFAULT_USER_ROLE not in ['pending', 'user', 'admin']:
        updates.pop('ui.default_user_role', None)

    pattern = r'^(-1|0|(-?\d+(\.\d+)?)(ms|s|m|h|d|w))$'

    # Check if the input string matches the pattern
    if not re.match(pattern, form_data.JWT_EXPIRES_IN):
        updates.pop('auth.jwt_expiry', None)

    await Config.upsert(updates)
    return await get_config_values(ADMIN_CONFIG_KEYS)


class LdapServerConfig(BaseModel):
    label: str
    host: str
    port: int | None = None
    attribute_for_mail: str = 'mail'
    attribute_for_username: str = 'uid'
    app_dn: str
    app_dn_password: str
    search_base: str
    search_filters: str = ''
    use_tls: bool = True
    certificate_path: str | None = None
    validate_cert: bool = True
    ciphers: str | None = 'ALL'


@router.get('/admin/config/ldap/server', response_model=LdapServerConfig)
async def get_ldap_server(request: Request, user=Depends(get_admin_user)):
    return await get_config_values(LDAP_SERVER_CONFIG_KEYS)


@router.post('/admin/config/ldap/server')
async def update_ldap_server(request: Request, form_data: LdapServerConfig, user=Depends(get_admin_user)):
    required_fields = [
        'label',
        'host',
        'attribute_for_mail',
        'attribute_for_username',
        'search_base',
    ]
    for key in required_fields:
        value = getattr(form_data, key)
        if not value:
            raise HTTPException(400, detail=ERROR_MESSAGES.REQUIRED_FIELD_EMPTY(key))

    updates = config_updates(form_data.model_dump(), LDAP_SERVER_CONFIG_KEYS)
    updates['ldap.server.app_dn'] = form_data.app_dn or ''
    updates['ldap.server.app_password'] = form_data.app_dn_password or ''
    await Config.upsert(updates)
    return await get_config_values(LDAP_SERVER_CONFIG_KEYS)


@router.get('/admin/config/ldap')
async def get_ldap_config(request: Request, user=Depends(get_admin_user)):
    return {'ENABLE_LDAP': await Config.get('ldap.enable')}


class LdapConfigForm(BaseModel):
    enable_ldap: bool | None = None


@router.post('/admin/config/ldap')
async def update_ldap_config(request: Request, form_data: LdapConfigForm, user=Depends(get_admin_user)):
    await Config.upsert({'ldap.enable': form_data.enable_ldap})
    return {'ENABLE_LDAP': await Config.get('ldap.enable')}


############################
# API Key
############################


class OAuthConfigForm(BaseModel):
    """All OAuth/OIDC settings exposed to the admin panel."""

    # General OAuth
    ENABLE_OAUTH_SIGNUP: bool | None = None
    OAUTH_MERGE_ACCOUNTS_BY_EMAIL: bool | None = None
    OAUTH_AUTO_REDIRECT: bool | None = None
    OAUTH_ALLOWED_DOMAINS: str | None = None
    OAUTH_BLOCKED_GROUPS: str | None = None

    # Role management
    ENABLE_OAUTH_ROLE_MANAGEMENT: bool | None = None
    OAUTH_ROLES_CLAIM: str | None = None
    OAUTH_ADMIN_ROLES: str | None = None
    OAUTH_ALLOWED_ROLES: str | None = None

    # Group management
    ENABLE_OAUTH_GROUP_MANAGEMENT: bool | None = None
    ENABLE_OAUTH_GROUP_CREATION: bool | None = None
    OAUTH_GROUP_CLAIM: str | None = None
    OAUTH_GROUP_DEFAULT_SHARE: bool | str | None = None

    # OIDC provider settings
    OAUTH_PROVIDER_NAME: str | None = None
    OPENID_PROVIDER_URL: str | None = None
    OAUTH_CLIENT_ID: str | None = None
    OAUTH_CLIENT_SECRET: str | None = None
    OPENID_REDIRECT_URI: str | None = None
    OAUTH_SCOPES: str | None = None
    OAUTH_CODE_CHALLENGE_METHOD: str | None = None
    OAUTH_TOKEN_ENDPOINT_AUTH_METHOD: str | None = None
    OPENID_END_SESSION_ENDPOINT: str | None = None
    OAUTH_TIMEOUT: int | str | None = None
    OAUTH_CLIENT_TIMEOUT: int | str | None = None

    # Claims
    OAUTH_EMAIL_CLAIM: str | None = None
    OAUTH_USERNAME_CLAIM: str | None = None
    OAUTH_PICTURE_CLAIM: str | None = None
    OAUTH_SUB_CLAIM: str | None = None
    OAUTH_AUDIENCE: str | None = None

    # Profile update toggles
    OAUTH_UPDATE_EMAIL_ON_LOGIN: bool | None = None
    OAUTH_UPDATE_NAME_ON_LOGIN: bool | None = None
    OAUTH_UPDATE_PICTURE_ON_LOGIN: bool | None = None

    # Token
    OAUTH_REFRESH_TOKEN_INCLUDE_SCOPE: bool | None = None


OAUTH_COMMA_LIST_FIELDS = {
    'OAUTH_ALLOWED_DOMAINS',
    'OAUTH_ADMIN_ROLES',
    'OAUTH_ALLOWED_ROLES',
}


OAUTH_CONFIG_KEYS = {
    'ENABLE_OAUTH_SIGNUP': 'oauth.enable_signup',
    'OAUTH_MERGE_ACCOUNTS_BY_EMAIL': 'oauth.merge_accounts_by_email',
    'OAUTH_AUTO_REDIRECT': 'oauth.auto_redirect',
    'OAUTH_ALLOWED_DOMAINS': 'oauth.allowed_domains',
    'OAUTH_BLOCKED_GROUPS': 'oauth.blocked_groups',
    'ENABLE_OAUTH_ROLE_MANAGEMENT': 'oauth.enable_role_mapping',
    'OAUTH_ROLES_CLAIM': 'oauth.roles_claim',
    'OAUTH_ADMIN_ROLES': 'oauth.admin_roles',
    'OAUTH_ALLOWED_ROLES': 'oauth.allowed_roles',
    'ENABLE_OAUTH_GROUP_MANAGEMENT': 'oauth.enable_group_mapping',
    'ENABLE_OAUTH_GROUP_CREATION': 'oauth.enable_group_creation',
    'OAUTH_GROUP_CLAIM': 'oauth.group_claim',
    'OAUTH_GROUP_DEFAULT_SHARE': 'oauth.group_default_share',
    'OAUTH_PROVIDER_NAME': 'oauth.provider_name',
    'OPENID_PROVIDER_URL': 'oauth.provider_url',
    'OAUTH_CLIENT_ID': 'oauth.client_id',
    'OAUTH_CLIENT_SECRET': 'oauth.client_secret',
    'OPENID_REDIRECT_URI': 'oauth.redirect_uri',
    'OAUTH_SCOPES': 'oauth.scopes',
    'OAUTH_CODE_CHALLENGE_METHOD': 'oauth.code_challenge_method',
    'OAUTH_TOKEN_ENDPOINT_AUTH_METHOD': 'oauth.token_endpoint_auth_method',
    'OPENID_END_SESSION_ENDPOINT': 'oauth.end_session_endpoint',
    'OAUTH_TIMEOUT': 'oauth.timeout',
    'OAUTH_CLIENT_TIMEOUT': 'oauth.client.timeout',
    'OAUTH_EMAIL_CLAIM': 'oauth.email_claim',
    'OAUTH_USERNAME_CLAIM': 'oauth.username_claim',
    'OAUTH_PICTURE_CLAIM': 'oauth.picture_claim',
    'OAUTH_SUB_CLAIM': 'oauth.sub_claim',
    'OAUTH_AUDIENCE': 'oauth.audience',
    'OAUTH_UPDATE_EMAIL_ON_LOGIN': 'oauth.update_email_on_login',
    'OAUTH_UPDATE_NAME_ON_LOGIN': 'oauth.update_name_on_login',
    'OAUTH_UPDATE_PICTURE_ON_LOGIN': 'oauth.update_picture_on_login',
    'OAUTH_REFRESH_TOKEN_INCLUDE_SCOPE': 'oauth.refresh_token.include_scope',
}


def _format_oauth_form_value(field: str, value):
    if field in OAUTH_COMMA_LIST_FIELDS and isinstance(value, list):
        return ','.join(str(item) for item in value)
    return value


def _parse_oauth_update_value(field: str, value):
    if field in OAUTH_COMMA_LIST_FIELDS and isinstance(value, str):
        return [item.strip() for item in value.split(',') if item.strip()]
    if field in {'OAUTH_TIMEOUT', 'OAUTH_CLIENT_TIMEOUT'} and value == '':
        return ''
    return value


async def get_oauth_config_values() -> dict:
    values = await Config.get_many(*OAUTH_CONFIG_KEYS.values())
    return {
        field: _format_oauth_form_value(field, values[storage_key])
        for field, storage_key in OAUTH_CONFIG_KEYS.items()
        if storage_key in values
    }


def oauth_config_updates(data: dict) -> dict:
    return {
        OAUTH_CONFIG_KEYS[field]: _parse_oauth_update_value(field, value)
        for field, value in data.items()
        if field in OAUTH_CONFIG_KEYS
    }


@router.get('/admin/config/oauth', response_model=OAuthConfigForm)
async def get_oauth_config(request: Request, user=Depends(get_admin_user)):
    return await get_oauth_config_values()


@router.post('/admin/config/oauth', response_model=OAuthConfigForm)
async def update_oauth_config(request: Request, form_data: OAuthConfigForm, user=Depends(get_admin_user)):
    await Config.upsert(oauth_config_updates(form_data.model_dump(exclude_none=True)))
    return await get_oauth_config_values()


async def _check_api_key_permission(request: Request, user, db: AsyncSession):
    if not await Config.get('auth.enable_api_keys') or (
        user.role != 'admin'
        and not await has_permission(user.id, 'features.api_keys', await Config.get('user.permissions'), db=db)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.API_KEY_CREATION_NOT_ALLOWED,
        )


# create api key
@router.post('/api_key', response_model=ApiKey)
async def generate_api_key(
    request: Request, user=Depends(get_current_user), db: AsyncSession = Depends(get_async_session)
):
    await _check_api_key_permission(request, user, db)

    api_key = create_api_key()
    success = await Users.update_user_api_key_by_id(user.id, api_key, db=db)

    if success:
        await publish_event(
            request,
            EVENTS.AUTH_API_KEY_CREATED,
            actor=user,
            subject_id=user.id,
            subject_type='user',
        )
        return {
            'api_key': api_key,
        }
    else:
        raise HTTPException(500, detail=ERROR_MESSAGES.CREATE_API_KEY_ERROR)


# delete api key
@router.delete('/api_key', response_model=bool)
async def delete_api_key(
    request: Request, user=Depends(get_current_user), db: AsyncSession = Depends(get_async_session)
):
    await _check_api_key_permission(request, user, db)
    success = await Users.delete_user_api_key_by_id(user.id, db=db)
    if success:
        await publish_event(
            request,
            EVENTS.AUTH_API_KEY_DELETED,
            actor=user,
            subject_id=user.id,
            subject_type='user',
        )
    return success


# get api key
@router.get('/api_key', response_model=ApiKey)
async def get_api_key(request: Request, user=Depends(get_current_user), db: AsyncSession = Depends(get_async_session)):
    await _check_api_key_permission(request, user, db)
    api_key = await Users.get_user_api_key_by_id(user.id, db=db)
    if api_key:
        return {
            'api_key': api_key,
        }
    else:
        raise HTTPException(404, detail=ERROR_MESSAGES.API_KEY_NOT_FOUND)


############################
# Token Exchange
############################


class TokenExchangeForm(BaseModel):
    token: str  # OAuth access token from external provider


@router.post('/oauth/{provider}/token/exchange', response_model=SessionUserResponse)
async def token_exchange(
    request: Request,
    response: Response,
    provider: str,
    form_data: TokenExchangeForm,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Exchange an external OAuth provider token for an OpenWebUI JWT.
    This endpoint is disabled by default. Set ENABLE_OAUTH_TOKEN_EXCHANGE=True to enable.
    """
    if not ENABLE_OAUTH_TOKEN_EXCHANGE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Token exchange is disabled',
        )

    provider = provider.lower()

    # Check if provider is configured
    if provider not in OAUTH_PROVIDERS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.OAUTH_NOT_CONFIGURED(provider),
        )
    # Get the OAuth client for this provider
    oauth_manager = request.app.state.oauth_manager
    client = oauth_manager.get_client(provider)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.OAUTH_NOT_CONFIGURED(provider),
        )

    # Validate the token by calling the userinfo endpoint
    try:
        token_data = {'access_token': form_data.token, 'token_type': 'Bearer'}
        user_data = await client.userinfo(token=token_data)

        if not user_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Invalid token or unable to fetch user info',
            )
    except Exception as e:
        log.warning(f'Token exchange failed for provider {provider}: {e}')
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Invalid token or unable to validate with provider',
        )

    # Extract user information from the token claims
    email_claim = await Config.get('oauth.email_claim', 'email')

    # Get sub claim
    sub_claim = await Config.get('oauth.sub_claim')
    sub = user_data.get(sub_claim or OAUTH_PROVIDERS[provider].get('sub_claim', 'sub'))
    if not sub:
        log.warning(f'Token exchange failed: sub claim missing from user data')
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token missing required 'sub' claim",
        )

    email = user_data.get(email_claim, '')
    if not email:
        log.warning(f'Token exchange failed: email claim missing from user data')
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Token missing required email claim',
        )
    email = email.lower()

    # Enforce domain allowlist — same check as the normal OAuth callback
    oauth_allowed_domains = await Config.get('oauth.allowed_domains', [])
    if isinstance(oauth_allowed_domains, str):
        oauth_allowed_domains = [domain.strip() for domain in oauth_allowed_domains.split(',') if domain.strip()]
    if '*' not in oauth_allowed_domains and email.split('@')[-1] not in oauth_allowed_domains:
        log.warning(f'Token exchange denied: email domain not in allowed domains list')
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    # Try to find the user by OAuth sub
    user = await Users.get_user_by_oauth_sub(provider, sub, db=db)

    if not user and await Config.get('oauth.merge_accounts_by_email'):
        # Try to find by email if merge is enabled
        user = await Users.get_user_by_email(email, db=db)
        if user:
            # Link the OAuth sub to this user
            await Users.update_user_oauth_by_id(user.id, provider, sub, db=db)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='User not found. Please sign in via the web interface first.',
        )

    return await create_session_response(request, user, db, source='oauth')
