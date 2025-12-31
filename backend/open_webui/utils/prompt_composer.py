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

import logging
from typing import Optional
from open_webui.models.prompt_groups import PromptGroupMappings
from open_webui.models.prompts import Prompts

log = logging.getLogger(__name__)

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
    log.info("="*80)
    log.info("[PROMPT COMPOSER] 프롬프트 조합 시작")
    log.info(f"  그룹 ID: {group_id}")
    log.info(f"  난이도: {proficiency_level}")
    log.info(f"  스타일: {response_style}")
    log.info("="*80)

    # Get all mappings for the group, ordered by order field
    mappings = PromptGroupMappings.get_mappings_by_group_id(group_id)

    if not mappings:
        log.warning("[PROMPT COMPOSER] ⚠️  그룹에 매핑된 프롬프트가 없습니다!")
        return ""

    log.info(f"[PROMPT COMPOSER] 그룹에서 {len(mappings)}개 매핑 발견")

    prompt_parts = []

    # Process each mapping in order
    for i, mapping in enumerate(mappings, 1):
        prompt = Prompts.get_prompt_by_command(mapping.prompt_command)
        if not prompt:
            log.warning(f"  [{i}] ❌ {mapping.prompt_command} - 프롬프트를 찾을 수 없음")
            continue

        # Determine if this prompt should be included
        should_include = False
        reason = ""

        if prompt.prompt_type == "base":
            # Always include base prompts
            should_include = True
            reason = "base 타입 (항상 포함)"

        elif prompt.prompt_type == "proficiency":
            # Include if proficiency_level matches
            if proficiency_level is not None and proficiency_level == prompt.persona_value:
                should_include = True
                reason = f"proficiency 일치 (요청: {proficiency_level}, 프롬프트: {prompt.persona_value})"
            else:
                reason = f"proficiency 불일치 (요청: {proficiency_level}, 프롬프트: {prompt.persona_value})"

        elif prompt.prompt_type == "style":
            # Include if response_style matches
            if response_style is not None and response_style == prompt.persona_value:
                should_include = True
                reason = f"style 일치 (요청: {response_style})"
            else:
                reason = f"style 불일치 (요청: {response_style}, 프롬프트: {prompt.persona_value})"

        elif prompt.prompt_type is None:
            # Legacy prompts without type - skip in composition
            # (These are meant to be used as /commands)
            should_include = False
            reason = "타입 없음 (레거시, 제외)"

        status = "✅ 포함" if should_include else "⏭️  제외"
        log.info(f"  [{i}] {status} - {mapping.prompt_command}")
        log.info(f"       타입: {prompt.prompt_type}, 페르소나값: {prompt.persona_value}")
        log.info(f"       이유: {reason}")

        if should_include:
            prompt_parts.append(prompt.content)
            log.info(f"       내용: {prompt.content[:100]}...")

    # Join prompts with double newlines
    result = "\n\n".join(prompt_parts)

    log.info("[PROMPT COMPOSER] 최종 조합 결과:")
    log.info(f"  포함된 프롬프트 수: {len(prompt_parts)}")
    log.info(f"  최종 프롬프트 길이: {len(result)} 문자")
    log.info(f"  내용 미리보기:\n{result[:300]}...")
    log.info("="*80)

    return result


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
    log.info("="*80)
    log.info("[FALLBACK COMPOSER] 입력 파라미터:")
    log.info(f"  group_id: {group_id}")
    log.info(f"  system_prompt: {system_prompt[:50] if system_prompt else None}...")
    log.info(f"  default_group_id: {default_group_id}")
    log.info(f"  proficiency_level: {proficiency_level}")
    log.info(f"  response_style: {response_style}")
    log.info("="*80)

    # Priority 1: Use specified group
    if group_id:
        log.info(f"[FALLBACK COMPOSER] ✅ Priority 1: 지정된 그룹 사용 ({group_id})")
        composed = compose_prompts_from_group(group_id, proficiency_level, response_style)

        # If system_prompt also exists, append it
        if system_prompt and composed:
            log.info("[FALLBACK COMPOSER] 그룹 조합 + system 프롬프트 병합")
            return f"{composed}\n\n{system_prompt}"
        elif composed:
            log.info("[FALLBACK COMPOSER] 그룹 조합만 사용")
            return composed

    # Priority 2: Use system prompt directly
    if system_prompt:
        log.info("[FALLBACK COMPOSER] ✅ Priority 2: system 프롬프트 직접 사용")
        return system_prompt

    # Priority 3: Use default group
    if default_group_id:
        log.info(f"[FALLBACK COMPOSER] ✅ Priority 3: 기본 그룹 사용 ({default_group_id})")
        return compose_prompts_from_group(
            default_group_id, proficiency_level, response_style
        )

    # Priority 4: No prompt
    log.warning("[FALLBACK COMPOSER] ⚠️  Priority 4: 프롬프트 없음")
    return None
