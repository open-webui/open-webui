import logging
import time
import uuid
from typing import Optional

from open_webui.internal.db import Base, get_db
from open_webui.env import SRC_LOG_LEVELS
from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Column, Text, JSON

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

####################
# Grants Feedback DB Schema
####################


class GrantsNote(Base):
    __tablename__ = "grants_notes"
    id = Column(Text, primary_key=True)
    user_id = Column(Text)
    chat_id = Column(Text)
    version = Column(BigInteger, default=0)
    type = Column(Text)
    note = Column(Text, nullable=True)
    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)


class GrantsNoteModel(BaseModel):
    id: str
    user_id: str
    chat_id: str
    version: int
    type: str
    note: Optional[str] = None
    created_at: int
    updated_at: int

    model_config = ConfigDict(from_attributes=True)


####################
# Forms
####################


class GrantsNoteResponse(BaseModel):
    id: str
    user_id: str
    chat_id: str
    version: int
    type: str
    note: Optional[str] = None
    created_at: int
    updated_at: int


class GrantsNoteForm(BaseModel):
    note: str  # the actual feedback string
    extra_data: Optional[dict] = None  # if you want extensibility later

    model_config = ConfigDict(extra="allow")  # allows arbitrary fields if needed

####################


class GrantsNotesTable:
    def insert_new_note(
        self, user_id: str, chat_id: str, note: str
    ) -> GrantsNoteModel:
        with get_db() as db:
            id = str(uuid.uuid4())
            notes = GrantsNoteModel(
                **{
                    "id": id,
                    "user_id": user_id,
                    "chat_id": chat_id,
                    "version": 0,
                    "type": "grants_feedback",
                    "note": note,
                    "created_at": int(time.time()),
                    "updated_at": int(time.time()),
                }
            )
            try:
                result = GrantsNote(**notes.model_dump())
                db.add(result)
                db.commit()
                db.refresh(result)
                if result:
                    return GrantsNoteModel.model_validate(result)
                else:
                    return None

            except Exception as e:
                log.exception(f"Error creating a new grants feedback: {e}")
                return None

    def get_note_by_user_id_and_chat_id(
        self, user_id: str, chat_id: str
    ) -> Optional[GrantsNoteModel]:
        try:
            with get_db() as db:
                note = (
                    db.query(GrantsNote)
                    .filter_by(user_id=user_id, chat_id=chat_id)
                    .first()
                )
                if not note:
                    return None
                return GrantsNoteModel.model_validate(note)
        except Exception:
            return None


    def update_note_by_user_id_and_chat_id(
            self, user_id: str, chat_id: str, note: str
    ) -> Optional[GrantsNoteModel]:
        try:
            with get_db() as db:
                result = (
                    db.query(GrantsNote)
                    .filter_by(user_id=user_id, chat_id=chat_id)
                    .first()
                )
                if not result:
                    return None
                result.note = note
                db.commit()
                #db.refresh(db_note)
                return GrantsNoteModel.model_validate(result)
        except Exception:
            return None


Notes = GrantsNotesTable()
