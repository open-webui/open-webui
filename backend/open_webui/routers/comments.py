import logging
import time
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from open_webui.models.notifications import emit_changes
from open_webui.internal.db import get_async_session
from open_webui.models.comments import (
    Comment,
    CommentForm,
    CommentReaction,
    CommentReplyForm,
    CommentUpdateForm,
    ResourceType,
    comment_responses,
)
from open_webui.models.users import User, UserModel
from open_webui.utils.auth import get_verified_user
from open_webui.utils.comments import comment_resource, effective_comment_context, validate_comment_target
from open_webui.utils.rate_limit import RateLimiter
from pydantic import BaseModel, Field
from sqlalchemy import and_, delete, func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from open_webui.events import EVENTS, build_event, publish_event
from open_webui.utils.inbox import mentioned_users
from open_webui.models.notifications import delete_notifications

router = APIRouter()
write_limiter = RateLimiter(30, 60)
reaction_limiter = RateLimiter(120, 60)


async def limit_write(request, user, limiter=write_limiter):
    if await limiter.is_limited(getattr(request.app.state, 'redis', None), f'comments:{limiter.limit}:{user.id}'):
        raise HTTPException(429, 'Too many requests')


async def changed(resource_type, resource_id):
    from open_webui.socket.comments import comment_room
    from open_webui.socket.main import sio

    # No comment text, author, or activity IDs are sent to possibly stale subscribers.
    try:
        await sio.emit(
            'comments:changed',
            {'resource_type': resource_type, 'resource_id': resource_id},
            room=comment_room(resource_type, resource_id),
        )
    except Exception:
        logging.getLogger(__name__).exception('Could not broadcast comment change')


async def accessible_comment(id, user, db, *, lock=False, request=None):
    comment = await db.get(Comment, id)
    if comment is None:
        raise HTTPException(404, 'Comment not found')
    resource = await comment_resource(comment.resource_type, comment.resource_id, user, db, lock=lock, request=request)
    if lock:
        comment = await db.scalar(
            select(Comment).where(Comment.id == id).with_for_update().execution_options(populate_existing=True)
        )
        if comment is None:
            raise HTTPException(404, 'Comment not found')
    return comment, resource


@router.get('/context')
async def context(
    request: Request,
    resource_type: ResourceType,
    resource_id: str,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    return await effective_comment_context(resource_type, resource_id, user, db, request=request)


@router.get('/mentions')
async def mentions(
    request: Request,
    resource_type: ResourceType,
    resource_id: str,
    query: str = Query('', max_length=100),
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    await comment_resource(resource_type, resource_id, user, db, request=request)
    # Bound directory work even in deployments with many thousands of accounts.
    candidates = (
        await db.scalars(
            select(User)
            .where(
                User.role.in_(['user', 'admin']),
                User.name.ilike(
                    '%' + query.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_') + '%', escape='\\'
                ),
            )
            .order_by(User.name, User.id)
            .limit(40)
        )
    ).all()
    result = []
    for candidate in candidates:
        try:
            await comment_resource(resource_type, resource_id, UserModel.model_validate(candidate), db, request=request)
        except HTTPException:
            continue
        result.append({'id': candidate.id, 'name': candidate.name})
        if len(result) == 20:
            break
    return result


async def list_comments(db, user, resource, resource_type, resource_id, parent_id, cursor, limit, *, anchored=False):
    query = select(Comment).where(
        Comment.resource_type == resource_type, Comment.resource_id == resource_id, Comment.parent_id == parent_id
    )
    if anchored:
        query = query.where(Comment.meta['anchor'].as_string().is_not(None), Comment.deleted_at.is_(None))
    if cursor:
        try:
            timestamp, id = cursor.split(':', 1)
            timestamp = int(timestamp)
            UUID(id)
            if not 0 <= timestamp <= 2**63 - 1:
                raise ValueError()
        except (ValueError, TypeError):
            raise HTTPException(422, 'Invalid cursor')
        query = query.where(or_(Comment.created_at > timestamp, and_(Comment.created_at == timestamp, Comment.id > id)))
    query = query.order_by(Comment.created_at.asc(), Comment.id.asc())
    rows = list((await db.scalars(query.limit(limit + 1))).all())
    items = rows[:limit]
    return {
        'items': await comment_responses(db, items, user, resource.user_id),
        'next_cursor': f'{items[-1].created_at}:{items[-1].id}' if len(rows) > limit else None,
    }


@router.get('/')
async def list_resource_comments(
    request: Request,
    resource_type: ResourceType,
    resource_id: str,
    cursor: str | None = None,
    limit: int = Query(20, ge=1, le=50),
    anchored: bool = False,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    resource = await comment_resource(resource_type, resource_id, user, db, request=request)
    result = await list_comments(db, user, resource, resource_type, resource_id, None, cursor, limit, anchored=anchored)
    result['total'] = await db.scalar(
        select(func.count())
        .select_from(Comment)
        .where(
            Comment.resource_type == resource_type,
            Comment.resource_id == resource_id,
            Comment.deleted_at.is_(None),
        )
    )
    return result


@router.post('/')
async def create_comment(
    request: Request, form: CommentForm, user=Depends(get_verified_user), db: AsyncSession = Depends(get_async_session)
):
    await limit_write(request, user)
    resource = await comment_resource(form.resource_type, form.resource_id, user, db, lock=True, request=request)
    now = time.time_ns()
    comment = Comment(
        id=str(form.temp_id or uuid4()),
        user_id=user.id,
        resource_type=form.resource_type,
        resource_id=form.resource_id,
        content=form.content,
        target_type=form.target_type,
        target_id=form.target_id,
        meta={'anchor': form.anchor.model_dump()} if form.anchor else None,
        created_at=now,
        updated_at=now,
    )
    previous = await db.get(Comment, comment.id)
    if previous:
        if (
            any(
                getattr(previous, key) != getattr(comment, key)
                for key in ('user_id', 'resource_type', 'resource_id', 'content', 'target_type', 'target_id', 'meta')
            )
            or previous.parent_id
            or previous.deleted_at
        ):
            raise HTTPException(409, 'Comment ID already used')
        return (await comment_responses(db, [previous], user, resource.user_id))[0]
    validate_comment_target(form.resource_type, resource, form)
    db.add(comment)
    await db.flush()
    response = (await comment_responses(db, [comment], user, resource.user_id))[0]
    from open_webui.utils.inbox import consume_event
    from open_webui.models.notifications import emit_changes

    event = build_event(
        request,
        EVENTS.COMMENT_CREATED,
        actor=user,
        subject_id=comment.id,
        subject_type='comment',
        event_id=f'comment:{comment.id}:created',
    )
    recipients = await consume_event(event, db=db)
    await db.commit()
    await emit_changes(recipients)
    await publish_event(request, event)
    await changed(form.resource_type, form.resource_id)
    return response


@router.get('/{id}')
async def get_comment(
    request: Request, id: str, user=Depends(get_verified_user), db: AsyncSession = Depends(get_async_session)
):
    comment, resource = await accessible_comment(id, user, db, request=request)
    return (await comment_responses(db, [comment], user, resource.user_id))[0]


@router.get('/{id}/replies')
async def replies(
    request: Request,
    id: str,
    cursor: str | None = None,
    limit: int = Query(50, ge=1, le=100),
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    comment, resource = await accessible_comment(id, user, db, request=request)
    if comment.parent_id:
        raise HTTPException(422, 'Replies must be requested for the starting comment')
    return await list_comments(db, user, resource, comment.resource_type, comment.resource_id, id, cursor, limit)


@router.post('/{id}/replies')
async def reply(
    request: Request,
    id: str,
    form: CommentReplyForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    await limit_write(request, user)
    parent, resource = await accessible_comment(id, user, db, lock=True, request=request)
    if parent.parent_id:
        raise HTTPException(422, 'Replies must reference the starting comment')
    reply_to = await db.get(Comment, form.reply_to_id) if form.reply_to_id else parent
    if not reply_to or reply_to.deleted_at or (reply_to.id != parent.id and reply_to.parent_id != parent.id):
        raise HTTPException(422, 'Reply target is unavailable')
    now = time.time_ns()
    comment = Comment(
        id=str(form.temp_id or uuid4()),
        user_id=user.id,
        resource_type=parent.resource_type,
        resource_id=parent.resource_id,
        parent_id=id,
        reply_to_id=form.reply_to_id,
        content=form.content,
        created_at=now,
        updated_at=now,
    )
    previous = await db.get(Comment, comment.id)
    if previous:
        if (
            any(
                getattr(previous, key) != getattr(comment, key)
                for key in ('user_id', 'parent_id', 'reply_to_id', 'content')
            )
            or previous.deleted_at
        ):
            raise HTTPException(409, 'Comment ID already used')
        return (await comment_responses(db, [previous], user, resource.user_id))[0]
    db.add(comment)
    await db.flush()
    response = (await comment_responses(db, [comment], user, resource.user_id))[0]
    from open_webui.utils.inbox import consume_event
    from open_webui.models.notifications import emit_changes

    event = build_event(
        request,
        EVENTS.COMMENT_CREATED,
        actor=user,
        subject_id=comment.id,
        subject_type='comment',
        event_id=f'comment:{comment.id}:created',
    )
    recipients = await consume_event(event, db=db)
    await db.commit()
    await emit_changes(recipients)
    await publish_event(request, event)
    await changed(parent.resource_type, parent.resource_id)
    return response


@router.patch('/{id}')
async def edit(
    request: Request,
    id: str,
    form: CommentUpdateForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    await limit_write(request, user)
    comment, resource = await accessible_comment(id, user, db, lock=True, request=request)
    if comment.user_id != user.id or comment.deleted_at:
        raise HTTPException(403, 'Cannot edit this comment')
    if str(comment.updated_at) != form.etag:
        raise HTTPException(409, 'Comment changed. Reload before editing.')
    previous_content = comment.content
    result = await db.execute(
        update(Comment)
        .where(Comment.id == id, Comment.updated_at == int(form.etag), Comment.deleted_at.is_(None))
        .values(content=form.content, updated_at=max(time.time_ns(), comment.updated_at + 1))
        .execution_options(synchronize_session=False)
    )
    if result.rowcount != 1:
        raise HTTPException(409, 'Comment changed. Reload before editing.')
    await db.refresh(comment)
    response = (await comment_responses(db, [comment], user, resource.user_id))[0]
    from open_webui.utils.inbox import consume_event
    from open_webui.models.notifications import emit_changes

    event = build_event(
        request,
        EVENTS.COMMENT_UPDATED,
        actor=user,
        subject_id=comment.id,
        subject_type='comment',
        event_id=f'comment:{comment.id}:{comment.updated_at}',
        data={'previous_mentions': sorted(mentioned_users(previous_content))},
    )
    recipients = await consume_event(event, db=db)
    await db.commit()
    await emit_changes(recipients)
    await publish_event(request, event)
    await changed(comment.resource_type, comment.resource_id)
    return response


@router.delete('/{id}')
async def remove(
    request: Request,
    id: str,
    etag: str = Query(pattern=r'^\d{1,20}$'),
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    comment, resource = await accessible_comment(id, user, db, lock=True, request=request)
    if comment.user_id != user.id and resource.user_id != user.id and user.role != 'admin':
        raise HTTPException(403, 'Cannot delete this comment')
    if str(comment.updated_at) != etag:
        raise HTTPException(409, 'Comment changed. Reload before deleting.')
    await limit_write(request, user)
    kind, resource_id = comment.resource_type, comment.resource_id
    now = time.time_ns()
    result = await db.execute(
        update(Comment)
        .where(Comment.id == id, Comment.updated_at == int(etag), Comment.deleted_at.is_(None))
        .values(content='', user_id=None, meta=None, deleted_at=now, updated_at=now)
        .execution_options(synchronize_session=False)
    )
    if result.rowcount != 1:
        raise HTTPException(409, 'Comment changed. Reload before deleting.')
    await db.execute(delete(CommentReaction).where(CommentReaction.comment_id == id))
    recipients = await delete_notifications(object_type='comment', object_ids=[id], db=db)
    # Keep thread and quoted-reply references intact, without retaining deleted text.
    await db.commit()
    await emit_changes(recipients)
    await changed(kind, resource_id)
    return True


class ReactionForm(BaseModel):
    name: str = Field(min_length=1, max_length=100)


@router.put('/{id}/reactions')
async def add_reaction(
    request: Request,
    id: str,
    form: ReactionForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    await limit_write(request, user, reaction_limiter)
    comment, resource = await accessible_comment(id, user, db, lock=True, request=request)
    if comment.deleted_at:
        raise HTTPException(409, 'Comment was deleted')
    existing = await db.scalar(
        select(CommentReaction.id).where(
            CommentReaction.comment_id == id, CommentReaction.user_id == user.id, CommentReaction.name == form.name
        )
    )
    if not existing:
        try:
            async with db.begin_nested():
                db.add(
                    CommentReaction(
                        id=str(uuid4()), comment_id=id, user_id=user.id, name=form.name, created_at=time.time_ns()
                    )
                )
                await db.flush()
        except IntegrityError:
            # A concurrent identical reaction is already the requested result.
            pass
    await db.commit()
    await changed(comment.resource_type, comment.resource_id)
    return True


@router.delete('/{id}/reactions')
async def remove_reaction(
    request: Request,
    id: str,
    name: str = Query(min_length=1, max_length=100),
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    await limit_write(request, user, reaction_limiter)
    comment, resource = await accessible_comment(id, user, db, lock=True, request=request)
    await db.execute(
        delete(CommentReaction).where(
            CommentReaction.comment_id == id, CommentReaction.user_id == user.id, CommentReaction.name == name
        )
    )
    await db.commit()
    await changed(comment.resource_type, comment.resource_id)
    return True
