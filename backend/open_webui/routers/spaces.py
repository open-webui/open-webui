"""
Spaces Router - CRUD API for Perplexity-style Spaces feature.

Spaces combine:
- Custom instructions (system prompt)
- Knowledge bases (RAG)
- Model preferences
- Sharing/access control
"""

import time
from typing import Optional, List
from pydantic import BaseModel
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File as FastAPIFile,
    HTTPException,
    Request,
    UploadFile,
    status,
)
import logging

from sqlalchemy.orm import Session
from open_webui.internal.db import get_session
from open_webui.models.groups import Groups
from open_webui.models.spaces import (
    Spaces,
    SpaceForm,
    SpaceUpdateForm,
    SpaceInviteForm,
    SpaceInviteResponseForm,
    SpaceAccessLevelForm,
    SpaceLinkForm,
    SpaceLinkModel,
    SpaceModel,
    SpaceResponse,
    SpaceContributor,
    SpaceContributorResponse,
    SpacePermission,
    SpaceAccessLevel,
    SpaceBookmarkModel,
    SpaceBookmarkForm,
    SpacePinModel,
    SpacePinForm,
    SpaceCloneForm,
    SpaceSubscriptionModel,
    SpaceNotificationModel,
)
from open_webui.models.chats import Chats, Chat as ChatRecord
from open_webui.models.knowledge import Knowledges
from open_webui.models.users import Users
from open_webui.models.files import FileModelResponse
from open_webui.routers.files import upload_file_handler
from open_webui.routers.retrieval import ProcessFileForm, process_file

from open_webui.constants import ERROR_MESSAGES
from open_webui.utils.auth import get_verified_user
from open_webui.utils.access_control import (
    has_access,
    has_permission,
    can_bypass_access_control,
    can_manage_all,
)

from open_webui.config import BYPASS_ADMIN_ACCESS_CONTROL, ENABLE_SHAREPOINT_INTEGRATION


log = logging.getLogger(__name__)

router = APIRouter()


def is_space_contributor(user_email: str, space_id: str, db: Session) -> bool:
    """Check if a user is an accepted or pending contributor of a space."""
    contributor = (
        db.query(SpaceContributor)
        .filter_by(space_id=space_id, email=user_email)
        .first()
    )
    return contributor is not None


############################
# Pydantic Response Models
############################


class SpaceAccessResponse(SpaceResponse):
    """Space response with write_access indicator."""

    write_access: Optional[bool] = False


class SharePointFileRequest(BaseModel):
    """Request to add a SharePoint file to a space."""

    drive_id: str
    item_id: str
    filename: Optional[str] = None
    tenant_id: Optional[str] = None  # Optional tenant ID for multi-tenant

class SharePointFolderRequest(BaseModel):
    """Request to import all files from a SharePoint folder to a space."""

    drive_id: str
    folder_id: Optional[str] = None  # SharePoint folder ID (None for root)
    folder_name: Optional[str] = (
        None  # Display name of the folder/drive (for UI grouping)
    )
    site_name: Optional[str] = None  # Display name of the SharePoint site
    recursive: bool = True  # Whether to traverse subfolders
    max_depth: int = 10  # Maximum folder depth to traverse (1-20)
    tenant_id: Optional[str] = None  # Optional tenant ID for multi-tenant


class SharePointFolderResponse(BaseModel):
    """Response from folder import operation."""

    added: int  # Number of files successfully added
    skipped: int  # Number of files skipped (already exist or unsupported)
    failed: int  # Number of files that failed to process
    files: List[dict]  # Details of added files
    errors: List[str]  # Error messages for failed files


class LinkExistingFileRequest(BaseModel):
    """Request to link an existing file (by ID) to a space."""

    file_id: str


class SpaceListResponse(BaseModel):
    """Paginated list of spaces."""

    items: List[SpaceAccessResponse]
    total: int


############################
# Knowledge Forms
############################


class SpaceKnowledgeForm(BaseModel):
    """Form for adding/removing knowledge from a space."""

    knowledge_id: str


############################
# GetSpaces
############################

PAGE_ITEM_COUNT = 30


@router.get("/", response_model=SpaceListResponse)
async def get_spaces(
    page: Optional[int] = 1,
    category: Optional[str] = None,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    """Get all spaces accessible to the current user.

    Optional category filter: private, shared, invited
    """
    page = max(page, 1)
    limit = PAGE_ITEM_COUNT
    skip = (page - 1) * limit

    # Get all spaces user has access to, optionally filtered by category
    all_spaces = Spaces.get_spaces_by_user_id(
        user.id, permission="read", category=category, db=db
    )

    # Apply pagination
    total = len(all_spaces)
    paginated_spaces = all_spaces[skip : skip + limit]

    return SpaceListResponse(
        items=[
            SpaceAccessResponse(
                **Spaces.get_space_with_user_and_knowledge(
                    space.id, current_user_id=user.id, db=db
                ).model_dump(),
                write_access=(
                    user.id == space.user_id
                    or can_bypass_access_control(user.id)
                    or (user.role == "admin" and BYPASS_ADMIN_ACCESS_CONTROL)
                    or has_access(user.id, "write", space.access_control, db=db)
                ),
            )
            for space in paginated_spaces
        ],
        total=total,
    )


############################
# CreateSpace
############################


@router.post("/create", response_model=Optional[SpaceResponse])
async def create_space(
    request: Request,
    form_data: SpaceForm,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    """Create a new space."""
    # Check if user has permission to create spaces
    if (
        not can_manage_all(user.id, "spaces")
        and user.role != "admin"
        and not has_permission(
            user.id,
            "workspace.spaces",
            request.app.state.config.USER_PERMISSIONS,
            db=db,
        )
    ):
        # Default to allowing space creation if permission not configured
        pass

    # Check if user can share publicly
    if (
        not can_manage_all(user.id, "spaces")
        and user.role != "admin"
        and form_data.access_control is None
        and not has_permission(
            user.id,
            "sharing.public_spaces",
            request.app.state.config.USER_PERMISSIONS,
            db=db,
        )
    ):
        # Default to private if user can't share publicly
        form_data.access_control = {}

    space = Spaces.insert_new_space(user.id, form_data, db=db)

    if not space:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create space",
        )

    result = Spaces.get_space_with_user_and_knowledge(
        space.id, current_user_id=user.id, db=db
    )
    if not result:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Space created but could not retrieve details",
        )

    return result


############################
# Invitation Endpoints (MUST be before /{id} routes to avoid path conflict)
############################


class InvitationWithSpace(BaseModel):
    """Pending invitation with space details."""

    id: str
    space_id: str
    email: str
    permission: int
    space_name: str
    space_emoji: Optional[str] = None
    space_slug: str
    created_at: int


@router.get("/invitations/pending", response_model=List[InvitationWithSpace])
async def get_pending_invitations(
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    """Get pending invitations for the current user."""
    invitations = Spaces.get_pending_invitations_for_user(user.email, db=db)

    result = []
    for inv in invitations:
        space = Spaces.get_space_by_id(inv.space_id, db=db)
        if space:
            result.append(
                InvitationWithSpace(
                    id=inv.id,
                    space_id=inv.space_id,
                    email=inv.email,
                    permission=inv.permission,
                    space_name=space.name,
                    space_emoji=space.emoji,
                    space_slug=space.slug,
                    created_at=inv.created_at,
                )
            )

    return result


@router.post("/invitations/{space_id}/respond", response_model=bool)
async def respond_to_invitation(
    space_id: str,
    form_data: SpaceInviteResponseForm,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    """Accept or decline an invitation to a space."""
    result = Spaces.respond_to_invitation(
        space_id=space_id,
        email=user.email,
        accept=form_data.accept,
        db=db,
    )

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No pending invitation found",
        )

    return True


############################
# Bookmarks
############################


@router.post("/bookmarks/add", response_model=Optional[SpaceBookmarkModel])
async def add_bookmark(
    form_data: SpaceBookmarkForm,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    """Bookmark a space for quick access."""
    space = Spaces.get_space_by_id(id=form_data.space_id, db=db)
    if not space:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    result = Spaces.add_bookmark(
        space_id=form_data.space_id,
        user_id=user.id,
        db=db,
    )

    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to add bookmark",
        )

    return result


@router.delete("/bookmarks/{space_id}", response_model=bool)
async def remove_bookmark(
    space_id: str,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    """Remove a bookmark."""
    return Spaces.remove_bookmark(space_id=space_id, user_id=user.id, db=db)


@router.get("/bookmarks", response_model=List[SpaceAccessResponse])
async def get_bookmarked_spaces(
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    """List all bookmarked spaces for the current user."""
    bookmarked_spaces = Spaces.get_bookmarks_by_user_id(user.id, db=db)

    results = []
    for space in bookmarked_spaces:
        space_response = Spaces.get_space_with_user_and_knowledge(
            space.id, current_user_id=user.id, db=db
        )
        if space_response:
            results.append(
                SpaceAccessResponse(
                    **space_response.model_dump(),
                    write_access=(
                        user.id == space.user_id
                        or can_bypass_access_control(user.id)
                        or (user.role == "admin" and BYPASS_ADMIN_ACCESS_CONTROL)
                        or has_access(user.id, "write", space.access_control, db=db)
                    ),
                )
            )

    return results


############################
# Templates
############################


@router.get("/templates", response_model=List[SpaceAccessResponse])
async def get_templates(
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    """List all template spaces."""
    templates = Spaces.get_templates(db=db)

    results = []
    for space in templates:
        space_response = Spaces.get_space_with_user_and_knowledge(
            space.id, current_user_id=user.id, db=db
        )
        if space_response:
            results.append(
                SpaceAccessResponse(
                    **space_response.model_dump(),
                    write_access=(
                        user.id == space.user_id
                        or can_bypass_access_control(user.id)
                        or (user.role == "admin" and BYPASS_ADMIN_ACCESS_CONTROL)
                        or has_access(user.id, "write", space.access_control, db=db)
                    ),
                )
            )

    return results


@router.post("/templates/{template_id}/clone", response_model=Optional[SpaceResponse])
async def clone_template(
    template_id: str,
    form_data: SpaceCloneForm,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    """Clone a template space to create a new space."""
    template = Spaces.get_space_by_id(id=template_id, db=db)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )

    if not template.is_template:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Space is not a template",
        )

    new_space = Spaces.clone_space(
        template_id=template_id,
        user_id=user.id,
        name=form_data.name,
        description=form_data.description,
        emoji=form_data.emoji,
        db=db,
    )

    if not new_space:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to clone template",
        )

    result = Spaces.get_space_with_user_and_knowledge(
        new_space.id, current_user_id=user.id, db=db
    )
    if not result:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Space cloned but could not retrieve details",
        )

    return result


############################
# Pins (Org-wide)
############################


@router.post("/pins/add", response_model=Optional[SpacePinModel])
async def pin_space(
    form_data: SpacePinForm,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    """Pin a space org-wide (admin only)."""
    if not can_manage_all(user.id, "spaces") and user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    space = Spaces.get_space_by_id(id=form_data.space_id, db=db)
    if not space:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    result = Spaces.pin_space(
        space_id=form_data.space_id,
        admin_user_id=user.id,
        db=db,
    )

    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to pin space",
        )

    return result


@router.delete("/pins/{space_id}", response_model=bool)
async def unpin_space(
    space_id: str,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    """Unpin a space (admin only)."""
    if not can_manage_all(user.id, "spaces") and user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    return Spaces.unpin_space(space_id=space_id, db=db)


@router.get("/pins", response_model=List[SpaceAccessResponse])
async def get_pinned_spaces(
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    """List all org-wide pinned spaces."""
    pinned_spaces = Spaces.get_pinned_spaces(db=db)

    results = []
    for space in pinned_spaces:
        space_response = Spaces.get_space_with_user_and_knowledge(
            space.id, current_user_id=user.id, db=db
        )
        if space_response:
            results.append(
                SpaceAccessResponse(
                    **space_response.model_dump(),
                    write_access=(
                        user.id == space.user_id
                        or can_bypass_access_control(user.id)
                        or (user.role == "admin" and BYPASS_ADMIN_ACCESS_CONTROL)
                        or has_access(user.id, "write", space.access_control, db=db)
                    ),
                )
            )

    return results


############################
# Notification Endpoints (MUST be before /{id} to avoid path collision)
############################


@router.get("/notifications/unread", response_model=List[dict])
async def get_unread_notifications(
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    """Get all unread space notifications for the current user."""
    notifications = Spaces.get_unread_notifications(user.id, db=db)

    results = []
    for n in notifications:
        # Enrich with space name
        space = Spaces.get_space_by_id(n.space_id, db=db)
        results.append(
            {
                **n.model_dump(),
                "space_name": space.name if space else None,
                "space_slug": space.slug if space else None,
                "space_emoji": space.emoji if space else None,
            }
        )

    return results


@router.post("/notifications/{notification_id}/read", response_model=bool)
async def mark_notification_read(
    notification_id: str,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    """Mark a specific notification as read."""
    return Spaces.mark_notification_read(
        notification_id=notification_id,
        user_id=user.id,
        db=db,
    )


@router.post("/notifications/read-all", response_model=dict)
async def mark_all_notifications_read(
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    """Mark all unread notifications as read."""
    count = Spaces.mark_all_notifications_read(user_id=user.id, db=db)
    return {"marked_read": count}


############################
# GetSpaceById
############################


@router.get("/{id}", response_model=Optional[SpaceAccessResponse])
async def get_space_by_id(
    id: str,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    """Get a space by ID."""
    space = Spaces.get_space_by_id(id=id, db=db)

    if not space:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    # Check access (includes contributor/invitation check)
    if not (
        can_manage_all(user.id, "spaces")
        or user.role == "admin"
        or space.user_id == user.id
        or has_access(user.id, "read", space.access_control, db=db)
        or is_space_contributor(user.email, space.id, db)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    space_response = Spaces.get_space_with_user_and_knowledge(
        id, current_user_id=user.id, db=db
    )

    return SpaceAccessResponse(
        **space_response.model_dump(),
        write_access=(
            user.id == space.user_id
            or can_bypass_access_control(user.id)
            or (user.role == "admin" and BYPASS_ADMIN_ACCESS_CONTROL)
            or has_access(user.id, "write", space.access_control, db=db)
        ),
    )


############################
# GetSpaceBySlug
############################


@router.get("/slug/{slug}", response_model=Optional[SpaceAccessResponse])
async def get_space_by_slug(
    slug: str,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    """Get a space by slug."""
    space = Spaces.get_space_by_slug(slug=slug, db=db)

    if not space:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    # Check access (includes contributor/invitation check)
    if not (
        can_manage_all(user.id, "spaces")
        or user.role == "admin"
        or space.user_id == user.id
        or has_access(user.id, "read", space.access_control, db=db)
        or is_space_contributor(user.email, space.id, db)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    space_response = Spaces.get_space_with_user_and_knowledge(
        space.id, current_user_id=user.id, db=db
    )

    return SpaceAccessResponse(
        **space_response.model_dump(),
        write_access=(
            user.id == space.user_id
            or can_bypass_access_control(user.id)
            or (user.role == "admin" and BYPASS_ADMIN_ACCESS_CONTROL)
            or has_access(user.id, "write", space.access_control, db=db)
        ),
    )


############################
# UpdateSpaceById
############################


@router.post("/{id}/update", response_model=Optional[SpaceAccessResponse])
async def update_space_by_id(
    request: Request,
    id: str,
    form_data: SpaceUpdateForm,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    """Update a space by ID."""
    space = Spaces.get_space_by_id(id=id, db=db)

    if not space:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    # Check write access
    if not (
        space.user_id == user.id
        or has_access(user.id, "write", space.access_control, db=db)
        or can_manage_all(user.id, "spaces")
        or user.role == "admin"
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    # Check if user can share publicly
    if (
        not can_manage_all(user.id, "spaces")
        and user.role != "admin"
        and form_data.access_control is None
        and not has_permission(
            user.id,
            "sharing.public_spaces",
            request.app.state.config.USER_PERMISSIONS,
            db=db,
        )
    ):
        form_data.access_control = {}

    updated_space = Spaces.update_space_by_id(id=id, form_data=form_data, db=db)

    if updated_space:
        space_response = Spaces.get_space_with_user_and_knowledge(
            id, current_user_id=user.id, db=db
        )
        return SpaceAccessResponse(
            **space_response.model_dump(),
            write_access=True,  # User just successfully updated, so has write access
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to update space",
        )


############################
# DeleteSpaceById
############################


@router.delete("/{id}/delete", response_model=bool)
async def delete_space_by_id(
    id: str,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    """Delete a space by ID."""
    space = Spaces.get_space_by_id(id=id, db=db)

    if not space:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    # Check write access
    if not (
        space.user_id == user.id
        or has_access(user.id, "write", space.access_control, db=db)
        or can_manage_all(user.id, "spaces")
        or user.role == "admin"
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    log.info(f"Deleting space: {id} (name: {space.name})")

    result = Spaces.delete_space_by_id(id=id, db=db)
    return result


############################
# AddKnowledgeToSpace
############################


@router.post("/{id}/knowledge/add", response_model=Optional[SpaceAccessResponse])
async def add_knowledge_to_space(
    id: str,
    form_data: SpaceKnowledgeForm,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    """Add a knowledge base to a space."""
    space = Spaces.get_space_by_id(id=id, db=db)

    if not space:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    # Check write access to space
    if not (
        space.user_id == user.id
        or has_access(user.id, "write", space.access_control, db=db)
        or can_manage_all(user.id, "spaces")
        or user.role == "admin"
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    # Check that knowledge base exists and user has access
    knowledge = Knowledges.get_knowledge_by_id(id=form_data.knowledge_id, db=db)
    if not knowledge:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge base not found",
        )

    if not (
        can_manage_all(user.id, "spaces")
        or user.role == "admin"
        or knowledge.user_id == user.id
        or has_access(user.id, "read", knowledge.access_control, db=db)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No access to knowledge base",
        )

    # Add knowledge to space
    result = Spaces.add_knowledge_to_space(
        space_id=id,
        knowledge_id=form_data.knowledge_id,
        user_id=user.id,
        db=db,
    )

    if result:
        space_response = Spaces.get_space_with_user_and_knowledge(
            id, current_user_id=user.id, db=db
        )
        return SpaceAccessResponse(
            **space_response.model_dump(),
            write_access=True,
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to add knowledge to space",
        )


############################
# RemoveKnowledgeFromSpace
############################


@router.post("/{id}/knowledge/remove", response_model=Optional[SpaceAccessResponse])
async def remove_knowledge_from_space(
    id: str,
    form_data: SpaceKnowledgeForm,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    """Remove a knowledge base from a space."""
    space = Spaces.get_space_by_id(id=id, db=db)

    if not space:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    # Check write access to space
    if not (
        space.user_id == user.id
        or has_access(user.id, "write", space.access_control, db=db)
        or can_manage_all(user.id, "spaces")
        or user.role == "admin"
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    # Remove knowledge from space
    result = Spaces.remove_knowledge_from_space(
        space_id=id,
        knowledge_id=form_data.knowledge_id,
        db=db,
    )

    if result:
        space_response = Spaces.get_space_with_user_and_knowledge(
            id, current_user_id=user.id, db=db
        )
        return SpaceAccessResponse(
            **space_response.model_dump(),
            write_access=True,
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to remove knowledge from space",
        )


############################
# GetSpaceKnowledge
############################


@router.get("/{id}/knowledge", response_model=List[dict])
async def get_space_knowledge(
    id: str,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    """Get all knowledge bases linked to a space."""
    space = Spaces.get_space_by_id(id=id, db=db)

    if not space:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    # Check read access (includes contributor/invitation check)
    if not (
        can_manage_all(user.id, "spaces")
        or user.role == "admin"
        or space.user_id == user.id
        or has_access(user.id, "read", space.access_control, db=db)
        or is_space_contributor(user.email, space.id, db)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    knowledge_bases = Spaces.get_knowledge_bases_by_space_id(id, db=db)
    return [kb.model_dump() for kb in knowledge_bases]


############################
# Contributor Endpoints
############################


@router.post(
    "/{id}/contributors/invite", response_model=Optional[SpaceContributorResponse]
)
async def invite_contributor(
    id: str,
    form_data: SpaceInviteForm,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    """Invite a contributor to a space by email."""
    space = Spaces.get_space_by_id(id=id, db=db)

    if not space:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    # Only owner or admin can invite
    if not (
        space.user_id == user.id
        or can_manage_all(user.id, "spaces")
        or user.role == "admin"
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    # Can't invite yourself
    if form_data.email == user.email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot invite yourself",
        )

    result = Spaces.invite_contributor(
        space_id=id,
        email=form_data.email,
        db=db,
    )

    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to invite contributor",
        )

    # Build response with user info if available
    contributor_user = None
    if result.user_id:
        u = Users.get_user_by_id(result.user_id)
        if u:
            from open_webui.models.users import UserModel, UserResponse

            contributor_user = UserResponse(**UserModel.model_validate(u).model_dump())

    return SpaceContributorResponse(
        id=result.id,
        space_id=result.space_id,
        user_id=result.user_id,
        email=result.email,
        permission=result.permission,
        accepted=result.accepted,
        user=contributor_user,
    )


@router.delete("/{id}/contributors/{email}", response_model=bool)
async def remove_contributor(
    id: str,
    email: str,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    """Remove a contributor from a space."""
    space = Spaces.get_space_by_id(id=id, db=db)

    if not space:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    # Only owner or admin can remove contributors
    if not (
        space.user_id == user.id
        or can_manage_all(user.id, "spaces")
        or user.role == "admin"
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    result = Spaces.remove_contributor(space_id=id, email=email, db=db)
    return result


@router.get("/{id}/contributors", response_model=List[SpaceContributorResponse])
async def get_contributors(
    id: str,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    """Get all contributors for a space."""
    space = Spaces.get_space_by_id(id=id, db=db)

    if not space:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    # Check read access (includes contributor/invitation check)
    if not (
        can_manage_all(user.id, "spaces")
        or user.role == "admin"
        or space.user_id == user.id
        or has_access(user.id, "read", space.access_control, db=db)
        or is_space_contributor(user.email, space.id, db)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    return Spaces.get_contributors_by_space_id(id, db=db)


############################
# File Endpoints
############################


@router.post("/{id}/files/upload")
def upload_file_to_space(
    request: Request,
    id: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = FastAPIFile(...),
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    """Upload a file directly to a space."""
    space = Spaces.get_space_by_id(id=id, db=db)

    if not space:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    # Check write access
    if not (
        space.user_id == user.id
        or has_access(user.id, "write", space.access_control, db=db)
        or can_manage_all(user.id, "spaces")
        or user.role == "admin"
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    # Upload file using existing handler
    # MUST pass explicit values for metadata, process, process_in_background
    # because FastAPI DI descriptors (Form/Query) are not resolved when calling
    # upload_file_handler as a regular function (not as an endpoint).
    log.info(
        f"[spaces] upload_file_to_space: space_id={id}, file={file.filename}, user={user.id}"
    )
    try:
        result = upload_file_handler(
            request,
            file=file,
            metadata=None,
            process=True,
            process_in_background=True,
            user=user,
            background_tasks=background_tasks,
            db=db,
        )
        log.info(
            f"[spaces] upload_file_handler returned: type={type(result).__name__}, result={result}"
        )
    except Exception as e:
        log.error(f"[spaces] upload_file_handler FAILED: {e}")
        raise

    # Link file to space
    if isinstance(result, dict):
        file_id = result.get("id")
    else:
        file_id = result.id if hasattr(result, "id") else None

    assert file_id is not None, (
        f"[spaces] file_id is None after upload, result={result}"
    )
    log.info(f"[spaces] linking file_id={file_id} to space_id={id}")

    Spaces.add_file_to_space(
        space_id=id,
        file_id=file_id,
        user_id=user.id,
        db=db,
    )
    log.info(f"[spaces] file {file_id} linked to space {id} successfully")

    return result


def _process_file_background(request, file_id, user):
    """Background task wrapper for processing files for RAG indexing."""
    from open_webui.internal.db import SessionLocal

    try:
        with SessionLocal() as db_session:
            process_file(
                request,
                ProcessFileForm(file_id=file_id),
                user=user,
                db=db_session,
            )
            log.info(
                f"[spaces] file {file_id} processed and indexed for RAG (background)"
            )
    except Exception as e:
        log.warning(f"[spaces] Failed to process file {file_id} for RAG: {e}")


@router.post("/{id}/files/link")
async def link_existing_file_to_space(
    request: Request,
    id: str,
    form_data: LinkExistingFileRequest,
    background_tasks: BackgroundTasks,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    """Link an already-stored file (by ID) to a space.

    Used when a file has been downloaded via another flow (e.g. SharePoint picker)
    and just needs to be associated with a space.
    """
    space = Spaces.get_space_by_id(id=id, db=db)

    if not space:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    # Check write access
    if not (
        space.user_id == user.id
        or has_access(user.id, "write", space.access_control, db=db)
        or can_manage_all(user.id, "spaces")
        or user.role == "admin"
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    # Verify the file exists
    from open_webui.models.files import Files

    file_record = Files.get_file_by_id(form_data.file_id)
    if not file_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found",
        )

    log.info(f"[spaces] linking existing file_id={form_data.file_id} to space_id={id}")

    Spaces.add_file_to_space(
        space_id=id,
        file_id=form_data.file_id,
        user_id=user.id,
        db=db,
    )

    # Process and index the file for RAG in background (extract content, create embeddings)
    background_tasks.add_task(
        _process_file_background, request, form_data.file_id, user
    )
    log.info(f"[spaces] file {form_data.file_id} queued for RAG processing")

    return {
        "id": file_record.id,
        "filename": file_record.filename,
        "meta": file_record.meta,
        "created_at": file_record.created_at,
    }


@router.post("/{id}/files/sharepoint")
async def add_sharepoint_file_to_space(
    request: Request,
    id: str,
    form_data: SharePointFileRequest,
    background_tasks: BackgroundTasks,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    """
    Download a file from SharePoint/OneDrive and link it to a space.

    Reuses the existing SharePoint download flow (Graph API -> Storage -> Files).
    """
    if not ENABLE_SHAREPOINT_INTEGRATION.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="SharePoint integration is disabled",
        )

    space = Spaces.get_space_by_id(id=id, db=db)

    if not space:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    # Check write access
    if not (
        space.user_id == user.id
        or has_access(user.id, "write", space.access_control, db=db)
        or can_manage_all(user.id, "spaces")
        or user.role == "admin"
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    # Import SharePoint utilities (lazy to avoid circular imports)
    import io
    import uuid
    import aiohttp

    from open_webui.routers.sharepoint import (
        get_tokens,
        get_tokens_for_tenant,
        get_tenant_by_id,
        graph_api_request,
        graph_api_download,
    )
    from open_webui.models.files import Files, FileForm
    from open_webui.storage.provider import Storage

    drive_id = form_data.drive_id
    item_id = form_data.item_id

    log.info(
        f"[spaces] sharepoint download: space_id={id}, drive_id={drive_id}, item_id={item_id}, user={user.id}"
    )

    # 1. Get auth tokens for the user
    # Use tenant-specific tokens when tenant_id is provided (multi-tenant support)
    if form_data.tenant_id:
        tenant = get_tenant_by_id(form_data.tenant_id)
        if tenant:
            tokens = await get_tokens_for_tenant(tenant, user, request)
        else:
            log.warning(f"[spaces] Tenant '{form_data.tenant_id}' not found, falling back to default tokens")
            tokens = await get_tokens(user, request)
    else:
        tokens = await get_tokens(user, request)

    # 2. Get file metadata from Graph API
    metadata_endpoint = f"/drives/{drive_id}/items/{item_id}"
    params = {
        "$select": "id,name,size,file,lastModifiedDateTime,@microsoft.graph.downloadUrl"
    }

    try:
        metadata = await graph_api_request(
            "GET", metadata_endpoint, tokens, params=params
        )
    except HTTPException as e:
        raise HTTPException(
            status_code=e.status_code,
            detail=f"Failed to get file metadata: {e.detail}",
        )

    filename = form_data.filename or metadata.get("name", f"file_{item_id}")
    file_size = metadata.get("size", 0)
    mime_type = metadata.get("file", {}).get("mimeType", "application/octet-stream")

    # 3. Download the file content
    download_url = metadata.get("@microsoft.graph.downloadUrl")

    if download_url:
        async with aiohttp.ClientSession() as session:
            async with session.get(download_url) as response:
                if response.status >= 400:
                    raise HTTPException(
                        status_code=response.status,
                        detail="Failed to download file from SharePoint",
                    )
                file_bytes = await response.read()
    else:
        content_endpoint = f"/drives/{drive_id}/items/{item_id}/content"
        file_bytes, content_type = await graph_api_download(content_endpoint, tokens)
        if content_type and content_type != "application/octet-stream":
            mime_type = content_type

    # 4. Store in OpenWebUI storage
    file_id = str(uuid.uuid4())
    file_obj = io.BytesIO(file_bytes)
    storage_tags = {
        "source": "sharepoint",
        "content_type": mime_type,
    }
    contents, file_path = Storage.upload_file(file_obj, filename, storage_tags)

    file_form = FileForm(
        id=file_id,
        filename=filename,
        path=file_path,
        meta={
            "name": filename,
            "content_type": mime_type,
            "size": file_size,
            "source": "sharepoint",
            "sharepoint_drive_id": drive_id,
            "sharepoint_item_id": item_id,
            "sharepoint_modified_at": metadata.get("lastModifiedDateTime"),
        },
    )

    file_record = Files.insert_new_file(user.id, file_form)

    if not file_record:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create file record",
        )

    log.info(
        f"[spaces] sharepoint file stored: {filename} ({file_id}) for user {user.id}"
    )

    # 5. Link file to space
    Spaces.add_file_to_space(
        space_id=id,
        file_id=file_id,
        user_id=user.id,
        db=db,
    )

    log.info(f"[spaces] sharepoint file {file_id} linked to space {id}")

    # 6. Process and index the file for RAG in background (extract content, create embeddings)
    background_tasks.add_task(_process_file_background, request, file_id, user)
    log.info(f"[spaces] sharepoint file {file_id} queued for RAG processing")

    return {
        "id": file_record.id,
        "filename": file_record.filename,
        "meta": file_record.meta,
        "created_at": file_record.created_at,
    }


@router.post("/{id}/files/sharepoint/folder", response_model=SharePointFolderResponse)
async def add_sharepoint_folder_to_space(
    request: Request,
    id: str,
    form_data: SharePointFolderRequest,
    background_tasks: BackgroundTasks,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    """
    Import all files from a SharePoint folder into a space.

    Recursively enumerates files in the folder, downloads each one,
    stores them in OpenWebUI, links them to the space, and queues
    them for RAG processing.
    """
    if not ENABLE_SHAREPOINT_INTEGRATION.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="SharePoint integration is disabled",
        )

    space = Spaces.get_space_by_id(id=id, db=db)

    if not space:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if not (
        space.user_id == user.id
        or has_access(user.id, "write", space.access_control, db=db)
        or can_manage_all(user.id, "spaces")
        or user.role == "admin"
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    import io
    import uuid
    import aiohttp

    from open_webui.routers.sharepoint import (
        get_tokens,
        get_tokens_for_tenant,
        get_tenant_by_id,
        graph_api_request,
    )
    from open_webui.models.files import Files, FileForm
    from open_webui.storage.provider import Storage

    drive_id = form_data.drive_id
    folder_id = form_data.folder_id
    max_depth = min(max(1, form_data.max_depth), 20)

    log.info(
        f"[spaces] sharepoint folder import: space_id={id}, drive_id={drive_id}, "
        f"folder_id={folder_id}, recursive={form_data.recursive}, max_depth={max_depth}"
    )

    # Use tenant-specific tokens when tenant_id is provided (multi-tenant support)
    if form_data.tenant_id:
        tenant = get_tenant_by_id(form_data.tenant_id)
        if tenant:
            tokens = await get_tokens_for_tenant(tenant, user, request)
        else:
            log.warning(f"[spaces] Tenant '{form_data.tenant_id}' not found, falling back to default tokens")
            tokens = await get_tokens(user, request)
    else:
        tokens = await get_tokens(user, request)

    existing_files = Spaces.get_files_by_space_id(id, db=db)
    existing_sharepoint_ids = set()
    for f in existing_files:
        if f.meta and f.meta.get("source") == "sharepoint":
            sp_item_id = f.meta.get("sharepoint_item_id")
            if sp_item_id:
                existing_sharepoint_ids.add(sp_item_id)

    all_files = []
    # Queue now tracks: (folder_id, folder_name, depth)
    # This allows us to track each file's immediate parent folder
    initial_folder_name = form_data.folder_name or "SharePoint Folder"
    queue = [(folder_id if folder_id else None, initial_folder_name, 0)]

    async def fetch_folder_contents(fid):
        if fid:
            endpoint = f"/drives/{drive_id}/items/{fid}/children"
        else:
            endpoint = f"/drives/{drive_id}/root/children"

        params = {
            "$select": "id,name,size,folder,file,webUrl,lastModifiedDateTime,@microsoft.graph.downloadUrl",
            "$top": "200",
        }

        items = []
        response = await graph_api_request("GET", endpoint, tokens, params=params)
        items.extend(response.get("value", []))
        next_link = response.get("@odata.nextLink")

        while next_link:
            async with aiohttp.ClientSession() as session:
                headers = {"Authorization": f"Bearer {tokens.access_token}"}
                async with session.get(next_link, headers=headers) as resp:
                    if resp.status >= 400:
                        break
                    data = await resp.json()
                    items.extend(data.get("value", []))
                    next_link = data.get("@odata.nextLink")

        return items

    while queue:
        # Check for client disconnect periodically during folder enumeration
        if await request.is_disconnected():
            log.info("[spaces] Client disconnected during folder enumeration, stopping")
            break

        current_folder_id, current_folder_name, depth = queue.pop(0)

        if depth > max_depth:
            continue

        try:
            items = await fetch_folder_contents(current_folder_id)
        except Exception as e:
            log.warning(f"[spaces] Failed to fetch folder {current_folder_id}: {e}")
            continue

        for item in items:
            is_folder = "folder" in item

            if is_folder:
                if form_data.recursive:
                    # Track subfolder's own id and name for its children
                    queue.append((item["id"], item["name"], depth + 1))
            else:
                # Store file with its immediate parent folder info
                all_files.append(
                    {
                        "item": item,
                        "parent_folder_id": current_folder_id,
                        "parent_folder_name": current_folder_name,
                    }
                )

    log.info(f"[spaces] Found {len(all_files)} files in SharePoint folder")

    added_files = []
    skipped = 0
    failed = 0
    errors = []

    for file_idx, file_entry in enumerate(all_files):
        # Check for client disconnect every 5 files
        if file_idx % 5 == 0 and await request.is_disconnected():
            log.info(
                f"[spaces] Client disconnected, stopping folder import after {len(added_files)} files"
            )
            break

        # Extract item and its immediate parent folder info
        item = file_entry["item"]
        parent_folder_id = file_entry["parent_folder_id"]
        parent_folder_name = file_entry["parent_folder_name"]

        item_id = item["id"]
        filename = item.get("name", f"file_{item_id}")

        if item_id in existing_sharepoint_ids:
            log.debug(f"[spaces] Skipping {filename} - already in space")
            skipped += 1
            continue

        mime_type = item.get("file", {}).get("mimeType", "application/octet-stream")

        unsupported_types = [
            "application/vnd.ms-outlook",
            "application/x-msdownload",
        ]
        if mime_type in unsupported_types:
            log.debug(f"[spaces] Skipping {filename} - unsupported type {mime_type}")
            skipped += 1
            continue

        try:
            download_url = item.get("@microsoft.graph.downloadUrl")

            if download_url:
                async with aiohttp.ClientSession() as session:
                    async with session.get(download_url) as response:
                        if response.status >= 400:
                            raise Exception(
                                f"Download failed with status {response.status}"
                            )
                        file_bytes = await response.read()
            else:
                content_endpoint = f"/drives/{drive_id}/items/{item_id}/content"
                async with aiohttp.ClientSession() as session:
                    headers = {"Authorization": f"Bearer {tokens.access_token}"}
                    async with session.get(
                        f"https://graph.microsoft.com/v1.0{content_endpoint}",
                        headers=headers,
                    ) as resp:
                        if resp.status >= 400:
                            raise Exception(
                                f"Download failed with status {resp.status}"
                            )
                        file_bytes = await resp.read()

            file_id = str(uuid.uuid4())
            file_obj = io.BytesIO(file_bytes)
            storage_tags = {"source": "sharepoint", "content_type": mime_type}
            contents, file_path = Storage.upload_file(file_obj, filename, storage_tags)

            file_form = FileForm(
                id=file_id,
                filename=filename,
                path=file_path,
                meta={
                    "name": filename,
                    "content_type": mime_type,
                    "size": item.get("size", len(file_bytes)),
                    "source": "sharepoint",
                    "sharepoint_drive_id": drive_id,
                    "sharepoint_item_id": item_id,
                    "sharepoint_folder_id": parent_folder_id,
                    "sharepoint_folder_name": parent_folder_name,
                    "sharepoint_site_name": form_data.site_name,
                    "sharepoint_modified_at": item.get("lastModifiedDateTime"),
                },
            )

            file_record = Files.insert_new_file(user.id, file_form)

            if not file_record:
                raise Exception("Failed to create file record")

            Spaces.add_file_to_space(
                space_id=id,
                file_id=file_id,
                user_id=user.id,
                db=db,
            )

            background_tasks.add_task(_process_file_background, request, file_id, user)

            added_files.append(
                {
                    "id": file_record.id,
                    "filename": file_record.filename,
                    "meta": file_record.meta,
                }
            )

            log.info(f"[spaces] Added {filename} ({file_id}) from SharePoint folder")

        except Exception as e:
            log.warning(f"[spaces] Failed to process {filename}: {e}")
            failed += 1
            errors.append(f"{filename}: {str(e)}")

    log.info(
        f"[spaces] Folder import complete: added={len(added_files)}, skipped={skipped}, failed={failed}"
    )

    return SharePointFolderResponse(
        added=len(added_files),
        skipped=skipped,
        failed=failed,
        files=added_files,
        errors=errors,
    )


@router.get("/{id}/files", response_model=List[dict])
async def get_space_files(
    id: str,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    """Get all files linked to a space."""
    space = Spaces.get_space_by_id(id=id, db=db)

    if not space:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    # Check read access (includes contributor/invitation check)
    if not (
        can_manage_all(user.id, "spaces")
        or user.role == "admin"
        or space.user_id == user.id
        or has_access(user.id, "read", space.access_control, db=db)
        or is_space_contributor(user.email, space.id, db)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    files = Spaces.get_files_by_space_id(id, db=db)
    return [f.model_dump() for f in files]


@router.delete("/{id}/files/{file_id}", response_model=bool)
async def remove_file_from_space(
    id: str,
    file_id: str,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    """Remove a file link from a space (does NOT delete the actual file)."""
    space = Spaces.get_space_by_id(id=id, db=db)

    if not space:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    # Check write access
    if not (
        space.user_id == user.id
        or has_access(user.id, "write", space.access_control, db=db)
        or can_manage_all(user.id, "spaces")
        or user.role == "admin"
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    result = Spaces.remove_file_from_space(space_id=id, file_id=file_id, db=db)
    return result


class SharePointSyncResult(BaseModel):
    """Result of SharePoint file sync operation."""

    total_checked: int
    updated: int
    failed: int
    up_to_date: int
    updated_files: List[dict]
    errors: List[str]


@router.post("/{id}/files/sharepoint/sync")
async def sync_sharepoint_files(
    request: Request,
    id: str,
    background_tasks: BackgroundTasks,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
) -> SharePointSyncResult:
    """
    Check SharePoint files in this space for updates and re-sync changed files.

    For each file sourced from SharePoint:
    1. Fetch current lastModifiedDateTime from Microsoft Graph
    2. Compare with stored sharepoint_modified_at
    3. If changed: re-download file and re-process for RAG

    Returns summary of sync operation.
    """
    import io
    import aiohttp
    from open_webui.routers.sharepoint import (
        get_tokens,
        graph_api_request,
        ENABLE_SHAREPOINT_INTEGRATION,
    )
    from open_webui.models.files import Files
    from open_webui.storage.provider import Storage

    if not ENABLE_SHAREPOINT_INTEGRATION.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="SharePoint integration is disabled",
        )

    space = Spaces.get_space_by_id(id=id, db=db)

    if not space:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if not (
        space.user_id == user.id
        or has_access(user.id, "write", space.access_control, db=db)
        or can_manage_all(user.id, "spaces")
        or user.role == "admin"
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    # Get auth tokens
    try:
        tokens = await get_tokens(user, request)
    except HTTPException as e:
        raise HTTPException(
            status_code=e.status_code,
            detail=f"SharePoint authentication failed: {e.detail}",
        )

    # Get all files in this space that came from SharePoint
    all_files = Spaces.get_files_by_space_id(id, db=db)
    sharepoint_files = [
        f
        for f in all_files
        if f.meta
        and f.meta.get("source") == "sharepoint"
        and f.meta.get("sharepoint_drive_id")
        and f.meta.get("sharepoint_item_id")
    ]

    log.info(
        f"[spaces] Sync: checking {len(sharepoint_files)} SharePoint files in space {id}"
    )

    updated_files = []
    errors = []
    up_to_date = 0
    failed = 0

    for file in sharepoint_files:
        # file.meta is guaranteed to be non-None by our filter above
        meta = file.meta or {}
        drive_id = meta.get("sharepoint_drive_id")
        item_id = meta.get("sharepoint_item_id")
        stored_modified_at = meta.get("sharepoint_modified_at")

        try:
            # Fetch current metadata from Microsoft Graph
            endpoint = f"/drives/{drive_id}/items/{item_id}"
            params = {
                "$select": "id,name,size,file,lastModifiedDateTime,@microsoft.graph.downloadUrl"
            }

            current_metadata = await graph_api_request(
                "GET", endpoint, tokens, params=params
            )
            current_modified_at = current_metadata.get("lastModifiedDateTime")

            # Compare modification times
            if stored_modified_at == current_modified_at:
                log.debug(f"[spaces] Sync: {file.filename} is up to date")
                up_to_date += 1
                continue

            log.info(
                f"[spaces] Sync: {file.filename} changed ({stored_modified_at} -> {current_modified_at})"
            )

            # Download updated file
            download_url = current_metadata.get("@microsoft.graph.downloadUrl")
            filename = current_metadata.get("name", file.filename)
            file_size = current_metadata.get("size", 0)
            mime_type = current_metadata.get("file", {}).get(
                "mimeType", "application/octet-stream"
            )

            if download_url:
                async with aiohttp.ClientSession() as session:
                    async with session.get(download_url) as response:
                        if response.status >= 400:
                            raise Exception(
                                f"Download failed with status {response.status}"
                            )
                        file_bytes = await response.read()
            else:
                content_endpoint = f"/drives/{drive_id}/items/{item_id}/content"
                async with aiohttp.ClientSession() as session:
                    headers = {"Authorization": f"Bearer {tokens.access_token}"}
                    async with session.get(
                        f"https://graph.microsoft.com/v1.0{content_endpoint}",
                        headers=headers,
                    ) as resp:
                        if resp.status >= 400:
                            raise Exception(
                                f"Download failed with status {resp.status}"
                            )
                        file_bytes = await resp.read()

            # Update file in storage
            file_obj = io.BytesIO(file_bytes)
            storage_tags = {"source": "sharepoint", "content_type": mime_type}
            contents, new_file_path = Storage.upload_file(
                file_obj, filename, storage_tags
            )

            # Update file record with new metadata
            existing_meta = file.meta if file.meta else {}
            updated_meta = {
                **existing_meta,
                "name": filename,
                "content_type": mime_type,
                "size": file_size,
                "sharepoint_modified_at": current_modified_at,
                "last_synced_at": int(time.time()),
            }

            Files.update_file_metadata_by_id(file.id, updated_meta)

            # Re-process for RAG
            background_tasks.add_task(_process_file_background, request, file.id, user)

            updated_files.append(
                {
                    "id": file.id,
                    "filename": filename,
                    "previous_modified_at": stored_modified_at,
                    "current_modified_at": current_modified_at,
                }
            )

            log.info(
                f"[spaces] Sync: updated {filename} and queued for RAG reprocessing"
            )

        except Exception as e:
            log.warning(f"[spaces] Sync: failed to check/update {file.filename}: {e}")
            errors.append(f"{file.filename}: {str(e)}")
            failed += 1

    log.info(
        f"[spaces] Sync complete: {len(updated_files)} updated, {up_to_date} up-to-date, {failed} failed"
    )

    return SharePointSyncResult(
        total_checked=len(sharepoint_files),
        updated=len(updated_files),
        failed=failed,
        up_to_date=up_to_date,
        updated_files=updated_files,
        errors=errors,
    )


############################
# Link Endpoints
############################


@router.post("/{id}/links/add", response_model=Optional[SpaceLinkModel])
async def add_link_to_space(
    id: str,
    form_data: SpaceLinkForm,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    """Add a link to a space."""
    space = Spaces.get_space_by_id(id=id, db=db)

    if not space:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    # Check write access
    if not (
        space.user_id == user.id
        or has_access(user.id, "write", space.access_control, db=db)
        or can_manage_all(user.id, "spaces")
        or user.role == "admin"
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    result = Spaces.add_link_to_space(
        space_id=id,
        user_id=user.id,
        url=form_data.url,
        title=form_data.title,
        db=db,
    )

    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to add link to space",
        )

    return result


@router.delete("/{id}/links/{link_id}", response_model=bool)
async def remove_link_from_space(
    id: str,
    link_id: str,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    """Remove a link from a space."""
    space = Spaces.get_space_by_id(id=id, db=db)

    if not space:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    # Check write access
    if not (
        space.user_id == user.id
        or has_access(user.id, "write", space.access_control, db=db)
        or can_manage_all(user.id, "spaces")
        or user.role == "admin"
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    result = Spaces.remove_link_from_space(space_id=id, link_id=link_id, db=db)
    return result


@router.get("/{id}/links", response_model=List[SpaceLinkModel])
async def get_space_links(
    id: str,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    """Get all links for a space."""
    space = Spaces.get_space_by_id(id=id, db=db)

    if not space:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    # Check read access (includes contributor/invitation check)
    if not (
        can_manage_all(user.id, "spaces")
        or user.role == "admin"
        or space.user_id == user.id
        or has_access(user.id, "read", space.access_control, db=db)
        or is_space_contributor(user.email, space.id, db)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    return Spaces.get_links_by_space_id(id, db=db)


############################
# Access Level Endpoint
############################


@router.put("/{id}/access", response_model=Optional[SpaceAccessResponse])
async def update_space_access_level(
    id: str,
    form_data: SpaceAccessLevelForm,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    """Update the access level of a space."""
    space = Spaces.get_space_by_id(id=id, db=db)

    if not space:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    # Only owner or admin can change access level
    if not (
        space.user_id == user.id
        or can_manage_all(user.id, "spaces")
        or user.role == "admin"
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    # Validate access level
    valid_levels = [
        SpaceAccessLevel.PRIVATE,
        SpaceAccessLevel.ORG,
        SpaceAccessLevel.PUBLIC,
    ]
    if form_data.access_level not in valid_levels:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid access level. Must be one of: {valid_levels}",
        )

    updated = Spaces.update_space_by_id(
        id=id,
        form_data=SpaceUpdateForm(access_level=form_data.access_level),
        db=db,
    )

    if updated:
        space_response = Spaces.get_space_with_user_and_knowledge(
            id, current_user_id=user.id, db=db
        )
        return SpaceAccessResponse(
            **space_response.model_dump(),
            write_access=True,
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to update access level",
        )


############################
# Thread-level Sharing
############################


class ThreadAccessForm(BaseModel):
    access_level: str  # private, space, org, public


@router.put("/{space_id}/threads/{chat_id}/access", response_model=dict)
async def update_thread_access(
    space_id: str,
    chat_id: str,
    form_data: ThreadAccessForm,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    """Update the access level of a specific thread within a space."""
    space = Spaces.get_space_by_id(id=space_id, db=db)
    if not space:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Space not found",
        )

    # Check write access to space
    if not (
        space.user_id == user.id
        or has_access(user.id, "write", space.access_control, db=db)
        or can_manage_all(user.id, "spaces")
        or user.role == "admin"
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    # Verify chat belongs to this space
    chat = Chats.get_chat_by_id(chat_id)
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found",
        )

    if chat.space_id != space_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Chat does not belong to this space",
        )

    # Validate access level
    valid_levels = ["private", "space", "org", "public"]
    if form_data.access_level not in valid_levels:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid access level. Must be one of: {valid_levels}",
        )

    # Build access_control based on level
    if form_data.access_level == "private":
        new_access_control = {
            "read": {"user_ids": [], "group_ids": []},
            "write": {"user_ids": [], "group_ids": []},
        }
    elif form_data.access_level == "space":
        # Build from space contributors
        contributors = Spaces.get_contributors_by_space_id(space_id, db=db)
        contributor_user_ids = [
            c.user_id for c in contributors if c.user_id and c.accepted
        ]
        new_access_control = {
            "read": {"user_ids": contributor_user_ids, "group_ids": []},
            "write": {"user_ids": contributor_user_ids, "group_ids": []},
        }
    else:
        # org or public — open access
        new_access_control = None

    # Update chat meta with thread access level
    chat_record = db.query(ChatRecord).filter_by(id=chat_id).first()
    if not chat_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat record not found",
        )

    meta = chat_record.meta or {}
    meta["thread_access_level"] = form_data.access_level
    meta["thread_access_control"] = new_access_control
    chat_record.meta = meta
    db.commit()

    return {
        "chat_id": chat_id,
        "space_id": space_id,
        "access_level": form_data.access_level,
    }


############################
# Bulk Thread Sharing
############################


@router.post("/{id}/threads/bulk-share", response_model=dict)
async def bulk_share_threads(
    id: str,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    """Bulk-share all private threads in a space to space-level visibility.

    Called when changing space access from private to org/public and the user
    confirms they want to share their threads with all space members.
    """
    space = Spaces.get_space_by_id(id=id, db=db)
    if not space:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    # Only owner or admin can bulk-share
    if not (
        space.user_id == user.id
        or can_manage_all(user.id, "spaces")
        or user.role == "admin"
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    # Build contributor user_ids for "space"-level access
    contributors = Spaces.get_contributors_by_space_id(id, db=db)
    contributor_user_ids = [c.user_id for c in contributors if c.user_id and c.accepted]

    access_control = {
        "read": {"user_ids": contributor_user_ids, "group_ids": []},
        "write": {"user_ids": contributor_user_ids, "group_ids": []},
    }

    # Load all chats in this space and update private ones
    chats = db.query(ChatRecord).filter_by(space_id=id).all()

    updated_count = 0
    for chat in chats:
        meta = chat.meta or {}
        current_level = meta.get("thread_access_level", "private")
        if current_level == "private" or not current_level:
            meta["thread_access_level"] = "space"
            meta["thread_access_control"] = access_control
            chat.meta = meta
            updated_count += 1

    db.commit()

    log.info(f"[spaces] bulk-shared {updated_count} threads in space {id}")

    # Notify subscribers about the bulk share
    if updated_count > 0:
        Spaces.create_notifications_for_subscribers(
            space_id=id,
            event_type="threads_shared",
            event_data={
                "threads_count": updated_count,
                "actor_id": user.id,
                "actor_name": user.name if hasattr(user, "name") else user.email,
            },
            exclude_user_id=user.id,
            db=db,
        )

    return {
        "space_id": id,
        "threads_updated": updated_count,
    }


############################
# Subscription Endpoints
############################


@router.post("/{id}/subscribe", response_model=Optional[SpaceSubscriptionModel])
async def subscribe_to_space(
    id: str,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    """Subscribe to a space for notifications."""
    space = Spaces.get_space_by_id(id=id, db=db)
    if not space:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    # Check read access (includes contributor/invitation check)
    if not (
        can_manage_all(user.id, "spaces")
        or user.role == "admin"
        or space.user_id == user.id
        or has_access(user.id, "read", space.access_control, db=db)
        or is_space_contributor(user.email, space.id, db)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    result = Spaces.subscribe(space_id=id, user_id=user.id, db=db)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to subscribe",
        )

    return result


@router.delete("/{id}/subscribe", response_model=bool)
async def unsubscribe_from_space(
    id: str,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    """Unsubscribe from a space."""
    return Spaces.unsubscribe(space_id=id, user_id=user.id, db=db)


@router.get("/{id}/subscription", response_model=dict)
async def get_subscription_status(
    id: str,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    """Check if the current user is subscribed to a space."""
    return {
        "space_id": id,
        "subscribed": Spaces.is_subscribed(space_id=id, user_id=user.id, db=db),
    }
