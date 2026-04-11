import json
import logging
import os
from typing import Any

log = logging.getLogger(__name__)


FORK_DEFAULT_SKILLS: list[dict[str, Any]] = [
    {
        "id": "mws-collaboration",
        "name": "MWS Collaboration",
        "description": "Collaboration and delivery guardrails for this Open WebUI fork. "
        "Use when the task requires clean implementation, safe changes, and concise status updates.",
        "content": """# MWS Collaboration

## Goal
Ship reliable changes with clear communication and minimal regressions.

## Rules
1. Prefer simple, maintainable solutions over clever ones.
2. Keep changes scoped to the request and avoid unrelated refactors.
3. Preserve existing product behavior unless the task explicitly changes it.
4. Validate important paths before finalizing.
5. Report blockers early and propose a concrete fallback.

## Delivery Style
- Write short progress updates during longer tasks.
- Summarize what changed, why it changed, and what was verified.
- If something could not be verified, state it explicitly.
""",
        "meta": {"tags": ["default", "collaboration", "quality"]},
        "is_active": True,
    },
    {
        "id": "skill-creator",
        "name": "Skill Creator",
        "description": "Create and connect OpenWebUI skills. Use when a user wants to draft a new skill, improve an existing skill, or attach a skill to a model in this Open WebUI fork.",
        "content": """# Skill Creator

## Goal
Help users design concise OpenWebUI skills that are easy to use, maintain, and connect to models.

## Workflow
1. Clarify the task, trigger, expected input, desired output, and who should own the skill.
2. Draft a skill that stays narrow and specific.
3. Include only the instructions the model needs at runtime.
4. If the user wants the skill added to OpenWebUI, explain the shortest path to create or update it in the Skills workspace.
5. If the user wants the skill attached to a model, point them to the model's skill selector or `skillIds` metadata.

## What to produce
- Skill name
- Short description
- Skill body content
- Suggested tags
- OpenWebUI connection steps

## Guardrails
- Ask focused follow-up questions when requirements are unclear.
- Prefer simple, testable instructions over long prose.
- Preserve existing behavior when updating a skill unless the user asks for a change.
- Call out any missing details that block a good draft.

## Delivery
When useful, return the result in this order:
1. Draft skill
2. Connection steps for OpenWebUI
3. Any questions or risks
""",
        "meta": {"tags": ["default", "skills", "openwebui", "creator"]},
        "is_active": True,
    }
]


def load_default_skills() -> list[dict[str, Any]]:
    """
    Return default skills for startup seeding.

    Environment override:
    - DEFAULT_SKILLS: JSON array (or single object) with skill definitions.
    """
    raw = os.environ.get("DEFAULT_SKILLS", "").strip()
    if not raw:
        return FORK_DEFAULT_SKILLS

    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            parsed = [parsed]
        if isinstance(parsed, list):
            return parsed
        log.warning("DEFAULT_SKILLS must be a JSON object or array; using bundled defaults")
        return FORK_DEFAULT_SKILLS
    except Exception as e:
        log.warning(f"Failed to parse DEFAULT_SKILLS; using bundled defaults: {e}")
        return FORK_DEFAULT_SKILLS
