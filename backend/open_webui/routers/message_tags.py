"""
Message Tags API Router

Endpoints for managing message tags, tag definitions, and daemon configuration.
"""

import asyncio
import logging
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from open_webui.utils.auth import get_admin_user, get_verified_user
from open_webui.models.message_tags import (
    MessageTags,
    MessageTagDefinitions,
    TaggingDaemonConfigs,
    MessageTagModel,
    MessageTagDefinitionModel,
    TaggingDaemonConfigModel,
)
from open_webui.models.chats import Chats
from open_webui.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MAIN"])

router = APIRouter()


# ============================================================
# Request/Response Models
# ============================================================

class DaemonConfigUpdateRequest(BaseModel):
    enabled: Optional[bool] = None
    schedule: Optional[str] = None  # "daily" | "weekly"
    run_time: Optional[str] = None  # "HH:MM" format
    lookback_days: Optional[int] = None
    batch_size: Optional[int] = None
    max_tags: Optional[int] = None
    consolidation_threshold: Optional[int] = None
    custom_tagging_prompt: Optional[str] = None  # Custom prompt for AI tagging
    custom_system_instruction: Optional[str] = None  # Custom system instruction
    blacklisted_tags: Optional[List[str]] = None  # Tags that should never be created


class BlacklistUpdateRequest(BaseModel):
    tag_ids: List[str]  # Tag IDs to add/remove from blacklist


class TagMergeRequest(BaseModel):
    keep_tag_id: str
    merge_tag_ids: List[str]


class AdminTagCreateRequest(BaseModel):
    name: str
    is_protected: bool = True  # Admin-created tags are protected by default


class TagProtectionRequest(BaseModel):
    is_protected: bool


class ManualTagRequest(BaseModel):
    chat_id: str
    message_id: str
    tag_name: str
    summary: Optional[str] = None


class MessageTagsResponse(BaseModel):
    tags: List[MessageTagModel]
    definitions: List[MessageTagDefinitionModel]


class TagStatsResponse(BaseModel):
    total_unique_tags: int
    total_tagged_messages: int
    max_tags_limit: int
    last_run_at: Optional[int]
    last_run_status: Optional[str]
    daemon_enabled: bool


class TagWithChapterResponse(BaseModel):
    """Tag definition with chapter information."""
    id: str
    name: str
    usage_count: int = 0
    is_protected: bool = False
    chapter_id: Optional[str] = None
    chapter_name: Optional[str] = None  # From textbook_chapter.title
    meta: Optional[dict] = None
    created_at: int
    updated_at: int


class TagMessageDetail(BaseModel):
    """Detail of a message associated with a tag."""
    message_id: str
    chat_id: str
    user_id: str
    user_name: Optional[str] = None
    summary: Optional[str]
    created_at: int


class TagMessagesStatsResponse(BaseModel):
    """Statistics for messages with a specific tag."""
    tag: MessageTagDefinitionModel
    total_messages: int
    messages: List[TagMessageDetail]
    unique_users: int
    unique_chats: int


# ============================================================
# Daemon Configuration Endpoints (Admin Only)
# ============================================================

@router.get("/admin/config", response_model=TaggingDaemonConfigModel)
async def get_daemon_config(user=Depends(get_admin_user)):
    """Get current daemon configuration."""
    config = TaggingDaemonConfigs.get_config()
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    return config


@router.put("/admin/config", response_model=TaggingDaemonConfigModel)
async def update_daemon_config(
    body: DaemonConfigUpdateRequest,
    user=Depends(get_admin_user)
):
    """Update daemon configuration."""
    update_data = body.model_dump(exclude_none=True)

    # Validate schedule
    if "schedule" in update_data and update_data["schedule"] not in ["daily", "weekly"]:
        raise HTTPException(status_code=400, detail="Invalid schedule. Use 'daily' or 'weekly'")

    # Validate run_time format
    if "run_time" in update_data:
        try:
            parts = update_data["run_time"].split(":")
            if len(parts) != 2 or not (0 <= int(parts[0]) <= 23) or not (0 <= int(parts[1]) <= 59):
                raise ValueError()
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid run_time format. Use 'HH:MM'")

    config = TaggingDaemonConfigs.update_config(**update_data)
    if not config:
        raise HTTPException(status_code=500, detail="Failed to update config")
    return config


@router.post("/admin/run")
async def trigger_manual_run(request: Request, user=Depends(get_admin_user)):
    """Trigger a manual tagging run."""
    daemon = getattr(request.app.state, "message_tagging_daemon", None)
    if not daemon:
        raise HTTPException(status_code=500, detail="Daemon not initialized")

    asyncio.create_task(daemon.run_manual())
    return {"status": "started", "message": "Manual tagging run started"}


# ============================================================
# Tag Definition Management (Admin Only)
# ============================================================

@router.get("/admin/tags", response_model=List[TagWithChapterResponse])
async def list_all_tags(user=Depends(get_admin_user)):
    """List all tag definitions with usage counts and chapter information."""
    from open_webui.internal.db import get_db
    from open_webui.models.message_tags import MessageTagDefinition
    from open_webui.models.textbooks import TextbookChapter

    with get_db() as db:
        # Left join with textbook_chapter to get chapter name
        results = db.query(
            MessageTagDefinition,
            TextbookChapter.title.label("chapter_name")
        ).outerjoin(
            TextbookChapter,
            MessageTagDefinition.chapter_id == TextbookChapter.id
        ).order_by(
            MessageTagDefinition.usage_count.desc()
        ).all()

        return [
            TagWithChapterResponse(
                id=tag.id,
                name=tag.name,
                usage_count=tag.usage_count,
                is_protected=tag.is_protected,
                chapter_id=tag.chapter_id,
                chapter_name=chapter_name,
                meta=tag.meta,
                created_at=tag.created_at,
                updated_at=tag.updated_at
            )
            for tag, chapter_name in results
        ]


@router.delete("/admin/tags/{tag_id}")
async def delete_tag(tag_id: str, user=Depends(get_admin_user)):
    """Delete a tag definition and all associated message tags."""
    # First remove all message_tag entries
    MessageTags.delete_by_tag(tag_id)
    # Then remove the definition
    success = MessageTagDefinitions.delete(tag_id)
    if not success:
        raise HTTPException(status_code=404, detail="Tag not found")
    return {"success": True}


@router.post("/admin/tags/merge")
async def merge_tags(body: TagMergeRequest, user=Depends(get_admin_user)):
    """Merge multiple tags into one."""
    # Verify keep_tag exists
    keep_tag = MessageTagDefinitions.get_by_id(body.keep_tag_id)
    if not keep_tag:
        raise HTTPException(status_code=404, detail="Keep tag not found")

    # Update all message_tags to use kept tag
    for old_tag_id in body.merge_tag_ids:
        MessageTags.update_tag_id(old_tag_id, body.keep_tag_id)

    # Merge the definitions
    MessageTagDefinitions.merge_tags(body.keep_tag_id, body.merge_tag_ids)

    return {"success": True, "merged_count": len(body.merge_tag_ids)}


@router.post("/admin/tags/{tag_id}/rename")
async def rename_tag(
    tag_id: str,
    new_name: str,
    user=Depends(get_admin_user)
):
    """Rename a tag (changes display name, not ID)."""
    tag = MessageTagDefinitions.rename(tag_id, new_name)
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    return tag


@router.post("/admin/tags/create", response_model=MessageTagDefinitionModel)
async def create_admin_tag(
    body: AdminTagCreateRequest,
    user=Depends(get_admin_user)
):
    """Create a new tag definition (admin-created, optionally protected)."""
    # Check if tag already exists
    tag_id = body.name.lower().replace(" ", "_")
    existing = MessageTagDefinitions.get_by_id(tag_id)
    if existing:
        raise HTTPException(status_code=400, detail="Tag already exists")

    tag = MessageTagDefinitions.create(body.name, is_protected=body.is_protected)
    if not tag:
        raise HTTPException(status_code=500, detail="Failed to create tag")
    return tag


@router.put("/admin/tags/{tag_id}/protection", response_model=MessageTagDefinitionModel)
async def set_tag_protection(
    tag_id: str,
    body: TagProtectionRequest,
    user=Depends(get_admin_user)
):
    """Set or unset protection status for a tag."""
    tag = MessageTagDefinitions.set_protected(tag_id, body.is_protected)
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    return tag


# ============================================================
# Blacklist Management (Admin Only)
# ============================================================

@router.get("/admin/blacklist", response_model=List[str])
async def get_blacklist(user=Depends(get_admin_user)):
    """Get the list of blacklisted tag IDs."""
    config = TaggingDaemonConfigs.get_config()
    if not config:
        return []
    return config.blacklisted_tags or []


@router.post("/admin/blacklist/add")
async def add_to_blacklist(
    body: BlacklistUpdateRequest,
    user=Depends(get_admin_user)
):
    """Add tag IDs to the blacklist. Also deletes existing tags with these IDs."""
    config = TaggingDaemonConfigs.get_config()
    if not config:
        raise HTTPException(status_code=500, detail="Config not found")

    current_blacklist = set(config.blacklisted_tags or [])
    new_tags = set(body.tag_ids)

    # Delete existing tags and their associations
    for tag_id in new_tags:
        MessageTags.delete_by_tag(tag_id)
        MessageTagDefinitions.delete(tag_id)

    # Update blacklist
    updated_blacklist = list(current_blacklist | new_tags)
    TaggingDaemonConfigs.update_config(blacklisted_tags=updated_blacklist)

    return {"success": True, "blacklisted_tags": updated_blacklist, "deleted_count": len(new_tags)}


@router.post("/admin/blacklist/remove")
async def remove_from_blacklist(
    body: BlacklistUpdateRequest,
    user=Depends(get_admin_user)
):
    """Remove tag IDs from the blacklist."""
    config = TaggingDaemonConfigs.get_config()
    if not config:
        raise HTTPException(status_code=500, detail="Config not found")

    current_blacklist = set(config.blacklisted_tags or [])
    tags_to_remove = set(body.tag_ids)

    updated_blacklist = list(current_blacklist - tags_to_remove)
    TaggingDaemonConfigs.update_config(blacklisted_tags=updated_blacklist)

    return {"success": True, "blacklisted_tags": updated_blacklist}


# ============================================================
# Message Tag Endpoints (User)
# ============================================================

@router.get("/message/{chat_id}/{message_id}", response_model=MessageTagsResponse)
async def get_message_tags(
    chat_id: str,
    message_id: str,
    user=Depends(get_verified_user)
):
    """Get tags for a specific message."""
    # Verify user owns the chat
    chat = Chats.get_chat_by_id_and_user_id(chat_id, user.id)
    if not chat:
        raise HTTPException(status_code=403, detail="Chat not found or access denied")

    tags = MessageTags.get_by_message(chat_id, message_id)

    # Get definitions for these tags
    tag_ids = list(set(t.tag_id for t in tags))
    definitions = [MessageTagDefinitions.get_by_id(tid) for tid in tag_ids]
    definitions = [d for d in definitions if d]  # Filter None

    return MessageTagsResponse(tags=tags, definitions=definitions)


@router.post("/message/manual", response_model=MessageTagModel)
async def add_manual_tag(
    body: ManualTagRequest,
    user=Depends(get_verified_user)
):
    """Manually add a tag to a message."""
    # Verify user owns the chat
    chat = Chats.get_chat_by_id_and_user_id(body.chat_id, user.id)
    if not chat:
        raise HTTPException(status_code=403, detail="Chat not found or access denied")

    # Get or create tag definition
    tag_id = body.tag_name.lower().replace(" ", "_")
    tag_def = MessageTagDefinitions.get_by_id(tag_id)
    if not tag_def:
        tag_def = MessageTagDefinitions.create(body.tag_name)

    if not tag_def:
        raise HTTPException(status_code=500, detail="Failed to create tag definition")

    # Create message tag
    tag = MessageTags.create(
        chat_id=body.chat_id,
        message_id=body.message_id,
        tag_id=tag_id,
        summary=body.summary or "",
        user_id=user.id
    )

    if not tag:
        raise HTTPException(status_code=500, detail="Failed to create tag")

    MessageTagDefinitions.increment_usage(tag_id)
    return tag


@router.delete("/message/{chat_id}/{message_id}/{tag_id}")
async def remove_message_tag(
    chat_id: str,
    message_id: str,
    tag_id: str,
    user=Depends(get_verified_user)
):
    """Remove a tag from a message."""
    # Verify user owns the chat
    chat = Chats.get_chat_by_id_and_user_id(chat_id, user.id)
    if not chat:
        raise HTTPException(status_code=403, detail="Chat not found or access denied")

    # Find and delete the specific tag
    tags = MessageTags.get_by_message(chat_id, message_id)
    for t in tags:
        if t.tag_id == tag_id:
            MessageTags.delete_by_id(t.id)
            return {"success": True}

    raise HTTPException(status_code=404, detail="Tag not found on message")


@router.get("/search/{tag_id}", response_model=List[MessageTagModel])
async def search_by_tag(
    tag_id: str,
    limit: int = 50,
    user=Depends(get_verified_user)
):
    """Search messages by tag (returns user's messages only)."""
    return MessageTags.get_by_tag_and_user(tag_id, user.id, limit)


# ============================================================
# Statistics Endpoints
# ============================================================

@router.get("/admin/tags/top", response_model=List[TagWithChapterResponse])
async def get_top_tags(
    limit: int = 10,
    user=Depends(get_admin_user)
):
    """Get top N most frequently used tags with chapter information."""
    from open_webui.internal.db import get_db
    from open_webui.models.message_tags import MessageTagDefinition
    from open_webui.models.textbooks import TextbookChapter

    with get_db() as db:
        # Left join with textbook_chapter to get chapter name
        results = db.query(
            MessageTagDefinition,
            TextbookChapter.title.label("chapter_name")
        ).outerjoin(
            TextbookChapter,
            MessageTagDefinition.chapter_id == TextbookChapter.id
        ).order_by(
            MessageTagDefinition.usage_count.desc()
        ).limit(limit).all()

        return [
            TagWithChapterResponse(
                id=tag.id,
                name=tag.name,
                usage_count=tag.usage_count,
                is_protected=tag.is_protected,
                chapter_id=tag.chapter_id,
                chapter_name=chapter_name,
                meta=tag.meta,
                created_at=tag.created_at,
                updated_at=tag.updated_at
            )
            for tag, chapter_name in results
        ]


@router.get("/stats", response_model=TagStatsResponse)
async def get_tagging_stats(user=Depends(get_admin_user)):
    """Get tagging statistics."""
    from open_webui.internal.db import get_db
    from open_webui.models.message_tags import MessageTag, MessageTagDefinition

    with get_db() as db:
        total_tags = db.query(MessageTagDefinition).count()
        total_tagged_messages = db.query(MessageTag).count()

    config = TaggingDaemonConfigs.get_config()

    return TagStatsResponse(
        total_unique_tags=total_tags,
        total_tagged_messages=total_tagged_messages,
        max_tags_limit=config.max_tags if config else 100,
        last_run_at=config.last_run_at if config else None,
        last_run_status=config.last_run_status if config else None,
        daemon_enabled=config.enabled if config else False,
    )


@router.get("/admin/tags/{tag_id}/messages", response_model=TagMessagesStatsResponse)
async def get_tag_messages_stats(
    tag_id: str,
    limit: int = 10,
    offset: int = 0,
    user=Depends(get_admin_user)
):
    """Get detailed statistics for messages with a specific tag (Admin only)."""
    from open_webui.internal.db import get_db
    from open_webui.models.message_tags import MessageTag, MessageTagDefinition
    from open_webui.models.users import User

    # Get tag definition
    tag_def = MessageTagDefinitions.get_by_id(tag_id)
    if not tag_def:
        raise HTTPException(status_code=404, detail="Tag not found")

    with get_db() as db:
        # Get all messages with this tag
        query = db.query(MessageTag).filter_by(tag_id=tag_id)
        total_messages = query.count()

        # Get unique counts
        unique_users = db.query(MessageTag.user_id).filter_by(tag_id=tag_id).distinct().count()
        unique_chats = db.query(MessageTag.chat_id).filter_by(tag_id=tag_id).distinct().count()

        # Get paginated messages
        messages = query.order_by(MessageTag.created_at.desc()).offset(offset).limit(limit).all()

        # Batch fetch user names
        user_ids = list(set(m.user_id for m in messages))
        users = db.query(User).filter(User.id.in_(user_ids)).all() if user_ids else []
        user_map = {u.id: u.name for u in users}

        message_details = [
            TagMessageDetail(
                message_id=m.message_id,
                chat_id=m.chat_id,
                user_id=m.user_id,
                user_name=user_map.get(m.user_id),
                summary=m.summary,
                created_at=m.created_at
            )
            for m in messages
        ]

    return TagMessagesStatsResponse(
        tag=tag_def,
        total_messages=total_messages,
        messages=message_details,
        unique_users=unique_users,
        unique_chats=unique_chats
    )


# ============================================================
# User Tag List
# ============================================================

@router.get("/my-tags", response_model=List[MessageTagDefinitionModel])
async def get_my_tags(user=Depends(get_verified_user)):
    """Get all tag definitions that have been used on user's messages."""
    from open_webui.internal.db import get_db
    from open_webui.models.message_tags import MessageTag, MessageTagDefinition

    with get_db() as db:
        # Get unique tag_ids from user's messages
        tag_ids = db.query(MessageTag.tag_id).filter_by(user_id=user.id).distinct().all()
        tag_ids = [t[0] for t in tag_ids]

        # Get the definitions
        if tag_ids:
            tags = db.query(MessageTagDefinition).filter(
                MessageTagDefinition.id.in_(tag_ids)
            ).order_by(MessageTagDefinition.usage_count.desc()).all()
            return [MessageTagDefinitionModel.model_validate(t) for t in tags]

    return []
