"""
Regression tests for open-webui/open-webui#27074.

Issue: when an upstream provider streams a raw JSON error payload *without*
the SSE `data:` prefix, the streaming handler parses it and attempts to
persist it to the assistant chat message via
``Chats.upsert_message_to_chat_by_id_and_message_id``. That call is async, but
the fallback path created the coroutine without ``await`` -- so the upsert was
never executed. The error was emitted to the client but was NOT persisted to
the chat history, leaving the assistant message without an error record.

These tests guard against the regression by statically verifying that every
``Chats.upsert_message_to_chat_by_id_and_message_id`` call site in
``backend/open_webui/utils/middleware.py`` is actually awaited, and that the
raw-JSON error fallback specifically persists the error to the DB.
"""

import ast
from pathlib import Path

MIDDLEWARE_PATH = (
    Path(__file__).resolve().parents[2] / "utils" / "middleware.py"
)
UPSERT_NAME = "upsert_message_to_chat_by_id_and_message_id"


def _load_tree():
    assert MIDDLEWARE_PATH.exists(), (
        f"Expected middleware source at {MIDDLEWARE_PATH}"
    )
    return ast.parse(MIDDLEWARE_PATH.read_text(encoding="utf-8"))


def test_middleware_file_exists():
    assert MIDDLEWARE_PATH.exists(), (
        f"middleware.py not found at {MIDDLEWARE_PATH}"
    )


def _unawaited_upsert_calls(tree):
    """Return a list of (lineno) for any upsert call that is NOT awaited.

    A Call like ``Chats.upsert_message_to_chat_by_id_and_message_id(...)`` is
    considered awaited only when its immediate parent in the AST is an
    ``ast.Await`` node.  We map every node to its parent so we can inspect the
    parent of each candidate Call.
    """
    parent_of = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            parent_of[child] = node

    bad = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if (
            isinstance(func, ast.Attribute)
            and func.attr == UPSERT_NAME
            and isinstance(func.value, ast.Name)
            and func.value.id == "Chats"
        ):
            if not isinstance(parent_of.get(node), ast.Await):
                bad.append(node.lineno)
    return bad


def test_all_upsert_calls_are_awaited():
    tree = _load_tree()
    bad = _unawaited_upsert_calls(tree)
    assert not bad, (
        f"Found async upsert calls that are NOT awaited "
        f"(missing `await Chats.{UPSERT_NAME}(...)`) at line(s): {bad}. "
        f"These create coroutines that are never executed, so the error "
        f"payload is dropped and never persisted to chat history."
    )


def test_raw_json_error_fallback_persists_error():
    """
    The raw-JSON streaming error fallback (a JSON line streamed without the
    `data:` SSE prefix that carries an `error` key) must persist that error to
    the assistant message via an awaited upsert, mirroring the normal streaming
    error path. Confirm the fallback block awaits the upsert.
    """
    tree = _load_tree()
    source = MIDDLEWARE_PATH.read_text(encoding="utf-8")

    # Locate the raw-JSON fallback block: it parses a non-`data:` line as JSON
    # and reads `error` from it.
    fallback_block = None
    for node in ast.walk(tree):
        if isinstance(node, ast.If):
            snippet = ast.get_source_segment(source, node) or ""
            if "raw_obj" in snippet and "error" in snippet and "json.loads" in snippet:
                fallback_block = snippet
                break

    assert fallback_block is not None, (
        "Could not locate the raw-JSON streaming error fallback block in "
        "middleware.py. The persistence path for #27074 may have moved."
    )

    # The fallback must perform an awaited upsert that writes
    # {'error': {'content': ...}} to the chat message.
    assert "await Chats.upsert_message_to_chat_by_id_and_message_id" in fallback_block, (
        "The raw-JSON error fallback does not AWAIT the upsert that persists "
        "the error to chat history. The coroutine will be dropped (open-webui#27074)."
    )
    assert "'error': {'content': raw_error}" in fallback_block, (
        "The raw-JSON error fallback does not persist the parsed raw error "
        "payload to the assistant message."
    )
