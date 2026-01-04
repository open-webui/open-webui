"""
Tool Inline Executor - On-demand tool execution during streaming

Detects tool markers in streaming response and executes tool prompts inline.

Flow:
1. LLM responds with markers like <base-graph-spec>description</base-graph-spec>
2. When marker detected, pause streaming and emit "tool_executing"
3. Make separate LLM call with full tool prompt + context
4. Insert generated content into stream
5. Emit "tool_completed" and continue streaming
"""

import re
import logging
from typing import Optional, Callable, Awaitable, Dict, List, Any, Set

from open_webui.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS.get("MAIN", logging.INFO))


class ToolInlineExecutor:
    """
    Executes tool prompts inline during streaming.

    When a tool marker is detected in the stream:
    1. Emit tool_executing event
    2. Call LLM with full tool prompt
    3. Insert result into stream
    4. Emit tool_completed event
    """

    def __init__(
        self,
        event_emitter: Optional[Callable[[dict], Awaitable[None]]] = None,
        tool_prompts: Optional[Dict[str, Any]] = None,
        llm_call_fn: Optional[Callable] = None,
    ):
        self.event_emitter = event_emitter
        # Map: normalized command -> full prompt content
        self.tool_prompts = tool_prompts or {}
        self.llm_call_fn = llm_call_fn

        # Buffer for detecting markers across chunks
        self.buffer = ""
        self.in_tool_marker = False
        self.current_marker_start = -1

        # Build dynamic pattern from tool_prompts keys
        self._marker_pattern = self._build_marker_pattern()

        log.info("=" * 60)
        log.info("[TOOL INLINE] Initialized")
        log.info(f"  event_emitter: {'SET' if event_emitter else 'NONE'}")
        log.info(f"  tool_prompts: {list(self.tool_prompts.keys())}")
        log.info(f"  llm_call_fn: {'SET' if llm_call_fn else 'NONE'}")
        log.info(f"  marker_pattern: {self._marker_pattern.pattern if self._marker_pattern else 'NONE'}")
        log.info("=" * 60)

    def _build_marker_pattern(self) -> Optional[re.Pattern]:
        """
        Build regex pattern to match tool markers.

        Matches format: <command>content</command>
        e.g., <base-flow-spec>...</base-flow-spec>
        """
        if not self.tool_prompts:
            return None

        # Get all command names (already normalized without leading slash)
        commands = list(self.tool_prompts.keys())
        if not commands:
            return None

        # Build pattern: <command>content</command>
        # Capture group 1: command name
        # Capture group 2: content
        escaped_commands = '|'.join(re.escape(cmd) for cmd in commands)
        pattern = rf'<({escaped_commands})>(.*?)</\1>'

        log.info(f"[TOOL INLINE] Built marker pattern for commands: {commands}")
        return re.compile(pattern, re.DOTALL | re.IGNORECASE)

    async def process_chunk(self, chunk: str) -> str:
        """
        Process a streaming chunk.

        Returns text to display immediately.
        When a tool marker is detected, returns text before marker,
        executes tool, and buffers rest for next call.
        """
        if not self._marker_pattern:
            return chunk

        self.buffer += chunk
        output = ""

        while True:
            # Look for tool markers in buffer
            match = self._marker_pattern.search(self.buffer)

            if match:
                # Found a complete marker
                marker_start = match.start()
                marker_end = match.end()

                # Output text before marker
                output += self.buffer[:marker_start]

                # Extract tool info
                tool_command = match.group(1)
                tool_context = match.group(2).strip()

                log.info(f"[TOOL INLINE] Marker detected: command={tool_command}")
                log.info(f"[TOOL INLINE] Context preview: {tool_context[:100]}...")

                # Execute tool
                tool_result = await self._execute_tool(tool_command, tool_context)

                # Append tool result to output
                output += tool_result

                # Remove processed marker from buffer
                self.buffer = self.buffer[marker_end:]
            else:
                # No complete marker found
                # Check for partial marker at end of buffer
                # Look for any opening tag that might be incomplete
                found_partial = False
                for cmd in self.tool_prompts.keys():
                    open_tag = f"<{cmd}>"
                    # Check for partial opening tag
                    for i in range(1, len(open_tag)):
                        if self.buffer.endswith(open_tag[:i]):
                            output += self.buffer[:-i]
                            self.buffer = self.buffer[-i:]
                            found_partial = True
                            break
                    if found_partial:
                        break

                if not found_partial:
                    # No partial marker, output entire buffer
                    output += self.buffer
                    self.buffer = ""

                break

        return output

    async def _execute_tool(self, command: str, context: str) -> str:
        """
        Execute a tool prompt and return the generated content.
        """
        log.info(f"[TOOL INLINE] Executing tool: {command}")

        # Emit tool_executing event
        await self._emit_event("tool_executing", command, f"도구 실행 중: {command}")

        # Find matching tool prompt
        tool_prompt = self._find_tool_prompt(command)

        if not tool_prompt:
            log.warning(f"[TOOL INLINE] Tool prompt not found: {command}")
            await self._emit_event("tool_completed", command, f"도구 완료: {command}")
            return f"\n<!-- Tool '{command}' not found -->\n"

        if not self.llm_call_fn:
            log.warning("[TOOL INLINE] No LLM call function provided")
            await self._emit_event("tool_completed", command, f"도구 완료: {command}")
            return f"\n<!-- No LLM function for tool '{command}' -->\n"

        try:
            # Build tool-specific system prompt
            tool_system = f"""{tool_prompt}

Generate the visualization for the following request:
{context}

Output ONLY the tool-specific JSON block wrapped in appropriate markers.
Do NOT include any explanatory text before or after the output block."""

            log.info(f"[TOOL INLINE] Calling LLM with tool prompt ({len(tool_system)} chars)")

            # Call LLM
            result = await self.llm_call_fn(
                system_prompt=tool_system,
                user_message=context,
            )

            if result.get("success"):
                tool_output = result.get("text", "")
                log.info(f"[TOOL INLINE] Tool output received: {len(tool_output)} chars")
                await self._emit_event("tool_completed", command, f"도구 완료: {command}")
                return f"\n{tool_output}\n"
            else:
                error = result.get("error", "Unknown error")
                log.error(f"[TOOL INLINE] Tool execution failed: {error}")
                await self._emit_event("tool_completed", command, f"도구 실패: {command}")
                return f"\n<!-- Tool error: {error} -->\n"

        except Exception as e:
            log.error(f"[TOOL INLINE] Exception during tool execution: {e}")
            await self._emit_event("tool_completed", command, f"도구 오류: {command}")
            return f"\n<!-- Tool exception: {str(e)} -->\n"

    def _find_tool_prompt(self, command: str) -> Optional[str]:
        """Find tool prompt by command name."""
        # Normalize command
        normalized = command.lower().replace('_', '-').lstrip('/')

        # Direct match first
        if normalized in self.tool_prompts:
            return self.tool_prompts[normalized]

        # Fuzzy match
        for key, prompt in self.tool_prompts.items():
            key_normalized = key.lower().replace('_', '-').lstrip('/')
            if normalized in key_normalized or key_normalized in normalized:
                return prompt

        return None

    async def _emit_event(self, event_type: str, tool: str, message: str):
        """Emit socket event."""
        if self.event_emitter:
            try:
                await self.event_emitter({
                    "type": event_type,
                    "data": {
                        "tool": tool,
                        "message": message
                    }
                })
                log.info(f"[TOOL INLINE] Event emitted: {event_type} - {tool}")
            except Exception as e:
                log.error(f"[TOOL INLINE] Event emission failed: {e}")

    async def flush(self) -> str:
        """Return any remaining buffer content."""
        remaining = self.buffer
        self.buffer = ""
        return remaining


def build_tool_hints(tool_prompts: List[Any]) -> str:
    """
    Build short tool hints for the initial prompt.

    Instead of full tool prompts, just provide hints about available tools
    and how to request them using the tool's description.
    """
    if not tool_prompts:
        return ""

    lines = [
        "[사용 가능한 시각화 도구]",
        "시각화가 필요할 때 다음 형식을 사용하세요:",
        "",
    ]

    for tool in tool_prompts:
        command = tool.command.lstrip('/')
        title = tool.title or command
        description = tool.tool_description or ""
        # Truncate long descriptions
        if len(description) > 400:
            description = description[:400] + "..."
        lines.append(f"- {title}: {description}")
        lines.append(f"  형식: <{command}>시각화할 내용 설명</{command}>")

    lines.extend([
        "",
        "사용 예시:",
    ])

    # Add examples based on available tools
    for tool in tool_prompts[:2]:  # Show 2 examples max
        command = tool.command.lstrip('/')
        title = tool.title or command
        if 'graph' in command.lower():
            lines.append(f"<{command}>y = sin(x) 함수의 그래프를 0부터 2π까지 그려주세요</{command}>")
        elif 'flow' in command.lower():
            lines.append(f"<{command}>이차방정식 풀이 과정을 순서도로 나타내세요</{command}>")
        elif 'diagram' in command.lower():
            lines.append(f"<{command}>삼각형의 내심과 외심 관계를 다이어그램으로 표현</{command}>")
        elif 'scene' in command.lower():
            lines.append(f"<{command}>원기둥의 부피 공식을 3D로 시각화</{command}>")

    lines.extend([
        "",
        "중요: 시각화가 이해에 도움이 될 때만 도구를 사용하세요.",
        "도구 출력은 별도로 생성되어 응답에 삽입됩니다.",
    ])

    return "\n".join(lines)
