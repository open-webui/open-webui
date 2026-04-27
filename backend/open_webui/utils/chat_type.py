"""
Chat type routing heuristic.

Classifies a chat completion request into one of:
- "concept"  (Type 1): conceptual explanations
- "problem"  (Type 2): problem-solving with hints/attempts
- "review"   (Type 3): solution review/feedback
- "session"  (Type 4): structured review session / quiz

Heuristic only — definitive routing should later use explicit metadata
from the frontend (e.g., a `chat_type` field on the request).
"""

from typing import Optional

# Tool name fragments → chat_type
_TOOL_HINTS = {
    "concept": ["concept", "explain", "definition"],
    "problem": ["hint", "attempt", "solve_step"],
    "review": ["review", "check_solution", "feedback"],
    "session": ["quiz", "session_summary", "session_pick"],
}


def infer_chat_type(payload: dict, metadata: dict) -> Optional[str]:
    """
    Best-effort classification. Returns None if undecidable.
    """
    # 1) explicit override from frontend
    explicit = metadata.get("chat_type") or payload.get("chat_type")
    if explicit in {"concept", "problem", "review", "session"}:
        return explicit

    # 2) tool name hints
    tool_names = metadata.get("tool_commands") or set()
    if not isinstance(tool_names, (set, list, tuple)):
        tool_names = []
    tool_names = [str(t).lower() for t in tool_names]

    for ctype, fragments in _TOOL_HINTS.items():
        for frag in fragments:
            if any(frag in t for t in tool_names):
                return ctype

    # 3) fall back: prompt_group_id name hints
    pg = (metadata.get("prompt_group_id") or "").lower()
    for ctype, fragments in _TOOL_HINTS.items():
        if any(frag in pg for frag in fragments):
            return ctype

    return None
