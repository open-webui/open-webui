"""
LLM-as-Judge stub.

Provides the interface for grading a Langfuse trace's response against a rubric.
Implementation is deferred — this file only defines the contract so that callers
(e.g., Phase B3 attempt scoring, scheduled re-grading jobs) can be wired now.
"""

import logging
from dataclasses import dataclass
from typing import Optional

from open_webui.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS.get("RAG", "INFO"))


@dataclass
class JudgeVerdict:
    score: float
    passed: bool
    rationale: Optional[str] = None
    rubric_breakdown: Optional[dict] = None


def judge_response(
    trace_id: str,
    rubric: dict,
    judge_model: Optional[str] = None,
) -> Optional[JudgeVerdict]:
    """
    Grade the response stored on `trace_id` against the given rubric.

    rubric: {"criteria": [{"name": str, "weight": float, "prompt": str}], "pass_threshold": float}
    judge_model: optional override; defaults to the configured judge model.

    Returns None when judging is disabled or fails.
    """
    log.info(
        "[JUDGE] judge_response(trace_id=%s, judge_model=%s) — stub, no-op",
        trace_id,
        judge_model,
    )
    return None
