import json
import re
import time
import uuid
from copy import deepcopy
from html import escape
from typing import Literal, Optional

import markdown
from bs4 import BeautifulSoup
from open_webui.internal.db import Base, get_async_db_context
from open_webui.models.access_grants import AccessGrantModel, AccessGrants
from open_webui.models.groups import Groups
from open_webui.models.users import User, UserModel, UserResponse
from open_webui.utils.json_codec import JSONCodec
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import JSON, BigInteger, Column, ForeignKey, Text, cast, delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession


class NotePageConflict(ValueError):
    pass


class NotePageOperation(BaseModel):
    action: Literal['create', 'rename', 'duplicate', 'reorder', 'move', 'delete']
    page_id: str | None = None
    new_id: str | None = None
    parent_id: str | None = None
    before_id: str | None = None
    title: str | None = Field(default=None, max_length=200)
    order: list[str] | None = None
    revision: int = Field(ge=0)


def order_pages(pages: list[dict]) -> list[dict]:
    """Keep sibling order while storing each subtree together, parent first."""
    ids = {page['id'] for page in pages}
    if len(ids) != len(pages):
        raise ValueError('Page IDs must be unique')
    children: dict[str | None, list[dict]] = {}
    for page in pages:
        if page['id'] == 'main':
            page['parent_id'] = None
        else:
            page.setdefault('parent_id', None)
        parent = page['parent_id']
        if parent is not None and parent not in ids:
            raise ValueError('Parent page no longer exists')
        children.setdefault(parent, []).append(page)
    ordered = []
    roots = children.get(None, [])
    roots.sort(key=lambda page: page['id'] != 'main')
    stack = list(reversed(roots))
    while stack:
        page = stack.pop()
        ordered.append(page)
        stack.extend(reversed(children.get(page['id'], [])))
    if len(ordered) != len(pages):
        raise ValueError('A page cannot be nested inside itself or its subpages')
    return ordered


def subtree_ids(pages: list[dict], page_id: str) -> set[str]:
    # Tabs are in preorder, so all ancestors precede their descendants.
    result = {page_id}
    for page in pages:
        if page.get('parent_id') in result:
            result.add(page['id'])
    return result


def page_paths(pages: list[dict]) -> dict[str, str]:
    paths = {}
    for page in pages:
        parent_path = paths.get(page.get('parent_id'))
        paths[page['id']] = f'{parent_path} / {page["title"]}' if parent_path else page['title']
    return paths


def get_content_files(content: dict | None) -> list[dict]:
    """Attachment blocks are authoritative; HTML/Markdown support external note writers."""
    if not isinstance(content, dict):
        return []
    document = content.get('json')
    files = {}
    if isinstance(document, dict):
        stack = [document]
        while stack:
            node = stack.pop()
            if not isinstance(node, dict):
                continue
            if node.get('type') == 'fileAttachment':
                attrs = node.get('attrs') or {}
                file_id = attrs.get('id')
                if isinstance(file_id, str) and re.fullmatch(r'[\w-]+', file_id):
                    files[file_id] = {
                        'type': 'file',
                        'id': file_id,
                        'name': attrs.get('name') or file_id,
                        'size': attrs.get('size', 0),
                    }
            stack.extend(reversed(node.get('content') or []))
    else:
        html = content.get('html') or markdown.markdown(content.get('md') or '')
        for link in BeautifulSoup(html, 'html.parser').find_all('a', href=True):
            match = re.fullmatch(r'/api/v1/files/([\w-]+)/content', link['href'])
            if match:
                file_id = match[1]
                files[file_id] = {'type': 'file', 'id': file_id, 'name': link.get_text() or file_id, 'size': 0}
    return list(files.values())


def migrate_page_files(page: dict, files: list[dict]) -> None:
    """Consume legacy attachment lists once, preserving existing content and inline images."""
    content = page['content']
    existing = {file['id'] for file in get_content_files(content)}
    changed = False
    for file in files:
        if not isinstance(file, dict) or not file.get('id'):
            continue
        if file.get('type') == 'image':
            reference = f'data://{file["id"]}'
            url = file.get('url') or ''
            if not url:
                continue
            # These assets also back images in older versions of the page.
            for snapshot in [content, *(page.get('versions') or [])]:
                if not isinstance(snapshot, dict):
                    continue
                encoded = json.dumps(snapshot)
                if reference in encoded:
                    snapshot.update(json.loads(encoded.replace(reference, json.dumps(url)[1:-1])))
                    changed = True
        elif file['id'] not in existing:
            attrs = {'id': file['id'], 'name': file.get('name') or file['id'], 'size': file.get('size') or 0}
            href = f'/api/v1/files/{file["id"]}/content'
            block = f'<div data-file-id="{escape(file["id"], quote=True)}"><a href="{escape(href, quote=True)}">{escape(attrs["name"])}</a></div>'
            content['html'] = (content.get('html') or markdown.markdown(content.get('md') or '')) + block
            content['md'] = (
                (content.get('md') or '') + '\n\n' + f'[{attrs["name"].replace("[", "").replace("]", "")}]({href})'
            )
            if isinstance(content.get('json'), dict):
                content['json'].setdefault('content', []).append({'type': 'fileAttachment', 'attrs': attrs})
            existing.add(file['id'])
            changed = True
    if changed:
        # Old collaboration documents must not overwrite the migrated content.
        page['generation'] = page.get('generation', 0) + 1


def get_note_files(data: dict | None) -> list[dict]:
    return [file for page in normalize_pages(data)['pages'] for file in get_content_files(page['content'])]


def normalize_pages(data: dict | None, note_title: str | None = None) -> dict:
    data = deepcopy(data or {})
    if not data.get('pages'):
        data['pages'] = [
            {
                'id': 'main',
                'title': note_title or 'Untitled',
                'content': data.get('content') or {'json': None, 'html': '', 'md': ''},
                'versions': data.get('versions') or [],
                'revision': 0,
                'generation': 0,
            }
        ]
    if not any(page['id'] == 'main' for page in data['pages']):
        data['pages'].insert(
            0,
            {
                'id': 'main',
                'title': note_title or 'Untitled',
                'content': {'json': None, 'html': '', 'md': ''},
                'versions': [],
                'revision': 0,
                'generation': 0,
            },
        )
    if note_title is not None:
        for page in data['pages']:
            if page['id'] == 'main' and page.get('inherit_note_title', True):
                page['title'] = note_title or 'Untitled'
    data['pages'] = order_pages(data['pages'])
    legacy_files = data.pop('files', None) or []
    for page in data['pages']:
        files = page.pop('files', None)
        if files is None:
            # Old whole-note files belong to main; subpages only retain referenced images.
            references = json.dumps([page.get('content'), page.get('versions')])
            files = (
                legacy_files
                if page['id'] == 'main'
                else [
                    file
                    for file in legacy_files
                    if isinstance(file, dict)
                    and file.get('type') == 'image'
                    and f'data://{file.get("id")}' in references
                ]
            )
        if files:
            migrate_page_files(page, files)
    data.setdefault('pages_revision', 0)
    data.pop('versions', None)
    # A derived projection keeps existing SQL search and whole-note retrieval cheap.
    pages = data['pages']
    paths = page_paths(pages)
    data['content'] = (
        deepcopy(pages[0]['content'])
        if len(pages) == 1
        else {
            'json': None,
            'md': '\n\n'.join(f'## {paths[p["id"]]}\n\n{p["content"].get("md", "")}' for p in pages),
            'html': '',
        }
    )
    data['search_text'] = '\n\n'.join(f'{paths[p["id"]]}\n{p["content"].get("md", "")}' for p in pages)
    return data


def get_page(data: dict, page_id: str | None = None) -> dict:
    pages = normalize_pages(data)['pages']
    if page_id is None:
        if len(pages) != 1:
            raise NotePageConflict('Select a page before editing this note')
        return pages[0]
    page = next((page for page in pages if page['id'] == page_id), None)
    if page is None:
        raise NotePageConflict('Page no longer exists')
    return page


def document_page(data: dict, document_id: str) -> dict:
    parts = document_id.split(':')
    if len(parts) == 2:
        page = get_page(data)
        if page.get('generation', 0) != 0:
            raise NotePageConflict('Reload this page before editing')
        return page
    if len(parts) != 5 or parts[2] != 'page':
        raise ValueError('Invalid note document ID')
    page = get_page(data, parts[3])
    if str(page.get('generation', 0)) != parts[4]:
        raise NotePageConflict('Page changed; reload before editing')
    return page


def apply_page_operation(data: dict, operation: NotePageOperation) -> dict:
    data = normalize_pages(data)
    pages = data['pages']
    if operation.action in ('create', 'duplicate'):
        if not operation.new_id:
            raise ValueError('A new page ID is required')
        uuid.UUID(operation.new_id)
        if any(p['id'] == operation.new_id for p in pages):
            return data
    if operation.revision != data['pages_revision']:
        raise NotePageConflict('Pages changed. Refresh and try again')
    if operation.action == 'create':
        title = (operation.title or '').strip()
        if not title:
            raise ValueError('Page title is required')
        pages.append(
            {
                'id': operation.new_id,
                'parent_id': operation.parent_id,
                'title': title,
                'content': {'json': None, 'html': '', 'md': ''},
                'versions': [],
                'revision': 0,
                'generation': 0,
            }
        )
    elif operation.action == 'reorder':
        order = operation.order or []
        if len(order) != len(pages) or set(order) != {p['id'] for p in pages}:
            raise ValueError('Order must contain each page exactly once')
        if order[0] != 'main':
            raise ValueError('The default page must stay first')
        lookup = {p['id']: p for p in pages}
        data['pages'] = [lookup[id] for id in order]
    else:
        page = next((p for p in pages if p['id'] == operation.page_id), None)
        if page is None:
            raise NotePageConflict('Page no longer exists')
        if page['id'] == 'main' and operation.action in ('move', 'delete'):
            raise ValueError('The default page cannot be moved or deleted')
        if operation.action == 'rename':
            title = (operation.title or '').strip()
            if not title:
                raise ValueError('Page title is required')
            page['title'] = title
            if page['id'] == 'main':
                page['inherit_note_title'] = False
        elif operation.action == 'move':
            parent_id = operation.parent_id
            if operation.before_id == 'main':
                raise ValueError('The default page must stay first')
            branch_ids = subtree_ids(pages, page['id'])
            if parent_id in branch_ids:
                raise ValueError('A page cannot be nested inside itself or its subpages')
            if parent_id is not None and not any(p['id'] == parent_id for p in pages):
                raise ValueError('Parent page no longer exists')
            branch = [p for p in pages if p['id'] in branch_ids]
            remaining = [p for p in pages if p['id'] not in branch_ids]
            position = len(remaining)
            if operation.before_id is not None:
                anchor = next((p for p in remaining if p['id'] == operation.before_id), None)
                if anchor is None or anchor['parent_id'] != parent_id:
                    raise ValueError('Move target must be a sibling in the destination')
                position = remaining.index(anchor)
            page['parent_id'] = parent_id
            data['pages'] = remaining[:position] + branch + remaining[position:]
        elif operation.action == 'delete':
            if len(pages) == 1:
                raise ValueError('A note must have at least one page')
            # Deleting one tab never silently deletes its children's content.
            for child in pages:
                if child['parent_id'] == page['id']:
                    child['parent_id'] = page['parent_id']
            pages.remove(page)
        elif operation.action == 'duplicate':
            branch_ids = subtree_ids(pages, page['id'])
            branch = [p for p in pages if p['id'] in branch_ids]
            ids = {p['id']: str(uuid.uuid5(uuid.UUID(operation.new_id), p['id'])) for p in branch}
            ids[page['id']] = operation.new_id
            if set(ids.values()) & {p['id'] for p in pages}:
                raise ValueError('A duplicated page ID already exists')
            copies = deepcopy(branch)
            for copy in copies:
                copy.update(
                    id=ids[copy['id']],
                    parent_id=ids.get(copy['parent_id'], copy['parent_id']),
                    versions=[],
                    revision=0,
                    generation=0,
                )
            copies[0]['title'] = page['title'][:193] + ' (Copy)'
            position = pages.index(branch[-1]) + 1
            pages[position:position] = copies
    data['pages_revision'] += 1
    return normalize_pages(data)


def update_page_content(
    data: dict, page_id: str | None, changes: dict, generation: int | None = None, revision: int | None = None
) -> dict:
    data = normalize_pages(data)
    target = get_page(data, page_id)
    page = next(p for p in data['pages'] if p['id'] == target['id'])
    if generation is not None and generation != page.get('generation', 0):
        raise NotePageConflict('Page changed; reload before editing')
    if revision is not None and revision != page.get('revision', 0):
        raise NotePageConflict('Page content changed. Read it again before editing')
    if 'content' in changes:
        content = changes['content']
        if not isinstance(content, dict) or any(
            key in content and not isinstance(content[key], str) for key in ('md', 'html')
        ):
            raise ValueError('Page content must contain text markdown and HTML')
        page['content'] = {'json': None, 'html': '', 'md': '', **deepcopy(content)}
        page['revision'] = page.get('revision', 0) + 1
        # Socket snapshots retain their generation. External replacements invalidate old documents.
        if generation is None:
            page['generation'] = page.get('generation', 0) + 1
    if 'versions' in changes:
        page['versions'] = deepcopy(changes['versions'])
    if 'files' in changes:
        raise ValueError('Attach files through page content')
    return normalize_pages(data)


def matching_page(data: dict, query: str = '') -> dict:
    pages = normalize_pages(data)['pages']
    paths = page_paths(pages)
    terms = query.lower().split()
    for require_all in (True, False):
        for page in pages:
            text = f'{paths[page["id"]]} {page["content"].get("md", "")}'.lower()
            if terms and (all(t in text for t in terms) if require_all else any(t in text for t in terms)):
                return page
    return pages[0]


####################
# Note DB Schema
####################


class Note(Base):
    __tablename__ = 'note'

    id = Column(Text, primary_key=True, unique=True)
    user_id = Column(Text)

    title = Column(Text)
    data = Column(JSON, nullable=True)
    meta = Column(JSON, nullable=True)

    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)


def sanitize_note_data(data: Optional[dict]) -> Optional[dict]:
    """Sanitize malformed note.data so content.md is always markdown text."""
    if data is None:
        return None
    if not isinstance(data, dict):
        return {'content': {'md': str(data)}}

    content = data.get('content')
    if not isinstance(content, dict) or 'md' not in content or isinstance(content.get('md'), str):
        return data

    md = content.get('md') if content.get('md') is not None else ''
    if isinstance(md, (dict, list)):
        md = f'```json\n{JSONCodec.dumps(md, indent=2, ensure_ascii=False)}\n```'
    else:
        md = str(md)

    return {
        **data,
        'content': {
            **content,
            'md': md,
        },
    }


class NoteModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str

    title: str
    data: Optional[dict] = None
    meta: Optional[dict] = None
    is_pinned: Optional[bool] = False

    access_grants: list[AccessGrantModel] = Field(default_factory=list)

    created_at: int  # timestamp in epoch
    updated_at: int  # timestamp in epoch

    @field_validator('data', mode='before')
    @classmethod
    def sanitize_data(cls, data):
        return sanitize_note_data(data)


class PinnedNote(Base):
    __tablename__ = 'pinned_note'

    id = Column(Text, primary_key=True)
    user_id = Column(Text, nullable=False)
    note_id = Column(Text, ForeignKey('note.id', ondelete='CASCADE'), nullable=False)
    created_at = Column(BigInteger, nullable=False)


####################
# Forms
####################


class NoteForm(BaseModel):
    title: str
    data: Optional[dict] = None
    meta: Optional[dict] = None
    access_grants: Optional[list[dict]] = None

    @field_validator('data', mode='before')
    @classmethod
    def sanitize_data(cls, data):
        if isinstance(data, dict) and 'pages' in data:
            raise ValueError('Create pages using page operations')
        return sanitize_note_data(data)


class NoteUpdateForm(BaseModel):
    title: Optional[str] = None
    data: Optional[dict] = None
    meta: Optional[dict] = None
    page_id: Optional[str] = None
    page_revision: Optional[int] = None
    page_generation: Optional[int] = None
    page_operation: Optional[NotePageOperation] = None

    @field_validator('data', mode='before')
    @classmethod
    def sanitize_data(cls, data):
        return sanitize_note_data(data)


class NoteUserResponse(NoteModel):
    user: Optional[UserResponse] = None


class NoteItemResponse(BaseModel):
    id: str
    title: str
    data: Optional[dict]
    is_pinned: Optional[bool] = False
    updated_at: int
    created_at: int
    user: Optional[UserResponse] = None


class NoteListResponse(BaseModel):
    items: list[NoteUserResponse]
    total: int


class NoteTable:
    async def _get_access_grants(self, note_id: str, db: Optional[AsyncSession] = None) -> list[AccessGrantModel]:
        return await AccessGrants.get_grants_by_resource('note', note_id, db=db)

    async def _to_note_model(
        self,
        note: Note,
        access_grants: Optional[list[AccessGrantModel]] = None,
        db: Optional[AsyncSession] = None,
    ) -> NoteModel:
        # We exclude access_grants to inject them
        note_model = NoteModel.model_validate(note)
        note_model.data = normalize_pages(note_model.data, note_model.title)
        note_model.access_grants = (
            access_grants if access_grants is not None else await self._get_access_grants(note_model.id, db=db)
        )
        return note_model

    def _has_permission(self, db, query, filter: dict, permission: str = 'read'):
        return AccessGrants.has_permission_filter(
            db=db,
            query=query,
            DocumentModel=Note,
            filter=filter,
            resource_type='note',
            permission=permission,
        )

    async def insert_new_note(
        self, user_id: str, form_data: NoteForm, db: Optional[AsyncSession] = None
    ) -> Optional[NoteModel]:
        async with get_async_db_context(db) as db:
            note = NoteModel(
                **{
                    'id': str(uuid.uuid4()),
                    'user_id': user_id,
                    **form_data.model_dump(exclude={'access_grants'}),
                    'created_at': int(time.time_ns()),
                    'updated_at': int(time.time_ns()),
                    'access_grants': [],
                }
            )

            note.data = normalize_pages(note.data, note.title)
            new_note = Note(**note.model_dump(exclude={'access_grants', 'is_pinned'}))

            db.add(new_note)
            await db.commit()
            await AccessGrants.set_access_grants('note', note.id, form_data.access_grants, db=db)
            return await self._to_note_model(new_note, db=db)

    async def get_notes(self, skip: int = 0, limit: int = 50, db: Optional[AsyncSession] = None) -> list[NoteModel]:
        async with get_async_db_context(db) as db:
            stmt = select(Note).order_by(Note.updated_at.desc())
            if skip is not None:
                stmt = stmt.offset(skip)
            if limit is not None:
                stmt = stmt.limit(limit)
            result = await db.execute(stmt)
            notes = result.scalars().all()
            note_ids = [note.id for note in notes]
            grants_map = await AccessGrants.get_grants_by_resources('note', note_ids, db=db)
            return [await self._to_note_model(note, access_grants=grants_map.get(note.id, []), db=db) for note in notes]

    async def search_notes(
        self,
        user_id: str,
        filter: dict = {},
        skip: int = 0,
        limit: int = 30,
        db: Optional[AsyncSession] = None,
    ) -> NoteListResponse:
        async with get_async_db_context(db) as db:
            stmt = select(Note, User).outerjoin(User, User.id == Note.user_id)
            if filter:
                query_key = filter.get('query')
                if query_key:
                    # Split query into individual words and normalize each
                    # (strip hyphens so "todo" matches "to-do").
                    # All words must match somewhere in title OR content (AND semantics).
                    search_words = query_key.split()
                    normalized_words = [w.replace('-', '') for w in search_words if w.replace('-', '')]
                    for word in normalized_words:
                        stmt = stmt.filter(
                            or_(
                                func.replace(func.replace(Note.title, '-', ''), ' ', '').ilike(f'%{word}%'),
                                func.replace(
                                    func.replace(
                                        func.coalesce(
                                            Note.data['search_text'].as_string(), Note.data['content']['md'].as_string()
                                        ),
                                        '-',
                                        '',
                                    ),
                                    ' ',
                                    '',
                                ).ilike(f'%{word}%'),
                            )
                        )

                view_option = filter.get('view_option')
                if view_option == 'created':
                    stmt = stmt.filter(Note.user_id == user_id)
                elif view_option == 'shared':
                    stmt = stmt.filter(Note.user_id != user_id)

                # Apply access control filtering
                if 'permission' in filter:
                    permission = filter['permission']
                else:
                    permission = 'write'

                stmt = self._has_permission(
                    db,
                    stmt,
                    filter,
                    permission=permission,
                )

                order_by = filter.get('order_by')
                direction = filter.get('direction')

                if order_by == 'name':
                    if direction == 'asc':
                        stmt = stmt.order_by(Note.title.asc())
                    else:
                        stmt = stmt.order_by(Note.title.desc())
                elif order_by == 'created_at':
                    if direction == 'asc':
                        stmt = stmt.order_by(Note.created_at.asc())
                    else:
                        stmt = stmt.order_by(Note.created_at.desc())
                elif order_by == 'updated_at':
                    if direction == 'asc':
                        stmt = stmt.order_by(Note.updated_at.asc())
                    else:
                        stmt = stmt.order_by(Note.updated_at.desc())
                else:
                    stmt = stmt.order_by(Note.updated_at.desc())

            else:
                stmt = stmt.order_by(Note.updated_at.desc())

            # Count BEFORE pagination
            count_result = await db.execute(select(func.count()).select_from(stmt.subquery()))
            total = count_result.scalar()

            if skip:
                stmt = stmt.offset(skip)
            if limit:
                stmt = stmt.limit(limit)

            result = await db.execute(stmt)
            items = result.all()

            note_ids = [note.id for note, _ in items]
            grants_map = await AccessGrants.get_grants_by_resources('note', note_ids, db=db)

            notes = []
            for note, user in items:
                notes.append(
                    NoteUserResponse(
                        **(
                            await self._to_note_model(
                                note,
                                access_grants=grants_map.get(note.id, []),
                                db=db,
                            )
                        ).model_dump(),
                        user=(UserResponse(**UserModel.model_validate(user).model_dump()) if user else None),
                    )
                )

            return NoteListResponse(items=notes, total=total)

    async def get_notes_by_user_id(
        self,
        user_id: str,
        permission: str = 'read',
        skip: int = 0,
        limit: int = 50,
        db: Optional[AsyncSession] = None,
    ) -> list[NoteModel]:
        async with get_async_db_context(db) as db:
            user_groups = await Groups.get_groups_by_member_id(user_id, db=db, include_inherited=True)
            user_group_ids = [group.id for group in user_groups]

            stmt = select(Note).order_by(Note.updated_at.desc())
            stmt = self._has_permission(db, stmt, {'user_id': user_id, 'group_ids': user_group_ids}, permission)

            if skip is not None:
                stmt = stmt.offset(skip)
            if limit is not None:
                stmt = stmt.limit(limit)

            result = await db.execute(stmt)
            notes = result.scalars().all()
            note_ids = [note.id for note in notes]
            grants_map = await AccessGrants.get_grants_by_resources('note', note_ids, db=db)
            return [await self._to_note_model(note, access_grants=grants_map.get(note.id, []), db=db) for note in notes]

    async def get_note_by_id(self, id: str, db: Optional[AsyncSession] = None) -> Optional[NoteModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(select(Note).filter(Note.id == id).execution_options(populate_existing=True))
            note = result.scalars().first()
            return await self._to_note_model(note, db=db) if note else None

    async def get_note_ids_by_file_id(self, file_id: str, owner_id: str, db: AsyncSession | None = None) -> list[str]:
        """Find current file attachments in notes owned by the file owner."""
        async with get_async_db_context(db) as db:
            result = await db.execute(
                select(Note.id, Note.data).filter(
                    Note.user_id == owner_id,
                    cast(Note.data, Text).like(f'%{file_id}%'),
                )
            )
            # The text filter only narrows candidates; authorization needs an exact attachment.
            return [
                note_id
                for note_id, data in result.all()
                if isinstance(data, dict)
                and any(
                    isinstance(item, dict) and item.get('type') == 'file' and item.get('id') == file_id
                    for item in get_note_files(data)
                )
            ]

    async def update_note_by_id(
        self, id: str, form_data: NoteUpdateForm, db: Optional[AsyncSession] = None
    ) -> Optional[NoteModel]:
        changes = form_data.model_dump(exclude_unset=True)
        incoming = changes.get('data') or {}
        if 'pages' in incoming or 'pages_revision' in incoming:
            raise ValueError('Use page operations instead of replacing all pages')
        async with get_async_db_context(db) as db:
            # CAS protects the entire JSON from writers on other pages and other workers.
            for _ in range(8):
                result = await db.execute(select(Note).where(Note.id == id).execution_options(populate_existing=True))
                note = result.scalars().first()
                if not note:
                    return None
                previous_updated_at = note.updated_at
                data = normalize_pages(sanitize_note_data(note.data), note.title)
                if form_data.page_operation:
                    data = apply_page_operation(data, form_data.page_operation)
                if any(key in incoming for key in ('content', 'versions', 'files')):
                    data = update_page_content(
                        data,
                        form_data.page_id or ('main' if not {'content', 'versions'} & incoming.keys() else None),
                        incoming,
                        form_data.page_generation,
                        form_data.page_revision,
                    )
                data = normalize_pages(
                    {**data, **{k: v for k, v in incoming.items() if k not in ('content', 'versions', 'files')}},
                    changes.get('title', note.title),
                )
                values = {'data': data, 'updated_at': max(time.time_ns(), (previous_updated_at or 0) + 1)}
                if 'title' in changes:
                    values['title'] = changes['title']
                if 'meta' in changes:
                    values['meta'] = {**(note.meta or {}), **(changes['meta'] or {})}
                result = await db.execute(
                    update(Note)
                    .where(Note.id == id, Note.updated_at == previous_updated_at)
                    .values(**values)
                    .execution_options(synchronize_session=False)
                )
                if result.rowcount:
                    await db.commit()
                    return await self.get_note_by_id(id, db=db)
                await db.rollback()
            raise NotePageConflict('Note changed while saving. Please try again')

    async def toggle_note_pinned_by_id(
        self, id: str, user_id: str, db: Optional[AsyncSession] = None
    ) -> Optional[NoteModel]:
        try:
            async with get_async_db_context(db) as db:
                result = await db.execute(select(Note).filter(Note.id == id))
                note = result.scalars().first()
                if not note:
                    return None

                # Check if already pinned
                pin_result = await db.execute(select(PinnedNote).filter_by(user_id=user_id, note_id=id))
                pinned_note = pin_result.scalars().first()

                if pinned_note:
                    await db.execute(delete(PinnedNote).filter_by(user_id=user_id, note_id=id))
                else:
                    new_pin = PinnedNote(
                        id=str(uuid.uuid4()), user_id=user_id, note_id=id, created_at=int(time.time_ns())
                    )
                    db.add(new_pin)

                await db.commit()
                return await self._to_note_model(note, db=db)
        except Exception:
            return None

    async def get_pinned_notes_by_user_id(
        self,
        user_id: str,
        permission: str = 'read',
        db: Optional[AsyncSession] = None,
    ) -> list[NoteModel]:
        async with get_async_db_context(db) as db:
            user_groups = await Groups.get_groups_by_member_id(user_id, db=db, include_inherited=True)
            user_group_ids = [group.id for group in user_groups]

            stmt = (
                select(Note)
                .join(PinnedNote, PinnedNote.note_id == Note.id)
                .filter(PinnedNote.user_id == user_id)
                .order_by(PinnedNote.created_at.desc())
            )
            stmt = self._has_permission(db, stmt, {'user_id': user_id, 'group_ids': user_group_ids}, permission)

            result = await db.execute(stmt)
            notes = result.scalars().all()
            note_ids = [note.id for note in notes]
            grants_map = await AccessGrants.get_grants_by_resources('note', note_ids, db=db)
            return [await self._to_note_model(note, access_grants=grants_map.get(note.id, []), db=db) for note in notes]

    async def delete_note_by_id(self, id: str, db: Optional[AsyncSession] = None) -> bool:
        try:
            async with get_async_db_context(db) as db:
                await AccessGrants.revoke_all_access('note', id, db=db)
                await db.execute(delete(PinnedNote).filter(PinnedNote.note_id == id))
                await db.execute(delete(Note).filter(Note.id == id))
                await db.commit()
                return True
        except Exception:
            return False

    async def get_pinned_note_ids(self, user_id: str, db: Optional[AsyncSession] = None) -> list[str]:
        async with get_async_db_context(db) as db:
            result = await db.execute(select(PinnedNote.note_id).filter_by(user_id=user_id))
            return result.scalars().all()


Notes = NoteTable()
