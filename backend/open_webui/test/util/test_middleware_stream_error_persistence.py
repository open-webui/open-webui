"""Regression tests for streaming error persistence in middleware.

Covers open-webui issue #27074: raw JSON streaming error payloads must be
persisted to the assistant chat message. The raw-JSON fallback path created a
``Chats.upsert_message_to_chat_by_id_and_message_id(...)`` coroutine but never
awaited it, so the error was emitted to the client yet silently dropped from the
chat history (and emitted an un-awaited-coroutine RuntimeWarning).

These tests assert, via static AST analysis, that *every* call to
``upsert_message_to_chat_by_id_and_message_id`` inside ``middleware.py`` is
awaited -- an un-awaited coroutine for this DB write is always a bug.
"""

import ast
import pathlib

MIDDLEWARE_PATH = (
    pathlib.Path(__file__).resolve().parents[2] / "utils" / "middleware.py"
)

UPSERT_NAME = "upsert_message_to_chat_by_id_and_message_id"


def _upsert_calls(tree: ast.AST):
    """Yield every Call node invoking the upsert coroutine."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute) and func.attr == UPSERT_NAME:
                yield node


def _awaited_upsert_calls(tree: ast.AST):
    """Yield every Call node that is the direct child of an ``await``."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Await):
            value = node.value
            if (
                isinstance(value, ast.Call)
                and isinstance(value.func, ast.Attribute)
                and value.func.attr == UPSERT_NAME
            ):
                yield value


def _load_tree():
    source = MIDDLEWARE_PATH.read_text(encoding="utf-8")
    return ast.parse(source)


def test_middleware_file_exists():
    assert MIDDLEWARE_PATH.is_file(), f"missing {MIDDLEWARE_PATH}"


def test_all_upsert_calls_are_awaited():
    """upsert_message_to_chat_by_id_and_message_id is async -> must be awaited.

    Guards against the #27074 regression where the raw-JSON streaming error
    fallback built the coroutine but never awaited it, dropping the error from
    chat history.
    """
    tree = _load_tree()

    all_calls = list(_upsert_calls(tree))
    awaited_calls = {id(c) for c in _awaited_upsert_calls(tree)}

    assert all_calls, "expected upsert calls in middleware.py"

    unawaited = [
        c for c in all_calls if id(c) not in awaited_calls
    ]
    unawaited_lines = sorted(c.lineno for c in unawaited)
    assert not unawaited, (
        "un-awaited upsert_message_to_chat_by_id_and_message_id call(s) at "
        f"line(s) {unawaited_lines}; the raw-JSON streaming error fallback "
        "(issue #27074) must persist errors to chat history via `await`"
    )


def test_raw_json_error_fallback_persists_error():
    """The raw-JSON (no `data:` prefix) fallback must await the DB persistence.

    Locate the branch that reads `raw_error` from a plain-JSON line and confirm
    it contains an awaited upsert writing an `error` payload.
    """
    tree = _load_tree()

    awaited = list(_awaited_upsert_calls(tree))
    # At least one awaited upsert must carry an {'error': ...} payload dict,
    # matching the raw-JSON fallback persistence introduced by the fix.
    def has_error_payload(call: ast.Call) -> bool:
        for arg in call.args:
            if isinstance(arg, ast.Dict):
                for key in arg.keys:
                    if isinstance(key, ast.Constant) and key.value == "error":
                        return True
        return False

    assert any(has_error_payload(c) for c in awaited), (
        "expected an awaited upsert persisting an 'error' payload "
        "(raw-JSON streaming error fallback, issue #27074)"
    )
