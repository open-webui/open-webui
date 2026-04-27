"""
Learning span emitter — Type 1~4 Langfuse instrumentation contract.

Mirrors the 63 connection points from the educational design spec:
- Type 1 (Concept):       14 points
- Type 2 (Problem):       20 points
- Type 3 (Review):        16 points
- Type 4 (Session):       13 points

Usage:
    from open_webui.integrations.learning_spans import LearningSpanEmitter
    from open_webui.integrations.langfuse_tracing import get_langfuse_tracer

    emitter = LearningSpanEmitter(
        tracer=get_langfuse_tracer(),
        parent=trace_obj,                # generation/trace from trace_chat_completion
        chat_type="problem",             # concept | problem | review | session
        base_meta={"user_id": ..., "topic_id": ..., "proficiency": ...},
    )
    emitter.input_classification(intent_class="high", latency_ms=4.1)
    emitter.routing(routed_type="type2", confidence="high")
    emitter.problem_classification(case="case2", confidence="mid")
    ...

All emitter methods are best-effort — they never raise. If the tracer
or parent is None, calls are silent no-ops.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, Iterable, List, Optional

log = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# Span name constants — kept here as the single source of truth so dashboards,
# Langfuse filters, and LLM-as-Judge prompts all reference identical strings.
# ──────────────────────────────────────────────────────────────────────────────

# Base / shared
SPAN_INPUT_CLASSIFICATION = "input_classification"
SPAN_RAG_CALL = "rag_call"

# Type 1
SPAN_T1_INTERNAL_THINKING = "internal_thinking"
SPAN_T1_STEP1_DEFINITION = "step1_definition"
SPAN_T1_STEP2_EXAMPLE = "step2_example"
SPAN_T1_STEP3_BOUNDARY = "step3_boundary"
SPAN_T1_STEP4_SOCRATIC = "step4_socratic"
SPAN_T1_STEP5_EXPANSION = "step5_expansion"

# Type 2
SPAN_T2_PROBLEM_CLASSIFICATION = "problem_classification"
SPAN_T2_STEP1_CONCEPT = "step1_concept"
SPAN_T2_STEP2_SUBEXPRESSION = "step2_subexpression"
SPAN_T2_STEP2_MIDGOAL = "step2_midgoal"
SPAN_T2_STEP3_STRATEGY = "step3_strategy"
SPAN_T2_STEP4_ANSWER = "step4_answer"
SPAN_T2_ESCALATION = "escalation"
SPAN_T2_ATTEMPT_LOG = "attempt_log"

# Type 3
SPAN_T3_INPUT_COMPLETENESS = "input_completeness"
SPAN_T3_GAP_DIAGNOSIS = "gap_diagnosis"
SPAN_T3_VERDICT = "verdict"
SPAN_T3_STEP1_DIAGNOSIS = "step1_diagnosis"
SPAN_T3_STEP2_ALTERNATIVE = "step2_alternative"
SPAN_T3_ATTEMPT_LOG = "attempt_log"

# Type 4
SPAN_T4_SESSION_START = "session_start"
SPAN_T4_PROBLEM_SELECTION = "problem_selection"
SPAN_T4_PROBLEM_PRESENT = "problem_present"
SPAN_T4_RESPONSE_COLLECT = "response_collect"
SPAN_T4_EVALUATION_BASE = "evaluation_base"
SPAN_T4_EVALUATION_TIME = "evaluation_time"
SPAN_T4_LOG_API_CALL = "log_api_call"


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────


def _safe(fn):
    """Decorator: swallow exceptions so instrumentation never breaks the request."""

    def wrapper(self, *args, **kwargs):
        try:
            return fn(self, *args, **kwargs)
        except Exception as e:
            log.warning(f"[LEARNING_SPAN] {fn.__name__} failed: {e}")
            return None

    wrapper.__name__ = fn.__name__
    wrapper.__doc__ = fn.__doc__
    return wrapper


class _SpanCtx:
    """Context manager wrapping a Langfuse span — auto-end on exit, capture output."""

    def __init__(self, tracer, span):
        self._tracer = tracer
        self._span = span
        self._output: Any = None

    def set_output(self, output: Any) -> None:
        self._output = output

    def end(
        self, output: Any = None, metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        if self._tracer and self._span is not None:
            self._tracer.end_span(
                self._span,
                output=output if output is not None else self._output,
                metadata=metadata,
            )
        self._span = None

    def __enter__(self) -> "_SpanCtx":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if exc_type is not None and self._span is not None:
            try:
                self._span.update(metadata={"error": str(exc)})
            except Exception:
                pass
        self.end()


# ──────────────────────────────────────────────────────────────────────────────
# LearningSpanEmitter — the contract
# ──────────────────────────────────────────────────────────────────────────────


class LearningSpanEmitter:
    """
    Best-effort emitter of all 63 Type 1~4 instrumentation points.

    Every method is silent on failure and on missing tracer/parent.
    For Type 4 (session-scoped), use `begin_iteration(idx)` to nest spans
    under a `problem_iteration_N` sub-span.
    """

    def __init__(
        self,
        tracer,
        parent: Any,
        chat_type: Optional[str],
        base_meta: Optional[Dict[str, Any]] = None,
    ):
        self.tracer = tracer
        self.parent = parent
        self.chat_type = chat_type
        self.base_meta = dict(base_meta or {})
        self._iteration_span = None  # current Type 4 iteration parent

    # ── internal ───────────────────────────────────────────────────────────

    def _meta(self, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        m = dict(self.base_meta)
        if self.chat_type:
            m.setdefault("chat_type", self.chat_type)
        if extra:
            m.update(extra)
        return m

    def _parent(self):
        return self._iteration_span if self._iteration_span is not None else self.parent

    def _open(
        self,
        name: str,
        input: Any = None,
        meta: Optional[Dict[str, Any]] = None,
    ):
        if self.tracer is None:
            return None
        return self.tracer.start_span(
            self._parent(), name=name, input=input, metadata=self._meta(meta)
        )

    def _emit(
        self,
        name: str,
        input: Any = None,
        output: Any = None,
        meta: Optional[Dict[str, Any]] = None,
    ) -> None:
        """One-shot span: open → close immediately with the given output."""
        if self.tracer is None:
            return
        span = self._open(name, input=input, meta=meta)
        if span is None:
            return
        self.tracer.end_span(span, output=output, metadata=self._meta(meta))

    def _tag(self, **fields) -> None:
        """
        Tags are recorded as no-input spans named `tag:<key=value,...>` so they
        appear in the Langfuse trace timeline but don't pollute generation IO.
        """
        if not fields or self.tracer is None:
            return
        meta = self._meta({"_kind": "tag", **fields})
        self._emit(
            name="tag:" + ",".join(f"{k}={v}" for k, v in fields.items()), meta=meta
        )

    # ── Base / shared (T1#1~4, T2#1~6, T3#1~6, T4#1~2) ─────────────────────

    @_safe
    def input_classification(
        self, intent_class: str, latency_ms: Optional[float] = None
    ) -> None:
        """T1#2 / T2#2 / T3#2 — Base input classification (low/high)."""
        self._emit(
            name=SPAN_INPUT_CLASSIFICATION,
            output={"intent_class": intent_class, "latency_ms": latency_ms},
            meta={"intent_class": intent_class},
        )

    @_safe
    def routing(self, routed_type: str, confidence: Optional[str] = None) -> None:
        """T1#3 / T2#3 / T3#3 — Type self-routing tag."""
        self._tag(routed_type=routed_type, routing_confidence=confidence or "n/a")

    @_safe
    def rag_call(
        self,
        topic_ids: Optional[Iterable[str]] = None,
        chunks_count: Optional[int] = None,
        latency_ms: Optional[float] = None,
    ) -> None:
        """T1#4 / T2#6 / T3#6 — RAG retrieval span."""
        self._emit(
            name=SPAN_RAG_CALL,
            output={
                "rag_topic_ids": list(topic_ids) if topic_ids is not None else [],
                "rag_chunks_count": chunks_count,
                "rag_latency_ms": latency_ms,
            },
        )

    @_safe
    def refusal(self, reason: str) -> None:
        """Base — refusal tag."""
        self._tag(refused="true", refusal_reason=reason)

    @_safe
    def trace_complete(
        self,
        total_latency_ms: float,
        extras: Optional[Dict[str, Any]] = None,
    ) -> None:
        """T1#12 / T2#18 / T3#14 / T4#11 — final trace completion meta."""
        self._tag(total_latency_ms=int(total_latency_ms), **(extras or {}))

    @_safe
    def followup(self, kind: str, within_session: bool = True) -> None:
        """T1#14 / T2#20 / T3#16 — user follow-up signal (post-hoc)."""
        self._tag(
            followup_within_session=str(within_session).lower(), followup_kind=kind
        )

    # ── Type 1: Concept (#5~10, #13) ───────────────────────────────────────

    @_safe
    def t1_internal_thinking(
        self,
        concept_target: Optional[str],
        gap_estimation: Optional[str],
    ) -> None:
        """T1#5 — concept target & gap estimation (definition/condition/role/application)."""
        self._emit(
            name=SPAN_T1_INTERNAL_THINKING,
            output={"concept_target": concept_target, "gap_estimation": gap_estimation},
        )

    @_safe
    def t1_step1_definition(
        self,
        step_token_count: Optional[int],
        has_verbal_meaning: bool,
        has_purpose_line: bool,
    ) -> None:
        """T1#6 — definition step (R4 verification)."""
        self._emit(
            name=SPAN_T1_STEP1_DEFINITION,
            output={
                "step_token_count": step_token_count,
                "has_verbal_meaning": has_verbal_meaning,
                "has_purpose_line": has_purpose_line,
            },
        )

    @_safe
    def t1_step2_example(
        self,
        has_example: bool,
        example_domain: Optional[str] = None,
        step_token_count: Optional[int] = None,
    ) -> None:
        """T1#7 — representative example."""
        self._emit(
            name=SPAN_T1_STEP2_EXAMPLE,
            output={
                "has_example": has_example,
                "example_domain": example_domain,
                "step_token_count": step_token_count,
            },
        )

    @_safe
    def t1_step3_boundary(
        self,
        has_boundary: bool,
        boundary_count: int = 0,
        boundary_kind: Optional[str] = None,
    ) -> None:
        """T1#8 — boundary/condition/counterexample (R5 verification)."""
        self._emit(
            name=SPAN_T1_STEP3_BOUNDARY,
            output={
                "has_boundary": has_boundary,
                "boundary_count": boundary_count,
                "boundary_kind": boundary_kind,
            },
        )

    @_safe
    def t1_step4_socratic(
        self,
        has_socratic: bool,
        socratic_qtype: Optional[str] = None,
        has_hint: bool = False,
    ) -> None:
        """T1#9 — Socratic-lite check question (R1 verification)."""
        self._emit(
            name=SPAN_T1_STEP4_SOCRATIC,
            output={
                "has_socratic": has_socratic,
                "socratic_qtype": socratic_qtype,
                "has_hint": has_hint,
            },
        )

    @_safe
    def t1_step5_expansion(
        self,
        expansion_triggered: bool,
        expansion_kind: Optional[str] = None,
    ) -> None:
        """T1#10 — optional proof/derivation/counterexample expansion."""
        self._emit(
            name=SPAN_T1_STEP5_EXPANSION,
            output={
                "expansion_triggered": expansion_triggered,
                "expansion_kind": expansion_kind,
            },
        )

    @_safe
    def t1_judge_score(
        self,
        eval_definition_accuracy: Optional[float] = None,
        eval_boundary_quality: Optional[float] = None,
        eval_meaning_first: Optional[float] = None,
        eval_concept_count: Optional[float] = None,
    ) -> None:
        """T1#13 — LLM-as-Judge scores (recorded as multiple `score_trace` entries)."""
        scores = {
            "eval_definition_accuracy": eval_definition_accuracy,
            "eval_boundary_quality": eval_boundary_quality,
            "eval_meaning_first": eval_meaning_first,
            "eval_concept_count": eval_concept_count,
        }
        trace_id = self.base_meta.get("trace_id")
        if not trace_id or self.tracer is None:
            return
        for name, value in scores.items():
            if value is not None:
                self.tracer.score_trace(trace_id=trace_id, name=name, value=value)

    # ── Type 2: Problem (#4~16, #19~20) ────────────────────────────────────

    @_safe
    def t2_problem_classification(
        self,
        case: str,
        classification_confidence: Optional[str] = None,
    ) -> None:
        """T2#4 — Case 1 (mechanical) vs Case 2 (deep-thinking) self-classification."""
        self._emit(
            name=SPAN_T2_PROBLEM_CLASSIFICATION,
            output={
                "case": case,
                "classification_confidence": classification_confidence,
            },
        )

    @_safe
    def t2_inferred_block(self, block: str) -> None:
        """T2#5 — info_lack/concept/procedure/interpretation."""
        self._tag(inferred_block=block)

    @_safe
    def t2_step1_concept(
        self,
        recalled_concept_count: int,
        recalled_concepts: Optional[List[str]] = None,
    ) -> None:
        """T2#7 — concept/formula recall (both Cases)."""
        self._emit(
            name=SPAN_T2_STEP1_CONCEPT,
            output={
                "recalled_concept_count": recalled_concept_count,
                "recalled_concepts": recalled_concepts or [],
            },
        )

    @_safe
    def t2_step2_subexpression(
        self,
        sub_expression_provided: bool,
        expression_complexity: Optional[str] = None,
    ) -> None:
        """T2#8 — Case 1 immediately-usable sub-expression."""
        self._emit(
            name=SPAN_T2_STEP2_SUBEXPRESSION,
            output={
                "sub_expression_provided": sub_expression_provided,
                "expression_complexity": expression_complexity,
            },
        )

    @_safe
    def t2_step2_midgoal(
        self,
        midgoal_count: int,
        midgoal_concrete: bool,
    ) -> None:
        """T2#9 — Case 2 mid-goal."""
        self._emit(
            name=SPAN_T2_STEP2_MIDGOAL,
            output={
                "midgoal_count": midgoal_count,
                "midgoal_concrete": midgoal_concrete,
            },
        )

    @_safe
    def t2_step3_strategy(
        self,
        strategy_steps_count: int,
        route_rationale_kind: Optional[str] = None,
    ) -> None:
        """T2#10 — Case 2 solving strategy with rationale (R3)."""
        self._emit(
            name=SPAN_T2_STEP3_STRATEGY,
            output={
                "strategy_steps_count": strategy_steps_count,
                "route_rationale_kind": route_rationale_kind,
            },
        )

    @_safe
    def t2_step4_answer(self, sanity_check_kind: Optional[str] = None) -> None:
        """T2#11 — Case 2 final answer + sanity check."""
        self._emit(
            name=SPAN_T2_STEP4_ANSWER,
            output={"sanity_check_kind": sanity_check_kind or "none"},
        )

    @_safe
    def t2_escalation(
        self,
        escalation_count: int,
        escalation_turn: int,
        prev_block_location: Optional[str] = None,
    ) -> None:
        """T2#12 — escalation trigger (R4)."""
        self._emit(
            name=SPAN_T2_ESCALATION,
            output={
                "escalation_count": escalation_count,
                "escalation_turn": escalation_turn,
                "prev_block_location": prev_block_location,
            },
        )

    @_safe
    def t2_escalation_action(self, action: str) -> None:
        """T2#13 — reinforce_step3 vs reveal_step4 tag."""
        self._tag(escalation_action=action)

    @_safe
    def t2_info_insufficient(
        self,
        insufficient: bool,
        assumption_made: bool = False,
        info_requested_count: int = 0,
    ) -> None:
        """T2#14 — info-insufficient handling (R5)."""
        self._tag(
            info_insufficient=str(insufficient).lower(),
            assumption_made=str(assumption_made).lower(),
            info_requested_count=info_requested_count,
        )

    @_safe
    def t2_multi_solution(
        self, multi: bool, conditions_specified: bool = False
    ) -> None:
        """T2#15 — multi-solution branch (R6)."""
        self._tag(
            multi_solution=str(multi).lower(),
            conditions_specified=str(conditions_specified).lower(),
        )

    @_safe
    def t2_attempt_log(
        self,
        attempt_id: str,
        item_id: Optional[str] = None,
        topic_id: Optional[str] = None,
        user_solution_attached: bool = False,
    ) -> None:
        """T2#16 — Attempt Logger invocation span (R8)."""
        self._emit(
            name=SPAN_T2_ATTEMPT_LOG,
            output={
                "attempt_id": attempt_id,
                "item_id": item_id,
                "topic_id": topic_id,
                "user_solution_attached": user_solution_attached,
            },
        )

    @_safe
    def t2_judge_score(
        self,
        eval_subexpr_appropriateness: Optional[float] = None,
        eval_strategy_clarity: Optional[float] = None,
        eval_route_safety: Optional[float] = None,
        eval_assumption_quality: Optional[float] = None,
    ) -> None:
        """T2#19 — LLM-as-Judge scores."""
        scores = {
            "eval_subexpr_appropriateness": eval_subexpr_appropriateness,
            "eval_strategy_clarity": eval_strategy_clarity,
            "eval_route_safety": eval_route_safety,
            "eval_assumption_quality": eval_assumption_quality,
        }
        trace_id = self.base_meta.get("trace_id")
        if not trace_id or self.tracer is None:
            return
        for name, value in scores.items():
            if value is not None:
                self.tracer.score_trace(trace_id=trace_id, name=name, value=value)

    @_safe
    def t2_next_attempt(
        self,
        next_attempt_score: Optional[float],
        next_attempt_within_n_turns: Optional[int],
    ) -> None:
        """T2#20 — follow-up attempt outcome tag."""
        self._tag(
            next_attempt_score=next_attempt_score,
            next_attempt_within_n_turns=next_attempt_within_n_turns,
        )

    # ── Type 3: Review (#4~12, #15~16) ─────────────────────────────────────

    @_safe
    def t3_input_completeness(
        self,
        sufficient: bool,
        missing_fields: Optional[List[str]] = None,
    ) -> None:
        """T3#4 — input completeness check (R1)."""
        self._emit(
            name=SPAN_T3_INPUT_COMPLETENESS,
            output={"sufficient": sufficient, "missing_fields": missing_fields or []},
        )

    @_safe
    def t3_early_exit(self, reason: str = "insufficient_input") -> None:
        """T3#5 — early exit when input insufficient."""
        self._tag(early_exit="true", exit_reason=reason)

    @_safe
    def t3_gap_diagnosis(
        self,
        gap_type: str,
        gap_location_text: Optional[str] = None,
    ) -> None:
        """T3#7 — Conceptual/Procedural/Interpretational gap (R2/R3)."""
        self._emit(
            name=SPAN_T3_GAP_DIAGNOSIS,
            output={"gap_type": gap_type, "gap_location_text": gap_location_text},
        )

    @_safe
    def t3_verdict(
        self,
        verdict: str,
        topic_relevance: bool,
        confidence: Optional[str] = None,
    ) -> None:
        """T3#8 — Full / Partial / Wrong verdict + topic relevance."""
        self._emit(
            name=SPAN_T3_VERDICT,
            output={
                "verdict": verdict,
                "topic_relevance": topic_relevance,
                "confidence": confidence,
            },
        )

    @_safe
    def t3_step1_diagnosis(
        self,
        summary_lines: int,
        pinpoint_provided: bool,
        natural_phrasing: bool,
    ) -> None:
        """T3#9 — solution summary + pinpoint diagnosis (R2/R3)."""
        self._emit(
            name=SPAN_T3_STEP1_DIAGNOSIS,
            output={
                "summary_lines": summary_lines,
                "pinpoint_provided": pinpoint_provided,
                "natural_phrasing": natural_phrasing,
            },
        )

    @_safe
    def t3_step2_alternative(
        self,
        alt_route_provided: bool,
        counterexample_used: bool,
        common_mistakes_count: int = 0,
    ) -> None:
        """T3#10 — alternative route + common mistakes (R4/R5)."""
        self._emit(
            name=SPAN_T3_STEP2_ALTERNATIVE,
            output={
                "alt_route_provided": alt_route_provided,
                "counterexample_used": counterexample_used,
                "common_mistakes_count": common_mistakes_count,
            },
        )

    @_safe
    def t3_nonstandard(
        self, accepted: bool, comparison_with_standard: bool = False
    ) -> None:
        """T3#11 — non-standard acceptance tag (R6)."""
        self._tag(
            nonstandard_accepted=str(accepted).lower(),
            comparison_with_standard=str(comparison_with_standard).lower(),
        )

    @_safe
    def t3_attempt_log(
        self,
        attempt_id: str,
        item_id: Optional[str] = None,
        topic_id: Optional[str] = None,
        base_score: Optional[float] = None,
        time_factor: Optional[float] = None,
        attempt_score: Optional[float] = None,
    ) -> None:
        """T3#12 — Attempt Logger span (R7)."""
        self._emit(
            name=SPAN_T3_ATTEMPT_LOG,
            output={
                "attempt_id": attempt_id,
                "item_id": item_id,
                "topic_id": topic_id,
                "base_score": base_score,
                "time_factor": time_factor,
                "attempt_score": attempt_score,
            },
        )

    @_safe
    def t3_judge_score(
        self,
        eval_diagnosis_accuracy: Optional[float] = None,
        eval_pinpoint_precision: Optional[float] = None,
        eval_alt_quality: Optional[float] = None,
        eval_natural_phrasing: Optional[float] = None,
    ) -> None:
        """T3#15 — LLM-as-Judge scores."""
        scores = {
            "eval_diagnosis_accuracy": eval_diagnosis_accuracy,
            "eval_pinpoint_precision": eval_pinpoint_precision,
            "eval_alt_quality": eval_alt_quality,
            "eval_natural_phrasing": eval_natural_phrasing,
        }
        trace_id = self.base_meta.get("trace_id")
        if not trace_id or self.tracer is None:
            return
        for name, value in scores.items():
            if value is not None:
                self.tracer.score_trace(trace_id=trace_id, name=name, value=value)

    @_safe
    def t3_retry_signal(
        self,
        retry_attempt_score: Optional[float],
        retry_within_n_turns: Optional[int],
        gap_persisted: Optional[bool],
    ) -> None:
        """T3#16 — follow-up retry effectiveness signal."""
        self._tag(
            retry_attempt_score=retry_attempt_score,
            retry_within_n_turns=retry_within_n_turns,
            gap_persisted=(
                str(gap_persisted).lower() if gap_persisted is not None else "n/a"
            ),
        )

    # ── Type 4: Session (loop-scoped) ──────────────────────────────────────

    @_safe
    def t4_session_start(
        self,
        due_topic_count: int,
        remediation_item_count: int,
        session_goal: Optional[str] = None,
    ) -> None:
        """T4#2 — queue load."""
        self._emit(
            name=SPAN_T4_SESSION_START,
            output={
                "due_topic_count": due_topic_count,
                "remediation_item_count": remediation_item_count,
                "session_goal": session_goal,
            },
        )

    def begin_iteration(self, idx: int) -> Optional[Any]:
        """
        Open a `problem_iteration_N` span and route subsequent T4 emits under it.
        Call `end_iteration()` to close.
        """
        if self.tracer is None:
            return None
        try:
            self._iteration_span = self.tracer.start_span(
                self.parent,
                name=f"problem_iteration_{idx}",
                input={"iteration_index": idx},
                metadata=self._meta({"iteration_index": idx}),
            )
            return self._iteration_span
        except Exception as e:
            log.warning(f"[LEARNING_SPAN] begin_iteration({idx}) failed: {e}")
            self._iteration_span = None
            return None

    def end_iteration(self, output: Optional[Dict[str, Any]] = None) -> None:
        if self._iteration_span is None or self.tracer is None:
            return
        try:
            self.tracer.end_span(self._iteration_span, output=output)
        finally:
            self._iteration_span = None

    @_safe
    def t4_problem_selection(
        self,
        problem_case: int,
        item_id: str,
        topic_id: Optional[str] = None,
        prev_topic_id: Optional[str] = None,
        interleaved: bool = True,
    ) -> None:
        """T4#3 — Case selection + interleaving (R1, R2)."""
        self._emit(
            name=SPAN_T4_PROBLEM_SELECTION,
            output={
                "problem_case": problem_case,
                "item_id": item_id,
                "topic_id": topic_id,
                "prev_topic_id": prev_topic_id,
                "interleaved": interleaved,
            },
        )

    @_safe
    def t4_problem_present(
        self,
        item_difficulty: Optional[str] = None,
        hint_level: Optional[str] = None,
    ) -> None:
        """T4#4 — present item (R3 hint reduction)."""
        self._emit(
            name=SPAN_T4_PROBLEM_PRESENT,
            output={"item_difficulty": item_difficulty, "hint_level": hint_level},
        )

    @_safe
    def t4_response_collect(
        self,
        response_token_count: Optional[int],
        response_time_ms: Optional[float] = None,
    ) -> None:
        """T4#5 — student response capture."""
        self._emit(
            name=SPAN_T4_RESPONSE_COLLECT,
            output={
                "response_token_count": response_token_count,
                "response_time_ms": response_time_ms,
            },
        )

    @_safe
    def t4_evaluation_base(
        self,
        base_score: float,
        partial_breakdown: Optional[Dict[str, float]] = None,
    ) -> None:
        """T4#6 — base score + partial breakdown."""
        self._emit(
            name=SPAN_T4_EVALUATION_BASE,
            output={
                "base_score": base_score,
                "partial_breakdown": partial_breakdown or {},
            },
        )

    @_safe
    def t4_evaluation_time(self, time_factor: float) -> None:
        """T4#7 — time factor (1.0/0.9/0.8)."""
        self._emit(
            name=SPAN_T4_EVALUATION_TIME,
            output={"time_factor": time_factor},
        )

    @_safe
    def t4_attempt_score(self, attempt_score: float, verdict: str) -> None:
        """T4#8 — final AttemptScore + verdict tag (R4)."""
        self._tag(attempt_score=attempt_score, verdict=verdict)

    @_safe
    def t4_log_api_call(
        self,
        api_status: str,
        latency_ms: Optional[float] = None,
        retry_count: int = 0,
    ) -> None:
        """T4#9 — Log API call (R5)."""
        self._emit(
            name=SPAN_T4_LOG_API_CALL,
            output={
                "api_status": api_status,
                "latency_ms": latency_ms,
                "retry_count": retry_count,
            },
        )

    @_safe
    def t4_loop_decision(
        self,
        loop_continue: bool,
        exit_reason: Optional[str] = None,
    ) -> None:
        """T4#10 — continue vs exit (R6)."""
        self._tag(
            loop_continue=str(loop_continue).lower(),
            exit_reason=exit_reason or "n/a",
        )

    @_safe
    def t4_session_end(
        self,
        items_completed: int,
        items_skipped: int,
        total_duration_ms: float,
        avg_attempt_score: Optional[float] = None,
        drop_off_step: Optional[str] = None,
    ) -> None:
        """T4#11 — session-level summary."""
        self._tag(
            items_completed=items_completed,
            items_skipped=items_skipped,
            total_duration_ms=int(total_duration_ms),
            avg_attempt_score=avg_attempt_score,
            drop_off_step=drop_off_step or "none",
        )

    @_safe
    def t4_judge_score(
        self,
        eval_problem_appropriateness: Optional[float] = None,
        eval_evaluation_consistency: Optional[float] = None,
        eval_interleaving_quality: Optional[float] = None,
    ) -> None:
        """T4#12 — LLM-as-Judge scores."""
        scores = {
            "eval_problem_appropriateness": eval_problem_appropriateness,
            "eval_evaluation_consistency": eval_evaluation_consistency,
            "eval_interleaving_quality": eval_interleaving_quality,
        }
        trace_id = self.base_meta.get("trace_id")
        if not trace_id or self.tracer is None:
            return
        for name, value in scores.items():
            if value is not None:
                self.tracer.score_trace(trace_id=trace_id, name=name, value=value)

    @_safe
    def t4_user_rating(
        self,
        rating: Optional[float],
        self_perceived_difficulty: Optional[str] = None,
    ) -> None:
        """T4#13 — optional UI-collected satisfaction tag."""
        self._tag(
            user_session_rating=rating,
            self_perceived_difficulty=self_perceived_difficulty or "n/a",
        )


# ──────────────────────────────────────────────────────────────────────────────
# Convenience builder
# ──────────────────────────────────────────────────────────────────────────────


def build_emitter(
    parent: Any,
    chat_type: Optional[str],
    base_meta: Optional[Dict[str, Any]] = None,
) -> LearningSpanEmitter:
    """Construct an emitter using the singleton tracer (None-safe)."""
    try:
        from open_webui.integrations.langfuse_tracing import get_langfuse_tracer

        tracer = get_langfuse_tracer()
    except Exception:
        tracer = None
    return LearningSpanEmitter(
        tracer=tracer,
        parent=parent,
        chat_type=chat_type,
        base_meta=base_meta or {},
    )
