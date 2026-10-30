"""Resource discussions. All operations use the caller's transaction."""

from typing import Literal
from uuid import UUID

from open_webui.internal.db import Base
from open_webui.models.users import User
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import JSON, BigInteger, Column, Index, Text, UniqueConstraint, case, delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

ResourceType = Literal['model', 'knowledge', 'prompt', 'skill', 'tool', 'note', 'chat']


class Comment(Base):
    __tablename__ = 'comment'
    id = Column(Text, primary_key=True)
    user_id = Column(Text, nullable=True)
    resource_type = Column(Text, nullable=False)
    resource_id = Column(Text, nullable=False)
    parent_id = Column(Text, nullable=True)
    reply_to_id = Column(Text, nullable=True)
    content = Column(Text, nullable=False)
    target_type = Column(Text, nullable=True)
    target_id = Column(Text, nullable=True)
    meta = Column(JSON, nullable=True)
    created_at = Column(BigInteger, nullable=False)
    updated_at = Column(BigInteger, nullable=False)
    deleted_at = Column(BigInteger, nullable=True)
    __table_args__ = (
        Index('ix_comment_resource', 'resource_type', 'resource_id', 'parent_id', 'created_at', 'id'),
        Index('ix_comment_parent', 'parent_id', 'created_at', 'id'),
        Index('ix_comment_target', 'resource_type', 'resource_id', 'target_type', 'target_id'),
    )


class CommentReaction(Base):
    __tablename__ = 'comment_reaction'
    id = Column(Text, primary_key=True)
    user_id = Column(Text, nullable=False)
    comment_id = Column(Text, nullable=False, index=True)
    name = Column(Text, nullable=False)
    created_at = Column(BigInteger, nullable=False)
    __table_args__ = (UniqueConstraint('comment_id', 'user_id', 'name', name='uq_comment_reaction'),)


class CommentAnchor(BaseModel):
    model_config = ConfigDict(extra='forbid')
    quote: str = Field(min_length=1, max_length=10000)
    prefix: str = Field(default='', max_length=64)
    suffix: str = Field(default='', max_length=64)
    start: int = Field(ge=0)
    end: int = Field(ge=1)
    surface_id: str = Field(max_length=256)
    source: str = Field(pattern=r'^[0-9a-f]{64}$')
    content_hash: str = Field(pattern=r'^[0-9a-f]{64}$')


class CommentContentForm(BaseModel):
    model_config = ConfigDict(extra='forbid')
    content: str = Field(min_length=1, max_length=20000)

    @field_validator('content')
    @classmethod
    def nonempty(cls, value):
        if not value.strip():
            raise ValueError('Comment cannot be empty')
        return value


class CommentForm(CommentContentForm):
    temp_id: UUID | None = None
    resource_type: ResourceType
    resource_id: str = Field(min_length=1, max_length=512)
    target_type: Literal['note_page', 'chat_message'] | None = None
    target_id: str | None = Field(default=None, max_length=256)
    anchor: CommentAnchor | None = None


class CommentReplyForm(CommentContentForm):
    temp_id: UUID | None = None
    reply_to_id: str | None = None


class CommentUpdateForm(CommentContentForm):
    etag: str = Field(pattern=r'^\d{1,20}$')


async def comment_responses(db: AsyncSession, comments: list[Comment], user, owner_id: str) -> list[dict]:
    if not comments:
        return []
    ids = [c.id for c in comments]
    authors = {
        u.id: {'id': u.id, 'name': u.name, 'profile_image_url': u.profile_image_url}
        for u in (await db.scalars(select(User).where(User.id.in_({c.user_id for c in comments if c.user_id})))).all()
    }
    counts = {
        parent_id: (count, latest)
        for parent_id, count, latest in (
            await db.execute(
                select(Comment.parent_id, func.count(), func.max(Comment.created_at))
                .where(Comment.parent_id.in_(ids))
                .group_by(Comment.parent_id)
            )
        ).all()
    }
    reactions = {}
    for comment_id, name, count, mine in (
        await db.execute(
            select(
                CommentReaction.comment_id,
                CommentReaction.name,
                func.count(),
                func.max(
                    # CASE is portable across PostgreSQL and SQLite (boolean MAX isn't).
                    case((CommentReaction.user_id == user.id, 1), else_=0)
                ),
            )
            .where(CommentReaction.comment_id.in_(ids))
            .group_by(CommentReaction.comment_id, CommentReaction.name)
        )
    ).all():
        reactions.setdefault(comment_id, []).append({'name': name, 'count': count, 'reacted': bool(mine)})
    return [
        {
            **{c.name: getattr(comment, c.name) for c in Comment.__table__.columns},
            'etag': str(comment.updated_at),
            'user': authors.get(comment.user_id),
            'reply_count': counts.get(comment.id, (0, None))[0],
            'latest_reply_at': counts.get(comment.id, (0, None))[1],
            'reactions': reactions.get(comment.id, []),
            'can_edit': not comment.deleted_at and comment.user_id == user.id,
            'can_delete': not comment.deleted_at
            and (comment.user_id == user.id or owner_id == user.id or user.role == 'admin'),
        }
        for comment in comments
    ]


async def delete_resource_comments(db: AsyncSession, resource_type: str, resource_ids):
    """Lock resources before cleanup so concurrent comment creation cannot leave orphans."""
    from open_webui.utils.comments import resource_models

    # Retain cleanup for legacy snapshot comments when their shared chat is deleted.
    if resource_type == 'shared_chat':
        from open_webui.models.shared_chats import SharedChat

        model = SharedChat
    else:
        model = resource_models()[resource_type]
    ids = list((await db.scalars(select(model.id).where(model.id.in_(resource_ids)).with_for_update())).all())
    if not ids:
        return
    if resource_type == 'chat':
        from open_webui.models.shared_chats import SharedChat

        await delete_resource_comments(db, 'shared_chat', select(SharedChat.id).where(SharedChat.chat_id.in_(ids)))
    comment_ids = select(Comment.id).where(Comment.resource_type == resource_type, Comment.resource_id.in_(ids))
    await db.execute(delete(CommentReaction).where(CommentReaction.comment_id.in_(comment_ids)))
    await db.execute(delete(Comment).where(Comment.resource_type == resource_type, Comment.resource_id.in_(ids)))


async def cleanup_comments_for_deleted_user(db: AsyncSession, user_id: str):
    """Remove reactions and clear authorship, preserving comment text and threads."""
    await db.execute(delete(CommentReaction).where(CommentReaction.user_id == user_id))
    await db.execute(update(Comment).where(Comment.user_id == user_id).values(user_id=None))
