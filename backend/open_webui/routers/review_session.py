"""
Review session router (Type 4).

Skeleton endpoints that wrap the loop-scoped Langfuse trace described in the
educational design spec section 6:

    Pre  : queue load             POST /api/v1/review-session/start
    Loop : per-iteration          POST /api/v1/review-session/{session_id}/iteration
    Post : session end            POST /api/v1/review-session/{session_id}/end

The actual problem-selection / evaluation / log-API logic is owned by upstream
services (TopicState scheduler, evaluation pipeline). This router provides:
- A session-scoped Langfuse trace (one trace per session)
- Iteration sub-spans via LearningSpanEmitter.begin_iteration / end_iteration
- All Type 4 instrumentation points (#1~#13) reachable via emit calls
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from open_webui.utils.auth import get_verified_user
from open_webui.integrations.learning_spans import LearningSpanEmitter, build_emitter
from open_webui.integrations.langfuse_tracing import get_langfuse_tracer

log = logging.getLogger(__name__)
router = APIRouter()


# ──────────────────────────────────────────────────────────────────────────────
# In-memory session registry (production: replace with Redis or DB).
# Each session holds its parent trace object and iteration count.
# ──────────────────────────────────────────────────────────────────────────────


class _SessionState:
    __slots__ = (
        "session_id",
        "user_id",
        "started_at",
        "iteration_idx",
        "items_completed",
        "items_skipped",
        "scores",
        "trace",
        "emitter",
    )

    def __init__(
        self, session_id: str, user_id: str, trace: Any, emitter: LearningSpanEmitter
    ):
        self.session_id = session_id
        self.user_id = user_id
        self.started_at = time.time()
        self.iteration_idx = 0
        self.items_completed = 0
        self.items_skipped = 0
        self.scores: List[float] = []
        self.trace = trace
        self.emitter = emitter


_SESSIONS: Dict[str, _SessionState] = {}


# ──────────────────────────────────────────────────────────────────────────────
# Schemas
# ──────────────────────────────────────────────────────────────────────────────


class SessionStartForm(BaseModel):
    due_topics: List[str] = []
    remediation_items: List[str] = []
    session_goal: Optional[str] = None
    proficiency: Optional[str] = None


class SessionStartResponse(BaseModel):
    session_id: str


class IterationForm(BaseModel):
    item_id: str
    topic_id: Optional[str] = None
    prev_topic_id: Optional[str] = None
    problem_case: int = 1  # 1 or 2
    item_difficulty: Optional[str] = None
    hint_level: Optional[str] = None
    response_text: Optional[str] = None
    response_time_ms: Optional[float] = None
    base_score: float = 0.0
    partial_breakdown: Optional[Dict[str, float]] = None
    time_factor: float = 1.0
    log_api_status: str = "ok"
    log_api_latency_ms: Optional[float] = None
    log_api_retry_count: int = 0
    loop_continue: bool = True
    exit_reason: Optional[str] = None


class IterationResponse(BaseModel):
    iteration_idx: int
    attempt_score: float
    verdict: str


class SessionEndForm(BaseModel):
    drop_off_step: Optional[str] = None
    user_rating: Optional[float] = None
    self_perceived_difficulty: Optional[str] = None


class SessionEndResponse(BaseModel):
    items_completed: int
    items_skipped: int
    avg_attempt_score: Optional[float]
    duration_ms: int


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────


def _verdict_for(attempt_score: float) -> str:
    if attempt_score >= 0.9:
        return "full"
    if attempt_score >= 0.4:
        return "partial"
    return "wrong"


def _new_session_trace(session_id: str, user_id: str) -> Optional[Any]:
    """Create a Langfuse trace dedicated to this review session."""
    tracer = get_langfuse_tracer()
    if tracer is None or tracer.langfuse is None:
        return None
    try:
        from langfuse.types import TraceContext

        normalized = session_id.replace("-", "").lower()[:32]
        trace_context = TraceContext(
            trace_id=normalized,
            session_id=normalized,
            user_id=user_id,
        )
        return tracer.langfuse.start_observation(
            trace_context=trace_context,
            name="type4_session",
            as_type="span",
            input={"session_id": session_id},
            metadata={"chat_type": "session", "model_tier": "flash"},
        )
    except Exception as e:
        log.warning(f"[REVIEW_SESSION] trace creation failed: {e}")
        return None


# ──────────────────────────────────────────────────────────────────────────────
# Endpoints
# ──────────────────────────────────────────────────────────────────────────────


@router.post("/start", response_model=SessionStartResponse)
async def start_session(form: SessionStartForm, user=Depends(get_verified_user)):
    session_id = str(uuid.uuid4())
    trace = _new_session_trace(session_id, user.id)
    emitter = build_emitter(
        parent=trace,
        chat_type="session",
        base_meta={
            "trace_id": session_id,
            "user_id": user.id,
            "proficiency": form.proficiency,
            "model_tier": "flash",
        },
    )
    emitter.routing(routed_type="type_session", confidence="explicit")
    emitter.t4_session_start(
        due_topic_count=len(form.due_topics),
        remediation_item_count=len(form.remediation_items),
        session_goal=form.session_goal,
    )
    _SESSIONS[session_id] = _SessionState(session_id, user.id, trace, emitter)
    return SessionStartResponse(session_id=session_id)


@router.post("/{session_id}/iteration", response_model=IterationResponse)
async def run_iteration(
    session_id: str, form: IterationForm, user=Depends(get_verified_user)
):
    state = _SESSIONS.get(session_id)
    if state is None:
        raise HTTPException(status_code=404, detail="session not found")
    if state.user_id != user.id:
        raise HTTPException(status_code=403, detail="not your session")

    state.iteration_idx += 1
    state.emitter.begin_iteration(state.iteration_idx)
    try:
        state.emitter.t4_problem_selection(
            problem_case=form.problem_case,
            item_id=form.item_id,
            topic_id=form.topic_id,
            prev_topic_id=form.prev_topic_id,
            interleaved=(
                (form.prev_topic_id != form.topic_id) if form.prev_topic_id else True
            ),
        )
        state.emitter.t4_problem_present(
            item_difficulty=form.item_difficulty,
            hint_level=form.hint_level,
        )
        if form.response_text is not None:
            state.emitter.t4_response_collect(
                response_token_count=len(form.response_text.split()),
                response_time_ms=form.response_time_ms,
            )
        state.emitter.t4_evaluation_base(
            base_score=form.base_score,
            partial_breakdown=form.partial_breakdown,
        )
        state.emitter.t4_evaluation_time(time_factor=form.time_factor)

        attempt_score = max(0.0, min(1.0, form.base_score * form.time_factor))
        verdict = _verdict_for(attempt_score)
        state.emitter.t4_attempt_score(attempt_score=attempt_score, verdict=verdict)
        state.scores.append(attempt_score)
        if form.loop_continue:
            state.items_completed += 1
        else:
            state.items_skipped += 1

        state.emitter.t4_log_api_call(
            api_status=form.log_api_status,
            latency_ms=form.log_api_latency_ms,
            retry_count=form.log_api_retry_count,
        )
        state.emitter.t4_loop_decision(
            loop_continue=form.loop_continue,
            exit_reason=form.exit_reason,
        )
    finally:
        state.emitter.end_iteration(
            output={"attempt_score": state.scores[-1] if state.scores else None}
        )

    return IterationResponse(
        iteration_idx=state.iteration_idx,
        attempt_score=state.scores[-1] if state.scores else 0.0,
        verdict=verdict,
    )


@router.post("/{session_id}/end", response_model=SessionEndResponse)
async def end_session(
    session_id: str, form: SessionEndForm, user=Depends(get_verified_user)
):
    state = _SESSIONS.pop(session_id, None)
    if state is None:
        raise HTTPException(status_code=404, detail="session not found")
    if state.user_id != user.id:
        raise HTTPException(status_code=403, detail="not your session")

    duration_ms = int((time.time() - state.started_at) * 1000)
    avg = (sum(state.scores) / len(state.scores)) if state.scores else None

    state.emitter.t4_session_end(
        items_completed=state.items_completed,
        items_skipped=state.items_skipped,
        total_duration_ms=duration_ms,
        avg_attempt_score=avg,
        drop_off_step=form.drop_off_step,
    )
    if form.user_rating is not None:
        state.emitter.t4_user_rating(
            rating=form.user_rating,
            self_perceived_difficulty=form.self_perceived_difficulty,
        )

    if state.trace is not None:
        try:
            state.trace.end()
            tracer = get_langfuse_tracer()
            if tracer:
                tracer.langfuse.flush()
        except Exception as e:
            log.warning(f"[REVIEW_SESSION] trace.end failed: {e}")

    return SessionEndResponse(
        items_completed=state.items_completed,
        items_skipped=state.items_skipped,
        avg_attempt_score=avg,
        duration_ms=duration_ms,
    )
