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

    # Attention check tracking
    is_attention_check = Column(Boolean, nullable=False, default=False)
    attention_check_selected = Column(Boolean, nullable=False, default=False)
    attention_check_passed = Column(Boolean, nullable=False, default=False)

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
    is_attention_check: bool
    attention_check_selected: bool
    attention_check_passed: bool
    created_at: int
    updated_at: int


class ModerationSessionForm(BaseModel):
    session_id: Optional[str] = None
    user_id: str
    child_id: str
    scenario_index: int
    attempt_number: int
    version_number: int
    session_number: Optional[int] = None
    scenario_prompt: str
    original_response: str
    initial_decision: Optional[str] = None
    strategies: Optional[List[str]] = None
    custom_instructions: Optional[List[str]] = None
    highlighted_texts: Optional[List[str]] = None
    refactored_response: Optional[str] = None
    is_final_version: Optional[bool] = False
    session_metadata: Optional[dict] = None
    is_attention_check: Optional[bool] = False
    attention_check_selected: Optional[bool] = False
    attention_check_passed: Optional[bool] = False


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

            # Resolve session number: prefer form, then user's session_number, fallback to 1
            user = Users.get_user_by_id(form.user_id)
            resolved_session_number = None
            if form.session_number is not None:
                try:
                    resolved_session_number = int(form.session_number)
                except Exception:
                    resolved_session_number = None
            if resolved_session_number is None and user and getattr(user, "session_number", None) is not None:
                try:
                    resolved_session_number = int(user.session_number)
                except Exception:
                    resolved_session_number = None
            if resolved_session_number is None:
                resolved_session_number = 1

            # Try to find an existing row for this specific version within the same session
            obj = (
                db.query(ModerationSession)
                .filter(
                    ModerationSession.user_id == form.user_id,
                    ModerationSession.child_id == form.child_id,
                    ModerationSession.scenario_index == form.scenario_index,
                    ModerationSession.attempt_number == form.attempt_number,
                    ModerationSession.version_number == form.version_number,
                    ModerationSession.session_number == resolved_session_number,
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
                obj.is_attention_check = bool(form.is_attention_check)
                obj.attention_check_selected = bool(form.attention_check_selected)
                obj.attention_check_passed = bool(form.attention_check_passed)
                # Ensure session_number remains consistent for this update
                obj.session_number = resolved_session_number
                obj.updated_at = ts
            else:
                # Create a new row for this version; generate a fresh id to avoid overwriting prior versions
                obj = ModerationSession(
                    id=str(uuid.uuid4()),
                    user_id=form.user_id,
                    child_id=form.child_id,
                    scenario_index=form.scenario_index,
                    attempt_number=form.attempt_number,
                    version_number=form.version_number,
                    session_number=resolved_session_number,
                    scenario_prompt=form.scenario_prompt,
                    original_response=form.original_response,
                    initial_decision=form.initial_decision,
                    is_final_version=bool(form.is_final_version),
                    strategies=form.strategies,
                    custom_instructions=form.custom_instructions,
                    highlighted_texts=form.highlighted_texts,
                    refactored_response=form.refactored_response,
                    session_metadata=form.session_metadata,
                    is_attention_check=bool(form.is_attention_check),
                    attention_check_selected=bool(form.attention_check_selected),
                    attention_check_passed=bool(form.attention_check_passed),
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


class ModerationSessionActivity(Base):
    __tablename__ = "moderation_session_activity"

    id = Column(Text, primary_key=True)
    user_id = Column(Text, nullable=False)
    child_id = Column(Text, nullable=False)
    session_number = Column(BigInteger, nullable=False, default=1)
    active_ms_delta = Column(BigInteger, nullable=False, default=0)
    cumulative_ms = Column(BigInteger, nullable=False, default=0)
    created_at = Column(BigInteger, nullable=False)

    __table_args__ = (
        Index("idx_mod_activity_user_child_session", "user_id", "child_id", "session_number"),
        Index("idx_mod_activity_created_at", "created_at"),
    )


class ModerationSessionActivityForm(BaseModel):
    user_id: str
    child_id: str
    session_number: int
    active_ms_cumulative: int


class ModerationSessionActivityModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    child_id: str
    session_number: int
    active_ms_delta: int
    cumulative_ms: int
    created_at: int


class ModerationSessionActivityTable:
    def add_activity(self, form: ModerationSessionActivityForm) -> ModerationSessionActivityModel:
        with get_db() as db:
            ts = int(time.time() * 1000)
            # Fetch last cumulative for this user/child/session
            last = (
                db.query(ModerationSessionActivity)
                .filter(
                    ModerationSessionActivity.user_id == form.user_id,
                    ModerationSessionActivity.child_id == form.child_id,
                    ModerationSessionActivity.session_number == form.session_number,
                )
                .order_by(ModerationSessionActivity.created_at.desc())
                .first()
            )
            last_cum = int(getattr(last, "cumulative_ms", 0) or 0)
            incoming = max(0, int(form.active_ms_cumulative))
            delta = max(0, incoming - last_cum)
            obj = ModerationSessionActivity(
                id=str(uuid.uuid4()),
                user_id=form.user_id,
                child_id=form.child_id,
                session_number=int(form.session_number),
                active_ms_delta=delta,
                cumulative_ms=incoming,
                created_at=ts,
            )
            db.add(obj)
            db.commit()
            db.refresh(obj)
            return ModerationSessionActivityModel.model_validate(obj)


ModerationSessionActivities = ModerationSessionActivityTable()