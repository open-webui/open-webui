"""
Tool JSON Tracker for Streaming Responses

스트리밍 중 prompt-based tool JSON 블록을 감지하고 소켓 이벤트 발생
"""

import re
import logging
from typing import Optional, Callable, Awaitable, Set

from open_webui.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS.get("MAIN", logging.INFO))


class ToolJsonTracker:
    """
    스트리밍 콘텐츠에서 도구 JSON 블록 추적

    감지 패턴:
    ```tool_command
    {"key": "value", ...}
    ```
    """

    def __init__(
        self,
        event_emitter: Optional[Callable[[dict], Awaitable[None]]] = None,
        tool_commands: Optional[Set[str]] = None
    ):
        self.event_emitter = event_emitter
        self.tool_commands = tool_commands or set()

        # 상태
        self.buffer = ""
        self.in_tool_block = False
        self.current_tool: Optional[str] = None

        # 동적 패턴 생성
        self._update_pattern()

        # 초기화 로깅
        log.info("=" * 60)
        log.info("[TOOL TRACKER] Initialized")
        log.info(f"  event_emitter: {'SET' if event_emitter else 'NONE'}")
        log.info(f"  tool_commands: {self.tool_commands}")
        log.info(f"  pattern: {self._start_pattern.pattern if self._start_pattern else 'NONE'}")
        log.info("=" * 60)

    def _update_pattern(self):
        """tool_commands 기반 정규식 패턴 생성"""
        if self.tool_commands:
            pattern = r'```(' + '|'.join(re.escape(cmd) for cmd in self.tool_commands) + r')\s*\n?'
            self._start_pattern = re.compile(pattern, re.IGNORECASE)
        else:
            self._start_pattern = None

    async def process_chunk(self, chunk: str) -> str:
        """
        스트리밍 청크 처리

        Args:
            chunk: 스트리밍 텍스트 청크

        Returns:
            표시할 텍스트 (tool JSON 내용 제외)
        """
        # tracker 비활성화 상태면 그대로 반환
        if not self._start_pattern:
            return chunk

        # 청크에 ``` 포함시 로깅
        if "```" in chunk:
            log.info(f"[TOOL TRACKER] Chunk contains ```: {repr(chunk[:100])}")
            log.info(f"  in_tool_block: {self.in_tool_block}, current_tool: {self.current_tool}")

        self.buffer += chunk
        output = ""

        while self.buffer:
            if not self.in_tool_block:
                # 도구 블록 시작 탐지
                match = self._start_pattern.search(self.buffer)

                if match:
                    # 도구 블록 이전 텍스트 출력
                    output += self.buffer[:match.start()]

                    # 도구 블록 시작
                    self.current_tool = match.group(1)
                    self.in_tool_block = True

                    # 이벤트 발생
                    await self._emit_tool_event("tool_executing")
                    log.info(f"[TOOL TRACKER] Tool block started: {self.current_tool}")

                    self.buffer = self.buffer[match.end():]
                else:
                    # 부분 매칭 가능성 체크 (버퍼 끝에 ``` 있을 수 있음)
                    potential_start = self.buffer.rfind("```")
                    if potential_start >= 0 and potential_start > len(self.buffer) - 20:
                        output += self.buffer[:potential_start]
                        self.buffer = self.buffer[potential_start:]
                        break
                    else:
                        output += self.buffer
                        self.buffer = ""
            else:
                # 도구 블록 내부 - 종료 탐지
                end_match = re.search(r'\n?```', self.buffer)

                if end_match:
                    # 도구 블록 종료
                    await self._emit_tool_event("tool_completed")
                    log.info(f"[TOOL TRACKER] Tool block completed: {self.current_tool}")

                    self.in_tool_block = False
                    self.current_tool = None
                    self.buffer = self.buffer[end_match.end():]
                else:
                    # 아직 도구 블록 내부 - 버퍼 비움
                    self.buffer = ""

        return output

    async def _emit_tool_event(self, event_type: str):
        """소켓 이벤트 발생"""
        log.info(f"[TOOL TRACKER] _emit_tool_event called: type={event_type}")
        log.info(f"  event_emitter: {'SET' if self.event_emitter else 'NONE'}")
        log.info(f"  current_tool: {self.current_tool}")

        if self.event_emitter and self.current_tool:
            message = f"도구 실행 중: {self.current_tool}" if event_type == "tool_executing" else f"도구 완료: {self.current_tool}"
            event_data = {
                "type": event_type,
                "data": {
                    "tool": self.current_tool,
                    "message": message
                }
            }
            log.info(f"[TOOL TRACKER] Emitting event: {event_data}")
            try:
                await self.event_emitter(event_data)
                log.info(f"[TOOL TRACKER] Event emitted successfully")
            except Exception as e:
                log.error(f"[TOOL TRACKER] Event emission failed: {e}")
        else:
            log.warning(f"[TOOL TRACKER] Event NOT emitted - emitter={bool(self.event_emitter)}, tool={self.current_tool}")

    async def flush(self) -> str:
        """스트리밍 종료 시 남은 버퍼 처리"""
        output = ""
        if self.buffer:
            if not self.in_tool_block:
                output = self.buffer
            else:
                log.warning(f"[TOOL TRACKER] Incomplete tool block: {self.current_tool}")
            self.buffer = ""
        return output

    def reset(self):
        """상태 초기화"""
        self.buffer = ""
        self.in_tool_block = False
        self.current_tool = None
