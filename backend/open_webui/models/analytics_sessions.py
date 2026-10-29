"""Read-only session analytics over existing chats and saved messages."""

import math

from open_webui.models.chat_messages import ChatMessage, _token_columns
from open_webui.models.chats import Chat
from open_webui.models.folders import Folder
from open_webui.models.groups import group_user_memberships
from open_webui.models.users import User
from open_webui.utils.session_records import safe_snippet
from sqlalchemy import (
    ARRAY,
    JSON,
    Float,
    Integer,
    Text,
    case,
    cast,
    distinct,
    func,
    literal,
    or_,
    select,
    true,
    union_all,
)
from sqlalchemy.ext.asyncio import AsyncSession


def json_text(db, column, *path):
    if db.get_bind().dialect.name == 'sqlite':
        return func.json_extract(column, '$' + ''.join(f'.{key}' for key in path))
    return (
        func.json_extract_path_text(column, *path)
        if path
        else column.op('#>>', return_type=Text)(cast(literal('{}'), ARRAY(Text)))
    )


def json_type(db, column):
    return func.json_type(column) if db.get_bind().dialect.name == 'sqlite' else func.json_typeof(column)


def message_filters(start_date=None, end_date=None):
    conditions = []
    if start_date is not None:
        conditions.append(ChatMessage.created_at >= start_date)
    if end_date is not None:
        conditions.append(ChatMessage.created_at <= end_date)
    return conditions


def chat_filters(db, group_id=None, query='', hide_subagents=False, model_id=None, start_date=None, end_date=None):
    conditions = []
    if group_id:
        members = group_user_memberships([group_id], True)
        conditions.append(Chat.user_id.in_(select(members.c.user_id)))
    if query.strip():
        # Literal search: '%' and '_' in titles are not wildcard operators.
        term = '%' + query.strip().replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_') + '%'
        conditions.append(
            or_(
                Chat.title.ilike(term, escape='\\'),
                User.name.ilike(term, escape='\\'),
                Folder.name.ilike(term, escape='\\'),
            )
        )
    if hide_subagents:
        conditions.append(func.coalesce(json_text(db, Chat.meta, 'type'), '') != 'subagent')
    if model_id:
        conditions.append(
            select(ChatMessage.id)
            .where(
                ChatMessage.chat_id == Chat.id,
                ChatMessage.model_id == model_id,
                *message_filters(start_date, end_date),
            )
            .exists()
        )
    return conditions


def session_query(
    db, *, start_date=None, end_date=None, group_id=None, query='', hide_subagents=False, model_id=None, chat_id=None
):
    input_tokens, output_tokens = _token_columns(db.get_bind().dialect.name)
    assistant = ChatMessage.role == 'assistant'
    human = (ChatMessage.role == 'user') & (
        func.coalesce(cast(json_text(db, ChatMessage.meta, 'internal'), Text), 'false').notin_(['true', '1'])
    )
    timestamp = case((ChatMessage.created_at > 0, ChatMessage.created_at))
    recorded = assistant & (input_tokens.isnot(None) | output_tokens.isnot(None))
    error = func.coalesce(cast(ChatMessage.error, Text), 'null').notin_(['null', '""', '{}', 'false'])
    filters = message_filters(start_date, end_date)
    if chat_id:
        filters.append(ChatMessage.chat_id == chat_id)
    # No transcript/output columns enter the list query, even when sorting by tokens.
    cache_fields = {
        'cache_read': func.coalesce(
            json_text(db, ChatMessage.usage, 'cache_read_input_tokens'),
            json_text(db, ChatMessage.usage, 'input_tokens_details', 'cached_tokens'),
            json_text(db, ChatMessage.usage, 'prompt_tokens_details', 'cached_tokens'),
        ),
        'cache_write': func.coalesce(
            json_text(db, ChatMessage.usage, 'cache_creation_input_tokens'),
            json_text(db, ChatMessage.usage, 'input_tokens_details', 'cache_write_tokens'),
            json_text(db, ChatMessage.usage, 'prompt_tokens_details', 'cache_write_tokens'),
        ),
    }
    stats = (
        select(
            ChatMessage.chat_id.label('chat_id'),
            *[func.sum(case((assistant, cast(field, Integer)))).label(key) for key, field in cache_fields.items()],
            *[
                func.sum(case((assistant & field.isnot(None), 1), else_=0)).label(key + '_responses')
                for key, field in cache_fields.items()
            ],
            func.count().label('messages'),
            func.sum(case((assistant, 1), else_=0)).label('responses'),
            func.sum(case((human, 1), else_=0)).label('prompts'),
            func.sum(case((recorded, 1), else_=0)).label('recorded_responses'),
            func.sum(
                case(
                    (
                        assistant
                        & input_tokens.isnot(None)
                        & output_tokens.isnot(None)
                        & func.coalesce(ChatMessage.usage['incomplete'].as_boolean(), False).is_(False),
                        1,
                    ),
                    else_=0,
                )
            ).label('complete_responses'),
            func.sum(
                case((assistant, func.coalesce(input_tokens, 0) + func.coalesce(output_tokens, 0)), else_=0)
            ).label('tokens'),
            func.sum(case((assistant & error, 1), else_=0)).label('errors'),
            func.min(timestamp).label('started_at'),
            func.max(timestamp).label('last_active'),
            case((func.count(timestamp) == func.count(), func.max(timestamp) - func.min(timestamp))).label(
                'span_seconds'
            ),
            func.min(case((assistant, ChatMessage.model_id))).label('model_id'),
            func.count(distinct(case((assistant, ChatMessage.model_id)))).label('model_count'),
        )
        .where(*filters)
        .group_by(ChatMessage.chat_id)
        .subquery()
    )
    statement = (
        select(
            Chat.id,
            func.substr(Chat.title, 1, 200).label('title'),
            User.id.label('user_id'),
            User.name.label('user_name'),
            Folder.name.label('folder_name'),
            json_text(db, Chat.meta, 'type').label('kind'),
            json_text(db, Chat.meta, 'forked_from').label('forked_from'),
            *[column for column in stats.c if column.name != 'chat_id'],
        )
        .join(stats, stats.c.chat_id == Chat.id)
        .outerjoin(User, User.id == Chat.user_id)
        .outerjoin(Folder, Folder.id == Chat.folder_id)
    )
    return statement.where(*chat_filters(db, group_id, query, hide_subagents, model_id, start_date, end_date)), stats


def page_result(rows, limit):
    items = [dict(row) for row in rows[:limit]]
    for item in items:
        if 'title' in item:
            item['title'] = safe_snippet(item['title']) or ''
    return {'items': items, 'has_more': len(rows) > limit}


TOKEN_RANGES = [(0, 1), (1, 1000), (1000, 10000), (10000, 100000), (100000, 1000000), (1000000, None)]


async def list_sessions(
    db: AsyncSession,
    *,
    skip=0,
    limit=25,
    order_by='recent',
    direction='desc',
    include_summary=False,
    token_min=None,
    token_max=None,
    **filters,
):
    statement, stats = session_query(db, **filters)
    order = {
        'title': func.lower(Chat.title),
        'user': func.lower(User.name),
        'recent': stats.c.last_active,
        'tokens': case((stats.c.recorded_responses > 0, stats.c.tokens)),
        'responses': stats.c.responses,
        'errors': stats.c.errors,
        'duration': stats.c.span_seconds,
    }[order_by]
    order = order.asc() if direction == 'asc' else order.desc()
    # The overview stays on the full search scope while its bars filter the table.
    page_statement = statement
    if token_min is not None or token_max is not None:
        page_statement = page_statement.where(stats.c.recorded_responses > 0)
    if token_min is not None:
        page_statement = page_statement.where(stats.c.tokens >= token_min)
    if token_max is not None:
        page_statement = page_statement.where(stats.c.tokens < token_max)
    rows = (
        (await db.execute(page_statement.order_by(order.nulls_last(), Chat.id).offset(skip).limit(limit + 1)))
        .mappings()
        .all()
    )
    result = page_result(rows, limit)
    if include_summary:
        eligible = statement.subquery()
        totals = (
            (
                await db.execute(
                    select(
                        func.count().label('sessions'),
                        func.coalesce(func.max(eligible.c.tokens), 0).label('max_tokens'),
                        func.count(case((eligible.c.recorded_responses == 0, 1))).label('unrecorded_sessions'),
                        *[
                            func.count(
                                case(
                                    (
                                        (eligible.c.recorded_responses > 0)
                                        & (eligible.c.tokens >= low)
                                        & ((eligible.c.tokens < high) if high is not None else true()),
                                        1,
                                    )
                                )
                            ).label(f'token_range_{index}')
                            for index, (low, high) in enumerate(TOKEN_RANGES)
                        ],
                        *[
                            func.coalesce(func.sum(eligible.c[key]), 0).label(key)
                            for key in (
                                'tokens',
                                'prompts',
                                'responses',
                                'errors',
                                'recorded_responses',
                                'complete_responses',
                            )
                        ],
                        func.min(eligible.c.started_at).label('start'),
                        func.max(eligible.c.last_active).label('end'),
                    )
                )
            )
            .mappings()
            .one()
        )
        result['overview'] = dict(totals)
        result['overview']['token_distribution'] = [
            result['overview'].pop(f'token_range_{index}') for index in range(len(TOKEN_RANGES))
        ]
    return result


async def session_messages(
    db: AsyncSession, chat_id: str, *, start_date=None, end_date=None, group_id=None, skip=0, limit=25
):
    statement, _ = session_query(db, chat_id=chat_id, start_date=start_date, end_date=end_date, group_id=group_id)
    session = (await db.execute(statement)).mappings().first()
    if session is None:
        return None
    input_tokens, output_tokens = _token_columns(db.get_bind().dialect.name)
    content = case(
        (json_type(db, ChatMessage.content).in_(['text', 'string']), json_text(db, ChatMessage.content)), else_=None
    )
    output_count = func.json_array_length(ChatMessage.output)
    output_count = case((json_type(db, ChatMessage.output) == 'array', output_count), else_=0)
    rows = (
        (
            await db.execute(
                select(
                    ChatMessage.id,
                    ChatMessage.role,
                    ChatMessage.model_id,
                    ChatMessage.created_at,
                    ChatMessage.parent_id,
                    ChatMessage.done,
                    func.substr(content, 1, 320).label('preview'),
                    (func.length(content) > 320).label('preview_truncated'),
                    func.substr(json_text(db, ChatMessage.error), 1, 500).label('error'),
                    case(
                        (
                            input_tokens.isnot(None) | output_tokens.isnot(None),
                            func.coalesce(input_tokens, 0) + func.coalesce(output_tokens, 0),
                        )
                    ).label('tokens'),
                    output_count.label('output_count'),
                )
                .where(ChatMessage.chat_id == chat_id, *message_filters(start_date, end_date))
                .order_by(ChatMessage.created_at, ChatMessage.id)
                .offset(skip)
                .limit(limit + 1)
            )
        )
        .mappings()
        .all()
    )
    session = {**dict(session), 'title': safe_snippet(session['title']) or ''}
    result = {'session': session, **page_result(rows, limit)}
    for item in result['items']:
        item['preview'] = safe_snippet(item['preview'])
        item['error'] = safe_snippet(item['error'])
    return result


def finite_number(value):
    if isinstance(value, bool):
        return None
    try:
        result = float(value)
        return result if math.isfinite(result) and result >= 0 else None
    except (ValueError, TypeError):
        return None


def output_items(db):
    empty = literal('[]') if db.get_bind().dialect.name == 'sqlite' else cast(literal('[]'), JSON)
    output = case((json_type(db, ChatMessage.output) == 'array', ChatMessage.output), else_=empty)
    if db.get_bind().dialect.name == 'sqlite':
        items = func.json_each(output).table_valued('key', 'value', 'type', joins_implicitly=True)
        index = cast(items.c.key, Integer)
        value = case((items.c.type == 'object', items.c.value), else_=literal('{}'))
    else:
        items = func.json_array_elements(output).table_valued('value', with_ordinality='ordinality').render_derived()
        index = items.c.ordinality - 1
        value = items.c.value

    def field(key):
        return json_text(db, value, key)

    return items, index, field


async def message_events(
    db: AsyncSession, chat_id: str, message_id: str, *, group_id=None, start_date=None, end_date=None, skip=0, limit=20
):
    # Guard the detail independently; IDs must not bypass the active group/date scope.
    allowed = (
        select(ChatMessage.id)
        .join(Chat, Chat.id == ChatMessage.chat_id)
        .where(
            Chat.id == chat_id,
            ChatMessage.id == message_id,
            *message_filters(start_date, end_date),
            *chat_filters(db, group_id=group_id),
        )
    )
    if (await db.execute(allowed)).scalar_one_or_none() is None:
        return None
    items, index, field = output_items(db)

    details = func.coalesce(
        field('arguments'),
        field('output'),
        field('content'),
        field('summary'),
        field('text'),
        field('code'),
        field('error'),
    )
    statement = (
        select(
            index.label('index'),
            func.substr(cast(field('type'), Text), 1, 80).label('type'),
            func.substr(cast(field('name'), Text), 1, 160).label('name'),
            func.substr(cast(field('call_id'), Text), 1, 200).label('call_id'),
            func.substr(cast(field('status'), Text), 1, 64).label('status'),
            func.substr(cast(field('error_type'), Text), 1, 80).label('error_type'),
            func.substr(cast(field('started_at'), Text), 1, 64).label('started_at'),
            func.substr(cast(field('ended_at'), Text), 1, 64).label('ended_at'),
            func.substr(cast(field('duration'), Text), 1, 64).label('duration_seconds'),
            func.substr(cast(details, Text), 1, 2000).label('details'),
            (func.length(cast(details, Text)) > 2000).label('truncated'),
        )
        .select_from(ChatMessage)
        .join(items, true())
        .where(ChatMessage.id == message_id, ChatMessage.chat_id == chat_id)
    )
    rows = (await db.execute(statement.order_by(index).offset(skip).limit(limit + 1))).mappings().all()
    result = page_result(rows, limit)
    normalize_durations(result['items'])
    for item in result['items']:
        item['details'] = safe_snippet(item['details'])
        item['truncated'] = True
    return result


def normalize_durations(items):
    for item in items:
        for key in ('started_at', 'ended_at', 'duration_seconds'):
            item[key] = finite_number(item[key])
        if (
            item['duration_seconds'] is None
            and item['started_at'] is not None
            and item['ended_at'] is not None
            and item['ended_at'] >= item['started_at']
        ):
            item['duration_seconds'] = item['ended_at'] - item['started_at']


async def session_trace(
    db: AsyncSession,
    chat_id: str,
    *,
    start_date=None,
    end_date=None,
    group_id=None,
    skip=0,
    limit=50,
    view='all',
    include_chart=False,
):
    statement, _ = session_query(db, chat_id=chat_id, start_date=start_date, end_date=end_date, group_id=group_id)
    session = (await db.execute(statement)).mappings().first()
    if session is None:
        return None
    items, index, field = output_items(db)
    filters = [ChatMessage.chat_id == chat_id, *message_filters(start_date, end_date)]
    error = func.coalesce(cast(ChatMessage.error, Text), 'null').notin_(['null', '""', '{}', 'false'])
    # Metadata only. Tool arguments/results are fetched separately when an item is selected.
    messages = select(
        ChatMessage.id.label('message_id'),
        literal(-1).label('index'),
        literal(None, Integer).label('result_index'),
        ChatMessage.created_at,
        ChatMessage.model_id,
        literal('response').label('type'),
        ChatMessage.role.label('name'),
        literal(None, Text).label('call_id'),
        case((error, 'failed'), (ChatMessage.done.is_(True), 'completed'), else_='in_progress').label('status'),
        literal(None, Text).label('error_type'),
        json_text(db, ChatMessage.meta, 'response_started_at').label('started_at'),
        json_text(db, ChatMessage.meta, 'response_ended_at').label('ended_at'),
        literal(None, Text).label('duration_seconds'),
    ).where(*filters, ChatMessage.role == 'assistant')
    outputs = (
        select(
            ChatMessage.id.label('message_id'),
            index.label('index'),
            ChatMessage.created_at,
            ChatMessage.model_id,
            *[
                func.substr(cast(field(key), Text), 1, size).label(key)
                for key, size in [
                    ('type', 80),
                    ('name', 160),
                    ('call_id', 200),
                    ('status', 64),
                    ('error_type', 80),
                    ('started_at', 64),
                    ('ended_at', 64),
                ]
            ],
            func.substr(cast(field('duration'), Text), 1, 64).label('duration_seconds'),
        )
        .select_from(ChatMessage)
        .join(items, true())
        .where(*filters)
    )
    # Pair by saved message/call identity before pagination, never by adjacent rows.
    saved = outputs.cte('saved_outputs')
    pairs = (
        select(
            saved.c.message_id,
            saved.c.call_id,
            func.max(case((saved.c.type == 'function_call', saved.c.index))).label('call_index'),
            func.max(case((saved.c.type == 'function_call_output', saved.c.index))).label('result_index'),
        )
        .where(saved.c.call_id.isnot(None), saved.c.call_id != '')
        .group_by(saved.c.message_id, saved.c.call_id)
        .subquery()
    )
    returned = saved.alias('saved_result')
    is_call = saved.c.type == 'function_call'
    outputs = (
        select(
            saved.c.message_id,
            saved.c.index,
            case((is_call, pairs.c.result_index)).label('result_index'),
            *[
                case((is_call, func.coalesce(returned.c[key], saved.c[key])), else_=saved.c[key]).label(key)
                if key in {'status', 'error_type'}
                else saved.c[key]
                for key in saved.c.keys()
                if key not in {'message_id', 'index'}
            ],
        )
        .select_from(saved)
        .outerjoin(pairs, (pairs.c.message_id == saved.c.message_id) & (pairs.c.call_id == saved.c.call_id))
        .outerjoin(returned, (returned.c.message_id == saved.c.message_id) & (returned.c.index == pairs.c.result_index))
        .where(saved.c.type.isnot(None), or_(saved.c.type != 'function_call_output', pairs.c.call_index.is_(None)))
    )
    trace = union_all(messages, outputs).subquery()
    query = select(trace)
    if view == 'tools':
        query = query.where(trace.c.type.in_(['function_call', 'function_call_output', 'open_webui:code_interpreter']))
    elif view == 'errors':
        query = query.where(trace.c.status == 'failed')
    rows = (
        (
            await db.execute(
                query.order_by(trace.c.created_at, trace.c.message_id, trace.c.index).offset(skip).limit(limit + 1)
            )
        )
        .mappings()
        .all()
    )
    session = {**dict(session), 'title': safe_snippet(session['title']) or ''}
    result = {'session': session, **page_result(rows, limit)}
    if include_chart:
        result['chart'] = await trace_chart(db, trace, session['responses'])
    normalize_durations(result['items'])
    return result


async def trace_chart(db, trace, responses):
    # Keep the full session's order and page offsets, but return at most 128 bars.
    ordered = select(
        trace,
        (func.row_number().over(order_by=[trace.c.created_at, trace.c.message_id, trace.c.index]) - 1).label('offset'),
    ).cte('ordered_trace')
    input_tokens, output_tokens = _token_columns(db.get_bind().dialect.name)
    usage = (
        select(
            ordered.c.offset,
            ordered.c.model_id,
            ordered.c.status,
            input_tokens.label('input_tokens'),
            output_tokens.label('output_tokens'),
            func.coalesce(ChatMessage.usage['incomplete'].as_boolean(), False).label('incomplete'),
            func.row_number().over(order_by=ordered.c.offset).label('ordinal'),
        )
        .join(ChatMessage, ChatMessage.id == ordered.c.message_id)
        .where(ordered.c.index == -1, ChatMessage.role == 'assistant')
        .subquery()
    )
    group_size = max(1, math.ceil(responses / 128))
    position = usage.c.ordinal - 1
    bucket = cast((position - position % group_size) / group_size, Integer)
    recorded = usage.c.input_tokens.isnot(None) | usage.c.output_tokens.isnot(None)
    complete = usage.c.input_tokens.isnot(None) & usage.c.output_tokens.isnot(None) & usage.c.incomplete.is_(False)
    bars = (
        (
            await db.execute(
                select(
                    func.min(usage.c.ordinal).label('first'),
                    func.max(usage.c.ordinal).label('last'),
                    func.min(usage.c.offset).label('offset'),
                    func.sum(usage.c.input_tokens).label('input_tokens'),
                    func.sum(usage.c.output_tokens).label('output_tokens'),
                    func.sum(case((recorded, 1), else_=0)).label('recorded'),
                    func.sum(case((complete, 1), else_=0)).label('complete'),
                    func.sum(case((usage.c.status == 'failed', 1), else_=0)).label('errors'),
                    case(
                        (
                            func.count(usage.c.model_id) == func.count(),
                            case((func.count(distinct(usage.c.model_id)) == 1, func.min(usage.c.model_id))),
                        )
                    ).label('model_id'),
                )
                .group_by(bucket)
                .order_by(bucket)
            )
        )
        .mappings()
        .all()
    )

    # Validate numeric text before casting, including on PostgreSQL. Malformed saved values are unknown.
    def number(column):
        if db.get_bind().dialect.name == 'sqlite':
            valid_json = case((func.json_valid(column), column), else_='null')
            valid = func.json_type(valid_json).in_(['integer', 'real'])
        else:
            valid = column.op('~')(r'^[0-9]+([.][0-9]+)?([eE][+-]?[0-9]{1,2})?$')
        value = cast(case((valid & (func.length(column) <= 100), column)), Float)
        return case(((value >= 0) & (value < 1e100), value))

    start, end, duration = [number(ordered.c[key]) for key in ('started_at', 'ended_at', 'duration_seconds')]
    timed = start.isnot(None) & end.isnot(None) & (end >= start)
    timing = (
        (
            await db.execute(
                select(
                    func.min(case((timed, start))).label('start'),
                    func.max(case((timed, end))).label('end'),
                    func.max(func.coalesce(duration, case((timed, end - start)))).label('max_duration'),
                    func.sum(case((timed, 1), else_=0)).label('timed_operations'),
                    func.sum(case((duration.isnot(None) | timed, 1), else_=0)).label('duration_operations'),
                )
            )
        )
        .mappings()
        .one()
    )
    return {'usage': [dict(bar) for bar in bars], **dict(timing)}
