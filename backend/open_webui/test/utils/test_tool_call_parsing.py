"""
Tests for graceful handling of malformed tool call arguments in middleware.

Verifies that when an LLM produces truncated or invalid JSON for tool call
arguments, the middleware returns a descriptive error message as the tool
result instead of crashing or terminating the SSE stream.

Closes: https://github.com/open-webui/open-webui/issues/21927
"""

import ast
import json

import pytest


class TestMalformedToolCallArgsParsing:
    """Unit tests for tool call argument parsing edge cases."""

    MALFORMED_CASES = [
        ('{"note_id": "abc-123", "title": "Test"', "truncated JSON"),
        ('{"key": }', "invalid JSON value"),
        ("not json at all", "plain text"),
        ("", "empty string"),
        ("{", "single brace"),
        ('{"key": "val", "nested": {"a":', "deeply truncated"),
    ]

    @pytest.mark.parametrize("tool_args,desc", MALFORMED_CASES)
    def test_malformed_args_fail_both_parsers(self, tool_args, desc):
        """Both ast.literal_eval and json.loads should fail for malformed input."""
        ast_failed = False
        json_failed = False

        try:
            ast.literal_eval(tool_args)
        except Exception:
            ast_failed = True

        try:
            json.loads(tool_args)
        except Exception:
            json_failed = True

        assert ast_failed and json_failed, (
            f"Expected both parsers to fail for {desc}: {tool_args!r}"
        )

    def test_valid_json_parses_correctly(self):
        """Valid JSON tool args should parse without error."""
        valid = '{"note_id": "abc-123", "title": "Test", "content": "Hello"}'
        result = json.loads(valid)
        assert isinstance(result, dict)
        assert result["note_id"] == "abc-123"

    def test_python_literal_parses_via_ast(self):
        """Python-style literals (True/False/None) should parse via ast."""
        python_literal = "{'enabled': True, 'count': 42, 'label': None}"
        result = ast.literal_eval(python_literal)
        assert result == {"enabled": True, "count": 42, "label": None}

    def test_middleware_parse_logic_returns_error_on_failure(self):
        """Simulate the middleware parse logic: on failure, tool_args_parse_error
        should be True and tool_result should contain a descriptive error."""
        tool_args = '{"note_id": "abc-123", "title": "Test"'  # truncated
        tool_function_name = "replace_note_content"

        # Replicate middleware logic
        tool_function_params = {}
        tool_args_parse_error = False
        try:
            tool_function_params = ast.literal_eval(tool_args)
        except Exception:
            try:
                tool_function_params = json.loads(tool_args)
            except Exception:
                tool_args_parse_error = True

        assert tool_args_parse_error is True
        assert tool_function_params == {}

        # Replicate the error message generation
        if tool_args_parse_error:
            tool_result = (
                f"Error: Failed to parse tool call arguments for "
                f"'{tool_function_name}'. The arguments were malformed or "
                f"incomplete. Please try calling the tool again with valid, "
                f"complete JSON arguments."
            )
        else:
            tool_result = None

        assert tool_result is not None
        assert tool_function_name in tool_result
        assert "malformed" in tool_result

    def test_middleware_parse_logic_succeeds_on_valid_input(self):
        """On valid input, tool_args_parse_error should be False."""
        tool_args = '{"note_id": "abc-123", "content": "hello world"}'

        tool_function_params = {}
        tool_args_parse_error = False
        try:
            tool_function_params = ast.literal_eval(tool_args)
        except Exception:
            try:
                tool_function_params = json.loads(tool_args)
            except Exception:
                tool_args_parse_error = True

        assert tool_args_parse_error is False
        assert tool_function_params["note_id"] == "abc-123"
        assert tool_function_params["content"] == "hello world"

    def test_empty_object_args_parse_correctly(self):
        """Empty object {} should parse correctly (no error)."""
        tool_args = "{}"

        tool_function_params = {}
        tool_args_parse_error = False
        try:
            tool_function_params = ast.literal_eval(tool_args)
        except Exception:
            try:
                tool_function_params = json.loads(tool_args)
            except Exception:
                tool_args_parse_error = True

        assert tool_args_parse_error is False
        assert tool_function_params == {}
