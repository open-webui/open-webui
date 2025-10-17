import time
import uuid
from typing import Optional, List

from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Boolean, Column, Integer, Text, Index

from open_webui.internal.db import Base, JSONField, get_db


class ModerationScenario(Base):
    __tablename__ = "moderation_scenario"

    id = Column(Text, primary_key=True)
    user_id = Column(Text, nullable=False)
    child_id = Column(Text, nullable=False)
    scenario_prompt = Column(Text, nullable=False)
    original_response = Column(Text, nullable=False)
    is_applicable = Column(Boolean, nullable=True)
    decision = Column(Text, nullable=True)  # 'accept_original' | 'moderate' | 'not_applicable'
    decided_at = Column(BigInteger, nullable=True)
    created_at = Column(BigInteger, nullable=False)
    updated_at = Column(BigInteger, nullable=False)

    __table_args__ = (
        Index("idx_mscenario_user_id", "user_id"),
        Index("idx_mscenario_child_id", "child_id"),
        Index("idx_mscenario_created_at", "created_at"),
    )


class ModerationApplied(Base):
    __tablename__ = "moderation_applied"

    id = Column(Text, primary_key=True)
    scenario_id = Column(Text, nullable=False)
    version_index = Column(Integer, nullable=False)
    strategies = Column(JSONField, nullable=False)
    custom_instructions = Column(JSONField, nullable=False)
    highlighted_texts = Column(JSONField, nullable=False)
    refactored_response = Column(Text, nullable=False)
    confirmed_preferred = Column(Boolean, nullable=False, default=False)
    created_at = Column(BigInteger, nullable=False)
    updated_at = Column(BigInteger, nullable=False)

    __table_args__ = (
        Index("idx_mapplied_scenario_id", "scenario_id"),
        Index("idx_mapplied_confirmed", "confirmed_preferred"),
    )


class ModerationQuestionAnswer(Base):
    __tablename__ = "moderation_question_answer"

    id = Column(Text, primary_key=True)
    scenario_id = Column(Text, nullable=False)
    question_key = Column(Text, nullable=False)
    value = Column(JSONField, nullable=False)
    answered_at = Column(BigInteger, nullable=False)

    __table_args__ = (
        Index("idx_mqa_scenario_id", "scenario_id"),
        Index("idx_mqa_answered_at", "answered_at"),
    )


class ModerationScenarioModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    child_id: str
    scenario_prompt: str
    original_response: str
    is_applicable: Optional[bool] = None
    decision: Optional[str] = None
    decided_at: Optional[int] = None
    created_at: int
    updated_at: int


class ModerationAppliedModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    scenario_id: str
    version_index: int
    strategies: List[str]
    custom_instructions: List[dict]
    highlighted_texts: List[str]
    refactored_response: str
    confirmed_preferred: bool
    created_at: int
    updated_at: int


class ModerationQuestionAnswerModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    scenario_id: str
    question_key: str
    value: dict | str | bool
    answered_at: int


class ModerationScenarioForm(BaseModel):
    user_id: str
    child_id: str
    scenario_prompt: str
    original_response: str


class ModerationScenarioTable:
    def upsert(self, form: ModerationScenarioForm, scenario_id: Optional[str] = None) -> ModerationScenarioModel:
        with get_db() as db:
            ts = int(time.time() * 1000)
            id_val = scenario_id or str(uuid.uuid4())
            obj = db.query(ModerationScenario).filter(ModerationScenario.id == id_val).first()
            if obj:
                obj.user_id = form.user_id
                obj.child_id = form.child_id
                obj.scenario_prompt = form.scenario_prompt
                obj.original_response = form.original_response
                obj.updated_at = ts
            else:
                obj = ModerationScenario(
                    id=id_val,
                    user_id=form.user_id,
                    child_id=form.child_id,
                    scenario_prompt=form.scenario_prompt,
                    original_response=form.original_response,
                    is_applicable=None,
                    decision=None,
                    decided_at=None,
                    created_at=ts,
                    updated_at=ts,
                )
                db.add(obj)
            db.commit()
            db.refresh(obj)
            return ModerationScenarioModel.model_validate(obj)


ModerationScenarios = ModerationScenarioTable()


class ModerationAppliedForm(BaseModel):
    scenario_id: str
    version_index: int
    strategies: list[str]
    custom_instructions: list[dict]
    highlighted_texts: list[str]
    refactored_response: str


class ModerationAppliedTable:
    def create_version(self, form: ModerationAppliedForm) -> ModerationAppliedModel:
        with get_db() as db:
            ts = int(time.time() * 1000)
            obj = ModerationApplied(
                id=str(uuid.uuid4()),
                scenario_id=form.scenario_id,
                version_index=form.version_index,
                strategies=form.strategies,
                custom_instructions=form.custom_instructions,
                highlighted_texts=form.highlighted_texts,
                refactored_response=form.refactored_response,
                confirmed_preferred=False,
                created_at=ts,
                updated_at=ts,
            )
            db.add(obj)
            db.commit()
            db.refresh(obj)
            return ModerationAppliedModel.model_validate(obj)

    def confirm_version(self, scenario_id: str, version_index: int) -> None:
        with get_db() as db:
            ts = int(time.time() * 1000)
            # Clear any previous confirmations
            db.query(ModerationApplied).filter(
                ModerationApplied.scenario_id == scenario_id
            ).update({ModerationApplied.confirmed_preferred: False})

            # Set selected version as confirmed
            obj = db.query(ModerationApplied).filter(
                ModerationApplied.scenario_id == scenario_id,
                ModerationApplied.version_index == version_index,
            ).first()
            if obj:
                obj.confirmed_preferred = True
                obj.updated_at = ts
                db.add(obj)
            db.commit()


ModerationApplieds = ModerationAppliedTable()


class ModerationQuestionAnswerForm(BaseModel):
    scenario_id: str
    question_key: str  # 'is_applicable' | 'satisfaction' | others
    value: dict | str | bool
    answered_at: int


class ModerationQuestionAnswersTable:
    def upsert(self, form: ModerationQuestionAnswerForm) -> ModerationQuestionAnswerModel:
        with get_db() as db:
            # Try to find an existing answer for this question_key
            obj = db.query(ModerationQuestionAnswer).filter(
                ModerationQuestionAnswer.scenario_id == form.scenario_id,
                ModerationQuestionAnswer.question_key == form.question_key,
            ).first()
            if obj:
                obj.value = form.value
                obj.answered_at = form.answered_at
            else:
                obj = ModerationQuestionAnswer(
                    id=str(uuid.uuid4()),
                    scenario_id=form.scenario_id,
                    question_key=form.question_key,
                    value=form.value,
                    answered_at=form.answered_at,
                )
                db.add(obj)
            db.commit()
            db.refresh(obj)
            return ModerationQuestionAnswerModel.model_validate(obj)


ModerationQuestionAnswers = ModerationQuestionAnswersTable()


