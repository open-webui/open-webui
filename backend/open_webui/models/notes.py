import json
import time
import uuid
from typing import Optional

from open_webui.internal.db import Base, get_db
from open_webui.utils.access_control import has_access
from open_webui.models.users import Users, UserResponse


from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Boolean, Column, String, Text, JSON
from sqlalchemy import or_, func, select, and_, text
from sqlalchemy.sql import exists

####################
# Note DB Schema
####################


class Note(Base):
    __tablename__ = "note"

    id = Column(Text, primary_key=True)
    user_id = Column(Text)

    title = Column(Text)
    data = Column(JSON, nullable=True)
    meta = Column(JSON, nullable=True)

    access_control = Column(JSON, nullable=True)

    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)


class NoteModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str

    title: str
    data: Optional[dict] = None
    meta: Optional[dict] = None

    access_control: Optional[dict] = None

    created_at: int  # timestamp in epoch
    updated_at: int  # timestamp in epoch


####################
# Forms
####################


class NoteForm(BaseModel):
    title: str
    data: Optional[dict] = None
    meta: Optional[dict] = None
    access_control: Optional[dict] = None


class NoteUserResponse(NoteModel):
    user: Optional[UserResponse] = None


class NoteTable:
    def insert_new_note(
        self,
        form_data: NoteForm,
        user_id: str,
    ) -> Optional[NoteModel]:
        with get_db() as db:
            note = NoteModel(
                **{
                    "id": str(uuid.uuid4()),
                    "user_id": user_id,
                    **form_data.model_dump(),
                    "created_at": int(time.time_ns()),
                    "updated_at": int(time.time_ns()),
                }
            )

            new_note = Note(**note.model_dump())

            db.add(new_note)
            db.commit()
            return note

    def get_notes(self) -> list[NoteModel]:
        with get_db() as db:
            notes = db.query(Note).order_by(Note.updated_at.desc()).all()
            return [NoteModel.model_validate(note) for note in notes]

    def get_notes_by_user_id(
        self, user_id: str, permission: str = "write"
    ) -> list[NoteModel]:
        notes = self.get_notes()
        return [
            note
            for note in notes
            if note.user_id == user_id
            or has_access(user_id, permission, note.access_control)
        ]

    def get_note_by_id(self, id: str) -> Optional[NoteModel]:
        with get_db() as db:
            note = db.query(Note).filter(Note.id == id).first()
            return NoteModel.model_validate(note) if note else None

    def update_note_by_id(self, id: str, form_data: NoteForm) -> Optional[NoteModel]:
        with get_db() as db:
            note = db.query(Note).filter(Note.id == id).first()
            if not note:
                return None

            note.title = form_data.title
            note.data = form_data.data
            note.meta = form_data.meta
            note.access_control = form_data.access_control
            note.updated_at = int(time.time_ns())

            db.commit()
            return NoteModel.model_validate(note) if note else None

    def delete_note_by_id(self, id: str):
        with get_db() as db:
            db.query(Note).filter(Note.id == id).delete()
            db.commit()
            return True


Notes = NoteTable()
