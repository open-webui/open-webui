import json
import time
import uuid
from typing import Optional
from functools import lru_cache

from sqlalchemy.orm import Session
from open_webui.internal.db import Base, get_db, get_db_context
from open_webui.models.groups import Groups
from open_webui.models.users import User, UserModel, Users, UserResponse
from open_webui.models.access_grants import AccessGrantModel, AccessGrants


from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import BigInteger, Column, Text, JSON
from sqlalchemy import or_, func, cast

####################
# Note DB Schema
####################


class Note(Base):
    __tablename__ = "note"

    id = Column(Text, primary_key=True, unique=True)
    user_id = Column(Text)

    title = Column(Text)
    data = Column(JSON, nullable=True)
    meta = Column(JSON, nullable=True)

    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)


class NoteModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str

    title: str
    data: Optional[dict] = None
    meta: Optional[dict] = None

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
    updated_at: int
    created_at: int
    user: Optional[UserResponse] = None


class NoteListResponse(BaseModel):
    items: list[NoteUserResponse]
    total: int


class NoteTable:
    def _get_access_grants(
        self, note_id: str, db: Optional[Session] = None
    ) -> list[AccessGrantModel]:
        return AccessGrants.get_grants_by_resource("note", note_id, db=db)

    def _to_note_model(self, note: Note, db: Optional[Session] = None) -> NoteModel:
        note_data = NoteModel.model_validate(note).model_dump(exclude={"access_grants"})
        note_data["access_grants"] = self._get_access_grants(note_data["id"], db=db)
        return NoteModel.model_validate(note_data)

    def _has_permission(self, db, query, filter: dict, permission: str = "read"):
        return AccessGrants.has_permission_filter(
            db=db,
            query=query,
            DocumentModel=Note,
            filter=filter,
            resource_type="note",
            permission=permission,
        )

    def insert_new_note(
        self, user_id: str, form_data: NoteForm, db: Optional[Session] = None
    ) -> Optional[NoteModel]:
        with get_db_context(db) as db:
            note = NoteModel(
                **{
                    "id": str(uuid.uuid4()),
                    "user_id": user_id,
                    **form_data.model_dump(exclude={"access_grants"}),
                    "created_at": int(time.time_ns()),
                    "updated_at": int(time.time_ns()),
                    "access_grants": [],
                }
            )

            new_note = Note(**note.model_dump(exclude={"access_grants"}))

            db.add(new_note)
            db.commit()
            AccessGrants.set_access_grants(
                "note", note.id, form_data.access_grants, db=db
            )
            return self._to_note_model(new_note, db=db)

    def get_notes(
        self, skip: int = 0, limit: int = 50, db: Optional[Session] = None
    ) -> list[NoteModel]:
        with get_db_context(db) as db:
            query = db.query(Note).order_by(Note.updated_at.desc())
            if skip is not None:
                query = query.offset(skip)
            if limit is not None:
                query = query.limit(limit)
            notes = query.all()
            return [self._to_note_model(note, db=db) for note in notes]

    def search_notes(
        self,
        user_id: str,
        filter: dict = {},
        skip: int = 0,
        limit: int = 30,
        db: Optional[Session] = None,
    ) -> NoteListResponse:
        with get_db_context(db) as db:
            query = db.query(Note, User).outerjoin(User, User.id == Note.user_id)
            if filter:
                query_key = filter.get("query")
                if query_key:
                    # Normalize search by removing hyphens and spaces (e.g., "todo" matches "to-do" and "to do")
                    normalized_query = query_key.replace("-", "").replace(" ", "")
                    query = query.filter(
                        or_(
                            func.replace(
                                func.replace(Note.title, "-", ""), " ", ""
                            ).ilike(f"%{normalized_query}%"),
                            func.replace(
                                func.replace(
                                    cast(Note.data["content"]["md"], Text), "-", ""
                                ),
                                " ",
                                "",
                            ).ilike(f"%{normalized_query}%"),
                        )
                    )

                view_option = filter.get("view_option")
                if view_option == "created":
                    query = query.filter(Note.user_id == user_id)
                elif view_option == "shared":
                    query = query.filter(Note.user_id != user_id)

                # Apply access control filtering
                if "permission" in filter:
                    permission = filter["permission"]
                else:
                    permission = "write"

                query = self._has_permission(
                    db,
                    query,
                    filter,
                    permission=permission,
                )

                order_by = filter.get("order_by")
                direction = filter.get("direction")

                if order_by == "name":
                    if direction == "asc":
                        query = query.order_by(Note.title.asc())
                    else:
                        query = query.order_by(Note.title.desc())
                elif order_by == "created_at":
                    if direction == "asc":
                        query = query.order_by(Note.created_at.asc())
                    else:
                        query = query.order_by(Note.created_at.desc())
                elif order_by == "updated_at":
                    if direction == "asc":
                        query = query.order_by(Note.updated_at.asc())
                    else:
                        query = query.order_by(Note.updated_at.desc())
                else:
                    query = query.order_by(Note.updated_at.desc())

            else:
                query = query.order_by(Note.updated_at.desc())

            # Count BEFORE pagination
            total = query.count()

            if skip:
                query = query.offset(skip)
            if limit:
                query = query.limit(limit)

            items = query.all()

            notes = []
            for note, user in items:
                notes.append(
                    NoteUserResponse(
                        **self._to_note_model(note, db=db).model_dump(),
                        user=(
                            UserResponse(**UserModel.model_validate(user).model_dump())
                            if user
                            else None
                        ),
                    )
                )

            return NoteListResponse(items=notes, total=total)

    def get_notes_by_user_id(
        self,
        user_id: str,
        permission: str = "read",
        skip: int = 0,
        limit: int = 50,
        db: Optional[Session] = None,
    ) -> list[NoteModel]:
        with get_db_context(db) as db:
            user_group_ids = [
                group.id for group in Groups.get_groups_by_member_id(user_id, db=db)
            ]

            query = db.query(Note).order_by(Note.updated_at.desc())
            query = self._has_permission(
                db, query, {"user_id": user_id, "group_ids": user_group_ids}, permission
            )

            if skip is not None:
                query = query.offset(skip)
            if limit is not None:
                query = query.limit(limit)

            notes = query.all()
            return [self._to_note_model(note, db=db) for note in notes]

    def get_note_by_id(
        self, id: str, db: Optional[Session] = None
    ) -> Optional[NoteModel]:
        with get_db_context(db) as db:
            note = db.query(Note).filter(Note.id == id).first()
            return self._to_note_model(note, db=db) if note else None

    def update_note_by_id(
        self, id: str, form_data: NoteUpdateForm, db: Optional[Session] = None
    ) -> Optional[NoteModel]:
        with get_db_context(db) as db:
            note = db.query(Note).filter(Note.id == id).first()
            if not note:
                return None

            form_data = form_data.model_dump(exclude_unset=True)

            if "title" in form_data:
                note.title = form_data["title"]
            if "data" in form_data:
                note.data = {**note.data, **form_data["data"]}
            if "meta" in form_data:
                note.meta = {**note.meta, **form_data["meta"]}

            if "access_grants" in form_data:
                AccessGrants.set_access_grants(
                    "note", id, form_data["access_grants"], db=db
                )

            note.updated_at = int(time.time_ns())

            db.commit()
            return self._to_note_model(note, db=db) if note else None

    def delete_note_by_id(self, id: str, db: Optional[Session] = None) -> bool:
        try:
            with get_db_context(db) as db:
                AccessGrants.revoke_all_access("note", id, db=db)
                db.query(Note).filter(Note.id == id).delete()
                db.commit()
                return True
        except Exception:
            return False


Notes = NoteTable()
