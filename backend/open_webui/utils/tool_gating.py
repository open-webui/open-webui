"""
Tool Gating - Two-Stage Prompt Selection

This module implements a two-stage LLM approach for selective tool prompt injection:

Stage 1 (Tool Selection):
- Send base + proficiency + style prompts + tool catalog (short descriptions only)
- LLM responds with JSON indicating which tools are needed

Stage 2 (Execution):
- If tools needed: Re-request with selected tool's full content included
- If no tools needed: Return Stage 1 answer directly

This optimization reduces token usage by ~60% for simple queries that don't need tools.
"""

import json
import re
import logging
from typing import Optional, List, Tuple, Callable, Any

from open_webui.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS.get("MAIN", logging.INFO))


def build_tool_catalog(tool_prompts: List[Any]) -> str:
    """
    Build a tool catalog from tool prompts for Stage 1.

    Args:
        tool_prompts: List of PromptModel objects with prompt_type='tool'

    Returns:
        Formatted tool catalog string with short descriptions
    """
    if not tool_prompts:
        return ""

    lines = ["[Available Tools]"]
    for tool in tool_prompts:
        description = tool.tool_description or tool.title or tool.command
        lines.append(f"- {tool.command}: {description}")

    return "\n".join(lines)


def build_tool_selection_system_prompt(
    base_system: str,
    tool_catalog: str
) -> str:
    """
    Build the Stage 1 system prompt with tool selection instructions.

    Args:
        base_system: Base system prompt (base + proficiency + style)
        tool_catalog: Tool catalog from build_tool_catalog()

    Returns:
        Complete Stage 1 system prompt
    """
    return f"""{base_system}

{tool_catalog}

---
[IMPORTANT: Tool Selection Instructions]
Before answering the user's question, determine if any of the above tools are needed.

Respond with ONLY a raw JSON object (no formatting):
- If tools needed: {{"need_tools": ["tool-command-1", "tool-command-2"], "reason": "brief reason"}}
- If no tools needed: {{"need_tools": [], "answer": "Your direct answer here"}}

CRITICAL OUTPUT FORMAT RULES:
1. Output ONLY the raw JSON object starting with {{ and ending with }}
2. Do NOT wrap in markdown code blocks (no ```json or ```)
3. Do NOT add any text before or after the JSON
4. Start your response directly with the opening brace {{"""


def parse_tool_selection_response(response: str) -> Tuple[List[str], Optional[str]]:
    """
    Parse LLM response from Stage 1 to extract tool selection.

    Args:
        response: Raw LLM response string

    Returns:
        Tuple of (selected_tools, direct_answer)
        - If selected_tools is non-empty: need Stage 2 with these tools
        - If selected_tools is empty and direct_answer exists: return answer directly
        - If parsing fails: return ([], response) to treat as direct answer
    """
    try:
        # Try to extract JSON from response
        # Handle potential markdown code blocks
        json_str = response.strip()

        # Remove markdown code block if present
        if json_str.startswith("```"):
            json_str = re.sub(r'^```(?:json)?\s*', '', json_str)
            json_str = re.sub(r'\s*```$', '', json_str)

        # Try to find JSON object in the response
        match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', json_str, re.DOTALL)
        if match:
            data = json.loads(match.group())
            tools = data.get("need_tools", [])
            answer = data.get("answer")

            # Ensure tools is a list
            if isinstance(tools, str):
                tools = [tools] if tools else []

            log.info(f"[TOOL GATING] Parsed response - tools: {tools}, has_answer: {answer is not None}")
            return (tools, answer)

    except json.JSONDecodeError as e:
        log.warning(f"[TOOL GATING] JSON parse error: {e}")
    except Exception as e:
        log.warning(f"[TOOL GATING] Parse error: {e}")

    # If parsing fails, treat entire response as direct answer
    log.info("[TOOL GATING] Parsing failed, treating as direct answer")
    return ([], response)


def get_tool_prompts_by_commands(
    tool_prompts: List[Any],
    selected_commands: List[str]
) -> List[Any]:
    """
    Filter tool prompts by selected command names.

    Args:
        tool_prompts: All available tool prompts
        selected_commands: List of selected tool commands (may or may not have leading slash)

    Returns:
        Filtered list of tool prompts matching selected commands
    """
    # Normalize commands: strip leading slash for comparison
    def normalize(cmd: str) -> str:
        return cmd.lstrip('/') if cmd else ''

    selected_normalized = {normalize(cmd) for cmd in selected_commands}

    result = [t for t in tool_prompts if normalize(t.command) in selected_normalized]

    log.info(f"[TOOL GATING] Command matching: selected={selected_commands}, normalized={selected_normalized}, matched={[t.command for t in result]}")

    return result


def compose_stage2_system_prompt(
    base_system: str,
    selected_tool_prompts: List[Any]
) -> str:
    """
    Compose the Stage 2 system prompt with selected tool contents.

    Args:
        base_system: Base system prompt (base + proficiency + style)
        selected_tool_prompts: Tool prompts selected in Stage 1

    Returns:
        Complete Stage 2 system prompt with full tool contents
    """
    if not selected_tool_prompts:
        return base_system

    # Sort by priority (higher priority first)
    sorted_tools = sorted(
        selected_tool_prompts,
        key=lambda t: t.tool_priority or 0,
        reverse=True
    )

    tool_contents = "\n\n".join([t.content for t in sorted_tools])
    return f"{base_system}\n\n{tool_contents}"


class ToolGatingResult:
    """Result from tool gating execution."""

    def __init__(
        self,
        text: str,
        used_tools: List[str],
        stage: int,
        stage1_response: Optional[str] = None
    ):
        self.text = text
        self.used_tools = used_tools
        self.stage = stage  # 1 or 2
        self.stage1_response = stage1_response

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "used_tools": self.used_tools,
            "stage": self.stage,
            "stage1_response": self.stage1_response
        }


async def execute_with_tool_gating(
    query: str,
    base_system: str,
    tool_prompts: List[Any],
    llm_call_fn: Callable,
    **llm_kwargs
) -> ToolGatingResult:
    """
    Execute two-stage tool gating.

    Args:
        query: User's question
        base_system: Base system prompt (base + proficiency + style)
        tool_prompts: All available tool prompts
        llm_call_fn: Async function to call LLM
            Expected signature: llm_call_fn(system_instruction, question, **kwargs) -> dict with 'text' key
        **llm_kwargs: Additional arguments for LLM call (model, temperature, store_names, etc.)

    Returns:
        ToolGatingResult with text, used_tools, stage info
    """
    log.info("=" * 80)
    log.info("[TOOL GATING] Starting two-stage execution")
    log.info(f"  Query: {query[:100]}...")
    log.info(f"  Available tools: {[t.command for t in tool_prompts]}")
    log.info("=" * 80)

    # Stage 1: Tool selection
    tool_catalog = build_tool_catalog(tool_prompts)
    stage1_system = build_tool_selection_system_prompt(base_system, tool_catalog)

    log.info(f"[TOOL GATING] Stage 1 System Prompt Length: {len(stage1_system)} chars")

    log.info("[TOOL GATING] Stage 1 - Calling LLM for tool selection...")
    stage1_result = llm_call_fn(
        question=query,
        system_instruction=stage1_system,
        **llm_kwargs
    )

    if not stage1_result.get("success"):
        log.error(f"[TOOL GATING] Stage 1 failed: {stage1_result.get('error')}")
        return ToolGatingResult(
            text=stage1_result.get("error", "Tool gating failed"),
            used_tools=[],
            stage=1
        )

    stage1_text = stage1_result.get("text", "")
    log.info(f"[TOOL GATING] Stage 1 response: {stage1_text[:200]}...")

    # Parse tool selection
    selected_tools, direct_answer = parse_tool_selection_response(stage1_text)

    # If no tools needed and we have a direct answer
    if not selected_tools and direct_answer:
        log.info("[TOOL GATING] No tools needed, returning direct answer")
        return ToolGatingResult(
            text=direct_answer,
            used_tools=[],
            stage=1,
            stage1_response=stage1_text
        )

    # Stage 2: Execute with selected tools
    log.info(f"[TOOL GATING] Stage 2 - Tools selected: {selected_tools}")

    selected_tool_prompts = get_tool_prompts_by_commands(tool_prompts, selected_tools)
    stage2_system = compose_stage2_system_prompt(base_system, selected_tool_prompts)

    log.info(f"[TOOL GATING] Stage 2 System Prompt Length: {len(stage2_system)} chars")
    log.info(f"[TOOL GATING] Selected tools: {[t.command for t in selected_tool_prompts]}")

    log.info("[TOOL GATING] Stage 2 - Calling LLM with tool prompts...")
    stage2_result = llm_call_fn(
        question=query,
        system_instruction=stage2_system,
        **llm_kwargs
    )

    if not stage2_result.get("success"):
        log.error(f"[TOOL GATING] Stage 2 failed: {stage2_result.get('error')}")
        # Fallback to Stage 1 answer if available
        if direct_answer:
            return ToolGatingResult(
                text=direct_answer,
                used_tools=[],
                stage=1,
                stage1_response=stage1_text
            )
        return ToolGatingResult(
            text=stage2_result.get("error", "Tool gating failed"),
            used_tools=selected_tools,
            stage=2
        )

    log.info("[TOOL GATING] Stage 2 completed successfully")
    return ToolGatingResult(
        text=stage2_result.get("text", ""),
        used_tools=selected_tools,
        stage=2,
        stage1_response=stage1_text
    )


def should_use_tool_gating(tool_prompts: List[Any], enable_tool_gating: bool = True) -> bool:
    """
    Determine if tool gating should be used.

    Args:
        tool_prompts: Available tool prompts
        enable_tool_gating: Flag to enable/disable tool gating

    Returns:
        True if tool gating should be used
    """
    return enable_tool_gating and len(tool_prompts) > 0
