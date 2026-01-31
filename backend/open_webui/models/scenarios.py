import time
import uuid
import hashlib
import random
import math
from typing import Optional, List, Tuple, Dict
from enum import Enum

from pydantic import BaseModel, ConfigDict
from sqlalchemy import (
    BigInteger,
    Column,
    Text,
    Index,
    Boolean,
    Integer,
    String,
    Float,
    ForeignKey,
)
from sqlalchemy.orm import relationship

from open_webui.internal.db import Base, get_db
import logging

log = logging.getLogger(__name__)


class AssignmentStatus(str, Enum):
    ASSIGNED = "assigned"
    STARTED = "started"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    ABANDONED = "abandoned"


class Scenario(Base):
    __tablename__ = "scenarios"

    scenario_id = Column(String, primary_key=True)
    prompt_text = Column(Text, nullable=False)
    response_text = Column(Text, nullable=False)

    # Metadata fields
    set_name = Column(String, nullable=True)  # 'pilot', 'scaled', etc.
    trait = Column(String, nullable=True)  # 'Agreeableness', 'Conscientiousness', etc.
    polarity = Column(String, nullable=True)  # 'positive', 'negative', 'neutral'
    prompt_style = Column(String, nullable=True)  # 'Journalistic', 'Should I', etc.
    domain = Column(String, nullable=True)  # 'Internet Interaction', 'Self', etc.

    # Source tracking fields
    source = Column(String, nullable=True)  # 'json_file', 'api_generated', 'manual'
    model_name = Column(String, nullable=True)  # Model that produced the response
    is_active = Column(
        Boolean, nullable=False, default=True
    )  # Whether to show to users

    # Counters
    n_assigned = Column(Integer, nullable=False, default=0)
    n_completed = Column(Integer, nullable=False, default=0)
    n_skipped = Column(Integer, nullable=False, default=0)
    n_abandoned = Column(Integer, nullable=False, default=0)

    # Timestamps
    created_at = Column(BigInteger, nullable=False)
    updated_at = Column(BigInteger, nullable=False)

    # Relationships
    assignments = relationship("ScenarioAssignment", back_populates="scenario")

    __table_args__ = (
        Index("idx_scenarios_set_name", "set_name"),
        Index("idx_scenarios_trait", "trait"),
        Index("idx_scenarios_polarity", "polarity"),
        Index("idx_scenarios_is_active", "is_active"),
        Index("idx_scenarios_source", "source"),
        Index("idx_scenarios_n_assigned", "n_assigned"),
    )


class AttentionCheckScenario(Base):
    __tablename__ = "attention_check_scenarios"

    scenario_id = Column(String, primary_key=True)
    prompt_text = Column(Text, nullable=False)
    response_text = Column(Text, nullable=False)

    # Metadata fields (matching CSV structure)
    trait_theme = Column(String, nullable=True)  # 'attention_check'
    trait_phrase = Column(String, nullable=True)  # 'attention_check'
    sentiment = Column(String, nullable=True)  # 'neutral', etc.
    trait_index = Column(Integer, nullable=True)
    prompt_index = Column(Integer, nullable=True)

    # Management fields
    set_name = Column(String, nullable=True)  # Optional set identifier
    is_active = Column(Boolean, nullable=False, default=True)
    source = Column(String, nullable=True)  # 'csv_file', 'api_generated', 'manual'

    # Timestamps
    created_at = Column(BigInteger, nullable=False)
    updated_at = Column(BigInteger, nullable=False)

    __table_args__ = (
        Index("idx_ac_scenarios_is_active", "is_active"),
        Index("idx_ac_scenarios_set_name", "set_name"),
        Index("idx_ac_scenarios_trait_theme", "trait_theme"),
    )


class ScenarioAssignment(Base):
    __tablename__ = "scenario_assignments"

    assignment_id = Column(String, primary_key=True)
    participant_id = Column(String, nullable=False)  # user_id
    scenario_id = Column(String, ForeignKey("scenarios.scenario_id"), nullable=False)
    child_profile_id = Column(String, nullable=True)

    # Status tracking
    status = Column(
        String, nullable=False
    )  # 'assigned', 'started', 'completed', 'skipped', 'abandoned'

    # Timestamps
    assigned_at = Column(BigInteger, nullable=False)
    started_at = Column(BigInteger, nullable=True)
    ended_at = Column(BigInteger, nullable=True)

    # Sampling audit fields
    alpha = Column(Float, nullable=True)  # Weighted sampling alpha parameter
    eligible_pool_size = Column(Integer, nullable=True)
    n_assigned_before = Column(
        Integer, nullable=True
    )  # n_assigned at time of assignment
    weight = Column(Float, nullable=True)  # Calculated weight
    sampling_prob = Column(Float, nullable=True)  # Realized sampling probability
    assignment_position = Column(
        Integer, nullable=True
    )  # Position in session (0-indexed)

    # Outcome fields
    issue_any = Column(Integer, nullable=True)  # 0, 1, or NULL
    skip_stage = Column(String, nullable=True)  # Stage where skip occurred
    skip_reason = Column(String, nullable=True)  # Reason code for skip
    skip_reason_text = Column(Text, nullable=True)  # Optional text explanation

    # Time tracking
    duration_seconds = Column(
        Integer, nullable=True
    )  # Time spent on scenario in seconds (including prompt generation time for custom scenarios)

    # Relationships
    scenario = relationship("Scenario", back_populates="assignments")
    # Bidirectional relationship to Selection (defined in selections.py).
    # Use string class names so SQLAlchemy can resolve them without import cycles.
    selections = relationship("Selection", back_populates="assignment")

    __table_args__ = (
        Index("idx_assignments_participant_id", "participant_id"),
        Index("idx_assignments_scenario_id", "scenario_id"),
        Index("idx_assignments_status", "status"),
        Index("idx_assignments_assigned_at", "assigned_at"),
        Index("idx_assignments_participant_scenario", "participant_id", "scenario_id"),
    )


class ScenarioModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    scenario_id: str
    prompt_text: str
    response_text: str
    set_name: Optional[str] = None
    trait: Optional[str] = None
    polarity: Optional[str] = None
    prompt_style: Optional[str] = None
    domain: Optional[str] = None
    source: Optional[str] = None
    model_name: Optional[str] = None
    is_active: bool
    n_assigned: int
    n_completed: int
    n_skipped: int
    n_abandoned: int
    created_at: int
    updated_at: int


class ScenarioForm(BaseModel):
    scenario_id: Optional[str] = None  # If None, will generate from content hash
    prompt_text: str
    response_text: str
    set_name: Optional[str] = None
    trait: Optional[str] = None
    polarity: Optional[str] = None
    prompt_style: Optional[str] = None
    domain: Optional[str] = None
    source: Optional[str] = None
    model_name: Optional[str] = None
    is_active: Optional[bool] = True


class ScenarioAssignmentModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    assignment_id: str
    participant_id: str
    scenario_id: str
    child_profile_id: Optional[str] = None
    status: str
    assigned_at: int
    started_at: Optional[int] = None
    ended_at: Optional[int] = None
    alpha: Optional[float] = None
    eligible_pool_size: Optional[int] = None
    n_assigned_before: Optional[int] = None
    weight: Optional[float] = None
    sampling_prob: Optional[float] = None
    assignment_position: Optional[int] = None
    issue_any: Optional[int] = None
    skip_stage: Optional[str] = None
    skip_reason: Optional[str] = None
    skip_reason_text: Optional[str] = None
    duration_seconds: Optional[int] = None


class ScenarioAssignmentForm(BaseModel):
    participant_id: str
    scenario_id: Optional[str] = None  # If None, will be assigned via weighted sampling
    child_profile_id: Optional[str] = None
    assignment_position: Optional[int] = None
    alpha: Optional[float] = 1.0  # Default alpha for weighted sampling


class ScenarioTable:
    def upsert(self, form: ScenarioForm) -> ScenarioModel:
        """Create or update a scenario. Generates scenario_id from content hash if not provided."""
        with get_db() as db:
            ts = int(time.time() * 1000)

            # Generate scenario_id from content hash if not provided
            if not form.scenario_id:
                content_hash = hashlib.sha256(
                    f"{form.prompt_text}|{form.response_text}".encode("utf-8")
                ).hexdigest()[:16]
                scenario_id = f"scenario_{content_hash}"
            else:
                scenario_id = form.scenario_id

            # Try to find existing scenario
            obj = db.query(Scenario).filter(Scenario.scenario_id == scenario_id).first()

            if obj:
                # Update existing scenario
                obj.prompt_text = form.prompt_text
                obj.response_text = form.response_text
                if form.set_name is not None:
                    obj.set_name = form.set_name
                if form.trait is not None:
                    obj.trait = form.trait
                if form.polarity is not None:
                    obj.polarity = form.polarity
                if form.prompt_style is not None:
                    obj.prompt_style = form.prompt_style
                if form.domain is not None:
                    obj.domain = form.domain
                if form.source is not None:
                    obj.source = form.source
                if form.model_name is not None:
                    obj.model_name = form.model_name
                if form.is_active is not None:
                    obj.is_active = form.is_active
                obj.updated_at = ts
            else:
                # Create new scenario
                obj = Scenario(
                    scenario_id=scenario_id,
                    prompt_text=form.prompt_text,
                    response_text=form.response_text,
                    set_name=form.set_name,
                    trait=form.trait,
                    polarity=form.polarity,
                    prompt_style=form.prompt_style,
                    domain=form.domain,
                    source=form.source,
                    model_name=form.model_name,
                    is_active=form.is_active if form.is_active is not None else True,
                    n_assigned=0,
                    n_completed=0,
                    n_skipped=0,
                    n_abandoned=0,
                    created_at=ts,
                    updated_at=ts,
                )
                db.add(obj)

            db.commit()
            db.refresh(obj)
            return ScenarioModel.model_validate(obj)

    def get_by_id(self, scenario_id: str) -> Optional[ScenarioModel]:
        """Get a scenario by ID"""
        with get_db() as db:
            obj = db.query(Scenario).filter(Scenario.scenario_id == scenario_id).first()
            return ScenarioModel.model_validate(obj) if obj else None

    def get_all(self, is_active: Optional[bool] = None) -> List[ScenarioModel]:
        """Get all scenarios, optionally filtered by is_active"""
        with get_db() as db:
            query = db.query(Scenario)
            if is_active is not None:
                query = query.filter(Scenario.is_active == is_active)
            rows = query.all()
            return [ScenarioModel.model_validate(row) for row in rows]

    def increment_counter(self, scenario_id: str, counter_name: str) -> bool:
        """Increment a counter (n_assigned, n_completed, n_skipped, n_abandoned)"""
        with get_db() as db:
            obj = db.query(Scenario).filter(Scenario.scenario_id == scenario_id).first()
            if not obj:
                return False

            if counter_name == "n_assigned":
                obj.n_assigned += 1
            elif counter_name == "n_completed":
                obj.n_completed += 1
            elif counter_name == "n_skipped":
                obj.n_skipped += 1
            elif counter_name == "n_abandoned":
                obj.n_abandoned += 1
            else:
                return False

            obj.updated_at = int(time.time() * 1000)
            db.commit()
            return True

    def deactivate_by_set_name(self, set_name: str) -> int:
        """Deactivate all active scenarios with the given set_name. Returns count deactivated."""
        with get_db() as db:
            updated = (
                db.query(Scenario)
                .filter(Scenario.set_name == set_name, Scenario.is_active == True)
                .update({"is_active": False, "updated_at": int(time.time() * 1000)})
            )
            db.commit()
            return updated

    def get_distinct_set_names(self) -> List[Optional[str]]:
        """Get all distinct set_name values from scenarios table (including None/null)"""
        try:
            with get_db() as db:
                # Query returns tuples, extract first element and handle None
                set_names_raw = db.query(Scenario.set_name).distinct().all()
                # Extract scalar values from tuples (each row is a 1-tuple)
                set_names = [row[0] for row in set_names_raw]
                return set_names
        except Exception as e:
            log.error(f"Error getting distinct set names from scenarios: {e}")
            return []

    def set_active_set(self, set_name: Optional[str]) -> dict:
        """
        Activate scenarios with set_name, deactivate all others.
        If set_name is None, activate all scenarios.
        Returns counts of activated and deactivated scenarios.
        """
        with get_db() as db:
            ts = int(time.time() * 1000)
            if set_name is None:
                # Activate all scenarios
                activated = (
                    db.query(Scenario)
                    .filter(Scenario.is_active == False)
                    .update({"is_active": True, "updated_at": ts})
                )
                deactivated = 0
            else:
                # Activate scenarios with this set_name
                activated = (
                    db.query(Scenario)
                    .filter(Scenario.set_name == set_name, Scenario.is_active == False)
                    .update({"is_active": True, "updated_at": ts})
                )

                # Deactivate all other scenarios
                deactivated = (
                    db.query(Scenario)
                    .filter(Scenario.set_name != set_name, Scenario.is_active == True)
                    .update({"is_active": False, "updated_at": ts})
                )

            db.commit()
            return {"activated": activated, "deactivated": deactivated}

    def get_eligible_scenarios(
        self,
        participant_id: str,
        is_active: bool = True,
        set_name: Optional[str] = None,
    ) -> List[Tuple[ScenarioModel, float]]:
        """
        Get eligible scenarios for weighted sampling.
        Excludes scenarios that participant has completed, skipped, assigned, or started.
        Allows scenarios that were abandoned (can be reassigned).

        Returns list of (scenario, weight) tuples.
        """
        with get_db() as db:
            # Get scenario IDs that participant has completed, skipped, assigned, or started
            excluded_scenario_ids = (
                ScenarioAssignments.get_completed_or_skipped_scenario_ids(
                    participant_id
                )
            )

            # Build query for eligible scenarios
            query = db.query(Scenario)
            query = query.filter(Scenario.is_active == is_active)

            if set_name:
                query = query.filter(Scenario.set_name == set_name)

            if excluded_scenario_ids:
                query = query.filter(~Scenario.scenario_id.in_(excluded_scenario_ids))

            scenarios = query.all()

            # Convert to models and calculate weights
            result = []
            for scenario in scenarios:
                scenario_model = ScenarioModel.model_validate(scenario)
                result.append((scenario_model, scenario.n_assigned))

            return result

    def weighted_sample(
        self,
        participant_id: str,
        alpha: float = 1.0,
        is_active: bool = True,
        set_name: Optional[str] = None,
    ) -> Optional[Tuple[ScenarioModel, Dict]]:
        """
        Perform weighted sampling of a scenario for a participant.

        Formula: p(s) ∝ 1/(n_s + 1)^α

        Returns:
            Tuple of (ScenarioModel, sampling_audit_dict) or None if no eligible scenarios
        """
        eligible = self.get_eligible_scenarios(participant_id, is_active, set_name)

        if not eligible:
            return None

        eligible_pool_size = len(eligible)

        # Calculate weights: weight = 1 / (n_assigned + 1)^alpha
        weights = []
        for scenario, n_assigned in eligible:
            weight = 1.0 / math.pow(n_assigned + 1, alpha)
            weights.append(weight)

        # Calculate total weight for normalization
        total_weight = sum(weights)

        if total_weight == 0:
            return None

        # Sample using weighted random selection
        # Use a more robust approach to handle floating point precision
        rand_val = random.random() * total_weight
        cumulative = 0.0
        selected_idx = None

        for i, weight in enumerate(weights):
            # Check if rand_val falls within this weight's range [cumulative, cumulative + weight)
            # For the last item, use <= to handle edge case where rand_val equals total_weight
            # (shouldn't happen with random.random() but could due to floating point precision)
            if i == len(weights) - 1:
                # Last item: use <= to ensure we always select something
                if rand_val <= cumulative + weight:
                    selected_idx = i
                    break
            else:
                # Not last item: use < for half-open interval
                if rand_val < cumulative + weight:
                    selected_idx = i
                    break
            cumulative += weight

        # Safety check: ensure we selected a valid index
        # This should never trigger, but provides a fallback if floating point errors occur
        if selected_idx is None or selected_idx >= len(eligible):
            selected_idx = len(eligible) - 1

        selected_scenario, n_assigned_before = eligible[selected_idx]
        selected_weight = weights[selected_idx]
        sampling_prob = selected_weight / total_weight

        # Build sampling audit dict
        sampling_audit = {
            "eligible_pool_size": eligible_pool_size,
            "n_assigned_before": n_assigned_before,
            "weight": selected_weight,
            "sampling_prob": sampling_prob,
        }

        return (selected_scenario, sampling_audit)


class ScenarioAssignmentTable:
    def create(
        self,
        form: ScenarioAssignmentForm,
        scenario_id: str,
        sampling_audit: Optional[dict] = None,
    ) -> ScenarioAssignmentModel:
        """Create a new assignment"""
        with get_db() as db:
            ts = int(time.time() * 1000)
            assignment_id = str(uuid.uuid4())

            obj = ScenarioAssignment(
                assignment_id=assignment_id,
                participant_id=form.participant_id,
                scenario_id=scenario_id,
                child_profile_id=form.child_profile_id,
                status=AssignmentStatus.ASSIGNED.value,
                assigned_at=ts,
                started_at=None,
                ended_at=None,
                alpha=form.alpha,
                eligible_pool_size=(
                    sampling_audit.get("eligible_pool_size") if sampling_audit else None
                ),
                n_assigned_before=(
                    sampling_audit.get("n_assigned_before") if sampling_audit else None
                ),
                weight=sampling_audit.get("weight") if sampling_audit else None,
                sampling_prob=(
                    sampling_audit.get("sampling_prob") if sampling_audit else None
                ),
                assignment_position=form.assignment_position,
                issue_any=None,
                skip_stage=None,
                skip_reason=None,
                skip_reason_text=None,
            )
            db.add(obj)
            db.commit()
            db.refresh(obj)
            return ScenarioAssignmentModel.model_validate(obj)

    def update_status(
        self,
        assignment_id: str,
        status: AssignmentStatus,
        started_at: Optional[int] = None,
        ended_at: Optional[int] = None,
        issue_any: Optional[int] = None,
        skip_stage: Optional[str] = None,
        skip_reason: Optional[str] = None,
        skip_reason_text: Optional[str] = None,
        duration_seconds: Optional[int] = None,
    ) -> Optional[ScenarioAssignmentModel]:
        """Update assignment status and related fields"""
        with get_db() as db:
            obj = (
                db.query(ScenarioAssignment)
                .filter(ScenarioAssignment.assignment_id == assignment_id)
                .first()
            )
            if not obj:
                return None

            obj.status = status.value
            if started_at is not None:
                obj.started_at = started_at
            if ended_at is not None:
                obj.ended_at = ended_at
            if issue_any is not None:
                obj.issue_any = issue_any
            if skip_stage is not None:
                obj.skip_stage = skip_stage
            if skip_reason is not None:
                obj.skip_reason = skip_reason
            if skip_reason_text is not None:
                obj.skip_reason_text = skip_reason_text
            if duration_seconds is not None:
                obj.duration_seconds = duration_seconds

            db.commit()
            db.refresh(obj)
            return ScenarioAssignmentModel.model_validate(obj)

    def update_duration(
        self, assignment_id: str, duration_seconds: int
    ) -> Optional[ScenarioAssignmentModel]:
        """Update duration_seconds for an assignment without changing status"""
        with get_db() as db:
            obj = (
                db.query(ScenarioAssignment)
                .filter(ScenarioAssignment.assignment_id == assignment_id)
                .first()
            )
            if not obj:
                return None

            obj.duration_seconds = duration_seconds
            db.commit()
            db.refresh(obj)
            return ScenarioAssignmentModel.model_validate(obj)

    def get_by_id(self, assignment_id: str) -> Optional[ScenarioAssignmentModel]:
        """Get an assignment by ID"""
        with get_db() as db:
            obj = (
                db.query(ScenarioAssignment)
                .filter(ScenarioAssignment.assignment_id == assignment_id)
                .first()
            )
            return ScenarioAssignmentModel.model_validate(obj) if obj else None

    def get_by_participant(
        self, participant_id: str, status: Optional[AssignmentStatus] = None
    ) -> List[ScenarioAssignmentModel]:
        """Get all assignments for a participant, optionally filtered by status"""
        with get_db() as db:
            query = db.query(ScenarioAssignment).filter(
                ScenarioAssignment.participant_id == participant_id
            )
            if status:
                query = query.filter(ScenarioAssignment.status == status.value)
            rows = query.order_by(ScenarioAssignment.assigned_at.desc()).all()
            return [ScenarioAssignmentModel.model_validate(row) for row in rows]

    def get_completed_or_skipped_scenario_ids(self, participant_id: str) -> List[str]:
        """
        Get list of scenario_ids that participant has completed, skipped, assigned, or started.
        This ensures uniqueness when assigning multiple scenarios in a session.
        Allows scenarios that were abandoned to be reassigned.
        """
        with get_db() as db:
            rows = (
                db.query(ScenarioAssignment.scenario_id)
                .filter(
                    ScenarioAssignment.participant_id == participant_id,
                    ScenarioAssignment.status.in_(
                        [
                            AssignmentStatus.COMPLETED.value,
                            AssignmentStatus.SKIPPED.value,
                            AssignmentStatus.ASSIGNED.value,  # Exclude already assigned
                            AssignmentStatus.STARTED.value,  # Exclude already started
                        ]
                    ),
                )
                .distinct()
                .all()
            )
            return [row[0] for row in rows]

    def get_assignments_by_child(
        self, child_profile_id: str, status_filter: Optional[List[str]] = None
    ) -> List[ScenarioAssignmentModel]:
        """Get all assignments for a child profile, optionally filtered by status"""
        with get_db() as db:
            query = db.query(ScenarioAssignment).filter(
                ScenarioAssignment.child_profile_id == child_profile_id
            )
            if status_filter:
                query = query.filter(ScenarioAssignment.status.in_(status_filter))
            # Order by assignment_position to maintain order
            rows = query.order_by(ScenarioAssignment.assignment_position.asc()).all()
            return [ScenarioAssignmentModel.model_validate(row) for row in rows]


class AttentionCheckScenarioModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    scenario_id: str
    prompt_text: str
    response_text: str
    trait_theme: Optional[str] = None
    trait_phrase: Optional[str] = None
    sentiment: Optional[str] = None
    trait_index: Optional[int] = None
    prompt_index: Optional[int] = None
    set_name: Optional[str] = None
    is_active: bool
    source: Optional[str] = None
    created_at: int
    updated_at: int


class AttentionCheckScenarioForm(BaseModel):
    prompt_text: str
    response_text: str
    trait_theme: Optional[str] = None
    trait_phrase: Optional[str] = None
    sentiment: Optional[str] = None
    trait_index: Optional[int] = None
    prompt_index: Optional[int] = None
    set_name: Optional[str] = None
    is_active: bool = True
    source: Optional[str] = None


class AttentionCheckScenarioTable:
    def _generate_scenario_id(self, prompt_text: str, response_text: str) -> str:
        """Generate stable scenario_id from prompt and response hash"""
        content = f"{prompt_text}|{response_text}".encode("utf-8")
        hash_obj = hashlib.sha256(content)
        return f"ac_{hash_obj.hexdigest()[:16]}"

    def upsert(self, form: AttentionCheckScenarioForm) -> AttentionCheckScenarioModel:
        """Insert or update an attention check scenario"""
        scenario_id = self._generate_scenario_id(form.prompt_text, form.response_text)
        now = int(time.time() * 1000)

        with get_db() as db:
            obj = (
                db.query(AttentionCheckScenario)
                .filter(AttentionCheckScenario.scenario_id == scenario_id)
                .first()
            )

            if obj:
                # Update existing
                obj.prompt_text = form.prompt_text
                obj.response_text = form.response_text
                obj.trait_theme = form.trait_theme
                obj.trait_phrase = form.trait_phrase
                obj.sentiment = form.sentiment
                obj.trait_index = form.trait_index
                obj.prompt_index = form.prompt_index
                obj.set_name = form.set_name
                obj.is_active = form.is_active
                obj.source = form.source
                obj.updated_at = now
            else:
                # Create new
                obj = AttentionCheckScenario(
                    scenario_id=scenario_id,
                    prompt_text=form.prompt_text,
                    response_text=form.response_text,
                    trait_theme=form.trait_theme,
                    trait_phrase=form.trait_phrase,
                    sentiment=form.sentiment,
                    trait_index=form.trait_index,
                    prompt_index=form.prompt_index,
                    set_name=form.set_name,
                    is_active=form.is_active,
                    source=form.source,
                    created_at=now,
                    updated_at=now,
                )
                db.add(obj)

            db.commit()
            db.refresh(obj)
            return AttentionCheckScenarioModel.model_validate(obj)

    def get_by_id(self, scenario_id: str) -> Optional[AttentionCheckScenarioModel]:
        """Get an attention check scenario by ID"""
        with get_db() as db:
            obj = (
                db.query(AttentionCheckScenario)
                .filter(AttentionCheckScenario.scenario_id == scenario_id)
                .first()
            )
            return AttentionCheckScenarioModel.model_validate(obj) if obj else None

    def get_all(
        self, is_active: Optional[bool] = None, set_name: Optional[str] = None
    ) -> List[AttentionCheckScenarioModel]:
        """Get all attention check scenarios, optionally filtered"""
        with get_db() as db:
            query = db.query(AttentionCheckScenario)
            if is_active is not None:
                query = query.filter(AttentionCheckScenario.is_active == is_active)
            if set_name:
                query = query.filter(AttentionCheckScenario.set_name == set_name)
            rows = query.order_by(AttentionCheckScenario.created_at.asc()).all()
            return [AttentionCheckScenarioModel.model_validate(row) for row in rows]

    def get_random(
        self, is_active: bool = True
    ) -> Optional[AttentionCheckScenarioModel]:
        """Get a random active attention check scenario"""
        with get_db() as db:
            rows = (
                db.query(AttentionCheckScenario)
                .filter(AttentionCheckScenario.is_active == is_active)
                .all()
            )
            if not rows:
                return None
            selected = random.choice(rows)
            return AttentionCheckScenarioModel.model_validate(selected)

    def deactivate_by_set_name(self, set_name: str) -> int:
        """Deactivate all active attention check scenarios with the given set_name. Returns count deactivated."""
        with get_db() as db:
            updated = (
                db.query(AttentionCheckScenario)
                .filter(
                    AttentionCheckScenario.set_name == set_name,
                    AttentionCheckScenario.is_active == True,
                )
                .update({"is_active": False, "updated_at": int(time.time() * 1000)})
            )
            db.commit()
            return updated

    def get_distinct_set_names(self) -> List[Optional[str]]:
        """Get all distinct set_name values from attention_check_scenarios table (including None/null)"""
        try:
            with get_db() as db:
                # Query returns tuples, extract first element and handle None
                set_names_raw = (
                    db.query(AttentionCheckScenario.set_name).distinct().all()
                )
                # Extract scalar values from tuples (each row is a 1-tuple)
                set_names = [row[0] for row in set_names_raw]
                return set_names
        except Exception as e:
            log.error(f"Error getting distinct set names from attention checks: {e}")
            return []

    def set_active_set(self, set_name: Optional[str]) -> dict:
        """
        Activate attention check scenarios with set_name, deactivate all others.
        If set_name is None, activate all attention check scenarios.
        Returns counts of activated and deactivated scenarios.
        """
        with get_db() as db:
            ts = int(time.time() * 1000)
            if set_name is None:
                # Activate all attention check scenarios
                activated = (
                    db.query(AttentionCheckScenario)
                    .filter(AttentionCheckScenario.is_active == False)
                    .update({"is_active": True, "updated_at": ts})
                )
                deactivated = 0
            else:
                # Activate attention check scenarios with this set_name
                activated = (
                    db.query(AttentionCheckScenario)
                    .filter(
                        AttentionCheckScenario.set_name == set_name,
                        AttentionCheckScenario.is_active == False,
                    )
                    .update({"is_active": True, "updated_at": ts})
                )

                # Deactivate all other attention check scenarios
                deactivated = (
                    db.query(AttentionCheckScenario)
                    .filter(
                        AttentionCheckScenario.set_name != set_name,
                        AttentionCheckScenario.is_active == True,
                    )
                    .update({"is_active": False, "updated_at": ts})
                )

            db.commit()
            return {"activated": activated, "deactivated": deactivated}


# Global instances
Scenarios = ScenarioTable()
ScenarioAssignments = ScenarioAssignmentTable()
AttentionCheckScenarios = AttentionCheckScenarioTable()
