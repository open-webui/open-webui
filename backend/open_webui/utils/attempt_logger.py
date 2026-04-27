"""
Attempt logger.

Records a single problem-solving attempt:
- Persists to the `attempts` table (DB).
- Pushes a `correctness` score (0|1) onto the linked Langfuse trace.

Used by Type 2 (problem-solving) and Type 3 (solution review) flows.
"""

import logging
from typing import Optional

from open_webui.env import SRC_LOG_LEVELS
from open_webui.models.attempts import Attempts, AttemptForm, AttemptModel

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS.get("MODELS", "INFO"))


def _get_tracer():
    try:
        from open_webui.integrations.langfuse_tracing import get_langfuse_tracer
        return get_langfuse_tracer()
    except Exception:
        return None


def log_attempt(
    user_id: str,
    problem_id: Optional[str] = None,
    chapter_id: Optional[str] = None,
    answer: Optional[str] = None,
    is_correct: Optional[bool] = None,
    score: Optional[float] = None,
    trace_id: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> Optional[AttemptModel]:
    """
    Persist a problem-solving attempt and emit a Langfuse score on the trace.

    Returns the created AttemptModel, or None on DB failure.
    """
    record = Attempts.insert_new_attempt(
        AttemptForm(
            user_id=user_id,
            problem_id=problem_id,
            chapter_id=chapter_id,
            answer=answer,
            is_correct=is_correct,
            score=score,
            trace_id=trace_id,
            metadata=metadata or {},
        )
    )
    if record is None:
        log.warning("[ATTEMPT] DB insert failed for user=%s problem=%s", user_id, problem_id)

    if trace_id:
        tracer = _get_tracer()
        if tracer is not None and hasattr(tracer, "score_trace"):
            try:
                if is_correct is not None:
                    tracer.score_trace(
                        trace_id=trace_id,
                        name="correctness",
                        value=1.0 if is_correct else 0.0,
                        comment=(metadata or {}).get("comment"),
                    )
                if score is not None:
                    tracer.score_trace(
                        trace_id=trace_id,
                        name="rubric_score",
                        value=float(score),
                    )
            except Exception as e:
                log.warning(f"[ATTEMPT] score_trace failed: {e}")

        # Emit attempt_log span (T2#16 / T3#12) so the timeline shows the call.
        try:
            from open_webui.integrations.learning_spans import build_emitter
            chat_type = (metadata or {}).get("chat_type") or "problem"
            emitter = build_emitter(
                parent=None,
                chat_type=chat_type,
                base_meta={"trace_id": trace_id, "user_id": user_id},
            )
            attempt_id = record.id if record else "unknown"
            if chat_type == "review":
                emitter.t3_attempt_log(
                    attempt_id=attempt_id,
                    item_id=problem_id,
                    topic_id=chapter_id,
                    base_score=(metadata or {}).get("base_score"),
                    time_factor=(metadata or {}).get("time_factor"),
                    attempt_score=score,
                )
            else:
                emitter.t2_attempt_log(
                    attempt_id=attempt_id,
                    item_id=problem_id,
                    topic_id=chapter_id,
                    user_solution_attached=bool(answer),
                )
        except Exception as e:
            log.warning(f"[ATTEMPT] attempt_log span failed: {e}")

    return record
