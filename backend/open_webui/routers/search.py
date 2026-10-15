"""Permission-scoped workspace search. Shared snapshots never read the live chat."""

from typing import Literal
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Query
from open_webui.internal.db import get_async_session
from open_webui.models.access_grants import AccessGrant, AccessGrants
from open_webui.models.channels import ChannelMember, Channels
from open_webui.models.chats import Chat
from open_webui.models.config import Config
from open_webui.models.folders import Folder
from open_webui.models.groups import Groups
from open_webui.models.messages import Message
from open_webui.models.notes import Note, PinnedNote
from open_webui.models.shared_chats import SharedChat
from open_webui.models.users import User
from open_webui.utils.access_control import has_permission
from open_webui.utils.auth import get_verified_user
from pydantic import BaseModel, Field
from sqlalchemy import BigInteger, and_, case, cast, func, literal, or_, select, text, union_all
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()
PAGE_SIZE = 24


class SearchResult(BaseModel):
    id: str
    kind: Literal['chat', 'message', 'note']
    title: str
    context: str
    snippet: str
    preview: str
    url: str
    updated_at: int
    shared: bool = False
    pinned: bool = False
    rank: int = Field(exclude=True, default=3)


class SearchScope(BaseModel):
    id: str
    name: str
    kind: Literal['folder', 'channel']


class SearchResponse(BaseModel):
    items: list[SearchResult]
    has_more: bool
    scopes: list[SearchScope]
    kinds: list[str]


def terms_for(query: str) -> list[str]:
    return list(dict.fromkeys(query.lower().split()))[:12]


def pattern(value: str) -> str:
    return '%' + value.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_') + '%'


def excerpt(content: str, query: str, length: int = 200) -> str:
    content = content or ''
    positions = [content.lower().find(term) for term in terms_for(query)]
    position = min((p for p in positions if p >= 0), default=0)
    start = max(0, position - length // 4)
    return (
        ('…' if start else '')
        + content[start : start + length].strip()
        + ('…' if start + length < len(content) else '')
    )


def chat_passage(data: dict, query: str) -> tuple[str, str | None]:
    history = (data.get('history') or {}).get('messages') or {}
    messages = list(history.values()) if history else data.get('messages') or []
    messages = [m for m in messages if isinstance(m, dict) and isinstance(m.get('content'), str)]
    terms = terms_for(query)
    match = next((m for m in messages if terms and all(t in m['content'].lower() for t in terms)), None)
    if match is None:
        match = next((m for m in messages if any(t in m['content'].lower() for t in terms)), None)
    fallback = messages[-1] if messages else {}
    return (match or fallback).get('content', ''), match.get('id') if match else None


def title_rank(title, query: str):
    if not query:
        return literal(3)
    return case((func.lower(title) == query.lower(), 0), (title.ilike(pattern(query), escape='\\'), 1), else_=3)


def message_match_sql(table: str, dialect: str, key: str):
    # Identifiers are internal constants; all user input remains bound parameters.
    if dialect == 'sqlite':
        sources = [f"json_each({table}.chat, '$.history.messages')", f"json_each({table}.chat, '$.messages')"]
        return text(
            '('
            + ' OR '.join(
                f"EXISTS (SELECT 1 FROM {source} AS m WHERE json_type(m.value, '$.content') = 'text' "
                f"AND lower(m.value ->> 'content') LIKE :{key} ESCAPE '\\')"
                for source in sources
            )
            + ')'
        )
    sources = [f"json_each({table}.chat->'history'->'messages')", f"json_array_elements({table}.chat->'messages')"]
    return text(
        '('
        + ' OR '.join(
            f"EXISTS (SELECT 1 FROM {source} AS m WHERE json_typeof(m.value->'content') = 'string' "
            f"AND lower(m.value->>'content') LIKE :{key} ESCAPE '\\')"
            for source in sources
        )
        + ')'
    )


async def search_workspace(  # noqa: C901 — keep permission scoping and source dispatch together
    db: AsyncSession,
    user,
    query: str = '',
    kind: str = 'all',
    sharing: str = 'all',
    scope: str = '',
    page: int = 1,
    enabled: tuple[str, ...] = ('chat', 'message', 'note'),
) -> SearchResponse:
    groups = [g.id for g in await Groups.get_groups_by_member_id(user.id, db=db, include_inherited=True)]
    principal = or_(
        and_(AccessGrant.principal_type == 'user', AccessGrant.principal_id == user.id),
        and_(AccessGrant.principal_type == 'group', AccessGrant.principal_id.in_(groups)),
    )

    def granted(resource, resource_id, public=False):
        principals = (
            or_(principal, and_(AccessGrant.principal_type == 'user', AccessGrant.principal_id == '*'))
            if public
            else principal
        )
        return (
            select(AccessGrant.id)
            .where(
                AccessGrant.resource_type == resource,
                AccessGrant.resource_id == resource_id,
                AccessGrant.permission == 'read',
                principals,
            )
            .exists()
        )

    # UNION (not UNION ALL) terminates even if malformed folder data contains a cycle.
    folders = (
        select(Folder.id)
        .where(or_(Folder.user_id == user.id, granted('folder', Folder.id, True)))
        .cte('search_folders', recursive=True)
    )
    folders = folders.union(select(Folder.id).join(folders, Folder.parent_id == folders.c.id))
    folder_rows = (
        await db.execute(
            select(Folder.id, Folder.name, Folder.parent_id, Folder.user_id).where(Folder.id.in_(select(folders.c.id)))
        )
    ).all()
    folder_map = {f.id: f for f in folder_rows}
    channels = await Channels.get_channels_by_user_id(user.id, db=db) if 'message' in enabled else []
    channel_map = {c.id: c for c in channels}
    channel_names = {c.id: c.name for c in channels}
    direct_message_ids = [c.id for c in channels if c.type == 'dm' and not c.name]
    if direct_message_ids:
        members = (
            await db.execute(
                select(ChannelMember.channel_id, User.name)
                .join(User, User.id == ChannelMember.user_id)
                .where(ChannelMember.channel_id.in_(direct_message_ids), User.id != user.id)
                .order_by(User.name, User.id)
            )
        ).all()
        participants = {channel_id: [] for channel_id in direct_message_ids}
        for channel_id, name in members:
            participants[channel_id].append(name)
        for channel_id, names in participants.items():
            channel_names[channel_id] = ', '.join(names) or user.name
    scopes = [SearchScope(id='folder:' + f.id, name=f.name, kind='folder') for f in folder_rows]
    scopes += [SearchScope(id='channel:' + c.id, name=channel_names[c.id], kind='channel') for c in channels]
    scopes.sort(key=lambda s: (s.kind, s.name.lower(), s.id))
    shared_folder_ids = set(
        (
            await db.execute(
                select(Folder.id).where(
                    Folder.id.in_(folder_map),
                    select(AccessGrant.id)
                    .where(
                        AccessGrant.resource_type == 'folder',
                        AccessGrant.resource_id == Folder.id,
                        AccessGrant.permission == 'read',
                    )
                    .exists(),
                )
            )
        ).scalars()
    )
    while True:
        children = {f.id for f in folder_rows if f.parent_id in shared_folder_ids}
        if children.issubset(shared_folder_ids):
            break
        shared_folder_ids |= children
    scoped_folders = set(folder_map)
    if scope.startswith('folder:'):
        root = scope.removeprefix('folder:')
        scoped_folders = {root} if root in folder_map else set()
        while True:
            children = {f.id for f in folder_rows if f.parent_id in scoped_folders}
            if children.issubset(scoped_folders):
                break
            scoped_folders |= children
    if scope and scope not in {s.id for s in scopes}:
        return SearchResponse(items=[], has_more=False, scopes=scopes, kinds=list(enabled))

    query = query.strip()
    terms = terms_for(query)
    results = []
    dialect = db.bind.dialect.name

    def sharing_filter(owner):
        if sharing == 'mine':
            return owner == user.id
        if sharing == 'shared':
            return owner != user.id
        return True

    def apply_match(stmt, model, body=None):
        params = {}
        for index, term in enumerate(terms):
            key = f'search_{index}'
            params[key] = pattern(term)
            content_match = (
                body.ilike(pattern(term), escape='\\')
                if body is not None
                else message_match_sql(model.__tablename__, dialect, key)
            )
            stmt = stmt.where(or_(model.title.ilike(pattern(term), escape='\\'), content_match))
        return stmt.params(**params)

    def append_result(id, result_kind, title, context, content, url, updated, shared, pinned=False, rank=3):
        results.append(
            SearchResult(
                id=id,
                kind=result_kind,
                title=title or 'Untitled',
                context=context,
                snippet=excerpt(content, query),
                preview=excerpt(content, query, 2400),
                url=url,
                updated_at=updated,
                shared=shared,
                pinned=bool(pinned),
                rank=rank,
            )
        )

    sources = {}
    if 'chat' in enabled and kind in ('all', 'chat') and not scope.startswith('channel:'):
        continue_shared = select(SharedChat.chat_id).where(
            SharedChat.chat['share_mode'].as_string() == 'continue', granted('shared_chat', SharedChat.chat_id)
        )
        live_access = or_(
            Chat.user_id == user.id, Chat.folder_id.in_(select(folders.c.id)), Chat.id.in_(continue_shared)
        )
        live_ids = select(Chat.id).where(live_access)
        rank = (
            title_rank(Chat.title, query)
            if query
            else case((and_(Chat.pinned.is_(True), Chat.user_id == user.id), 0), else_=3)
        )
        stmt = select(Chat).where(
            live_access,
            Chat.archived.is_(False),
            func.coalesce(Chat.meta['internal'].as_boolean(), False).is_(False),
            sharing_filter(Chat.user_id),
        )
        if scope:
            stmt = stmt.where(Chat.folder_id.in_(scoped_folders))
        sources['chat'] = (Chat, apply_match(stmt, Chat), rank, Chat.updated_at)
        if not scope and sharing != 'mine':
            stmt = select(SharedChat).where(
                granted('shared_chat', SharedChat.chat_id), ~SharedChat.chat_id.in_(live_ids)
            )
            if sharing == 'shared':
                stmt = stmt.where(SharedChat.user_id != user.id)
            sources['shared'] = (
                SharedChat,
                apply_match(stmt, SharedChat),
                title_rank(SharedChat.title, query),
                SharedChat.updated_at,
            )

    if 'note' in enabled and kind in ('all', 'note') and not scope:
        pinned = select(PinnedNote.id).where(PinnedNote.note_id == Note.id, PinnedNote.user_id == user.id).exists()
        note_shared = (
            select(AccessGrant.id)
            .where(
                AccessGrant.resource_type == 'note',
                AccessGrant.resource_id == Note.id,
                AccessGrant.permission == 'read',
            )
            .exists()
        )
        stmt = AccessGrants.has_permission_filter(
            db, select(Note, pinned, note_shared), Note, {'user_id': user.id, 'group_ids': groups}, 'note', 'read'
        )
        stmt = stmt.where(sharing_filter(Note.user_id))
        stmt = apply_match(stmt, Note, Note.data['content']['md'].as_string())
        rank = title_rank(Note.title, query) if query else case((pinned, 0), else_=3)
        sources['note'] = (Note, stmt, rank, cast(Note.updated_at.op('/')(literal(1_000_000_000)), BigInteger))

    if 'message' in enabled and kind in ('all', 'message') and not scope.startswith('folder:'):
        ids = [scope.removeprefix('channel:')] if scope else list(channel_map)
        stmt = select(Message, User.name).outerjoin(User, User.id == Message.user_id).where(Message.channel_id.in_(ids))
        stmt = stmt.where(sharing_filter(Message.user_id))
        for term in terms:
            stmt = stmt.where(Message.content.ilike(pattern(term), escape='\\'))
        sources['message'] = (
            Message,
            stmt,
            literal(3),
            cast(Message.updated_at.op('/')(literal(1_000_000_000)), BigInteger),
        )

    if not sources:
        return SearchResponse(items=[], has_more=False, scopes=scopes, kinds=list(enabled))

    # Page one combined, permission-filtered ID query. Only hydrate the 24 visible
    # results, rather than repeatedly loading full conversation JSON while scrolling.
    candidates = union_all(
        *[
            stmt.with_only_columns(
                literal(source).label('source'),
                model.id.label('id'),
                rank.label('rank'),
                updated.label('updated_at'),
                maintain_column_froms=True,
            )
            for source, (model, stmt, rank, updated) in sources.items()
        ]
    ).subquery()
    matches = (
        await db.execute(
            select(candidates)
            .order_by(candidates.c.rank, candidates.c.updated_at.desc(), candidates.c.source, candidates.c.id)
            .offset((page - 1) * PAGE_SIZE)
            .limit(PAGE_SIZE + 1)
        )
    ).all()
    has_more = len(matches) > PAGE_SIZE
    matches = matches[:PAGE_SIZE]
    hydrated = {}
    for source, (model, stmt, _, _) in sources.items():
        ids = [match.id for match in matches if match.source == source]
        if ids:
            hydrated[source] = {row[0].id: row for row in (await db.execute(stmt.where(model.id.in_(ids)))).all()}

    for match in matches:
        row = hydrated.get(match.source, {}).get(match.id)
        if row is None:
            continue  # Access may have been revoked between selecting IDs and hydrating.
        item = row[0]
        if match.source in ('chat', 'shared'):
            content, message_id = chat_passage(item.chat or {}, query)
            snapshot = match.source == 'shared'
            folder = None if snapshot else folder_map.get(item.folder_id)
            context = (
                'Shared snapshot'
                if snapshot
                else (folder.name if folder else ('Shared chat' if item.user_id != user.id else 'Personal chat'))
            )
            url = ('/s/' if snapshot else '/c/') + item.id
            if message_id:
                url += '?' + urlencode({'message': message_id})
            is_shared = (
                snapshot or item.user_id != user.id or bool(item.share_id) or item.folder_id in shared_folder_ids
            )
            append_result(
                match.source + ':' + item.id,
                'chat',
                item.title,
                context,
                content,
                url,
                match.updated_at,
                is_shared,
                not snapshot and item.pinned and item.user_id == user.id,
                match.rank,
            )
        elif match.source == 'note':
            content = ((item.data or {}).get('content') or {}).get('md') or ''
            append_result(
                'note:' + item.id,
                'note',
                item.title,
                'Shared note' if item.user_id != user.id or row[2] else 'Personal note',
                content if isinstance(content, str) else '',
                '/notes/' + item.id + ('?' + urlencode({'search': query}) if query else ''),
                match.updated_at,
                item.user_id != user.id or row[2],
                row[1],
                match.rank,
            )
        else:
            channel = channel_map[item.channel_id]
            url = '/channels/' + channel.id + '?' + urlencode({'thread': item.parent_id or item.id, 'message': item.id})
            append_result(
                'message:' + item.id,
                'message',
                row[1] or 'Message',
                channel_names[channel.id] if channel.type == 'dm' else '#' + channel_names[channel.id],
                item.content,
                url,
                match.updated_at,
                True,
                rank=match.rank,
            )

    return SearchResponse(items=results, has_more=has_more, scopes=scopes, kinds=list(enabled))


@router.get('', response_model=SearchResponse)
async def search(
    q: str = Query('', max_length=500),
    kind: Literal['all', 'chat', 'message', 'note'] = 'all',
    sharing: Literal['all', 'mine', 'shared'] = 'all',
    scope: str = Query('', max_length=200),
    page: int = Query(1, ge=1, le=100_000),
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    enabled = ['chat']
    permissions = await Config.get('user.permissions')
    for feature, result_kind in [('channels', 'message'), ('notes', 'note')]:
        if await Config.get(feature + '.enable') and (
            user.role == 'admin' or await has_permission(user.id, 'features.' + feature, permissions, db=db)
        ):
            enabled.append(result_kind)
    return await search_workspace(db, user, q, kind, sharing, scope, page, tuple(enabled))
