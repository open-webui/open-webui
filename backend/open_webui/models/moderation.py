import time
import uuid
from typing import Optional, List

from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Column, Text, Index, Boolean, Integer

from open_webui.internal.db import Base, JSONField, get_db
from open_webui.models.users import Users


class ModerationSession(Base):
    __tablename__ = "moderation_session"

    id = Column(Text, primary_key=True)
    user_id = Column(Text, nullable=False)
    child_id = Column(Text, nullable=False)

    # Versioning/attempt tracking
    scenario_index = Column(Integer, nullable=False, default=0)
    attempt_number = Column(Integer, nullable=False, default=1)
    version_number = Column(Integer, nullable=False, default=0)
    session_number = Column(BigInteger, nullable=False, default=1)

    scenario_prompt = Column(Text, nullable=False)
    original_response = Column(Text, nullable=False)

    # Initial decision and confirmation flags
    initial_decision = Column(Text, nullable=True)  # 'accept_original' | 'moderate' | 'not_applicable'
    is_final_version = Column(Boolean, nullable=False, default=False)

    strategies = Column(JSONField, nullable=True)  # Array of strategy names
    custom_instructions = Column(JSONField, nullable=True)  # Array of strings
    highlighted_texts = Column(JSONField, nullable=True)  # Array of strings
    refactored_response = Column(Text, nullable=True)  # Final moderated response
    session_metadata = Column(JSONField, nullable=True)  # Any additional data (answers, etc.)

    created_at = Column(BigInteger, nullable=False)
    updated_at = Column(BigInteger, nullable=False)

    __table_args__ = (
        Index("idx_moderation_session_user_id", "user_id"),
        Index("idx_moderation_session_child_id", "child_id"),
        Index("idx_moderation_session_created_at", "created_at"),
        Index("idx_mod_session_composite", "user_id", "child_id", "scenario_index", "attempt_number", "session_number"),
        Index("idx_mod_session_final", "user_id", "child_id", "is_final_version"),
        Index("idx_mod_session_user_session", "user_id", "session_number"),
    )


class ModerationSessionModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    child_id: str
    scenario_index: int
    attempt_number: int
    version_number: int
    session_number: int
    scenario_prompt: str
    original_response: str
    initial_decision: Optional[str] = None
    is_final_version: bool
    strategies: Optional[List[str]] = None
    custom_instructions: Optional[List[str]] = None
    highlighted_texts: Optional[List[str]] = None
    refactored_response: Optional[str] = None
    session_metadata: Optional[dict] = None
    created_at: int
    updated_at: int


class ModerationSessionForm(BaseModel):
    session_id: Optional[str] = None
    user_id: str
    child_id: str
    scenario_index: int
    attempt_number: int
    version_number: int
    scenario_prompt: str
    original_response: str
    initial_decision: Optional[str] = None
    strategies: Optional[List[str]] = None
    custom_instructions: Optional[List[str]] = None
    highlighted_texts: Optional[List[str]] = None
    refactored_response: Optional[str] = None
    is_final_version: Optional[bool] = False
    session_metadata: Optional[dict] = None


class ModerationSessionTable:
    def upsert(self, form: ModerationSessionForm) -> ModerationSessionModel:
        """
        Create or update a moderation session version row.
        - Versions are uniquely identified by (user_id, child_id, scenario_index, attempt_number, version_number)
        - Each version is a separate row; client-provided session_id is not used to overwrite prior versions
        - is_final_version marks which version was selected at the end
        """
        with get_db() as db:
            ts = int(time.time() * 1000)

            # Try to find an existing row for this specific version
            obj = (
                db.query(ModerationSession)
                .filter(
                    ModerationSession.user_id == form.user_id,
                    ModerationSession.child_id == form.child_id,
                    ModerationSession.scenario_index == form.scenario_index,
                    ModerationSession.attempt_number == form.attempt_number,
                    ModerationSession.version_number == form.version_number,
                )
                .first()
            )

            if obj:
                # Update this exact version row
                obj.scenario_prompt = form.scenario_prompt
                obj.original_response = form.original_response
                obj.initial_decision = form.initial_decision
                obj.strategies = form.strategies
                obj.custom_instructions = form.custom_instructions
                obj.highlighted_texts = form.highlighted_texts
                obj.refactored_response = form.refactored_response
                obj.is_final_version = bool(form.is_final_version)
                obj.session_metadata = form.session_metadata
                # Ensure session_number is stamped for updated rows as well
                user = Users.get_user_by_id(form.user_id)
                if user and getattr(user, "session_number", None) is not None:
                    try:
                        obj.session_number = int(user.session_number)
                    except Exception:
                        pass
                obj.updated_at = ts
            else:
                # Create a new row for this version; generate a fresh id to avoid overwriting prior versions
                user = Users.get_user_by_id(form.user_id)
                session_number = 1
                if user and getattr(user, "session_number", None) is not None:
                    try:
                        session_number = int(user.session_number)
                    except Exception:
                        session_number = 1
                obj = ModerationSession(
                    id=str(uuid.uuid4()),
                    user_id=form.user_id,
                    child_id=form.child_id,
                    scenario_index=form.scenario_index,
                    attempt_number=form.attempt_number,
                    version_number=form.version_number,
                    session_number=session_number,
                    scenario_prompt=form.scenario_prompt,
                    original_response=form.original_response,
                    initial_decision=form.initial_decision,
                    is_final_version=bool(form.is_final_version),
                    strategies=form.strategies,
                    custom_instructions=form.custom_instructions,
                    highlighted_texts=form.highlighted_texts,
                    refactored_response=form.refactored_response,
                    session_metadata=form.session_metadata,
                    created_at=ts,
                    updated_at=ts,
                )
                db.add(obj)

            # If marking a final version, clear previous finals for this scenario/attempt
            if form.is_final_version:
                (
                    db.query(ModerationSession)
                    .filter(
                        ModerationSession.user_id == form.user_id,
                        ModerationSession.child_id == form.child_id,
                        ModerationSession.scenario_index == form.scenario_index,
                        ModerationSession.attempt_number == form.attempt_number,
                        ModerationSession.id != obj.id,
                    )
                    .update({"is_final_version": False})
                )

            db.commit()
            db.refresh(obj)
            return ModerationSessionModel.model_validate(obj)

    def get_sessions_by_user(self, user_id: str, child_id: Optional[str] = None) -> List[ModerationSessionModel]:
        """Get all sessions for a user, optionally filtered by child_id"""
        with get_db() as db:
            query = db.query(ModerationSession).filter(ModerationSession.user_id == user_id)
            if child_id:
                query = query.filter(ModerationSession.child_id == child_id)
            rows = query.order_by(ModerationSession.created_at.desc()).all()
            return [ModerationSessionModel.model_validate(row) for row in rows]

    def get_session_by_id(self, session_id: str, user_id: str) -> Optional[ModerationSessionModel]:
        """Get a specific session by ID, ensuring user ownership"""
        with get_db() as db:
            row = (
                db.query(ModerationSession)
                .filter(ModerationSession.id == session_id, ModerationSession.user_id == user_id)
                .first()
            )
            return ModerationSessionModel.model_validate(row) if row else None

    def delete_session(self, session_id: str, user_id: str) -> bool:
        """Delete a session, ensuring user ownership"""
        with get_db() as db:
            row = (
                db.query(ModerationSession)
                .filter(ModerationSession.id == session_id, ModerationSession.user_id == user_id)
                .first()
            )
            if not row:
                return False
            db.delete(row)
            db.commit()
            return True


ModerationSessions = ModerationSessionTable()