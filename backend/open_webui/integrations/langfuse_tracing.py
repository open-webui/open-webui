"""
Langfuse Tracing Integration

Provides tracing wrapper for LLM calls to enable observability in Langfuse Cloud.
"""

from typing import Optional, Dict, Any
import logging

log = logging.getLogger(__name__)

_MODEL_PRICING = {
    # (input USD/token, output USD/token)
    "gemini-2.0-flash":         (0.075 / 1_000_000,  0.30 / 1_000_000),
    "gemini-2.0-flash-exp":     (0.075 / 1_000_000,  0.30 / 1_000_000),
    "gemini-2.0-flash-lite":    (0.0375 / 1_000_000, 0.15 / 1_000_000),
    "gemini-2.5-pro":           (1.25 / 1_000_000,  10.00 / 1_000_000),
    "gemini-2.5-pro-preview":   (1.25 / 1_000_000,  10.00 / 1_000_000),
    "gemini-2.5-flash":         (0.15 / 1_000_000,   0.60 / 1_000_000),
    "gemini-2.5-flash-preview": (0.15 / 1_000_000,   0.60 / 1_000_000),
    "gemini-3-flash-preview":   (0.15 / 1_000_000,   0.60 / 1_000_000),
    "gemini-1.5-flash":         (0.075 / 1_000_000,  0.30 / 1_000_000),
    "gemini-1.5-pro":           (1.25 / 1_000_000,   5.00 / 1_000_000),
}


def _get_cost_details(model: str, usage_details: Optional[Dict]) -> Optional[Dict[str, float]]:
    if not usage_details or not model:
        return None
    key = model.lower().split("/")[-1]
    pricing = None
    for prefix, price in _MODEL_PRICING.items():
        if key.startswith(prefix):
            pricing = price
            break
    if not pricing:
        return None
    in_cost = usage_details.get("input", 0) * pricing[0]
    out_cost = usage_details.get("output", 0) * pricing[1]
    return {"input": in_cost, "output": out_cost, "total": in_cost + out_cost}


class LangfuseTracer:
    """Wrapper for Langfuse tracing"""

    def __init__(self, langfuse):
        """
        Initialize tracer with Langfuse client.

        Args:
            langfuse: Langfuse client instance
        """
        self.langfuse = langfuse
        log.info("[LANGFUSE] Tracer initialized")

    def trace_chat_completion(
        self,
        chat_id: str,
        model: str,
        messages: list,
        response: Any,
        metadata: Dict[str, Any],
        start_time: Optional[float] = None,
        end_time: Optional[float] = None
    ):
        """
        Trace a chat completion call using Langfuse v3 API.

        Args:
            chat_id: Unique chat/conversation ID (used as session_id)
            model: Model name (e.g., "gpt-4", "gemini-1.5-pro")
            messages: Input messages
            response: LLM response object
            metadata: Additional metadata (user_id, prompt_group_id, message_id, etc.)
            start_time: Optional Unix timestamp (seconds) when LLM call started
            end_time: Optional Unix timestamp (seconds) when LLM call completed

        Returns:
            Tuple of (trace, generation) or (None, None) if tracing fails
        """
        try:
            import uuid
            from langfuse.types import TraceContext

            # Extract token usage and response content based on provider
            output_text = self._extract_response_text(response)
            usage_info = self._extract_usage(response)

            # Prepare usage_details for Langfuse v3 format
            usage_details = None
            if usage_info:
                usage_details = {
                    "input": usage_info.get("prompt_tokens", 0),
                    "output": usage_info.get("completion_tokens", 0),
                    "total": usage_info.get("total_tokens", 0)
                }

            # Debug: Log the usage data being sent
            log.info(f"[LANGFUSE TRACE] Sending usage_details to Langfuse: {usage_details}, raw usage_info: {usage_info}")

            # Create unique trace_id for each message (not chat_id!)
            # Use message_id from metadata if available, otherwise generate new UUID
            message_id = metadata.get("message_id") or str(uuid.uuid4())
            langfuse_trace_id = message_id.replace("-", "").lower()[:32]

            # Use chat_id as session_id to group messages in the same conversation
            langfuse_session_id = chat_id.replace("-", "").lower()[:32]

            # Create trace context for this message
            trace_context = TraceContext(
                trace_id=langfuse_trace_id,
                session_id=langfuse_session_id,
                user_id=metadata.get("user_id")
            )

            # Prepare observation parameters
            obs_params = {
                "trace_context": trace_context,
                "name": "chat-completion",
                "as_type": "generation",
                "model": model,
                "input": messages,
                "output": output_text,
                "usage_details": usage_details,
                "metadata": {
                    "user_id": metadata.get("user_id"),  # Also store in metadata for easier access
                    "prompt_group_id": metadata.get("prompt_group_id"),
                    "proficiency_level": metadata.get("proficiency_level"),
                    "response_style": metadata.get("response_style"),
                    "composed_prompt_length": metadata.get("composed_prompt_length", 0),
                    "tool_count": metadata.get("tool_count", 0),
                    "provider": metadata.get("provider", "unknown"),
                    "model": model,  # Also store in observation metadata
                    "chapter_id": metadata.get("chapter_id"),
                    "stream": metadata.get("stream", False),
                    "chat_id": chat_id,  # Store original chat_id for reference
                }
            }

            # cost_details (v4 supports cost_details directly)
            cost_details = _get_cost_details(model, usage_details)
            if cost_details:
                obs_params["cost_details"] = cost_details

            # completion_start_time: when model started generating (supported in v4)
            if start_time is not None:
                from datetime import datetime, timezone
                obs_params["completion_start_time"] = datetime.fromtimestamp(start_time, tz=timezone.utc)

            if start_time and end_time:
                duration_ms = (end_time - start_time) * 1000
                log.info(f"[LANGFUSE TRACE] Timing: duration={duration_ms:.0f}ms, cost={cost_details}")

            # Create generation observation
            generation = self.langfuse.start_observation(**obs_params)

            log.debug(f"[LANGFUSE] Usage details: {usage_details}, user_id: {metadata.get('user_id')}")

            # End the observation
            generation.end()

            # Flush to ensure data is sent immediately
            self.langfuse.flush()

            log.debug(f"[LANGFUSE] Traced chat message: trace={langfuse_trace_id[:8]}... session={langfuse_session_id[:8]}... model={model}")
            return (generation, generation)  # Return generation object as trace for tool linking

        except Exception as e:
            log.error(f"[LANGFUSE] Failed to trace chat completion: {e}", exc_info=True)
            return (None, None)

    def trace_tool_call(
        self,
        trace_obj,  # Can be trace object or trace_id string
        tool_name: str,
        tool_input: Dict[str, Any],
        tool_output: Any,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Trace a tool/function call within an existing trace using Langfuse v3 API.

        Args:
            trace_obj: Trace object (from trace_chat_completion) or trace_id string
            tool_name: Name of the tool/function called
            tool_input: Tool input parameters
            tool_output: Tool execution result
            metadata: Additional metadata

        Returns:
            Tool observation object or None if tracing fails
        """
        try:
            # If trace_obj is a string (backward compatibility), use TraceContext
            if isinstance(trace_obj, str):
                from langfuse.types import TraceContext

                # Convert trace_id to valid Langfuse format
                langfuse_trace_id = trace_obj.replace("-", "").lower()[:32]

                # Create trace context for linking to parent trace
                trace_context = TraceContext(
                    trace_id=langfuse_trace_id,
                    session_id=langfuse_trace_id
                )

                # Create tool observation
                tool_obs = self.langfuse.start_observation(
                    trace_context=trace_context,
                    name=tool_name,
                    as_type="tool",
                    input=tool_input,
                    output=tool_output,
                    metadata=metadata or {}
                )
            else:
                # Use trace object directly (preferred method)
                tool_obs = trace_obj.span(
                    name=tool_name,
                    input=tool_input,
                    output=tool_output,
                    metadata=metadata or {}
                )

            # End the observation
            tool_obs.end()

            # Flush to send data
            self.langfuse.flush()

            log.debug(f"[LANGFUSE] Tool call traced: {tool_name}")
            return tool_obs
        except Exception as e:
            log.error(f"[LANGFUSE] Failed to trace tool call: {e}", exc_info=True)
            return None

    def _extract_response_text(self, response: Any) -> str:
        """
        Extract response text from different LLM provider response formats.

        Args:
            response: LLM response object

        Returns:
            Extracted text content
        """
        try:
            # OpenAI format
            if hasattr(response, 'choices') and len(response.choices) > 0:
                choice = response.choices[0]
                if hasattr(choice, 'message') and hasattr(choice.message, 'content'):
                    return choice.message.content
                elif hasattr(choice, 'text'):
                    return choice.text

            # Gemini format (google-genai)
            if hasattr(response, 'text'):
                return response.text

            # Fallback: convert to string
            return str(response)

        except Exception as e:
            log.warning(f"[LANGFUSE] Failed to extract response text: {e}")
            return str(response)

    def _extract_usage(self, response: Any) -> Dict[str, Any]:
        """
        Extract token usage from response.

        Args:
            response: LLM response object

        Returns:
            Dictionary with usage metadata
        """
        usage_metadata = {}

        try:
            # OpenAI format
            if hasattr(response, 'usage'):
                usage = response.usage
                if hasattr(usage, 'prompt_tokens'):
                    usage_metadata['prompt_tokens'] = usage.prompt_tokens
                if hasattr(usage, 'completion_tokens'):
                    usage_metadata['completion_tokens'] = usage.completion_tokens
                if hasattr(usage, 'total_tokens'):
                    usage_metadata['total_tokens'] = usage.total_tokens

            # Gemini format (google-genai SDK)
            elif hasattr(response, 'usage_metadata'):
                usage = response.usage_metadata
                if hasattr(usage, 'prompt_token_count'):
                    usage_metadata['prompt_tokens'] = usage.prompt_token_count
                if hasattr(usage, 'candidates_token_count'):
                    usage_metadata['completion_tokens'] = usage.candidates_token_count
                if hasattr(usage, 'total_token_count'):
                    usage_metadata['total_tokens'] = usage.total_token_count

            # If response is a dict (already converted)
            elif isinstance(response, dict) and 'usage' in response:
                usage = response['usage']
                usage_metadata['prompt_tokens'] = usage.get('prompt_tokens', 0)
                usage_metadata['completion_tokens'] = usage.get('completion_tokens', 0)
                usage_metadata['total_tokens'] = usage.get('total_tokens', 0)

        except Exception as e:
            log.warning(f"[LANGFUSE] Failed to extract usage: {e}")

        return usage_metadata


# Singleton instance
_tracer: Optional[LangfuseTracer] = None


def get_langfuse_tracer() -> Optional[LangfuseTracer]:
    """
    Get or create Langfuse tracer singleton.

    Returns:
        LangfuseTracer instance if configured, None otherwise
    """
    global _tracer
    if _tracer is None:
        try:
            from open_webui.integrations.langfuse_adapter import get_langfuse_adapter
            adapter = get_langfuse_adapter()
            if adapter:
                _tracer = LangfuseTracer(adapter.langfuse)
                log.info("[LANGFUSE] Tracer singleton created")
        except Exception as e:
            log.error(f"[LANGFUSE] Failed to initialize tracer: {e}", exc_info=True)

    return _tracer
