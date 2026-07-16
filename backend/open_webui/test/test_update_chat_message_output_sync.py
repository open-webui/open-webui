"""Regression tests for open-webui issue #26952.

Update Chat Message By Id (POST /api/v1/chats/{id}/messages/{message_id})
must keep the rendered chat state in sync. The UI renders
``message.output[].content[].text`` in preference to ``message.content`` (see
``getOutputText`` / ``ResponseMessage.svelte``), so a message that already
carries an ``output`` blob would otherwise keep rendering the stale original
text after a successful API update -- and reloading the chat would show the
old text as well.

These tests assert, via static AST analysis of the router, that the
``update_chat_message_by_id`` handler keeps the ``output`` blob in sync with
the updated ``content`` whenever the message has an ``output`` list. This is
the same guard style used by the rest of the suite (issue #27074).
"""

import ast
import pathlib

ROUTER_PATH = (
    pathlib.Path(__file__).resolve().parents[1] / "routers" / "chats.py"
)


def _load_tree():
    source = ROUTER_PATH.read_text(encoding="utf-8")
    return ast.parse(source)


def _func_named(tree: ast.AST, name: str) -> ast.AsyncFunctionDef | None:
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == name:
            return node
    return None


def _assigns_output_text(func: ast.AST) -> bool:
    """Return True if the function rewrites a 'message' output part's text."""
    for node in ast.walk(func):
        # Look for a literal dict key 'text' being assigned the new content.
        if isinstance(node, ast.Dict):
            for key in node.keys:
                if isinstance(key, ast.Constant) and key.value == "text":
                    return True
    return False


def _references_output(func: ast.AST) -> bool:
    for node in ast.walk(func):
        if isinstance(node, ast.Attribute) and node.attr == "output":
            return True
        if isinstance(node, ast.Constant) and node.value == "output":
            return True
    return False


def test_router_file_exists():
    assert ROUTER_PATH.is_file(), f"missing {ROUTER_PATH}"


def test_update_handler_syncs_output_text():
    """update_chat_message_by_id must keep output[].content[].text in sync.

    Guards against the #26952 regression where a successful API update left the
    rendered (and reloaded) UI showing the stale original text because only
    ``message.content`` was updated while the ``output`` blob kept the old text.
    """
    tree = _load_tree()
    handler = _func_named(tree, "update_chat_message_by_id")
    assert handler is not None, "update_chat_message_by_id handler not found"

    assert _references_output(handler), (
        "update_chat_message_by_id must reference the message 'output' field "
        "so the rendered/reloaded UI stays in sync (issue #26952)"
    )
    assert _assigns_output_text(handler), (
        "update_chat_message_by_id must rewrite the 'text' of message-type "
        "output parts to the updated content (issue #26952)"
    )
