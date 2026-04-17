import json
import time
import uuid
from typing import Optional
from functools import lru_cache

from sqlalchemy import Boolean, select, delete, update, or_, func, cast
from sqlalchemy.ext.asyncio import AsyncSession
from open_webui.internal.db import Base, get_async_db_context
from open_webui.models.groups import Groups
from open_webui.models.users import User, UserModel, Users, UserResponse
from open_webui.models.access_grants import AccessGrantModel, AccessGrants


from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import BigInteger, Column, Text, JSON

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
    is_pinned = Column(Boolean, default=False, nullable=True)

    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)


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


####################
# Forms
####################


class NoteForm(BaseModel):
    title: str
    data: Optional[dict] = None
    meta: Optional[dict] = None
    access_grants: Optional[list[dict]] = None


class NoteUpdateForm(BaseModel):
    title: Optional[str] = None
    data: Optional[dict] = None
    meta: Optional[dict] = None
    access_grants: Optional[list[dict]] = None


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
        note_data = NoteModel.model_validate(note).model_dump(exclude={'access_grants'})
        note_data['access_grants'] = (
            access_grants if access_grants is not None else await self._get_access_grants(note_data['id'], db=db)
        )
        return NoteModel.model_validate(note_data)

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

            new_note = Note(**note.model_dump(exclude={'access_grants'}))

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
                                    func.replace(cast(Note.data['content']['md'], Text), '-', ''),
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
            user_groups = await Groups.get_groups_by_member_id(user_id, db=db)
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
            result = await db.execute(select(Note).filter(Note.id == id))
            note = result.scalars().first()
            return await self._to_note_model(note, db=db) if note else None

    async def update_note_by_id(
        self, id: str, form_data: NoteUpdateForm, db: Optional[AsyncSession] = None
    ) -> Optional[NoteModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(select(Note).filter(Note.id == id))
            note = result.scalars().first()
            if not note:
                return None

            form_data = form_data.model_dump(exclude_unset=True)

            if 'title' in form_data:
                note.title = form_data['title']
            if 'data' in form_data:
                note.data = {**note.data, **form_data['data']}
            if 'meta' in form_data:
                note.meta = {**note.meta, **form_data['meta']}

            if 'access_grants' in form_data:
                await AccessGrants.set_access_grants('note', id, form_data['access_grants'], db=db)

            note.updated_at = int(time.time_ns())

            await db.commit()
            return await self._to_note_model(note, db=db) if note else None

    async def toggle_note_pinned_by_id(self, id: str, db: Optional[AsyncSession] = None) -> Optional[NoteModel]:
        try:
            async with get_async_db_context(db) as db:
                result = await db.execute(select(Note).filter(Note.id == id))
                note = result.scalars().first()
                if not note:
                    return None
                note.is_pinned = not note.is_pinned
                note.updated_at = int(time.time_ns())
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
            user_groups = await Groups.get_groups_by_member_id(user_id, db=db)
            user_group_ids = [group.id for group in user_groups]

            stmt = select(Note).filter(Note.is_pinned == True).order_by(Note.updated_at.desc())
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
                await db.execute(delete(Note).filter(Note.id == id))
                await db.commit()
                return True
        except Exception:
            return False


Notes = NoteTable()
