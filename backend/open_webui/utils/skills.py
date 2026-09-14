"""Helpers for chat skill mentions and skill-authoring slash commands."""

import re

from open_webui.utils.misc import get_content_from_message, set_last_user_message_content


# Match DB skill IDs and terminal skill IDs created by the $ picker.
SKILL_ID_RE = r'(?:[a-z0-9_-]+|terminal:[^|>\s]+)'
SKILL_MENTION_RE = re.compile(rf'<(?:\$({SKILL_ID_RE})(?:\|[^>]*)?|/({SKILL_ID_RE})\|[^>]*)>')


def _get_text_parts(message: dict) -> list[str]:
    """Return all text segments from a message's content."""
    content = message.get('content')
    if isinstance(content, str):
        return [content]
    if isinstance(content, list):
        return [p.get('text', '') for p in content if isinstance(p, dict) and p.get('type') == 'text']
    return []


def extract_skill_ids_from_messages(messages: list[dict]) -> set[str]:
    """Extract skill IDs from <$skillId|label> and </skillId|label> mention tags."""
    ids: set[str] = set()
    for message in messages:
        for text in _get_text_parts(message):
            ids.update(m.group(1) or m.group(2) for m in SKILL_MENTION_RE.finditer(text))
    return ids


SKILL_MENTION_STRIP_RE = re.compile(rf'<(?:\$({SKILL_ID_RE})(?:\|([^>]*))?|/({SKILL_ID_RE})\|([^>]*))>')


SKILLS_CREATE_RE = re.compile(r"^/skills:create(?:\s+(.*))?$", re.IGNORECASE | re.DOTALL)

OPEN_WEBUI_SKILL_AUTHORING_STANDARDS = """\
Follow the Open WebUI skill-authoring standards:

Frontmatter:
- name: lowercase-hyphenated, <=64 chars, no spaces.
- description: one sentence, <=60 characters, ends with a period. State the
  capability, not the implementation. Do not repeat the skill name. Avoid
  marketing words like powerful, comprehensive, seamless, advanced, or robust.
  Count the characters before saving.
- version: 0.1.0.
- platforms: declare [macos], [linux], or [windows] only when the skill uses
  OS-bound primitives. Omit it for portable skills.

Body section order:
1. "# <Human Title>" plus a short intro covering what it does, what it does not
   do, and important dependency assumptions.
2. "## When to Use" with concrete trigger phrases.
3. "## Prerequisites" with exact env vars, credentials, install steps, or "None".
4. "## How to Run" with the canonical workflow framed through the available tools.
5. "## Quick Reference" with flat commands, routes, files, or APIs.
6. "## Procedure" with numbered, copy-paste-exact steps.
7. "## Pitfalls" with known limits and failure modes.
8. "## Verification" with one focused check that proves the skill works.

Tool framing:
- Reference available tools by name in backticks, including `run_command`,
  `write_file`, and `view_skill` when relevant.
- Frame shell work as "run through `run_command`".
- Prefer available read/search tools in prose over raw shell utilities when a
  tool exists.
- Third-party CLIs are fine inside procedures or scripts, but explain that the
  agent invokes them through `run_command`.

Quality bar:
- Prefer exact commands, routes, file paths, function names, config keys, and
  error text found verbatim in the sources. Do not invent flags, paths, APIs,
  or behavior.
- Keep SKILL.md tight and scannable: about 100 lines for a simple workflow,
  about 200 for a complex one.
- Do not create a router/index/hub skill that only points at other skills.
- Put larger reusable scripts in `scripts/`, detailed docs in `references/`,
  reusable outputs in `templates/`, and binary or visual assets in `assets/`."""


def _build_skill_create_prompt(user_request: str) -> str:
    req = (user_request or '').strip()
    if not req:
        req = (
            'the workflow we just went through in this conversation - review the '
            'steps taken and distill them into a reusable skill'
        )
    return (
        '[/skills:create] The user wants you to create a reusable Open WebUI skill '
        'for the selected Open Terminal and save it.\n\n'
        f'THE REQUEST:\n{req}\n\n'
        'The request is open-ended and may mix SOURCES to gather (directories, '
        'file paths, URLs, what we just did, pasted notes) and REQUIREMENTS that '
        'shape the skill (focus, exclusions, scope, naming, style, constraints). '
        'Treat every part of the request as load-bearing. Prose after a path or '
        'URL is not incidental; it is authoring guidance. Never fetch the first '
        'source and ignore the rest.\n\n'
        'Do this:\n'
        '1. Gather every source the user named with the tools you already have: '
        'available file/search/web tools, the current conversation if they refer '
        'to what just happened, pasted text as-is, and `run_command` for shell '
        'work. If scope is ambiguous, make a reasonable choice and note it; do '
        'not stall.\n'
        '2. Apply every requirement, focus, and constraint in the request to what '
        'the skill covers and emphasizes.\n'
        '3. Author one SKILL.md using the standards below.\n'
        '4. Save with the selected terminal tools. Run `pwd` through '
        '`run_command`, then write SKILL.md at '
        '<terminal-cwd>/.agents/skills/<skill-name>/SKILL.md. If the skill '
        'needs supporting files, add them under scripts/, references/, '
        'templates/, or assets/.\n\n'
        f'{OPEN_WEBUI_SKILL_AUTHORING_STANDARDS}\n\n'
        'When done, tell the user the skill name, location, and one-line summary.'
    )


def _message_has_real_content(message: dict) -> bool:
    text = (get_content_from_message(message) or '').strip()
    return bool(text or message.get('tool_calls') or message.get('output'))


def has_prior_real_chat_content(messages: list[dict]) -> bool:
    last_user_idx = next(
        (idx for idx in range(len(messages) - 1, -1, -1) if messages[idx].get('role') == 'user'),
        len(messages),
    )
    return any(
        message.get('role') == 'user' and _message_has_real_content(message)
        for message in messages[:last_user_idx]
    )


def _build_skill_create_gate_prompt(reason: str = 'empty_chat') -> str:
    if reason == 'disabled':
        return (
            '[/skills:create] Skill creation requires a selected Open Terminal. '
            'Explain this briefly and do not try to create or update a skill.'
        )
    return (
        '[/skills:create] The user tried to create a skill before this chat had '
        'any prior real content. Explain briefly that skill creation needs an '
        'existing chat with the workflow or source material already in it, then '
        'ask them to continue in a chat with content first.'
    )


def apply_skills_create_prompt(
    messages: list[dict],
    *,
    allowed: bool,
    denial_reason: str = 'empty_chat',
) -> bool:
    for message in reversed(messages):
        if message.get('role') != 'user':
            continue
        text = get_content_from_message(message) or ''
        match = SKILLS_CREATE_RE.match(text.strip())
        if not match:
            return False
        set_last_user_message_content(
            _build_skill_create_prompt(match.group(1) or '')
            if allowed
            else _build_skill_create_gate_prompt(denial_reason),
            messages,
        )
        return True
    return False


def strip_skill_mentions(messages: list[dict], skill_ids: set[str]) -> None:
    """Replace mentions of resolved skills with their label, preserving all other text."""

    def label(match):
        if (match.group(1) or match.group(3)) not in skill_ids:
            return match.group(0)
        return match.group(2) or match.group(4) or ''

    for message in messages:
        content = message.get('content')
        if isinstance(content, str) and SKILL_MENTION_STRIP_RE.search(content):
            message['content'] = SKILL_MENTION_STRIP_RE.sub(label, content)
        elif isinstance(content, list):
            for part in content:
                if isinstance(part, dict) and part.get('type') == 'text':
                    text = part.get('text', '')
                    if SKILL_MENTION_STRIP_RE.search(text):
                        part['text'] = SKILL_MENTION_STRIP_RE.sub(label, text)
