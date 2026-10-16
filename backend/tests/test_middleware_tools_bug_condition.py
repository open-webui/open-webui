"""
Bug Condition Exploration - Property-Based Test
==================================================
Property 1: Bug Condition - Tools Injected for Tool-Incapable Model Without User Selection

CRITICAL: This test MUST FAIL on unfixed code — failure confirms the bug exists.
DO NOT fix the test or the code when this test fails.

This test encodes the EXPECTED behaviour after the fix:
  - form_data MUST NOT contain a 'tools' key when:
      • the model has capabilities.tools = False  (no native tool calling)
      • the user has NOT selected any tools       (tool_ids=[], direct_tool_servers=[])

On UNFIXED code the test will fail because:
  use_builtin_tools evaluates to True (it checks only capabilities.builtin_tools,
  not capabilities.tools), so get_builtin_tools() injects builtin tools into
  form_data['tools'] even though the model cannot handle them.

Validates: Requirements 1.1, 1.2
"""

from __future__ import annotations

import asyncio
import copy
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from hypothesis import HealthCheck, given, note, settings
from hypothesis import strategies as st

# ---------------------------------------------------------------------------
# Import the ACTUAL process_chat_payload from the backend source.
# conftest.py has already injected all open_webui.* stubs into sys.modules
# and added backend/ to sys.path, so this import resolves to the real file.
# ---------------------------------------------------------------------------
from open_webui.utils.middleware import process_chat_payload  # noqa: E402


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# Model IDs matching the Ollama registry pattern used in the bug report
OLLAMA_MODEL_IDS = [
    "registry.ollama.ai/library/gemma3:12b",
    "registry.ollama.ai/library/gemma3:4b",
    "registry.ollama.ai/library/gemma3:27b",
    "registry.ollama.ai/library/llama3.2:3b",
    "registry.ollama.ai/library/phi4:latest",
    "registry.ollama.ai/library/mistral:7b",
    "registry.ollama.ai/library/deepseek-r1:8b",
    "gemma3:12b",           # short form also used in practice
    "llama3.2:3b",
    "phi4:latest",
]

ollama_model_id_st = st.one_of(
    st.sampled_from(OLLAMA_MODEL_IDS),
    st.from_regex(
        r"registry\.ollama\.ai/library/[a-z][a-z0-9]{1,15}:[0-9]+b",
        fullmatch=True,
    ),
)

session_id_st = st.text(
    alphabet=st.characters(
        whitelist_categories=["Lu", "Ll", "Nd"],
        whitelist_characters="-_",
    ),
    min_size=4,
    max_size=36,
)


def _build_tool_incapable_model(model_id: str) -> dict:
    """
    Build a model dict that has capabilities.tools = False.

    Mirrors what Open WebUI stores for an Ollama model whose template has no
    tool-calling support (e.g., gemma3:12b).

    NOTE: 'builtin_tools' is intentionally NOT set here.  The defaults for
    every builtin-tool sub-flag therefore resolve to True inside
    process_chat_payload — this is the exact gap that causes the bug.
    """
    return {
        "id": model_id,
        "name": model_id.split("/")[-1] if "/" in model_id else model_id,
        "owned_by": "ollama",
        "info": {
            "meta": {
                "capabilities": {
                    "tools": False,         # ← model does NOT support native tool calling
                    # 'builtin_tools' intentionally absent → defaults to True → BUG
                },
                "builtinTools": {
                    "skills": False,        # disable skills to simplify test (skip lazy imports)
                    "knowledge": False,     # disable knowledge injection to simplify test
                },
            }
        },
    }


def _build_metadata(session_id: str) -> dict:
    """
    Build a metadata dict that looks like a real UI-originated chat request.

    Key fields:
      - session_id: present → use_builtin_tools defaults to True (the bug trigger)
      - chat_id: '' → is_saved_chat_id() = False → skips DB loads
      - tool_ids: None → no user-selected tools
      - tool_servers: None → no direct tool servers
    """
    return {
        "session_id": session_id,
        "chat_id": "",            # temporary/unsaved chat
        "tool_ids": None,         # no user-selected tools
        "tool_servers": None,     # no direct tool servers
    }


def _build_form_data() -> dict:
    """Minimal chat payload with a single user message."""
    return {
        "messages": [{"role": "user", "content": "Hello, can you help me?"}],
        "model": "gemma3:12b",    # will be overridden by model fixture
    }


# ---------------------------------------------------------------------------
# Property-Based Test  —  Bug Condition Exploration
# ---------------------------------------------------------------------------

@given(
    model_id=ollama_model_id_st,
    session_id=session_id_st,
)
@settings(
    max_examples=30,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    deadline=None,
)
def test_no_tools_in_payload_for_tool_incapable_model_without_user_selection(
    model_id: str,
    session_id: str,
    mock_request,
    mock_user,
):
    """
    Property 1: Bug Condition

    GIVEN: A model where capabilities.tools = False
           (model lacks native tool-calling support — like gemma3:12b)
    AND:   No user-selected tools (tool_ids=None, tool_servers=None)
    AND:   A UI-originated request with a session_id (triggers builtin-tool injection)
    THEN:  process_chat_payload MUST NOT populate form_data['tools']

    On UNFIXED code this assertion FAILS:
      - use_builtin_tools evaluates to True (checks builtin_tools, not tools)
      - get_builtin_tools() returns non-empty builtin tools
      - tools_dict becomes non-empty
      - form_data['tools'] is populated with builtin tool specs
      - Ollama would reject the request with "model does not support tools"

    Validates: Requirements 1.1, 1.2
    """
    note(f"model_id={model_id!r}")
    note(f"session_id={session_id!r}")

    model = _build_tool_incapable_model(model_id)
    metadata = _build_metadata(session_id)
    form_data = _build_form_data()
    form_data["model"] = model_id

    # Run the async function synchronously for Hypothesis compatibility
    result_form_data, result_metadata, events, paused = asyncio.run(
        process_chat_payload(
            request=mock_request,
            form_data=form_data,
            user=mock_user,
            metadata=metadata,
            model=model,
        )
    )

    # -----------------------------------------------------------------------
    # ASSERTION: The bug condition — form_data must NOT contain 'tools'
    # -----------------------------------------------------------------------
    # On unfixed code this FAILS (confirming the bug):
    #   form_data['tools'] is non-empty because use_builtin_tools = True
    #   caused get_builtin_tools() to inject web_search, generate_image, etc.
    # -----------------------------------------------------------------------
    assert "tools" not in result_form_data, (
        f"\n\n*** BUG CONFIRMED ***\n"
        f"model_id={model_id!r} has capabilities.tools=False and no user tools\n"
        f"were selected, but form_data['tools'] was populated:\n"
        f"  {result_form_data.get('tools')}\n\n"
        f"Root cause: use_builtin_tools evaluated to True because it checks\n"
        f"  capabilities.builtin_tools (unset → True)\n"
        f"instead of capabilities.tools (= False).\n"
        f"Fix: add `and model_supports_tools` to the use_builtin_tools condition."
    )


# ---------------------------------------------------------------------------
# Focused concrete test (non-property) — the exact scenario from the bug report
# ---------------------------------------------------------------------------

def test_gemma3_12b_no_tools_in_payload(mock_request, mock_user):
    """
    Concrete scenario from the bug report:
      User opens a new chat with registry.ollama.ai/library/gemma3:12b.
      No tools are activated in the UI.
      Expected: chat completes normally, no 'tools' key in payload.

    This test FAILS on unfixed code.
    Validates: Requirements 1.1
    """
    model_id = "registry.ollama.ai/library/gemma3:12b"
    model = _build_tool_incapable_model(model_id)
    metadata = _build_metadata(session_id="ui-session-gemma3-abc123")
    form_data = _build_form_data()
    form_data["model"] = model_id

    result_form_data, _metadata, _events, _paused = asyncio.run(
        process_chat_payload(
            request=mock_request,
            form_data=form_data,
            user=mock_user,
            metadata=metadata,
            model=model,
        )
    )

    tools_in_payload = result_form_data.get("tools")
    assert "tools" not in result_form_data, (
        f"\n\n*** BUG CONFIRMED (gemma3:12b scenario) ***\n"
        f"form_data['tools'] = {tools_in_payload}\n\n"
        f"use_builtin_tools was True because capabilities.tools=False is NOT\n"
        f"checked by the use_builtin_tools condition in process_chat_payload.\n"
        f"Ollama would reject this request with:\n"
        f"  'registry.ollama.ai/library/gemma3:12b does not support tools'\n"
    )


def test_second_message_also_triggers_bug(mock_request, mock_user):
    """
    Requirement 1.2: The bug fires on EVERY message, not just the first.
    This mirrors sending a second message in the same chat.

    This test FAILS on unfixed code.
    Validates: Requirements 1.2
    """
    model_id = "registry.ollama.ai/library/gemma3:12b"
    model = _build_tool_incapable_model(model_id)
    metadata = _build_metadata(session_id="ui-session-gemma3-second-msg")
    form_data = {
        "messages": [
            {"role": "user", "content": "What is the capital of France?"},
            {"role": "assistant", "content": "Paris."},
            {"role": "user", "content": "And Germany?"},  # second message
        ],
        "model": model_id,
    }

    result_form_data, _metadata, _events, _paused = asyncio.run(
        process_chat_payload(
            request=mock_request,
            form_data=form_data,
            user=mock_user,
            metadata=metadata,
            model=model,
        )
    )

    assert "tools" not in result_form_data, (
        f"\n\n*** BUG CONFIRMED (second message) ***\n"
        f"On the second message, form_data['tools'] is still populated: "
        f"{result_form_data.get('tools')}\n"
        f"The bug fires on every interaction, not just the first message.\n"
    )
