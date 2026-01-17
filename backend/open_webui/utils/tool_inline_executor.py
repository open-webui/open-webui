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
from open_webui.utils.tool_validator import validate_tool_output
from open_webui.utils.hardcoded_tools import (
    is_hardcoded_tool,
    get_hardcoded_tool_by_command
)

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

    When a tool-unsupported marker is detected:
    1. Hide the marker from user
    2. Make recovery LLM call to continue naturally
    3. Insert recovery response into stream
    """

    # Pattern for tool-unsupported marker
    UNSUPPORTED_PATTERN = re.compile(
        r'<tool-unsupported\s+tool="([^"]+)"\s+reason="([^"]+)"\s*/?>',
        re.IGNORECASE
    )

    def __init__(
        self,
        event_emitter: Optional[Callable[[dict], Awaitable[None]]] = None,
        tool_prompts: Optional[Dict[str, Any]] = None,
        tool_validation_rules: Optional[Dict[str, Dict]] = None,
        llm_call_fn: Optional[Callable] = None,
        conversation_context: Optional[str] = None,
    ):
        self.event_emitter = event_emitter
        # Map: normalized command -> full prompt content
        self.tool_prompts = tool_prompts or {}
        # Map: normalized command -> validation rules dict (for json_tool types)
        self.tool_validation_rules = tool_validation_rules or {}
        self.llm_call_fn = llm_call_fn
        # Store conversation context for recovery calls
        self.conversation_context = conversation_context or ""

        # Buffer for detecting markers across chunks
        self.buffer = ""
        self.in_tool_marker = False
        self.current_marker_start = -1

        # Track content generated so far (for recovery context)
        self.generated_content = ""

        # Track which tools have already emitted tool_executing event
        # (to avoid duplicate emissions during streaming)
        self._emitted_tool_executing: Set[str] = set()

        # Build dynamic pattern from tool_prompts keys
        self._marker_pattern = self._build_marker_pattern()

        log.info("=" * 60)
        log.info("[TOOL INLINE] Initialized")
        log.info(f"  event_emitter: {'SET' if event_emitter else 'NONE'}")
        log.info(f"  tool_prompts: {list(self.tool_prompts.keys())}")
        log.info(f"  tool_validation_rules: {list(self.tool_validation_rules.keys())}")
        log.info(f"  llm_call_fn: {'SET' if llm_call_fn else 'NONE'}")
        log.info(f"  marker_pattern: {self._marker_pattern.pattern if self._marker_pattern else 'NONE'}")
        log.info("=" * 60)

    def _build_marker_pattern(self) -> Optional[re.Pattern]:
        """
        Build regex pattern to match tool markers.

        Matches format: <command>content</command>
        e.g., <base-flow-spec>...</base-flow-spec>

        Includes both DB tools (from self.tool_prompts) and hardcoded tools.
        """
        # Get all DB tool commands
        db_commands = list(self.tool_prompts.keys()) if self.tool_prompts else []

        # Get all hardcoded tool commands
        from open_webui.utils.hardcoded_tools import get_hardcoded_tools
        hardcoded_tools = get_hardcoded_tools()
        hardcoded_commands = [tool.command for tool in hardcoded_tools]

        # Combine all commands
        commands = db_commands + hardcoded_commands

        if not commands:
            log.warning("[TOOL INLINE] No tools available (neither DB nor hardcoded)")
            return None

        # Build pattern: <command>content</command>
        # Capture group 1: command name
        # Capture group 2: content
        escaped_commands = '|'.join(re.escape(cmd) for cmd in commands)
        pattern = rf'<({escaped_commands})>(.*?)</\1>'

        log.info(f"[TOOL INLINE] Built marker pattern for {len(commands)} commands:")
        log.info(f"  DB tools: {db_commands}")
        log.info(f"  Hardcoded tools: {hardcoded_commands}")
        return re.compile(pattern, re.DOTALL | re.IGNORECASE)

    async def process_chunk(self, chunk: str) -> str:
        """
        Process a streaming chunk.

        Returns text to display immediately.
        When a tool marker is detected, returns text before marker,
        executes tool, and buffers rest for next call.
        When tool-unsupported marker is detected, hide it and make recovery call.
        """
        if not self._marker_pattern:
            # Still check for unsupported pattern even without tool markers
            self.buffer += chunk
            output = await self._process_unsupported_markers(self.buffer)
            if output is not None:
                # Unsupported marker was found and handled
                self.buffer = ""
                self.generated_content += output
                return output
            # No unsupported marker, pass through
            self.generated_content += chunk
            self.buffer = ""
            return chunk

        self.buffer += chunk
        output = ""

        while True:
            # First check for tool-unsupported markers (higher priority)
            unsupported_match = self.UNSUPPORTED_PATTERN.search(self.buffer)

            # Look for complete tool markers in buffer
            match = self._marker_pattern.search(self.buffer)

            # Handle unsupported marker first if it appears before tool marker
            if unsupported_match:
                unsupported_pos = unsupported_match.start()
                tool_pos = match.start() if match else float('inf')

                if unsupported_pos < tool_pos:
                    # Unsupported marker comes first - handle it
                    # Output text before the unsupported marker
                    text_before = self.buffer[:unsupported_pos]
                    output += text_before
                    self.generated_content += text_before

                    tool_name = unsupported_match.group(1)
                    reason = unsupported_match.group(2)

                    log.info(f"[TOOL INLINE] Unsupported marker detected: tool={tool_name}, reason={reason}")

                    # Handle recovery - make LLM call to continue naturally
                    recovery_text = await self._handle_unsupported_tool(tool_name, reason)
                    output += recovery_text
                    self.generated_content += recovery_text

                    # Remove processed unsupported marker and everything after from buffer
                    # (LLM response after unsupported marker is likely incomplete/invalid)
                    self.buffer = self.buffer[unsupported_match.end():]
                    continue

            if match:
                # Found a complete marker
                marker_start = match.start()
                marker_end = match.end()

                # Output text before marker
                text_before = self.buffer[:marker_start]
                output += text_before
                self.generated_content += text_before

                # Extract tool info
                tool_command = match.group(1)
                tool_context = match.group(2).strip()

                log.info(f"[TOOL INLINE] Complete marker detected: command={tool_command}")
                log.info(f"[TOOL INLINE] Context preview: {tool_context[:100]}...")

                # NOTE: tool_executing event was already emitted when opening tag was detected
                # (see lines 222-227 above)

                # IMPORTANT: Execute tool inline (mid-response, not at the end)
                # This is non-blocking because llm_call_fn uses asyncio.to_thread()
                log.info(f"[TOOL INLINE] Executing tool inline: {tool_command}")

                # Execute tool immediately (inline during streaming)
                # NOTE: The LLM call inside _execute_tool uses thread pool, so it won't block
                tool_result = await self._execute_tool(tool_command, tool_context)

                # Append tool result to output immediately (inline in stream)
                output += tool_result
                self.generated_content += tool_result
                log.info(f"[TOOL INLINE] Tool result appended inline: {len(tool_result)} chars")

                # Clear tool_executing tracking
                self._emitted_tool_executing.discard(tool_command)
                log.debug(f"[TOOL INLINE] Cleared tool_executing tracking for {tool_command}")

                # Remove processed marker from buffer (don't show marker to user)
                self.buffer = self.buffer[marker_end:]
            else:
                # No complete marker found
                # Check if we're in the middle of a potential marker (opening tag seen but no closing tag yet)
                in_marker = False
                marker_start_pos = -1

                # Check both DB tools and hardcoded tools
                from open_webui.utils.hardcoded_tools import get_hardcoded_tools
                hardcoded_tools = get_hardcoded_tools()
                all_commands = list(self.tool_prompts.keys()) + [tool.command for tool in hardcoded_tools]

                for cmd in all_commands:
                    open_tag = f"<{cmd}>"
                    close_tag = f"</{cmd}>"

                    # Check if opening tag exists in buffer
                    open_pos = self.buffer.find(open_tag)
                    if open_pos != -1:
                        # Opening tag found - check if closing tag exists
                        close_pos = self.buffer.find(close_tag, open_pos + len(open_tag))
                        if close_pos == -1:
                            # Opening tag without closing tag - we're in the middle of a marker
                            in_marker = True
                            marker_start_pos = open_pos
                            log.info(f"[TOOL INLINE] Opening tag detected: {cmd} at pos {open_pos}")

                            # Emit tool_executing event IMMEDIATELY when opening tag is detected
                            # (only once per tool to avoid duplicates)
                            if cmd not in self._emitted_tool_executing:
                                log.info(f"[TOOL INLINE] Emitting tool_executing event for {cmd} (opening tag detected)")
                                await self._emit_event("tool_executing", cmd, f"도구 실행 중: {cmd}")
                                self._emitted_tool_executing.add(cmd)

                            break

                # Also check for partial unsupported marker
                unsupported_partial = "<tool-unsupported"
                unsupported_pos = self.buffer.find(unsupported_partial)
                if unsupported_pos != -1:
                    # Check if the marker is complete (ends with />)
                    end_pos = self.buffer.find("/>", unsupported_pos)
                    if end_pos == -1:
                        # Partial unsupported marker
                        if not in_marker or unsupported_pos < marker_start_pos:
                            in_marker = True
                            marker_start_pos = unsupported_pos
                            log.debug(f"[TOOL INLINE] Buffering partial unsupported marker at pos {unsupported_pos}")

                if in_marker and marker_start_pos >= 0:
                    # Output text before the opening tag, keep rest in buffer
                    text_before = self.buffer[:marker_start_pos]
                    output += text_before
                    self.generated_content += text_before
                    self.buffer = self.buffer[marker_start_pos:]
                    log.debug(f"[TOOL INLINE] Buffer retained ({len(self.buffer)} chars): {self.buffer[:50]}...")
                    break

                # Check for partial opening tag at the end of buffer
                found_partial = False
                for cmd in self.tool_prompts.keys():
                    open_tag = f"<{cmd}>"
                    # Check for partial opening tag at end
                    for i in range(1, len(open_tag)):
                        if self.buffer.endswith(open_tag[:i]):
                            text_before = self.buffer[:-i]
                            output += text_before
                            self.generated_content += text_before
                            self.buffer = self.buffer[-i:]
                            found_partial = True
                            log.debug(f"[TOOL INLINE] Partial opening tag retained: {self.buffer}")
                            break
                    if found_partial:
                        break

                # Also check for partial unsupported tag at end
                if not found_partial:
                    for i in range(1, len(unsupported_partial)):
                        if self.buffer.endswith(unsupported_partial[:i]):
                            text_before = self.buffer[:-i]
                            output += text_before
                            self.generated_content += text_before
                            self.buffer = self.buffer[-i:]
                            found_partial = True
                            log.debug(f"[TOOL INLINE] Partial unsupported tag retained: {self.buffer}")
                            break

                if not found_partial:
                    # No partial or in-progress marker, output entire buffer
                    output += self.buffer
                    self.generated_content += self.buffer
                    self.buffer = ""

                break

        return output

    async def _execute_tool(self, command: str, context: str) -> str:
        """
        Execute a tool prompt and return the generated content.
        NOTE: tool_executing event is emitted BEFORE this function is called (in process_chunk)
        """
        log.info(f"[TOOL INLINE] Executing tool: {command}")

        # Check if this is a hardcoded tool (uses response_schema)
        if is_hardcoded_tool(command):
            log.info(f"[HARDCODED TOOL] Detected hardcoded tool: {command}")
            return await self._execute_hardcoded_tool(command, context)

        # Find matching tool prompt (DB tool)
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
            log.info(f"[TOOL INLINE] Using Pro model for accurate tool execution")

            # Call LLM for tool execution (use_fast_model=False by default for accuracy)
            result = await self.llm_call_fn(
                system_prompt=tool_system,
                user_message=context,
                # use_fast_model=False (default) - Use Pro model for accurate tool execution
            )

            if result.get("success"):
                tool_output = result.get("text", "")
                log.info(f"[TOOL INLINE] Tool output received: {len(tool_output)} chars")

                # Validate output for json_tool types
                normalized_cmd = command.lower().replace('_', '-').lstrip('/')
                validation_rules = self.tool_validation_rules.get(normalized_cmd)
                if validation_rules:
                    is_valid, error_msg = validate_tool_output(tool_output, validation_rules)
                    if not is_valid:
                        log.warning(f"[TOOL INLINE] Validation failed for {command}: {error_msg}")
                        log.warning(f"[TOOL INLINE] Tool output FULL OUTPUT (for debugging):")
                        log.warning(tool_output)  # Full output for debugging
                        log.warning(f"[TOOL INLINE] Validation rules: {validation_rules}")
                        await self._emit_event("tool_validation_failed", command, f"검증 실패: {command}")
                        # Use recovery approach (same as tool-unsupported)
                        recovery_text = await self._handle_validation_failure(
                            command, error_msg, context
                        )
                        await self._emit_event("tool_completed", command, f"도구 완료 (복구): {command}")
                        return f"\n{recovery_text}\n"

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

    async def _execute_hardcoded_tool(self, command: str, context: str) -> str:
        """
        Execute a hardcoded tool with response_schema.

        Args:
            command: Tool command name
            context: User context/description from the tool marker

        Returns:
            Tool output (JSON from response_schema)
        """
        # Get hardcoded tool metadata
        hardcoded_tool = get_hardcoded_tool_by_command(command)

        if not hardcoded_tool:
            log.error(f"[HARDCODED TOOL] Tool metadata not found: {command}")
            await self._emit_event("tool_completed", command, f"도구 오류: {command}")
            return f"\n<!-- Hardcoded tool '{command}' not found -->\n"

        if not self.llm_call_fn:
            log.warning("[HARDCODED TOOL] No LLM call function provided")
            await self._emit_event("tool_completed", command, f"도구 완료: {command}")
            return f"\n<!-- No LLM function for hardcoded tool '{command}' -->\n"

        try:
            log.info(f"[HARDCODED TOOL] Executing {command} with response_schema")
            log.info(f"[HARDCODED TOOL] System prompt length: {len(hardcoded_tool.system_prompt)} chars")
            log.info(f"[HARDCODED TOOL] Response schema: {hardcoded_tool.response_schema.__name__}")

            # Call LLM with response_schema
            # Note: use_fast_model=False to use Pro model for accuracy (not Flash)
            result = await self.llm_call_fn(
                system_prompt=hardcoded_tool.system_prompt,
                user_message=context,
                use_fast_model=False,  # Use Pro model for hardcoded tools (accurate)
                response_schema=hardcoded_tool.response_schema
            )

            if result.get("success"):
                tool_output = result.get("text", "")
                log.info(f"[HARDCODED TOOL] Tool output received: {len(tool_output)} chars (JSON)")

                # Strip markdown code blocks if present (Gemini sometimes wraps JSON in ```json...```)
                import re
                import json

                # Remove markdown code blocks: ```json\n{...}\n``` → {...}
                tool_output = tool_output.strip()
                if tool_output.startswith("```"):
                    # Remove opening ```json or ```
                    tool_output = re.sub(r'^```(?:json)?\s*\n?', '', tool_output)
                    # Remove closing ```
                    tool_output = re.sub(r'\n?```\s*$', '', tool_output)
                    tool_output = tool_output.strip()
                    log.info(f"[HARDCODED TOOL] Stripped markdown code blocks, new length: {len(tool_output)} chars")

                # Parse JSON and check status
                try:
                    parsed = json.loads(tool_output)
                    log.info(f"[HARDCODED TOOL] Parsed JSON structure: {list(parsed.keys())}")

                    # Handle two possible JSON structures:
                    # 1. Correct: {"result": {"status": "...", ...}}
                    # 2. Gemini mistake: {"status": "...", ...} (missing "result" wrapper)
                    if "result" in parsed:
                        result_data = parsed["result"]
                    elif "status" in parsed:
                        # Gemini returned flat structure without "result" wrapper
                        result_data = parsed
                        log.warning(f"[HARDCODED TOOL] JSON missing 'result' wrapper, using top-level fields")
                    else:
                        # Completely unexpected structure
                        final_output = tool_output
                        log.warning(f"[HARDCODED TOOL] Unexpected JSON structure (no result/status), using original output")
                        result_data = None

                    if result_data:
                        status = result_data.get("status", "success")

                        if status == "unsupported":
                            # Graph generation failed - use recovery with Flash model
                            reason = result_data.get("reason", "지원하지 않는 그래프 유형입니다")
                            log.warning(f"[HARDCODED TOOL] Graph generation failed (unsupported): {reason}")
                            await self._emit_event("tool_unsupported", command, f"도구 미지원: {command}")

                            # Handle recovery - Flash model will generate natural text explanation
                            recovery_text = await self._handle_unsupported_tool(command, reason)
                            await self._emit_event("tool_completed", command, f"도구 완료 (복구): {command}")
                            return f"\n{recovery_text}\n"

                        elif status == "success" and "graph" in result_data:
                            # Success - extract graph data
                            graph_data = result_data["graph"]
                            final_output = json.dumps(graph_data, ensure_ascii=False)
                            log.info(f"[HARDCODED TOOL] Extracted graph data: {len(final_output)} chars")
                        else:
                            # Unexpected status or missing graph field
                            final_output = tool_output
                            log.warning(f"[HARDCODED TOOL] Unexpected result structure (status={status}), using original output")
                except json.JSONDecodeError as e:
                    log.error(f"[HARDCODED TOOL] JSON parsing failed: {e}")
                    final_output = tool_output

                # Emit tool_completed event
                await self._emit_event("tool_completed", command, f"도구 완료: {command}")

                # Return JSON output wrapped in output_tag (e.g., <graph-spec>...</graph-spec>)
                output_tag = hardcoded_tool.output_tag
                result_str = f"\n<{output_tag}>{final_output}</{output_tag}>\n"
                log.info(f"[HARDCODED TOOL] Wrapping output in <{output_tag}>...</{output_tag}>")
                log.info(f"[HARDCODED TOOL] Returning result: {len(result_str)} chars")
                log.info(f"[HARDCODED TOOL] Result preview: {result_str[:200]}...")
                return result_str
            else:
                error = result.get("error", "Unknown error")
                log.error(f"[HARDCODED TOOL] Tool execution failed: {error}")
                await self._emit_event("tool_completed", command, f"도구 실패: {command}")
                return f"\n<!-- Hardcoded tool error: {error} -->\n"

        except Exception as e:
            log.error(f"[HARDCODED TOOL] Exception during tool execution: {e}")
            await self._emit_event("tool_completed", command, f"도구 오류: {command}")
            return f"\n<!-- Hardcoded tool exception: {str(e)} -->\n"

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

    async def _process_unsupported_markers(self, text: str) -> Optional[str]:
        """
        Process unsupported markers in text when no tool pattern exists.

        Returns processed text if unsupported marker found, None otherwise.
        """
        match = self.UNSUPPORTED_PATTERN.search(text)
        if not match:
            return None

        # Output text before the unsupported marker
        text_before = text[:match.start()]
        tool_name = match.group(1)
        reason = match.group(2)

        log.info(f"[TOOL INLINE] Unsupported marker found (no-tool mode): tool={tool_name}, reason={reason}")

        # Handle recovery
        recovery_text = await self._handle_unsupported_tool(tool_name, reason)

        # Return text before marker + recovery text (discard everything after marker)
        return text_before + recovery_text

    async def _handle_unsupported_tool(self, tool_name: str, reason: str) -> str:
        """
        Handle unsupported tool by making a recovery LLM call.

        When a tool cannot process the request (e.g., complex ODE system),
        this method makes a new LLM call to continue the conversation naturally
        without the visualization.

        Args:
            tool_name: Name of the tool that couldn't process the request
            reason: Reason why the tool couldn't process it

        Returns:
            Recovery text to insert into the stream
        """
        log.info(f"[TOOL INLINE] Handling unsupported tool: {tool_name}, reason: {reason}")

        # Emit event for recovery
        await self._emit_event("tool_recovery", tool_name, f"시각화 도구 복구 중: {tool_name}")

        if not self.llm_call_fn:
            log.warning("[TOOL INLINE] No LLM call function for recovery")
            return f"\n\n(시각화를 생성할 수 없습니다: {reason})\n\n"

        try:
            # Build recovery system prompt
            recovery_system = """당신은 수학 학습을 돕는 AI 튜터입니다.

이전 응답에서 시각화 도구를 사용하려 했으나, 해당 내용을 시각화할 수 없습니다.
시각화 없이 텍스트 설명으로 자연스럽게 계속 설명해주세요.

주의사항:
- 시각화를 생성할 수 없다는 것을 명시적으로 언급하지 마세요
- 마치 처음부터 텍스트로 설명하려 했던 것처럼 자연스럽게 이어가세요
- 수식이 필요하면 LaTeX 형식 ($...$)을 사용하세요
- 간결하고 명확하게 설명하세요"""

            # Build context from generated content so far
            context_preview = self.generated_content[-1000:] if len(self.generated_content) > 1000 else self.generated_content

            user_message = f"""지금까지 생성된 응답:
{context_preview}

도구 실패 이유: {reason}

위 내용에서 자연스럽게 이어서 설명을 계속해주세요. 1-2문장 정도로 간결하게."""

            log.info(f"[TOOL INLINE] Making recovery LLM call with Flash model")

            result = await self.llm_call_fn(
                system_prompt=recovery_system,
                user_message=user_message,
                use_fast_model=True  # Use Flash model for fast recovery
            )

            if result.get("success"):
                recovery_text = result.get("text", "")
                log.info(f"[TOOL INLINE] Recovery text received: {len(recovery_text)} chars")
                await self._emit_event("tool_recovery_completed", tool_name, f"복구 완료: {tool_name}")
                # Add space before recovery text for natural flow
                return f" {recovery_text}"
            else:
                error = result.get("error", "Unknown error")
                log.error(f"[TOOL INLINE] Recovery LLM call failed: {error}")
                return ""

        except Exception as e:
            log.error(f"[TOOL INLINE] Exception during recovery: {e}")
            return ""

    async def _handle_validation_failure(
        self, tool_name: str, error_msg: str, original_context: str
    ) -> str:
        """
        Handle validation failure by making a recovery LLM call.

        When a json_tool output fails regex validation, this method makes a new
        LLM call to continue the conversation naturally without the visualization.

        Args:
            tool_name: Name of the tool whose output failed validation
            error_msg: Validation error message
            original_context: The original context passed to the tool

        Returns:
            Recovery text to insert into the stream
        """
        log.info(f"[TOOL INLINE] Handling validation failure: {tool_name}")

        await self._emit_event("tool_recovery", tool_name, f"도구 복구 중: {tool_name}")

        if not self.llm_call_fn:
            log.warning("[TOOL INLINE] No LLM call function for validation recovery")
            return f"\n\n(시각화 검증 실패: {error_msg})\n\n"

        try:
            recovery_system = """당신은 수학 학습을 돕는 AI 튜터입니다.

이전 시각화 도구 출력이 형식 검증에 실패했습니다.
시각화 없이 텍스트 설명으로 자연스럽게 계속 설명해주세요.

주의사항:
- 검증 실패를 명시적으로 언급하지 마세요
- 마치 처음부터 텍스트로 설명하려 했던 것처럼 자연스럽게 이어가세요
- 수식이 필요하면 LaTeX 형식 ($...$)을 사용하세요
- 간결하고 명확하게 설명하세요"""

            context_preview = (
                self.generated_content[-1000:]
                if len(self.generated_content) > 1000
                else self.generated_content
            )

            user_message = f"""지금까지 생성된 응답:
{context_preview}

원래 요청: {original_context}

위 내용에서 자연스럽게 이어서 설명을 계속해주세요. 1-2문장 정도로 간결하게."""

            log.info("[TOOL INLINE] Making validation recovery LLM call with Flash model")

            result = await self.llm_call_fn(
                system_prompt=recovery_system,
                user_message=user_message,
                use_fast_model=True  # Use Flash model for fast recovery
            )

            if result.get("success"):
                recovery_text = result.get("text", "")
                log.info(f"[TOOL INLINE] Validation recovery text received: {len(recovery_text)} chars")
                await self._emit_event("tool_recovery_completed", tool_name, f"복구 완료: {tool_name}")
                return f" {recovery_text}"
            else:
                error = result.get("error", "Unknown error")
                log.error(f"[TOOL INLINE] Validation recovery LLM call failed: {error}")
                return ""

        except Exception as e:
            log.error(f"[TOOL INLINE] Exception during validation recovery: {e}")
            return ""

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
        """
        Return any remaining buffer content.

        NOTE: Tools are now executed inline (during streaming), not deferred to flush.
        This method now just returns remaining buffer content.
        """
        log.info(f"[TOOL INLINE] Flushing: buffer={len(self.buffer)} chars")

        # Return remaining buffer content
        output = self.buffer
        self.buffer = ""

        return output


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
