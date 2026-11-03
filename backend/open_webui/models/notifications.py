"""Persistent, per-recipient inbox activity. Writers never commit the caller's transaction."""

import logging
import time
from uuid import uuid4

from open_webui.internal.db import Base
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import JSON, BigInteger, CheckConstraint, Column, Index, Text, UniqueConstraint, delete, update

log = logging.getLogger(__name__)


class Notification(Base):
    __tablename__ = 'notification'
    id = Column(Text, primary_key=True)
    user_id = Column(Text, nullable=False)
    event_type = Column(Text, nullable=False)
    event_key = Column(Text, nullable=False)
    actor_type = Column(Text, nullable=False)
    actor_id = Column(Text, nullable=True)
    resource_type = Column(Text, nullable=True)
    resource_id = Column(Text, nullable=True)
    object_type = Column(Text, nullable=True)
    object_id = Column(Text, nullable=True)
    data = Column(JSON, nullable=False)
    seen_at = Column(BigInteger, nullable=True)
    read_at = Column(BigInteger, nullable=True)
    created_at = Column(BigInteger, nullable=False)
    updated_at = Column(BigInteger, nullable=False)
    __table_args__ = (
        UniqueConstraint('user_id', 'event_key', name='uq_notification_occurrence'),
        CheckConstraint('(resource_type IS NULL) = (resource_id IS NULL)', name='ck_notification_resource'),
        CheckConstraint('(object_type IS NULL) = (object_id IS NULL)', name='ck_notification_object'),
        CheckConstraint("actor_type IN ('user', 'system')", name='ck_notification_actor'),
        Index('ix_notification_user_created', 'user_id', 'created_at', 'id'),
        Index(
            'ix_notification_unseen',
            'user_id',
            'created_at',
            'id',
            sqlite_where=seen_at.is_(None),
            postgresql_where=seen_at.is_(None),
        ),
        Index('ix_notification_resource', 'resource_type', 'resource_id'),
        Index('ix_notification_object', 'object_type', 'object_id'),
    )


class NotificationData(BaseModel):
    model_config = ConfigDict(extra='forbid')


class ReminderData(NotificationData):
    start_at: int


class SystemData(NotificationData):
    message: str = Field(min_length=1, max_length=2000)


DATA_TYPES = {
    'comment.created': NotificationData,
    'comment.replied': NotificationData,
    'comment.mentioned': NotificationData,
    'channel.mentioned': NotificationData,
    'channel.replied': NotificationData,
    'calendar.alert': ReminderData,
    'automation.run_failed': NotificationData,
    'system.announcement': SystemData,
}


async def emit_changes(user_ids):
    from open_webui.socket.main import sio

    for user_id in user_ids:
        try:
            await sio.emit('notifications:changed', {}, room=f'user:{user_id}')
        except Exception:
            log.exception('Could not broadcast inbox change for %s', user_id)


async def insert_notifications(
    *,
    recipients,
    event_key,
    actor_id=None,
    resource_type=None,
    resource_id=None,
    object_type=None,
    object_id=None,
    data=None,
    db,
):
    """recipients maps user IDs to event types; the producer chooses the strongest reason."""
    from open_webui.models.config import Config
    from open_webui.utils.inbox import validate_source, eligible_recipients

    if not recipients or not await Config.get('notifications.enable'):
        return set()
    if not event_key or len(event_key) > 512:
        raise ValueError('Invalid notification occurrence')
    payloads = {kind: DATA_TYPES[kind].model_validate(data or {}).model_dump() for kind in set(recipients.values())}
    for event_type in payloads:
        await validate_source(event_type, resource_type, resource_id, object_type, object_id, db=db)
    recipients = await eligible_recipients(recipients, resource_type, resource_id, actor_id, db=db)
    if not recipients:
        return set()
    dialect = db.get_bind().dialect.name
    if dialect == 'postgresql':
        from sqlalchemy.dialects.postgresql import insert
    elif dialect == 'sqlite':
        from sqlalchemy.dialects.sqlite import insert
    else:
        raise ValueError('Inbox requires SQLite or PostgreSQL')
    try:
        now = time.time_ns()
        result = await db.execute(
            insert(Notification)
            .on_conflict_do_nothing(index_elements=['user_id', 'event_key'])
            .returning(Notification.user_id),
            [
                dict(
                    id=str(uuid4()),
                    user_id=user_id,
                    event_type=event_type,
                    event_key=event_key,
                    actor_type='user' if actor_id else 'system',
                    actor_id=actor_id,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    object_type=object_type,
                    object_id=object_id,
                    data=payloads[event_type],
                    created_at=now,
                    updated_at=now,
                )
                for user_id, event_type in recipients.items()
            ],
        )
        return set(result.scalars().all())
    except Exception:
        log.exception('Inbox insertion failed for occurrence %s', event_key)
        raise


async def delete_notifications(*, resource_type=None, resource_ids=None, object_type=None, object_ids=None, db):
    condition = (
        (Notification.resource_type == resource_type) & Notification.resource_id.in_(resource_ids)
        if resource_type
        else (Notification.object_type == object_type) & Notification.object_id.in_(object_ids)
    )
    recipients = (
        (await db.execute(delete(Notification).where(condition).returning(Notification.user_id))).scalars().all()
    )
    return set(recipients)


async def delete_user_notifications(user_id, db):
    await db.execute(delete(Notification).where(Notification.user_id == user_id))
    await db.execute(update(Notification).where(Notification.actor_id == user_id).values(actor_id=None))
