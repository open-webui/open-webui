"""
Prompt Composition Utility

This module handles composing prompts from prompt groups based on persona values.

Composition Order:
1. base (order=0) - Always included
2. proficiency (order=10) - Based on proficiency_level (1, 2, 3)
3. style (order=20) - Based on response_style
4. tool (order=30) - Selectively included via tool gating

Response Style Values:
- "학생 진단 브리핑" (Student Diagnostic Briefing)
- "학습 향상 피드백" (Learning Improvement Feedback)
- "자기주도 학습 유도" (Self-Directed Learning Guidance)

Proficiency Level Values:
- "1" (Beginner)
- "2" (Intermediate)
- "3" (Advanced)

Tool prompts are NOT automatically included in composition.
They are returned separately for tool gating (two-stage LLM approach).
"""

import logging
from typing import Optional, Tuple, List
from open_webui.models.prompt_groups import PromptGroupMappings
from open_webui.models.prompts import Prompts, PromptModel

from open_webui.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS.get("MAIN", logging.INFO))

# Valid persona values
VALID_PROFICIENCY_LEVELS = ["1", "2", "3"]
VALID_RESPONSE_STYLES = [
    "학생 진단 브리핑",  # Student Diagnostic Briefing
    "학습 향상 피드백",  # Learning Improvement Feedback
    "자기주도 학습 유도",  # Self-Directed Learning Guidance
]


def compose_prompts_from_group(
    group_id: str,
    proficiency_level: Optional[str] = None,
    response_style: Optional[str] = None,
    include_tools: bool = False,
) -> Tuple[str, List[PromptModel]]:
    """
    Compose prompts from a group based on persona values.

    Tool prompts (prompt_type='tool') are NOT included in the composed string.
    They are returned separately for tool gating (two-stage LLM approach).

    Args:
        group_id: The prompt group ID
        proficiency_level: User's proficiency level (e.g., "1", "2", "3")
        response_style: Desired response style (one of VALID_RESPONSE_STYLES)
        include_tools: If True, include tool prompts in composed string (legacy mode)

    Returns:
        Tuple of (composed_prompt, tool_prompts)
        - composed_prompt: Base + proficiency + style prompts joined by double newlines
        - tool_prompts: List of tool PromptModel objects (for tool gating)

    Example:
        >>> composed, tools = compose_prompts_from_group("group-123", "1", "학생 진단 브리핑")
        >>> print(composed)
        "You are a helpful math tutor...\\n\\nUse simple language...\\n\\nProvide diagnostic briefing..."
        >>> print([t.command for t in tools])
        ["tool-step-solver", "tool-concept-explain"]
    """
    log.info("=" * 60)
    log.info(f"[PROMPT COMPOSER] Starting composition for group: {group_id}")
    log.info(f"  proficiency_level: {proficiency_level}")
    log.info(f"  response_style: {response_style}")
    log.info(f"  include_tools (legacy mode): {include_tools}")
    log.info("=" * 60)

    # Get all mappings for the group, ordered by order field
    mappings = PromptGroupMappings.get_mappings_by_group_id(group_id)

    if not mappings:
        log.warning(f"[PROMPT COMPOSER] No mappings found for group: {group_id}")
        return ("", [])

    log.info(f"[PROMPT COMPOSER] Found {len(mappings)} mappings")

    prompt_parts = []
    tool_prompts = []
    included_prompts = []  # For logging

    # Process each mapping in order
    for mapping in mappings:
        prompt = Prompts.get_prompt_by_command(mapping.prompt_command)
        if not prompt:
            log.warning(f"[PROMPT COMPOSER] Prompt not found: {mapping.prompt_command}")
            continue

        log.debug(f"[PROMPT COMPOSER] Processing: {mapping.prompt_command} (type={prompt.prompt_type}, order={mapping.order})")

        # Handle tool prompts separately
        if prompt.prompt_type == "tool":
            log.info(f"[PROMPT COMPOSER] Found TOOL prompt: {prompt.command}")
            log.info(f"  - title: {prompt.title}")
            log.info(f"  - tool_description: {prompt.tool_description}")
            log.info(f"  - tool_priority: {prompt.tool_priority}")
            log.info(f"  - content length: {len(prompt.content) if prompt.content else 0} chars")
            tool_prompts.append(prompt)
            if include_tools:
                # Legacy mode: include tools in composed string
                prompt_parts.append(prompt.content)
                log.info(f"  - INCLUDED in composed string (legacy mode)")
            else:
                log.info(f"  - NOT included in composed string (tool gating mode)")
            continue

        # Determine if this prompt should be included
        should_include = False
        reason = ""

        if prompt.prompt_type == "base":
            # Always include base prompts
            should_include = True
            reason = "base type (always included)"

        elif prompt.prompt_type == "proficiency":
            # Include if proficiency_level matches
            if proficiency_level is not None and proficiency_level == prompt.persona_value:
                should_include = True
                reason = f"proficiency matches ({proficiency_level} == {prompt.persona_value})"
            else:
                reason = f"proficiency mismatch ({proficiency_level} != {prompt.persona_value})"

        elif prompt.prompt_type == "style":
            # Include if response_style matches
            if response_style is not None and response_style == prompt.persona_value:
                should_include = True
                reason = f"style matches ({response_style} == {prompt.persona_value})"
            else:
                reason = f"style mismatch ({response_style} != {prompt.persona_value})"

        if should_include:
            prompt_parts.append(prompt.content)
            included_prompts.append(prompt.command)
            log.info(f"[PROMPT COMPOSER] INCLUDED: {prompt.command} ({prompt.prompt_type}) - {reason}")
        else:
            log.debug(f"[PROMPT COMPOSER] SKIPPED: {prompt.command} ({prompt.prompt_type}) - {reason}")

    # Sort tool prompts by priority (higher first)
    tool_prompts.sort(key=lambda t: t.tool_priority or 0, reverse=True)

    # Summary logging
    log.info("=" * 60)
    log.info("[PROMPT COMPOSER] Composition Summary:")
    log.info(f"  Included prompts ({len(included_prompts)}): {included_prompts}")
    log.info(f"  Tool prompts ({len(tool_prompts)}): {[t.command for t in tool_prompts]}")
    if tool_prompts:
        log.info("  Tool details:")
        for t in tool_prompts:
            log.info(f"    - {t.command}: priority={t.tool_priority}, desc='{t.tool_description or 'N/A'}'")
    log.info(f"  Total composed length: {len(''.join(prompt_parts))} chars")
    log.info("=" * 60)

    # Join prompts with double newlines
    return ("\n\n".join(prompt_parts), tool_prompts)


def compose_prompts_from_group_legacy(
    group_id: str,
    proficiency_level: Optional[str] = None,
    response_style: Optional[str] = None,
) -> str:
    """
    Legacy function that returns only the composed string.
    Tool prompts are included in the composed string.

    For new code, use compose_prompts_from_group() instead.
    """
    composed, _ = compose_prompts_from_group(
        group_id, proficiency_level, response_style, include_tools=True
    )
    return composed


def validate_persona_values(
    proficiency_level: Optional[str] = None,
    response_style: Optional[str] = None,
) -> tuple[bool, Optional[str]]:
    """
    Validate persona values.

    Args:
        proficiency_level: User's proficiency level (string)
        response_style: Desired response style (string)

    Returns:
        Tuple of (is_valid, error_message)
    """
    if proficiency_level is not None:
        if proficiency_level not in VALID_PROFICIENCY_LEVELS:
            return False, f"Invalid proficiency_level. Must be one of: {VALID_PROFICIENCY_LEVELS}"

    if response_style is not None:
        if response_style not in VALID_RESPONSE_STYLES:
            return False, f"Invalid response_style. Must be one of: {VALID_RESPONSE_STYLES}"

    return True, None


def get_default_prompt_for_persona(
    proficiency_level: Optional[str] = None,
    response_style: Optional[str] = None,
) -> Optional[str]:
    """
    Get a default prompt based on persona values without using groups.
    This is a fallback when no group is specified.

    Args:
        proficiency_level: User's proficiency level (string)
        response_style: Desired response style (string)

    Returns:
        Default prompt string or None
    """
    # This can be implemented later if needed
    # For now, return None to indicate no default
    return None


def compose_with_fallback(
    group_id: Optional[str] = None,
    system_prompt: Optional[str] = None,
    default_group_id: Optional[str] = None,
    proficiency_level: Optional[str] = None,
    response_style: Optional[str] = None,
    include_tools: bool = False,
) -> Tuple[Optional[str], List[PromptModel]]:
    """
    Compose prompt with fallback logic.

    Priority:
    1. If group_id is specified, use group composition
    2. If system_prompt is specified, use it directly
    3. If default_group_id is specified, use default group composition
    4. Return None (no prompt)

    Args:
        group_id: Specific group ID to use
        system_prompt: Direct system prompt
        default_group_id: Default group ID to use as fallback
        proficiency_level: User's proficiency level (string)
        response_style: Desired response style (string)
        include_tools: If True, include tool prompts in composed string (legacy mode)

    Returns:
        Tuple of (composed_prompt, tool_prompts)
        - composed_prompt: Composed prompt string or None
        - tool_prompts: List of tool PromptModel objects (for tool gating)
    """
    tool_prompts = []

    # Priority 1: Use specified group
    if group_id:
        composed, tool_prompts = compose_prompts_from_group(
            group_id, proficiency_level, response_style, include_tools
        )

        # If system_prompt also exists, append it
        if system_prompt and composed:
            return (f"{composed}\n\n{system_prompt}", tool_prompts)
        elif composed:
            return (composed, tool_prompts)

    # Priority 2: Use system prompt directly
    if system_prompt:
        return (system_prompt, [])

    # Priority 3: Use default group
    if default_group_id:
        return compose_prompts_from_group(
            default_group_id, proficiency_level, response_style, include_tools
        )

    # Priority 4: No prompt
    return (None, [])


def compose_with_fallback_legacy(
    group_id: Optional[str] = None,
    system_prompt: Optional[str] = None,
    default_group_id: Optional[str] = None,
    proficiency_level: Optional[str] = None,
    response_style: Optional[str] = None,
) -> Optional[str]:
    """
    Legacy function that returns only the composed string.
    Tool prompts are included in the composed string.

    For new code, use compose_with_fallback() instead.
    """
    composed, _ = compose_with_fallback(
        group_id, system_prompt, default_group_id,
        proficiency_level, response_style, include_tools=True
    )
    return composed
