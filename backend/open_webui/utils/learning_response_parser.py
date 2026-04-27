"""
Learning response parser.

Heuristic extraction of soft signals from LLM-generated responses, so
LearningSpanEmitter can fire post-hoc without changing the prompt template.

Detection is regex-based and intentionally conservative — it never fails,
only returns `None`/`False` on uncertainty.

Used by openai.py after stream completion (or sync response) to populate:
- Type 1 step boundaries (definition / example / boundary / socratic / expansion)
- Type 2 step boundaries (concept / sub-expression / mid-goal / strategy / answer)
- Type 3 step boundaries (diagnosis / alternative)
- Common signals (verbal meaning, sanity check, multi-solution, etc.)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional


# ──────────────────────────────────────────────────────────────────────────────
# Compiled patterns
# ──────────────────────────────────────────────────────────────────────────────

# Verbal meaning: "..., 즉 ...", "여기서 X는 ~을 의미", "X는 ~을 뜻", inline 한글 해설
_RE_VERBAL_MEANING = re.compile(
    r"(즉|여기서|뜻|의미)[\s,].{0,80}",
    re.UNICODE,
)

# Purpose line: "이 ~를 위해", "왜 ~ 필요한가", "이 개념이 다루는 문제"
_RE_PURPOSE_LINE = re.compile(
    r"(이 (개념|정리|이론)이?\s?(다루는|해결하는|등장하는|존재하는)|왜.{0,30}(필요|중요)|를 위해서?)",
    re.UNICODE,
)

# Boundary / 조건·반례·예외
_RE_BOUNDARY_KIND = {
    "condition": re.compile(r"(조건|성립.{0,4}(때|경우)|단,|단 |if\s)", re.UNICODE),
    "constraint": re.compile(
        r"(제약|범위|한계|적용 ?(불가|되지 ?않)|domain)", re.UNICODE
    ),
    "counterexample": re.compile(
        r"(반례|counter ?example|예외|이 경우는 성립하지 않)", re.UNICODE
    ),
}

# Socratic-lite check question: "어떻게 …?", "왜 …?", "한번 풀어보세요", "?$"
_RE_SOCRATIC = re.compile(
    r"(어떻게|왜|한번 (해|풀)|확인해보세요|시도해보세요)[^.]*\?", re.UNICODE
)
_RE_SOCRATIC_QTYPE = {
    "why": re.compile(r"왜", re.UNICODE),
    "how": re.compile(r"어떻게", re.UNICODE),
    "apply": re.compile(r"(적용|풀어|계산해)", re.UNICODE),
}
_RE_HINT = re.compile(r"(힌트|단서|먼저 ~?을?\s?생각|시작은)", re.UNICODE)

# Type 2 — sub-expression (Case 1) / mid-goal (Case 2) / strategy / sanity check
_RE_SUBEXPR = re.compile(
    r"(u\s?=|dv\s?=|치환:|놓으면|부분적분|let\s)", re.UNICODE | re.IGNORECASE
)
_RE_MIDGOAL = re.compile(r"(중간 ?목표|먼저 .{0,20} 구하|첫 ?단계)", re.UNICODE)
_RE_STRATEGY_RATIONALE = {
    "complexity": re.compile(r"(계산량|간단|복잡|효율)", re.UNICODE),
    "error": re.compile(r"(오류|실수|혼동|쉽게 틀)", re.UNICODE),
    "condition": re.compile(r"(조건이? 적용|condition)", re.UNICODE),
    "intuition": re.compile(r"(직관|의미가? 명확|해석)", re.UNICODE),
}
_RE_SANITY = {
    "limiting": re.compile(r"(극한|limit.{0,15} 검증|x\s?(→|->))", re.UNICODE),
    "special": re.compile(r"(특수.{0,4}(값|경우)|special case|x\s?=\s?0)", re.UNICODE),
    "units": re.compile(r"(단위|차원|dimension|units)", re.UNICODE),
}

# Type 3 — pinpoint, alt route, counterexample, common mistakes
_RE_PINPOINT = re.compile(
    r"(\d+\s?번째 ?줄|이 단계에서|여기 ?(에서)?|여기서부터|이 부분에서)",
    re.UNICODE,
)
_RE_ALT_ROUTE = re.compile(r"(다른 (방법|접근|풀이)|alternative|대안)", re.UNICODE)
_RE_COUNTEREX = re.compile(r"(반례|이 경우는 성립하지|우연히 맞)", re.UNICODE)
_RE_COMMON_MISTAKES = re.compile(
    r"(흔한 ?실수|자주 ?(하는|보이는) ?실수|함정)", re.UNICODE
)
_RE_NATURAL_PHRASING_BAD = re.compile(
    r"(Conceptual gap입니다|Procedural gap입니다|Interpretational gap입니다)",
    re.UNICODE,
)

# Multi-solution
_RE_MULTI_SOLUTION = re.compile(r"(±|\+/-|일반해|특수해|두 ?가지 ?해|both)", re.UNICODE)


# ──────────────────────────────────────────────────────────────────────────────
# Result containers
# ──────────────────────────────────────────────────────────────────────────────


@dataclass
class T1Signals:
    has_verbal_meaning: bool = False
    has_purpose_line: bool = False
    has_example: bool = False
    has_boundary: bool = False
    boundary_count: int = 0
    boundary_kind: Optional[str] = None
    has_socratic: bool = False
    socratic_qtype: Optional[str] = None
    has_hint: bool = False


@dataclass
class T2Signals:
    sub_expression_provided: bool = False
    midgoal_count: int = 0
    midgoal_concrete: bool = False
    strategy_steps_count: int = 0
    route_rationale_kind: Optional[str] = None
    sanity_check_kind: Optional[str] = None
    multi_solution: bool = False


@dataclass
class T3Signals:
    summary_lines: int = 0
    pinpoint_provided: bool = False
    natural_phrasing: bool = True
    alt_route_provided: bool = False
    counterexample_used: bool = False
    common_mistakes_count: int = 0


@dataclass
class CommonSignals:
    response_token_count: int = 0
    contains_latex: bool = False
    headers: List[str] = field(default_factory=list)


# ──────────────────────────────────────────────────────────────────────────────
# Parsers
# ──────────────────────────────────────────────────────────────────────────────


def _count_matches(pattern: re.Pattern, text: str) -> int:
    return len(pattern.findall(text or ""))


def parse_common(text: str) -> CommonSignals:
    text = text or ""
    return CommonSignals(
        response_token_count=len(text.split()),
        contains_latex=bool(re.search(r"\\(frac|sum|int|partial|alpha|beta)", text)),
        headers=re.findall(r"^#{1,6}\s.+$", text, flags=re.MULTILINE),
    )


def parse_t1(text: str) -> T1Signals:
    text = text or ""
    sig = T1Signals()
    sig.has_verbal_meaning = bool(_RE_VERBAL_MEANING.search(text))
    sig.has_purpose_line = bool(_RE_PURPOSE_LINE.search(text))
    sig.has_example = bool(
        re.search(r"(예시|예를 들어|예:|for example)", text, re.UNICODE | re.IGNORECASE)
    )

    boundary_hits: List[str] = []
    for kind, pat in _RE_BOUNDARY_KIND.items():
        n = _count_matches(pat, text)
        if n > 0:
            boundary_hits.append(kind)
            sig.boundary_count += n
    sig.has_boundary = bool(boundary_hits)
    if boundary_hits:
        sig.boundary_kind = boundary_hits[0]

    if _RE_SOCRATIC.search(text):
        sig.has_socratic = True
        for qtype, pat in _RE_SOCRATIC_QTYPE.items():
            if pat.search(text):
                sig.socratic_qtype = qtype
                break
    sig.has_hint = bool(_RE_HINT.search(text))
    return sig


def parse_t2(text: str) -> T2Signals:
    text = text or ""
    sig = T2Signals()
    sig.sub_expression_provided = bool(_RE_SUBEXPR.search(text))

    midgoal_matches = _RE_MIDGOAL.findall(text)
    sig.midgoal_count = len(midgoal_matches)
    sig.midgoal_concrete = sig.midgoal_count > 0 and bool(re.search(r"=", text))

    sig.strategy_steps_count = len(re.findall(r"(?:^|\n)\s*\d+[\.\)]\s", text))
    for kind, pat in _RE_STRATEGY_RATIONALE.items():
        if pat.search(text):
            sig.route_rationale_kind = kind
            break

    for kind, pat in _RE_SANITY.items():
        if pat.search(text):
            sig.sanity_check_kind = kind
            break

    sig.multi_solution = bool(_RE_MULTI_SOLUTION.search(text))
    return sig


def parse_t3(text: str) -> T3Signals:
    text = text or ""
    sig = T3Signals()

    lines = [ln for ln in (text.splitlines()) if ln.strip()]
    sig.summary_lines = min(len(lines), 6)
    sig.pinpoint_provided = bool(_RE_PINPOINT.search(text))
    sig.natural_phrasing = not bool(_RE_NATURAL_PHRASING_BAD.search(text))
    sig.alt_route_provided = bool(_RE_ALT_ROUTE.search(text))
    sig.counterexample_used = bool(_RE_COUNTEREX.search(text))
    sig.common_mistakes_count = _count_matches(_RE_COMMON_MISTAKES, text)
    return sig


# ──────────────────────────────────────────────────────────────────────────────
# Convenience: emit signals via LearningSpanEmitter
# ──────────────────────────────────────────────────────────────────────────────


def emit_post_response_spans(
    emitter, response_text: str, chat_type: Optional[str]
) -> None:
    """
    Run all parsers relevant to chat_type and fire the matching spans.
    No-op if emitter is None or chat_type is unknown.
    """
    if emitter is None or not response_text:
        return
    try:
        if chat_type == "concept":
            sig = parse_t1(response_text)
            emitter.t1_step1_definition(
                step_token_count=len(response_text.split()),
                has_verbal_meaning=sig.has_verbal_meaning,
                has_purpose_line=sig.has_purpose_line,
            )
            emitter.t1_step2_example(has_example=sig.has_example)
            emitter.t1_step3_boundary(
                has_boundary=sig.has_boundary,
                boundary_count=sig.boundary_count,
                boundary_kind=sig.boundary_kind,
            )
            emitter.t1_step4_socratic(
                has_socratic=sig.has_socratic,
                socratic_qtype=sig.socratic_qtype,
                has_hint=sig.has_hint,
            )
        elif chat_type == "problem":
            sig = parse_t2(response_text)
            if sig.sub_expression_provided:
                emitter.t2_step2_subexpression(
                    sub_expression_provided=True,
                    expression_complexity=None,
                )
            if sig.midgoal_count > 0:
                emitter.t2_step2_midgoal(
                    midgoal_count=sig.midgoal_count,
                    midgoal_concrete=sig.midgoal_concrete,
                )
            if sig.strategy_steps_count > 0:
                emitter.t2_step3_strategy(
                    strategy_steps_count=sig.strategy_steps_count,
                    route_rationale_kind=sig.route_rationale_kind,
                )
            if sig.sanity_check_kind is not None:
                emitter.t2_step4_answer(sanity_check_kind=sig.sanity_check_kind)
            emitter.t2_multi_solution(multi=sig.multi_solution)
        elif chat_type == "review":
            sig = parse_t3(response_text)
            emitter.t3_step1_diagnosis(
                summary_lines=sig.summary_lines,
                pinpoint_provided=sig.pinpoint_provided,
                natural_phrasing=sig.natural_phrasing,
            )
            emitter.t3_step2_alternative(
                alt_route_provided=sig.alt_route_provided,
                counterexample_used=sig.counterexample_used,
                common_mistakes_count=sig.common_mistakes_count,
            )
    except Exception:
        # Instrumentation must never break the request path.
        pass
