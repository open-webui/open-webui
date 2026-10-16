"""
Preservation Property Tests
============================
Property 2: Preservation - Tool-Capable Models and Explicitly Selected Tools Unaffected

These tests MUST PASS on UNFIXED code.  They capture the *baseline behaviour* that the
fix must not break:

  a) Tool-capable model + no user tools   → builtin tools ARE injected  (web_search, generate_image)
  b) Tool-capable model + user tools       → both user AND builtin tools present
  c) Tool-incapable model + user tool_ids  → form_data['tools'] still populated (warning path)
  d) Model with no capabilities key         → treated as tool-capable (defaults to True)

Implementation notes (observed from middleware.py):
  - tool_ids must be in form_data (not metadata); line 2406 does form_data.pop('tool_ids', None)
    and the result is stored into metadata via metadata.update({..., 'tool_ids': tool_ids, ...})
    at ~line 2625, then re-read from metadata inside the if-payload_tools-is-None block.
  - mock_request.app.state.MODELS must contain the model when user-selected tools are active,
    because get_tools receives models[task_model_id] as __model__ in extra_params.

Validates: Requirements 3.1, 3.2, 3.3
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from hypothesis import HealthCheck, given, note, settings
from hypothesis import strategies as st

from open_webui.utils.middleware import process_chat_payload  # noqa: E402


# ---------------------------------------------------------------------------
# Shared constants
# ---------------------------------------------------------------------------

BUILTIN_TOOL_NAMES = {"web_search", "generate_image"}

# A fake user-selected tool returned when get_tools is patched
_FAKE_USER_TOOL_ID = "test_user_tool"
_FAKE_USER_TOOLS_DICT = {
    "test_calculator": {
        "spec": {
            "name": "test_calculator",
            "description": "A simple calculator tool for testing",
            "parameters": {
                "type": "object",
                "properties": {"expression": {"type": "string", "description": "Math expression"}},
                "required": ["expression"],
            },
        },
        "type": "function",
        "tool_id": _FAKE_USER_TOOL_ID,
    }
}


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

session_id_st = st.text(
    alphabet=st.characters(
        whitelist_categories=["Lu", "Ll", "Nd"],
        whitelist_characters="-_",
    ),
    min_size=4,
    max_size=36,
)

tool_capable_model_id_st = st.one_of(
    st.sampled_from([
        "gpt-4o",
        "gpt-4o-mini",
        "claude-3-5-sonnet",
        "llama3.1:70b",
        "mistral-large:latest",
        "registry.ollama.ai/library/llama3.1:8b",
        "qwen2.5:72b",
    ]),
    st.from_regex(r"[a-z][a-z0-9]{1,15}:[a-z0-9]{1,8}", fullmatch=True),
)

tool_incapable_model_id_st = st.sampled_from([
    "registry.ollama.ai/library/gemma3:12b",
    "registry.ollama.ai/library/gemma3:4b",
    "registry.ollama.ai/library/gemma3:27b",
    "registry.ollama.ai/library/phi4:latest",
    "gemma3:12b",
    "phi4:latest",
])


# ---------------------------------------------------------------------------
# Model / metadata / form_data builders
# ---------------------------------------------------------------------------

def _build_tool_capable_model(model_id: str) -> dict:
    """Model with capabilities.tools = True (explicit)."""
    return {
        "id": model_id,
        "name": model_id,
        "owned_by": "openai",
        "info": {
            "meta": {
                "capabilities": {
                    "tools": True,
                    # builtin_tools not set → defaults to True → use_builtin_tools = True
                },
                "builtinTools": {
                    "skills": False,    # keep skills path simple in tests
                    "knowledge": False,
                },
            }
        },
    }


def _build_tool_capable_model_no_capabilities_key(model_id: str) -> dict:
    """Model with NO capabilities key at all — must default to tool-capable."""
    return {
        "id": model_id,
        "name": model_id,
        "owned_by": "ollama",
        "info": {
            "meta": {
                # no 'capabilities' key → tools defaults to True
                "builtinTools": {
                    "skills": False,
                    "knowledge": False,
                },
            }
        },
    }


def _build_tool_incapable_model(model_id: str) -> dict:
    """Model with capabilities.tools = False."""
    return {
        "id": model_id,
        "name": model_id,
        "owned_by": "ollama",
        "info": {
            "meta": {
                "capabilities": {
                    "tools": False,
                    # builtin_tools NOT set → defaults True → use_builtin_tools stays True on unfixed code
                },
                "builtinTools": {
                    "skills": False,
                    "knowledge": False,
                },
            }
        },
    }


def _build_metadata(session_id: str) -> dict:
    """Build metadata for a UI-originated request (no tool_ids here; pass them in form_data)."""
    return {
        "session_id": session_id,
        "chat_id": "",          # temporary chat — skips DB loads
        "tool_ids": None,       # tool_ids come from form_data, not metadata directly
        "tool_servers": None,   # no direct tool servers
    }


def _build_form_data(model_id: str, tool_ids: list | None = None) -> dict:
    """
    Minimal chat payload.

    IMPORTANT: tool_ids must be in form_data — process_chat_payload pops them via
    `form_data.pop('tool_ids', None)` at line ~2406 and stores the result into
    metadata.  Passing them only in metadata would be overwritten to None.
    """
    fd: dict = {
        "messages": [{"role": "user", "content": "Hello, what can you do?"}],
        "model": model_id,
    }
    if tool_ids is not None:
        fd["tool_ids"] = tool_ids
    return fd


def _make_request_with_model(model: dict) -> MagicMock:
    """
    Build a mock request whose MODELS registry contains the given model.

    get_tools receives models[task_model_id] as __model__ in extra_params,
    so MODELS must contain the model when tool_ids are present.
    """
    state = MagicMock()
    state.direct = False
    state.internal = False
    request = MagicMock()
    request.state = state
    request.app.state.MODELS = {model["id"]: model}
    request.app.state.config = MagicMock()
    return request


def _tool_names_in_payload(form_data: dict) -> set[str]:
    """Extract tool names from form_data['tools']."""
    tools_list = form_data.get("tools", [])
    return {entry["function"]["name"] for entry in tools_list if "function" in entry}


# ---------------------------------------------------------------------------
# Property 2a  —  Tool-Capable Model, No User Tools  →  Builtins ARE Injected
# ---------------------------------------------------------------------------

@given(
    model_id=tool_capable_model_id_st,
    session_id=session_id_st,
)
@settings(
    max_examples=25,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    deadline=None,
)
def test_builtin_tools_injected_for_tool_capable_model_no_user_tools(
    model_id: str,
    session_id: str,
    mock_request,
    mock_user,
):
    """
    Property 2a: Preservation - Builtin Tools Injected for Tool-Capable Models

    GIVEN: A model where capabilities.tools = True
    AND:   No user-selected tools (no tool_ids in form_data)
    AND:   A UI-originated request with a session_id
    THEN:  form_data['tools'] MUST be non-empty after process_chat_payload
           (web_search and generate_image are present)

    This PASSES on unfixed code, capturing the baseline the fix must preserve.
    Validates: Requirements 3.2, 3.3
    """
    note(f"model_id={model_id!r}")
    note(f"session_id={session_id!r}")

    model = _build_tool_capable_model(model_id)
    metadata = _build_metadata(session_id)
    form_data = _build_form_data(model_id)  # no tool_ids

    result_form_data, _, _, _ = asyncio.run(
        process_chat_payload(
            request=mock_request,
            form_data=form_data,
            user=mock_user,
            metadata=metadata,
            model=model,
        )
    )

    tool_names = _tool_names_in_payload(result_form_data)
    assert "tools" in result_form_data, (
        f"model_id={model_id!r}: expected builtin tools in form_data['tools'] "
        f"but the key is absent"
    )
    assert tool_names >= BUILTIN_TOOL_NAMES, (
        f"model_id={model_id!r}: expected at least {BUILTIN_TOOL_NAMES} in tools "
        f"but got {tool_names}"
    )


# ---------------------------------------------------------------------------
# Property 2a-variant  —  No Capabilities Key Defaults to Tool-Capable
# ---------------------------------------------------------------------------

@given(
    model_id=tool_capable_model_id_st,
    session_id=session_id_st,
)
@settings(
    max_examples=25,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    deadline=None,
)
def test_builtin_tools_injected_when_no_capabilities_key(
    model_id: str,
    session_id: str,
    mock_request,
    mock_user,
):
    """
    Property 2a-variant: When a model has NO capabilities key at all,
    it defaults to tool-capable behavior: builtin tools ARE injected.

    This PASSES on unfixed code.
    Validates: Requirements 3.2, 3.3
    """
    note(f"model_id={model_id!r}")
    note(f"session_id={session_id!r}")

    model = _build_tool_capable_model_no_capabilities_key(model_id)
    metadata = _build_metadata(session_id)
    form_data = _build_form_data(model_id)

    result_form_data, _, _, _ = asyncio.run(
        process_chat_payload(
            request=mock_request,
            form_data=form_data,
            user=mock_user,
            metadata=metadata,
            model=model,
        )
    )

    tool_names = _tool_names_in_payload(result_form_data)
    assert "tools" in result_form_data, (
        f"model_id={model_id!r} (no capabilities key): expected tool injection "
        f"to default to True but form_data['tools'] is absent"
    )
    assert tool_names >= BUILTIN_TOOL_NAMES, (
        f"model_id={model_id!r}: expected at least {BUILTIN_TOOL_NAMES} "
        f"but got {tool_names}"
    )


# ---------------------------------------------------------------------------
# Property 2b  —  Tool-Capable Model + User Tools  →  Both Present
# ---------------------------------------------------------------------------

@given(
    model_id=tool_capable_model_id_st,
    session_id=session_id_st,
)
@settings(
    max_examples=25,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    deadline=None,
)
def test_both_user_and_builtin_tools_for_tool_capable_model_with_user_selection(
    model_id: str,
    session_id: str,
    mock_user,
):
    """
    Property 2b: Preservation - User + Builtin Tools for Tool-Capable Models

    GIVEN: A model where capabilities.tools = True
    AND:   User has selected tools (tool_ids in form_data)
    AND:   A UI-originated request with a session_id
    THEN:  form_data['tools'] contains BOTH user-selected tools AND builtin tools

    This PASSES on unfixed code.
    Validates: Requirements 3.2
    """
    note(f"model_id={model_id!r}")
    note(f"session_id={session_id!r}")

    model = _build_tool_capable_model(model_id)
    # MODELS must contain the model so get_tools receives models[task_model_id]
    request = _make_request_with_model(model)
    metadata = _build_metadata(session_id)
    # Pass tool_ids in form_data (not metadata) — middleware pops them from there
    form_data = _build_form_data(model_id, tool_ids=[_FAKE_USER_TOOL_ID])

    with patch("open_webui.utils.middleware.get_tools", new=AsyncMock(return_value=_FAKE_USER_TOOLS_DICT)):
        result_form_data, _, _, _ = asyncio.run(
            process_chat_payload(
                request=request,
                form_data=form_data,
                user=mock_user,
                metadata=metadata,
                model=model,
            )
        )

    tool_names = _tool_names_in_payload(result_form_data)
    user_tool_names = set(_FAKE_USER_TOOLS_DICT.keys())

    assert "tools" in result_form_data, (
        f"model_id={model_id!r}: expected tools in form_data but the key is absent"
    )
    assert tool_names >= BUILTIN_TOOL_NAMES, (
        f"model_id={model_id!r}: builtin tools missing — got {tool_names}, "
        f"expected at least {BUILTIN_TOOL_NAMES}"
    )
    assert tool_names >= user_tool_names, (
        f"model_id={model_id!r}: user tools missing — got {tool_names}, "
        f"expected at least {user_tool_names}"
    )


# ---------------------------------------------------------------------------
# Property 2c  —  Tool-Incapable Model + Explicit User Tools  →  Populated
# ---------------------------------------------------------------------------

@given(
    model_id=tool_incapable_model_id_st,
    session_id=session_id_st,
)
@settings(
    max_examples=20,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    deadline=None,
)
def test_tool_incapable_model_with_explicit_user_tools_gets_populated_payload(
    model_id: str,
    session_id: str,
    mock_user,
):
    """
    Property 2c: Preservation - Warning Path Intact for Tool-Incapable + User Tools

    GIVEN: A model where capabilities.tools = False
    AND:   User has EXPLICITLY selected tools (tool_ids in form_data)
    AND:   A UI-originated request with a session_id
    THEN:  form_data['tools'] IS non-empty
           (the user deliberately activated tools; the backend error / warning
           path is preserved — we must NOT silently suppress user intent)

    This PASSES on unfixed code (the warning path must survive the fix too).
    Validates: Requirements 3.1
    """
    note(f"model_id={model_id!r}")
    note(f"session_id={session_id!r}")

    model = _build_tool_incapable_model(model_id)
    request = _make_request_with_model(model)
    metadata = _build_metadata(session_id)
    form_data = _build_form_data(model_id, tool_ids=[_FAKE_USER_TOOL_ID])

    with patch("open_webui.utils.middleware.get_tools", new=AsyncMock(return_value=_FAKE_USER_TOOLS_DICT)):
        result_form_data, _, _, _ = asyncio.run(
            process_chat_payload(
                request=request,
                form_data=form_data,
                user=mock_user,
                metadata=metadata,
                model=model,
            )
        )

    tool_names = _tool_names_in_payload(result_form_data)
    user_tool_names = set(_FAKE_USER_TOOLS_DICT.keys())

    assert "tools" in result_form_data, (
        f"\n\n*** PRESERVATION VIOLATION ***\n"
        f"model_id={model_id!r} has capabilities.tools=False, but the user explicitly\n"
        f"selected tools. form_data['tools'] must still be populated so the backend\n"
        f"can raise its tools-unsupported warning.\n"
        f"Got form_data keys: {list(result_form_data.keys())}"
    )
    assert tool_names >= user_tool_names, (
        f"model_id={model_id!r}: user-selected tools {user_tool_names} are absent "
        f"from form_data['tools']. Got: {tool_names}"
    )


# ---------------------------------------------------------------------------
# Concrete unit tests (non-property)
# ---------------------------------------------------------------------------

def test_tool_capable_model_gets_builtin_tools_concrete(mock_request, mock_user):
    """
    Concrete: gpt-4o with no user tools gets builtin tools injected.
    Validates: Requirements 3.2, 3.3
    """
    model_id = "gpt-4o"
    model = _build_tool_capable_model(model_id)
    metadata = _build_metadata(session_id="ui-session-gpt4o-abc123")
    form_data = _build_form_data(model_id)

    result_form_data, _, _, _ = asyncio.run(
        process_chat_payload(
            request=mock_request,
            form_data=form_data,
            user=mock_user,
            metadata=metadata,
            model=model,
        )
    )

    tool_names = _tool_names_in_payload(result_form_data)
    assert "tools" in result_form_data, "Expected builtin tools for tool-capable model"
    assert "web_search" in tool_names, "web_search builtin should be present"
    assert "generate_image" in tool_names, "generate_image builtin should be present"


def test_no_capabilities_model_gets_builtin_tools_concrete(mock_request, mock_user):
    """
    Concrete: A model with no capabilities key at all defaults to tool-capable.
    Validates: Requirements 3.3
    """
    model_id = "some-unknown-model:latest"
    model = _build_tool_capable_model_no_capabilities_key(model_id)
    metadata = _build_metadata(session_id="ui-session-unknown-model")
    form_data = _build_form_data(model_id)

    result_form_data, _, _, _ = asyncio.run(
        process_chat_payload(
            request=mock_request,
            form_data=form_data,
            user=mock_user,
            metadata=metadata,
            model=model,
        )
    )

    tool_names = _tool_names_in_payload(result_form_data)
    assert "tools" in result_form_data, (
        "Model with no capabilities key should default to tool-capable; "
        "expected form_data['tools'] to be populated"
    )
    assert tool_names >= BUILTIN_TOOL_NAMES


def test_tool_capable_model_user_tool_and_builtins_concrete(mock_user):
    """
    Concrete: llama3.1:70b with one user-selected tool gets both user + builtin tools.
    Validates: Requirements 3.2
    """
    model_id = "llama3.1:70b"
    model = _build_tool_capable_model(model_id)
    request = _make_request_with_model(model)
    metadata = _build_metadata(session_id="ui-session-llama-tools")
    form_data = _build_form_data(model_id, tool_ids=[_FAKE_USER_TOOL_ID])

    with patch("open_webui.utils.middleware.get_tools", new=AsyncMock(return_value=_FAKE_USER_TOOLS_DICT)):
        result_form_data, _, _, _ = asyncio.run(
            process_chat_payload(
                request=request,
                form_data=form_data,
                user=mock_user,
                metadata=metadata,
                model=model,
            )
        )

    tool_names = _tool_names_in_payload(result_form_data)
    assert "tools" in result_form_data, "Expected tools in payload"
    assert "test_calculator" in tool_names, "User-selected tool must be present"
    assert "web_search" in tool_names, "Builtin web_search must still be present"
    assert "generate_image" in tool_names, "Builtin generate_image must still be present"


def test_tool_incapable_model_explicit_user_tools_preserved_concrete(mock_user):
    """
    Concrete: gemma3:12b with explicit user tool selection → form_data['tools'] populated.
    The backend will then raise the tools-unsupported error, which is the expected warning path.
    Validates: Requirements 3.1
    """
    model_id = "registry.ollama.ai/library/gemma3:12b"
    model = _build_tool_incapable_model(model_id)
    request = _make_request_with_model(model)
    metadata = _build_metadata(session_id="ui-session-gemma3-with-tool")
    form_data = _build_form_data(model_id, tool_ids=[_FAKE_USER_TOOL_ID])

    with patch("open_webui.utils.middleware.get_tools", new=AsyncMock(return_value=_FAKE_USER_TOOLS_DICT)):
        result_form_data, _, _, _ = asyncio.run(
            process_chat_payload(
                request=request,
                form_data=form_data,
                user=mock_user,
                metadata=metadata,
                model=model,
            )
        )

    tool_names = _tool_names_in_payload(result_form_data)
    assert "tools" in result_form_data, (
        "gemma3:12b with explicit user tool selection: form_data['tools'] must be "
        "populated so the model backend surfaces the tools-unsupported warning"
    )
    assert "test_calculator" in tool_names, (
        "User-explicitly-selected tool must be present even for tool-incapable models"
    )
