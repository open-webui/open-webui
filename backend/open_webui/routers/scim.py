"""
Experimental SCIM 2.0 Implementation for Open WebUI
Provides System for Cross-domain Identity Management endpoints for users and groups

NOTE: This is an experimental implementation and may not fully comply with SCIM 2.0 standards, and is subject to change.
"""

import logging
import uuid
import time
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Query, Header, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, ConfigDict

from open_webui.models.users import Users, UserModel
from open_webui.models.groups import Groups, GroupModel
from open_webui.utils.auth import (
    get_admin_user,
    get_current_user,
    decode_token,
    get_verified_user,
)
from open_webui.constants import ERROR_MESSAGES

from open_webui.config import OAUTH_PROVIDERS
from open_webui.env import SCIM_AUTH_PROVIDER


from sqlalchemy.orm import Session
from open_webui.internal.db import get_session

log = logging.getLogger(__name__)

router = APIRouter()

# SCIM 2.0 Schema URIs
SCIM_USER_SCHEMA = "urn:ietf:params:scim:schemas:core:2.0:User"
SCIM_GROUP_SCHEMA = "urn:ietf:params:scim:schemas:core:2.0:Group"
SCIM_LIST_RESPONSE_SCHEMA = "urn:ietf:params:scim:api:messages:2.0:ListResponse"
SCIM_ERROR_SCHEMA = "urn:ietf:params:scim:api:messages:2.0:Error"

# SCIM Resource Types
SCIM_RESOURCE_TYPE_USER = "User"
SCIM_RESOURCE_TYPE_GROUP = "Group"


def scim_error(status_code: int, detail: str, scim_type: Optional[str] = None):
    """Create a SCIM-compliant error response"""
    error_body = {
        "schemas": [SCIM_ERROR_SCHEMA],
        "status": str(status_code),
        "detail": detail,
    }

    if scim_type:
        error_body["scimType"] = scim_type
    elif status_code == 404:
        error_body["scimType"] = "invalidValue"
    elif status_code == 409:
        error_body["scimType"] = "uniqueness"
    elif status_code == 400:
        error_body["scimType"] = "invalidSyntax"

    return JSONResponse(status_code=status_code, content=error_body)


class SCIMError(BaseModel):
    """SCIM Error Response"""

    schemas: List[str] = [SCIM_ERROR_SCHEMA]
    status: str
    scimType: Optional[str] = None
    detail: Optional[str] = None


class SCIMMeta(BaseModel):
    """SCIM Resource Metadata"""

    resourceType: str
    created: str
    lastModified: str
    location: Optional[str] = None
    version: Optional[str] = None


class SCIMName(BaseModel):
    """SCIM User Name"""

    formatted: Optional[str] = None
    familyName: Optional[str] = None
    givenName: Optional[str] = None
    middleName: Optional[str] = None
    honorificPrefix: Optional[str] = None
    honorificSuffix: Optional[str] = None


class SCIMEmail(BaseModel):
    """SCIM Email"""

    value: str
    type: Optional[str] = "work"
    primary: bool = True
    display: Optional[str] = None


class SCIMPhoto(BaseModel):
    """SCIM Photo"""

    value: str
    type: Optional[str] = "photo"
    primary: bool = True
    display: Optional[str] = None


class SCIMGroupMember(BaseModel):
    """SCIM Group Member"""

    value: str  # User ID
    ref: Optional[str] = Field(None, alias="$ref")
    type: Optional[str] = "User"
    display: Optional[str] = None


class SCIMUser(BaseModel):
    """SCIM User Resource"""

    model_config = ConfigDict(populate_by_name=True)

    schemas: List[str] = [SCIM_USER_SCHEMA]
    id: str
    externalId: Optional[str] = None
    userName: str
    name: Optional[SCIMName] = None
    displayName: str
    emails: List[SCIMEmail]
    active: bool = True
    photos: Optional[List[SCIMPhoto]] = None
    groups: Optional[List[Dict[str, str]]] = None
    meta: SCIMMeta


class SCIMUserCreateRequest(BaseModel):
    """SCIM User Create Request"""

    model_config = ConfigDict(populate_by_name=True)

    schemas: List[str] = [SCIM_USER_SCHEMA]
    externalId: Optional[str] = None
    userName: str
    name: Optional[SCIMName] = None
    displayName: str
    emails: List[SCIMEmail]
    active: bool = True
    password: Optional[str] = None
    photos: Optional[List[SCIMPhoto]] = None


class SCIMUserUpdateRequest(BaseModel):
    """SCIM User Update Request"""

    model_config = ConfigDict(populate_by_name=True)

    schemas: List[str] = [SCIM_USER_SCHEMA]
    id: Optional[str] = None
    externalId: Optional[str] = None
    userName: Optional[str] = None
    name: Optional[SCIMName] = None
    displayName: Optional[str] = None
    emails: Optional[List[SCIMEmail]] = None
    active: Optional[bool] = None
    photos: Optional[List[SCIMPhoto]] = None


class SCIMGroup(BaseModel):
    """SCIM Group Resource"""

    model_config = ConfigDict(populate_by_name=True)

    schemas: List[str] = [SCIM_GROUP_SCHEMA]
    id: str
    displayName: str
    members: Optional[List[SCIMGroupMember]] = []
    meta: SCIMMeta


class SCIMGroupCreateRequest(BaseModel):
    """SCIM Group Create Request"""

    model_config = ConfigDict(populate_by_name=True)

    schemas: List[str] = [SCIM_GROUP_SCHEMA]
    displayName: str
    members: Optional[List[SCIMGroupMember]] = []


class SCIMGroupUpdateRequest(BaseModel):
    """SCIM Group Update Request"""

    model_config = ConfigDict(populate_by_name=True)

    schemas: List[str] = [SCIM_GROUP_SCHEMA]
    displayName: Optional[str] = None
    members: Optional[List[SCIMGroupMember]] = None


class SCIMListResponse(BaseModel):
    """SCIM List Response"""

    schemas: List[str] = [SCIM_LIST_RESPONSE_SCHEMA]
    totalResults: int
    itemsPerPage: int
    startIndex: int
    Resources: List[Any]


class SCIMPatchOperation(BaseModel):
    """SCIM Patch Operation"""

    op: str  # "add", "replace", "remove"
    path: Optional[str] = None
    value: Optional[Any] = None


class SCIMPatchRequest(BaseModel):
    """SCIM Patch Request"""

    schemas: List[str] = ["urn:ietf:params:scim:api:messages:2.0:PatchOp"]
    Operations: List[SCIMPatchOperation]


def get_scim_auth(
    request: Request, authorization: Optional[str] = Header(None)
) -> bool:
    """
    Verify SCIM authentication
    Checks for SCIM-specific bearer token configured in the system
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        parts = authorization.split()
        if len(parts) != 2:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization format. Expected: Bearer <token>",
            )

        scheme, token = parts
        if scheme.lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication scheme",
            )

        # Check if SCIM is enabled
        enable_scim = getattr(request.app.state, "ENABLE_SCIM", False)
        log.info(
            f"SCIM auth check - raw ENABLE_SCIM: {enable_scim}, type: {type(enable_scim)}"
        )

        # Handle both PersistentConfig and direct value
        if hasattr(enable_scim, "value"):
            enable_scim = enable_scim.value

        if not enable_scim:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="SCIM is not enabled",
            )

        # Verify the SCIM token
        scim_token = getattr(request.app.state, "SCIM_TOKEN", None)
        # Handle both PersistentConfig and direct value
        if hasattr(scim_token, "value"):
            scim_token = scim_token.value
        log.debug(f"SCIM token configured: {bool(scim_token)}")
        if not scim_token or token != scim_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid SCIM token",
            )

        return True
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        log.error(f"SCIM authentication error: {e}")
        import traceback

        log.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
        )


def get_external_id(user: UserModel) -> Optional[str]:
    """Extract externalId from a user's scim data.

    Checks all stored provider entries and returns the first external_id found.
    """
    if not user.scim:
        return None
    for provider_data in user.scim.values():
        if isinstance(provider_data, dict) and "external_id" in provider_data:
            return provider_data["external_id"]
    return None


def get_scim_provider() -> str:
    """Return the configured SCIM auth provider.

    Requires SCIM_AUTH_PROVIDER env var to be set (e.g. 'microsoft', 'oidc').
    """
    if not SCIM_AUTH_PROVIDER:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="SCIM_AUTH_PROVIDER environment variable is required when SCIM is enabled",
        )
    return SCIM_AUTH_PROVIDER


def find_user_by_external_id(external_id: str, db=None) -> Optional[UserModel]:
    """Find a user by SCIM externalId, falling back to OAuth sub match."""
    provider = get_scim_provider()
    user = Users.get_user_by_scim_external_id(provider, external_id, db=db)
    if user:
        return user

    # Fallback: check if externalId matches an existing OAuth sub (account linking)
    return Users.get_user_by_oauth_sub(provider, external_id, db=db)


def user_to_scim(user: UserModel, request: Request, db=None) -> SCIMUser:
    """Convert internal User model to SCIM User"""
    # Parse display name into name components
    name_parts = user.name.split(" ", 1) if user.name else ["", ""]
    given_name = name_parts[0] if name_parts else ""
    family_name = name_parts[1] if len(name_parts) > 1 else ""

    # Get user's groups
    user_groups = Groups.get_groups_by_member_id(user.id, db=db)
    groups = [
        {
            "value": group.id,
            "display": group.name,
            "$ref": f"{request.base_url}api/v1/scim/v2/Groups/{group.id}",
            "type": "direct",
        }
        for group in user_groups
    ]

    return SCIMUser(
        id=user.id,
        externalId=get_external_id(user),
        userName=user.email,
        name=SCIMName(
            formatted=user.name,
            givenName=given_name,
            familyName=family_name,
        ),
        displayName=user.name,
        emails=[SCIMEmail(value=user.email)],
        active=user.role != "pending",
        photos=(
            [SCIMPhoto(value=user.profile_image_url)]
            if user.profile_image_url
            else None
        ),
        groups=groups if groups else None,
        meta=SCIMMeta(
            resourceType=SCIM_RESOURCE_TYPE_USER,
            created=datetime.fromtimestamp(
                user.created_at, tz=timezone.utc
            ).isoformat(),
            lastModified=datetime.fromtimestamp(
                user.updated_at, tz=timezone.utc
            ).isoformat(),
            location=f"{request.base_url}api/v1/scim/v2/Users/{user.id}",
        ),
    )


def group_to_scim(group: GroupModel, request: Request, db=None) -> SCIMGroup:
    """Convert internal Group model to SCIM Group"""
    member_ids = Groups.get_group_user_ids_by_id(group.id, db) or []

    # Batch-fetch all users to avoid N+1 queries
    users = Users.get_users_by_user_ids(member_ids, db=db) if member_ids else []
    members = [
        SCIMGroupMember(
            value=user.id,
            ref=f"{request.base_url}api/v1/scim/v2/Users/{user.id}",
            display=user.name,
        )
        for user in users
    ]

    return SCIMGroup(
        id=group.id,
        displayName=group.name,
        members=members,
        meta=SCIMMeta(
            resourceType=SCIM_RESOURCE_TYPE_GROUP,
            created=datetime.fromtimestamp(
                group.created_at, tz=timezone.utc
            ).isoformat(),
            lastModified=datetime.fromtimestamp(
                group.updated_at, tz=timezone.utc
            ).isoformat(),
            location=f"{request.base_url}api/v1/scim/v2/Groups/{group.id}",
        ),
    )


# SCIM Service Provider Config
@router.get("/ServiceProviderConfig")
async def get_service_provider_config():
    """Get SCIM Service Provider Configuration"""
    return {
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:ServiceProviderConfig"],
        "patch": {"supported": True},
        "bulk": {"supported": False, "maxOperations": 1000, "maxPayloadSize": 1048576},
        "filter": {"supported": True, "maxResults": 200},
        "changePassword": {"supported": False},
        "sort": {"supported": False},
        "etag": {"supported": False},
        "authenticationSchemes": [
            {
                "type": "oauthbearertoken",
                "name": "OAuth Bearer Token",
                "description": "Authentication using OAuth 2.0 Bearer Token",
            }
        ],
    }


# SCIM Resource Types
@router.get("/ResourceTypes")
async def get_resource_types(request: Request):
    """Get SCIM Resource Types"""
    return [
        {
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:ResourceType"],
            "id": "User",
            "name": "User",
            "endpoint": "/Users",
            "schema": SCIM_USER_SCHEMA,
            "meta": {
                "location": f"{request.base_url}api/v1/scim/v2/ResourceTypes/User",
                "resourceType": "ResourceType",
            },
        },
        {
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:ResourceType"],
            "id": "Group",
            "name": "Group",
            "endpoint": "/Groups",
            "schema": SCIM_GROUP_SCHEMA,
            "meta": {
                "location": f"{request.base_url}api/v1/scim/v2/ResourceTypes/Group",
                "resourceType": "ResourceType",
            },
        },
    ]


# SCIM Schemas
@router.get("/Schemas")
async def get_schemas():
    """Get SCIM Schemas"""
    return [
        {
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:Schema"],
            "id": SCIM_USER_SCHEMA,
            "name": "User",
            "description": "User Account",
            "attributes": [
                {
                    "name": "userName",
                    "type": "string",
                    "required": True,
                    "uniqueness": "server",
                },
                {"name": "displayName", "type": "string", "required": True},
                {
                    "name": "emails",
                    "type": "complex",
                    "multiValued": True,
                    "required": True,
                },
                {"name": "active", "type": "boolean", "required": False},
            ],
        },
        {
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:Schema"],
            "id": SCIM_GROUP_SCHEMA,
            "name": "Group",
            "description": "Group",
            "attributes": [
                {"name": "displayName", "type": "string", "required": True},
                {
                    "name": "members",
                    "type": "complex",
                    "multiValued": True,
                    "required": False,
                },
            ],
        },
    ]


# Users endpoints
@router.get("/Users", response_model=SCIMListResponse)
async def get_users(
    request: Request,
    startIndex: int = Query(1, ge=1),
    count: int = Query(20, ge=1, le=100),
    filter: Optional[str] = None,
    _: bool = Depends(get_scim_auth),
    db: Session = Depends(get_session),
):
    """List SCIM Users"""
    skip = startIndex - 1
    limit = count

    # Get users from database
    if filter:
        # Simple filter parsing - supports userName eq, externalId eq
        if "userName eq" in filter:
            email = filter.split('"')[1]
            user = Users.get_user_by_email(email, db=db)
            users_list = [user] if user else []
            total = 1 if user else 0
        elif "externalId eq" in filter:
            external_id = filter.split('"')[1]
            user = find_user_by_external_id(external_id, db=db)
            users_list = [user] if user else []
            total = 1 if user else 0
        else:
            response = Users.get_users(skip=skip, limit=limit, db=db)
            users_list = response["users"]
            total = response["total"]
    else:
        response = Users.get_users(skip=skip, limit=limit, db=db)
        users_list = response["users"]
        total = response["total"]

    # Convert to SCIM format
    scim_users = [user_to_scim(user, request, db=db) for user in users_list]

    return SCIMListResponse(
        totalResults=total,
        itemsPerPage=len(scim_users),
        startIndex=startIndex,
        Resources=scim_users,
    )


@router.get("/Users/{user_id}", response_model=SCIMUser)
async def get_user(
    user_id: str,
    request: Request,
    _: bool = Depends(get_scim_auth),
    db: Session = Depends(get_session),
):
    """Get SCIM User by ID"""
    user = Users.get_user_by_id(user_id, db=db)
    if not user:
        return scim_error(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"User {user_id} not found"
        )

    return user_to_scim(user, request, db=db)


@router.post("/Users", response_model=SCIMUser, status_code=status.HTTP_201_CREATED)
async def create_user(
    request: Request,
    user_data: SCIMUserCreateRequest,
    _: bool = Depends(get_scim_auth),
    db: Session = Depends(get_session),
):
    """Create SCIM User"""
    # Check for duplicate by externalId
    if user_data.externalId:
        existing_user = find_user_by_external_id(user_data.externalId, db=db)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"User with externalId {user_data.externalId} already exists",
            )

    # Determine primary email (lowercased per RFC 5321)
    email = user_data.userName
    for entry in user_data.emails:
        if entry.primary:
            email = entry.value
            break
    email = email.lower()

    # Check for duplicate by email
    existing_user = Users.get_user_by_email(email, db=db)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User with email {email} already exists",
        )

    # Create user
    user_id = str(uuid.uuid4())

    # Parse name if provided
    name = user_data.displayName
    if user_data.name:
        if user_data.name.formatted:
            name = user_data.name.formatted
        elif user_data.name.givenName or user_data.name.familyName:
            name = f"{user_data.name.givenName or ''} {user_data.name.familyName or ''}".strip()

    # Get profile image if provided
    profile_image = "/user.png"
    if user_data.photos and len(user_data.photos) > 0:
        profile_image = user_data.photos[0].value

    new_user = Users.insert_new_user(
        id=user_id,
        name=name,
        email=email,
        profile_image_url=profile_image,
        role="user" if user_data.active else "pending",
        db=db,
    )

    if not new_user:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user",
        )

    # Store externalId in the scim field
    if user_data.externalId:
        provider = get_scim_provider()
        Users.update_user_scim_by_id(user_id, provider, user_data.externalId, db=db)
        new_user = Users.get_user_by_id(user_id, db=db)

    return user_to_scim(new_user, request, db=db)


@router.put("/Users/{user_id}", response_model=SCIMUser)
async def update_user(
    user_id: str,
    request: Request,
    user_data: SCIMUserUpdateRequest,
    _: bool = Depends(get_scim_auth),
    db: Session = Depends(get_session),
):
    """Update SCIM User (full update)"""
    user = Users.get_user_by_id(user_id, db=db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found",
        )

    # Build update dict
    update_data = {}

    if user_data.userName:
        update_data["email"] = user_data.userName

    if user_data.displayName:
        update_data["name"] = user_data.displayName
    elif user_data.name:
        if user_data.name.formatted:
            update_data["name"] = user_data.name.formatted
        elif user_data.name.givenName or user_data.name.familyName:
            update_data["name"] = (
                f"{user_data.name.givenName or ''} {user_data.name.familyName or ''}".strip()
            )

    if user_data.emails and len(user_data.emails) > 0:
        update_data["email"] = user_data.emails[0].value

    if user_data.active is not None:
        update_data["role"] = "user" if user_data.active else "pending"

    if user_data.photos and len(user_data.photos) > 0:
        update_data["profile_image_url"] = user_data.photos[0].value

    updated_user = Users.update_user_by_id(user_id, update_data, db=db)
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user",
        )

    # Update externalId in the scim field
    if user_data.externalId:
        provider = get_scim_provider()
        Users.update_user_scim_by_id(user_id, provider, user_data.externalId, db=db)
        updated_user = Users.get_user_by_id(user_id, db=db)

    return user_to_scim(updated_user, request, db=db)


@router.patch("/Users/{user_id}", response_model=SCIMUser)
async def patch_user(
    user_id: str,
    request: Request,
    patch_data: SCIMPatchRequest,
    _: bool = Depends(get_scim_auth),
    db: Session = Depends(get_session),
):
    """Update SCIM User (partial update)"""
    user = Users.get_user_by_id(user_id, db=db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found",
        )

    update_data = {}

    for operation in patch_data.Operations:
        op = operation.op.lower()
        path = operation.path
        value = operation.value

        if op == "replace":
            if path == "active":
                update_data["role"] = "user" if value else "pending"
            elif path == "userName":
                update_data["email"] = value
            elif path == "displayName":
                update_data["name"] = value
            elif path == "emails[primary eq true].value":
                update_data["email"] = value
            elif path == "name.formatted":
                update_data["name"] = value
            elif path == "externalId":
                provider = get_scim_provider()
                Users.update_user_scim_by_id(user_id, provider, value, db=db)

    # Update user
    if update_data:
        updated_user = Users.update_user_by_id(user_id, update_data, db=db)
        if not updated_user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update user",
            )
    else:
        updated_user = user

    return user_to_scim(updated_user, request, db=db)


@router.delete("/Users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str,
    request: Request,
    _: bool = Depends(get_scim_auth),
    db: Session = Depends(get_session),
):
    """Delete SCIM User"""
    user = Users.get_user_by_id(user_id, db=db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found",
        )

    success = Users.delete_user_by_id(user_id, db=db)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete user",
        )

    return None


# Groups endpoints
@router.get("/Groups", response_model=SCIMListResponse)
async def get_groups(
    request: Request,
    startIndex: int = Query(1, ge=1),
    count: int = Query(20, ge=1, le=100),
    filter: Optional[str] = None,
    _: bool = Depends(get_scim_auth),
    db: Session = Depends(get_session),
):
    """List SCIM Groups"""
    # Get all groups
    groups_list = Groups.get_all_groups(db=db)

    # Apply pagination
    total = len(groups_list)
    start = startIndex - 1
    end = start + count
    paginated_groups = groups_list[start:end]

    # Convert to SCIM format
    scim_groups = [group_to_scim(group, request, db=db) for group in paginated_groups]

    return SCIMListResponse(
        totalResults=total,
        itemsPerPage=len(scim_groups),
        startIndex=startIndex,
        Resources=scim_groups,
    )


@router.get("/Groups/{group_id}", response_model=SCIMGroup)
async def get_group(
    group_id: str,
    request: Request,
    _: bool = Depends(get_scim_auth),
    db: Session = Depends(get_session),
):
    """Get SCIM Group by ID"""
    group = Groups.get_group_by_id(group_id, db=db)
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Group {group_id} not found",
        )

    return group_to_scim(group, request, db=db)


@router.post("/Groups", response_model=SCIMGroup, status_code=status.HTTP_201_CREATED)
async def create_group(
    request: Request,
    group_data: SCIMGroupCreateRequest,
    _: bool = Depends(get_scim_auth),
    db: Session = Depends(get_session),
):
    """Create SCIM Group"""
    # Extract member IDs
    member_ids = []
    if group_data.members:
        for member in group_data.members:
            member_ids.append(member.value)

    # Create group
    from open_webui.models.groups import GroupForm

    form = GroupForm(
        name=group_data.displayName,
        description="",
    )

    # Need to get the creating user's ID - we'll use the first admin
    admin_user = Users.get_super_admin_user(db=db)
    if not admin_user:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No admin user found",
        )

    new_group = Groups.insert_new_group(admin_user.id, form, db=db)
    if not new_group:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create group",
        )

    # Add members if provided
    if member_ids:
        from open_webui.models.groups import GroupUpdateForm

        update_form = GroupUpdateForm(
            name=new_group.name,
            description=new_group.description,
        )

        Groups.update_group_by_id(new_group.id, update_form, db=db)
        Groups.set_group_user_ids_by_id(new_group.id, member_ids, db=db)

        new_group = Groups.get_group_by_id(new_group.id, db=db)

    return group_to_scim(new_group, request, db=db)


@router.put("/Groups/{group_id}", response_model=SCIMGroup)
async def update_group(
    group_id: str,
    request: Request,
    group_data: SCIMGroupUpdateRequest,
    _: bool = Depends(get_scim_auth),
    db: Session = Depends(get_session),
):
    """Update SCIM Group (full update)"""
    group = Groups.get_group_by_id(group_id, db=db)
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Group {group_id} not found",
        )

    # Build update form
    from open_webui.models.groups import GroupUpdateForm

    update_form = GroupUpdateForm(
        name=group_data.displayName if group_data.displayName else group.name,
        description=group.description,
    )

    # Handle members if provided
    if group_data.members is not None:
        member_ids = [member.value for member in group_data.members]
        Groups.set_group_user_ids_by_id(group_id, member_ids, db=db)

    # Update group
    updated_group = Groups.update_group_by_id(group_id, update_form, db=db)
    if not updated_group:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update group",
        )

    return group_to_scim(updated_group, request, db=db)


@router.patch("/Groups/{group_id}", response_model=SCIMGroup)
async def patch_group(
    group_id: str,
    request: Request,
    patch_data: SCIMPatchRequest,
    _: bool = Depends(get_scim_auth),
    db: Session = Depends(get_session),
):
    """Update SCIM Group (partial update)"""
    group = Groups.get_group_by_id(group_id, db=db)
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Group {group_id} not found",
        )

    from open_webui.models.groups import GroupUpdateForm

    update_form = GroupUpdateForm(
        name=group.name,
        description=group.description,
    )

    for operation in patch_data.Operations:
        op = operation.op.lower()
        path = operation.path
        value = operation.value

        if op == "replace":
            if path == "displayName":
                update_form.name = value
            elif path == "members":
                # Replace all members
                Groups.set_group_user_ids_by_id(
                    group_id, [member["value"] for member in value], db=db
                )

        elif op == "add":
            if path == "members":
                # Add members
                if isinstance(value, list):
                    for member in value:
                        if isinstance(member, dict) and "value" in member:
                            Groups.add_users_to_group(
                                group_id, [member["value"]], db=db
                            )
        elif op == "remove":
            if path and path.startswith("members[value eq"):
                # Remove specific member
                member_id = path.split('"')[1]
                Groups.remove_users_from_group(group_id, [member_id], db=db)

    # Update group
    updated_group = Groups.update_group_by_id(group_id, update_form, db=db)
    if not updated_group:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update group",
        )

    return group_to_scim(updated_group, request, db=db)


@router.delete("/Groups/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_group(
    group_id: str,
    request: Request,
    _: bool = Depends(get_scim_auth),
    db: Session = Depends(get_session),
):
    """Delete SCIM Group"""
    group = Groups.get_group_by_id(group_id, db=db)
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Group {group_id} not found",
        )

    success = Groups.delete_group_by_id(group_id, db=db)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete group",
        )

    return None
