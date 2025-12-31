"""
Prompt Composition Utility

This module handles composing prompts from prompt groups based on persona values.

Composition Order:
1. base (order=0) - Always included
2. proficiency (order=10) - Based on proficiency_level (1, 2, 3)
3. style (order=20) - Based on response_style

Response Style Values:
- "학생 진단 브리핑" (Student Diagnostic Briefing)
- "학습 향상 피드백" (Learning Improvement Feedback)
- "자기주도 학습 유도" (Self-Directed Learning Guidance)

Proficiency Level Values:
- "1" (Beginner)
- "2" (Intermediate)
- "3" (Advanced)
"""

from typing import Optional
from open_webui.models.prompt_groups import PromptGroupMappings
from open_webui.models.prompts import Prompts

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
) -> str:
    """
    Compose prompts from a group based on persona values.

    Args:
        group_id: The prompt group ID
        proficiency_level: User's proficiency level (e.g., "beginner", "intermediate", "advanced")
        response_style: Desired response style (one of VALID_RESPONSE_STYLES)

    Returns:
        Composed prompt string (prompts joined by double newlines)

    Example:
        >>> compose_prompts_from_group("group-123", "beginner", "학생 진단 브리핑")
        "You are a helpful math tutor...\\n\\nUse simple language...\\n\\nProvide diagnostic briefing..."
    """
    # Get all mappings for the group, ordered by order field
    mappings = PromptGroupMappings.get_mappings_by_group_id(group_id)

    if not mappings:
        return ""

    prompt_parts = []

    # Process each mapping in order
    for mapping in mappings:
        prompt = Prompts.get_prompt_by_command(mapping.prompt_command)
        if not prompt:
            continue

        # Determine if this prompt should be included
        should_include = False

        if prompt.prompt_type == "base":
            # Always include base prompts
            should_include = True

        elif prompt.prompt_type == "proficiency":
            # Include if proficiency_level matches
            if proficiency_level is not None and proficiency_level == prompt.persona_value:
                should_include = True

        elif prompt.prompt_type == "style":
            # Include if response_style matches
            if response_style is not None and response_style == prompt.persona_value:
                should_include = True

        if should_include:
            prompt_parts.append(prompt.content)

    # Join prompts with double newlines
    return "\n\n".join(prompt_parts)


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
) -> Optional[str]:
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

    Returns:
        Composed prompt string or None
    """
    # Priority 1: Use specified group
    if group_id:
        composed = compose_prompts_from_group(group_id, proficiency_level, response_style)

        # If system_prompt also exists, append it
        if system_prompt and composed:
            return f"{composed}\n\n{system_prompt}"
        elif composed:
            return composed

    # Priority 2: Use system prompt directly
    if system_prompt:
        return system_prompt

    # Priority 3: Use default group
    if default_group_id:
        return compose_prompts_from_group(
            default_group_id, proficiency_level, response_style
        )

    # Priority 4: No prompt
    return None
