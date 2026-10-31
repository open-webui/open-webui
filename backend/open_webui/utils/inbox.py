"""Resource-aware producers and reads for the general inbox."""

from collections import defaultdict

from sqlalchemy import and_, false, or_, select, true
from sqlalchemy.orm import load_only

from open_webui.models.notifications import Notification, insert_notifications


def source_models():
    from open_webui.utils.comments import resource_models
    from open_webui.models.automations import Automation, AutomationRun
    from open_webui.models.calendar import Calendar, CalendarEvent
    from open_webui.models.channels import Channel
    from open_webui.models.comments import Comment
    from open_webui.models.messages import Message

    return {
        **resource_models(),
        'automation': Automation,
        'automation_run': AutomationRun,
        'calendar': Calendar,
        'calendar_event': CalendarEvent,
        'channel': Channel,
        'comment': Comment,
        'message': Message,
    }


async def validate_source(event_type, resource_type, resource_id, object_type, object_id, db):
    if event_type == 'system.announcement':
        if any((resource_type, resource_id, object_type, object_id)):
            raise ValueError('System announcements cannot attach resources')
        return
    models = source_models()
    if (
        not all((resource_type, resource_id, object_type, object_id))
        or resource_type not in models
        or object_type not in models
    ):
        raise ValueError('Incomplete notification source')
    obj = await db.get(models[object_type], object_id)
    if obj is None:
        raise ValueError('Notification object does not exist')
    valid = False
    if event_type.startswith('comment.'):
        valid = (
            object_type == 'comment'
            and not obj.deleted_at
            and (obj.resource_type, obj.resource_id) == (resource_type, resource_id)
        )
    elif event_type.startswith('channel.'):
        valid = object_type == 'message' and resource_type == 'channel' and obj.channel_id == resource_id
    elif event_type == 'automation.run_failed':
        valid = (
            object_type == 'automation_run'
            and resource_type == 'automation'
            and obj.automation_id == resource_id
            and obj.status == 'error'
        )
    elif event_type == 'calendar.alert':
        valid = (
            object_type == 'calendar_event'
            and resource_type == 'calendar'
            and obj.calendar_id == resource_id
            and not obj.is_cancelled
        )
    if not valid:
        raise ValueError('Notification object does not belong to resource')


async def resource_queries(user, db):
    """One set of indexed permission subqueries, shared by listing, counts and writes."""
    from open_webui.config import BYPASS_ADMIN_ACCESS_CONTROL
    from open_webui.env import ENABLE_ADMIN_CHAT_ACCESS
    from open_webui.models.access_grants import AccessGrants
    from open_webui.models.channels import ChannelMember
    from open_webui.models.config import Config
    from open_webui.models.folders import Folder
    from open_webui.models.groups import Groups
    from open_webui.models.shared_chats import SharedChat
    from open_webui.utils.access_control import has_permission

    if user.role not in {'user', 'admin'}:
        return {}
    groups = [g.id for g in await Groups.get_groups_by_member_id(user.id, db=db, include_inherited=True)]
    config = await Config.get_many(
        'comments.enable',
        'notes.enable',
        'channels.enable',
        'calendar.enable',
        'automations.enable',
        'user.permissions',
    )
    admin = user.role == 'admin'

    def grant(kind, column):
        return AccessGrants.has_grant_expression(user.id, kind, column, user_group_ids=groups)

    async def enabled(feature):
        return config.get(f'{feature}.enable') and (
            admin or await has_permission(user.id, f'features.{feature}', config.get('user.permissions'), db=db)
        )

    models = source_models()
    queries = {}
    for kind in ('model', 'knowledge', 'prompt', 'skill', 'tool', 'note'):
        if not config.get('comments.enable') or (kind == 'note' and not await enabled('notes')):
            continue
        model = models[kind]
        allowed = (
            true()
            if admin and (kind == 'note' or BYPASS_ADMIN_ACCESS_CONTROL)
            else or_(model.user_id == user.id, grant(kind, model.id))
        )
        queries[kind] = select(model.id).where(allowed)
    if config.get('comments.enable'):
        chat = models['chat']
        # UNION (not UNION ALL) terminates even if legacy folder data contains a cycle.
        folders = (
            select(Folder.id)
            .where(or_(Folder.user_id == user.id, grant('folder', Folder.id)))
            .cte('inbox_folders', recursive=True)
        )
        folders = folders.union(select(Folder.id).join(folders, Folder.parent_id == folders.c.id))
        shared = select(SharedChat.chat_id).where(
            SharedChat.chat['share_mode'].as_string() == 'continue', grant('shared_chat', SharedChat.chat_id)
        )
        queries['chat'] = select(chat.id).where(
            or_(
                chat.user_id == user.id,
                true() if admin and ENABLE_ADMIN_CHAT_ACCESS else false(),
                and_(true() if admin else false(), chat.meta['internal'].as_boolean().is_(True)),
                chat.id.in_(shared),
                chat.folder_id.in_(select(folders.c.id)),
            )
        )
    if await enabled('channels'):
        channel = models['channel']
        member = (
            select(ChannelMember.id)
            .where(
                ChannelMember.channel_id == channel.id,
                ChannelMember.user_id == user.id,
                ChannelMember.is_active.is_(True),
            )
            .exists()
        )
        queries['channel'] = select(channel.id).where(
            channel.deleted_at.is_(None),
            or_(
                and_(channel.type.in_(['group', 'dm']), member),
                and_(
                    or_(channel.type.is_(None), channel.type.not_in(['group', 'dm'])),
                    true() if admin else grant('channel', channel.id),
                ),
            ),
        )
    if await enabled('calendar'):
        model = models['calendar']
        queries['calendar'] = select(model.id).where(
            true() if admin else or_(model.user_id == user.id, grant('calendar', model.id))
        )
    if await enabled('automations'):
        model = models['automation']
        queries['automation'] = select(model.id).where(model.user_id == user.id)
    return queries


async def eligible_recipients(recipients, resource_type, resource_id, actor_id, db):
    from open_webui.models.users import User, UserModel

    users = (await db.scalars(select(User).where(User.id.in_(recipients), User.role.in_(['user', 'admin'])))).all()
    eligible = {}
    for row in users:
        kind = recipients[row.id]
        if row.id == actor_id and kind.startswith(('comment.', 'channel.')):
            continue
        if resource_type is not None:
            queries = await resource_queries(UserModel.model_validate(row), db=db)
            query = queries.get(resource_type)
            if query is None or not await db.scalar(
                select(query.where(source_models()[resource_type].id == resource_id).exists())
            ):
                continue
        eligible[row.id] = kind
    return eligible


async def visible_clause(user, db):
    queries = await resource_queries(user, db=db)
    models = source_models()
    resources = or_(
        *[
            and_(Notification.resource_type == kind, Notification.resource_id.in_(query))
            for kind, query in queries.items()
        ]
    )
    objects = []
    for kind, parent_column, events in (
        ('comment', 'resource_id', ['comment.created', 'comment.replied', 'comment.mentioned']),
        ('message', 'channel_id', ['channel.mentioned', 'channel.replied']),
        ('automation_run', 'automation_id', ['automation.run_failed']),
        ('calendar_event', 'calendar_id', ['calendar.alert']),
    ):
        model = models[kind]
        conditions = [model.id == Notification.object_id, getattr(model, parent_column) == Notification.resource_id]
        if kind == 'comment':
            conditions += [model.resource_type == Notification.resource_type, model.deleted_at.is_(None)]
        if kind == 'calendar_event':
            conditions.append(model.is_cancelled.is_(False))
        objects.append(
            and_(
                Notification.event_type.in_(events),
                Notification.object_type == kind,
                select(model.id).where(*conditions).exists(),
            )
        )
    return (
        and_(
            Notification.user_id == user.id,
            or_(
                and_(
                    Notification.event_type == 'system.announcement',
                    Notification.resource_type.is_(None),
                    Notification.object_type.is_(None),
                ),
                and_(resources, or_(*objects)),
            ),
        )
        if user.role in {'user', 'admin'}
        else false()
    )


async def hydrate(rows, db):
    """Fetch each actor/resource/object type once, never once per notification."""
    from open_webui.models.users import User
    from open_webui.utils.channels import replace_mentions

    models = source_models()
    ids = defaultdict(set)
    for row in rows:
        if row.resource_type:
            ids[row.resource_type].add(row.resource_id)
        if row.object_type:
            ids[row.object_type].add(row.object_id)
    objects = {}
    for kind, values in ids.items():
        model = models[kind]
        fields = ['id', 'title', 'name']
        if kind in {'comment', 'message'}:
            fields += ['content', 'target_type', 'target_id', 'parent_id']
        columns = [getattr(model, field) for field in fields if hasattr(model, field)]
        objects[kind] = {
            obj.id: obj
            for obj in (await db.scalars(select(model).options(load_only(*columns)).where(model.id.in_(values)))).all()
        }
    actors = {
        u.id: {'id': u.id, 'name': u.name}
        for u in (
            await db.scalars(
                select(User)
                .options(load_only(User.id, User.name))
                .where(User.id.in_({r.actor_id for r in rows if r.actor_id}))
            )
        ).all()
    }
    result = []
    for row in rows:
        resource = objects.get(row.resource_type, {}).get(row.resource_id)
        obj = objects.get(row.object_type, {}).get(row.object_id)
        title = (
            getattr(resource, 'title', None)
            or getattr(resource, 'name', None)
            or ''
        )
        preview = (
            replace_mentions(getattr(obj, 'content', '') or '')[:300]
            if row.object_type in {'comment', 'message'}
            else ''
        )
        data = dict(row.data or {})
        if row.object_type == 'comment':
            data.update(target_type=obj.target_type, target_id=obj.target_id, parent_id=obj.parent_id)
        elif row.object_type == 'message':
            data['parent_id'] = obj.parent_id
        elif row.object_type == 'calendar_event':
            title = obj.title
        result.append(
            {
                **{c.name: getattr(row, c.name) for c in Notification.__table__.columns},
                'actor': actors.get(row.actor_id),
                'title': title,
                'preview': preview,
                'data': data,
                # Epoch nanoseconds must not become imprecise JavaScript cursor values.
                'created_at': str(row.created_at),
                'updated_at': str(row.updated_at),
                'seen_at': str(row.seen_at) if row.seen_at is not None else None,
                'read_at': str(row.read_at) if row.read_at is not None else None,
            }
        )
    return result


def mentioned_users(content):
    from open_webui.utils.channels import extract_mentions

    return {m['id'] for m in extract_mentions(content or '') if m['id_type'] == 'U'}


async def comment_notifications(comment, owner_id, *, reply_to=None, previous_mentions=None, event_key=None, db):
    mentions = mentioned_users(comment.content)
    recipients = {}
    if previous_mentions is None:
        recipients = {
            id: 'comment.replied' if comment.parent_id else 'comment.created'
            for id in (owner_id, getattr(reply_to, 'user_id', None))
            if id
        }
    else:
        mentions -= set(previous_mentions)
    recipients.update({id: 'comment.mentioned' for id in mentions})
    return await insert_notifications(
        recipients=recipients,
        event_key=event_key
        or f'comment:{comment.id}:{(comment.updated_at if previous_mentions is not None else "created")}',
        actor_id=comment.user_id,
        resource_type=comment.resource_type,
        resource_id=comment.resource_id,
        object_type='comment',
        object_id=comment.id,
        db=db,
    )


async def channel_notifications(message, *, event_key=None, actor_type='user', db):
    from open_webui.models.channels import ChannelMember
    from open_webui.models.messages import Message

    mentions = mentioned_users(message.content)
    target = (
        await db.get(Message, message.reply_to_id or message.parent_id)
        if message.reply_to_id or message.parent_id
        else None
    )
    recipients = (
        {target.user_id: 'channel.replied'}
        if target and target.channel_id == message.channel_id and target.user_id
        else {}
    )
    recipients.update({id: 'channel.mentioned' for id in mentions})
    muted = (
        await db.scalars(
            select(ChannelMember.user_id).where(
                ChannelMember.channel_id == message.channel_id,
                ChannelMember.user_id.in_(recipients),
                ChannelMember.is_channel_muted.is_(True),
            )
        )
    ).all()
    for id in muted:
        if id not in mentions:
            recipients.pop(id, None)
    return await insert_notifications(
        recipients=recipients,
        event_key=event_key or f'message:{message.id}:created',
        actor_id=message.user_id if actor_type == 'user' else None,
        resource_type='channel',
        resource_id=message.channel_id,
        object_type='message',
        object_id=message.id,
        db=db,
    )


async def consume_event(event, db):
    """Transactional inbox consumer; source producers publish facts, not recipients."""
    from open_webui.events import EVENTS
    from open_webui.models.config import Config

    if not await Config.get('notifications.enable'):
        return set()

    subject_id = (event.subject or {}).get('id')
    models = source_models()
    if event.event in {EVENTS.COMMENT_CREATED.name, EVENTS.COMMENT_UPDATED.name}:
        comment = await db.get(models['comment'], subject_id)
        if not comment or comment.deleted_at:
            raise ValueError('Comment event references an unavailable comment')
        resource_model = models[comment.resource_type]
        owner_id = await db.scalar(select(resource_model.user_id).where(resource_model.id == comment.resource_id))
        reply_to = (
            await db.get(models['comment'], comment.reply_to_id or comment.parent_id) if comment.parent_id else None
        )
        recipients = await comment_notifications(
            comment,
            owner_id,
            reply_to=reply_to,
            previous_mentions=event.data.get('previous_mentions', [])
            if event.event == EVENTS.COMMENT_UPDATED.name
            else None,
            event_key=event.id,
            db=db,
        )
        if event.event == EVENTS.COMMENT_UPDATED.name:
            existing = await db.scalars(
                select(Notification.user_id)
                .where(Notification.object_type == 'comment', Notification.object_id == comment.id)
                .distinct()
            )
            recipients.update(existing.all())
        return recipients
    elif event.event == EVENTS.MESSAGE_CREATED.name:
        message = await db.get(models['message'], subject_id)
        if message and message.channel_id:
            return await channel_notifications(
                message, event_key=event.id, actor_type=(event.actor or {}).get('type', 'system'), db=db
            )
    elif event.event == EVENTS.AUTOMATION_RUN_FAILED.name:
        run = await db.get(models['automation_run'], event.data.get('run_id'))
        automation = await db.get(models['automation'], subject_id)
        if not run or not automation or run.automation_id != automation.id:
            raise ValueError('Automation failure event requires its persisted run')
        return await insert_notifications(
            recipients={automation.user_id: event.event},
            event_key=event.id,
            resource_type='automation',
            resource_id=automation.id,
            object_type='automation_run',
            object_id=run.id,
            db=db,
        )
    elif event.event == EVENTS.CALENDAR_ALERT.name:
        calendar_event = await db.get(models['calendar_event'], subject_id)
        if not calendar_event or event.data.get('start_at') != calendar_event.start_at:
            raise ValueError('Calendar alert must reference the current occurrence')
        return await insert_notifications(
            recipients={calendar_event.user_id: event.event},
            event_key=event.id,
            resource_type='calendar',
            resource_id=calendar_event.calendar_id,
            object_type='calendar_event',
            object_id=calendar_event.id,
            data={'start_at': calendar_event.start_at},
            db=db,
        )

    return set()
