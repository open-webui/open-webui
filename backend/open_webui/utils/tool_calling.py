"""Tool-call parsing, validation, and repetition checks.

Pure helpers for complete argument parsing, schema normalization, explicit tool
markup, and repetition checks. Callers own execution, history, and persistence.
"""

import ast
import copy
import json
import math
import re
from uuid import uuid4

FINAL_ANSWER_PROMPT = (
    'Tool use has stopped for this response. Use the results already available to answer the user. '
    'Explain any unfinished work briefly. Do not request or describe additional tool calls.'
)
INCOMPLETE_CALL_ERROR = (
    'Error: the model response was incomplete; its tool calls were not executed. Retry a complete call.'
)


def add_tool_call_metadata(tools, *, labels=False, approval=False, language='English'):
    """Extend request-local schemas; markers identify metadata owned by the application."""
    for name, tool in list(tools.items()):
        spec = tool.get('spec') or {}
        schema = spec.get('parameters') or {}
        if (
            tool.get('tool_id') == 'builtin:call_tool'
            or schema.get('type', 'object') != 'object'
            or any(key in schema for key in ('$ref', 'oneOf', 'anyOf', 'allOf', 'if'))
        ):
            continue
        properties = schema.get('properties', {})
        injected, markers = {}, {}
        if labels and not tool.get('hidden') and not tool.get('display_labels') and '__labels__' not in properties:
            injected['__labels__'] = {
                'type': 'object',
                'description': (
                    f'Short UI labels in {language}. Describe the action and its subject, not technical tool names. '
                    'Use at most 8 words and 120 characters each, without a trailing period. '
                    'The completed label describes the action taken, not an unverified outcome.'
                ),
                'properties': {
                    'running': {'type': 'string', 'description': 'While running, e.g. "Searching for flights".'},
                    'completed': {'type': 'string', 'description': 'After success, e.g. "Searched for flights".'},
                },
                'required': ['running', 'completed'],
                'additionalProperties': False,
            }
            markers['display_labels'] = True
        if (
            approval
            and not tool.get('approval_review')
            and '__approval__' not in properties
            and tool.get('tool_id') != 'builtin:search_tools'
            and not (name == 'ask_user' and tool.get('type') == 'builtin')
        ):
            injected['__approval__'] = {
                'type': 'object',
                'properties': {
                    'required': {
                        'type': 'boolean',
                        'description': 'Whether this call needs human approval under the approval policy. '
                        'When uncertain, use true.',
                    },
                },
                'required': ['required'],
                'additionalProperties': False,
            }
            markers['approval_review'] = True
        if injected:
            tools[name] = {
                **tool,
                **markers,
                'spec': {
                    **spec,
                    'parameters': {
                        **schema,
                        'type': 'object',
                        'properties': {**injected, **properties},
                        'required': [*injected, *schema.get('required', [])],
                    },
                },
            }


_TOOL_APPROVAL_PROMPT_RE = re.compile(r'\n?<tool_approval_policy>\n.*?</tool_approval_policy>', re.DOTALL)


def strip_tool_approval_prompt(prompt):
    """Remove request-specific approval instructions before rebuilding or reusing a prompt."""
    return _TOOL_APPROVAL_PROMPT_RE.sub('', prompt) if prompt else prompt


def set_tool_call_visibility(item, tools):
    """Copy trusted tool visibility metadata onto display output, without changing execution."""
    if item.get('type') == 'function_call' and tools.get(item.get('name'), {}).get('hidden') is True:
        item['hidden'] = True


def parse_arguments(raw):
    """Accept complete JSON or JSON-compatible Python literals, never invent missing values."""
    if isinstance(raw, str):
        text = raw.strip()
        fence = re.fullmatch(r'```(?:json)?\s*\n(.*?)\n```', text, re.DOTALL)
        if fence:
            text = fence[1]
        try:
            raw = json.loads(text or '{}')
        except (ValueError, RecursionError):
            try:
                # Literal recovery is bounded independently of valid JSON/code arguments.
                if len(text) > 65_536:
                    raise ValueError('Arguments are too large for literal recovery.')
                raw = ast.literal_eval(text)
            except (ValueError, SyntaxError, RecursionError, MemoryError) as exc:
                raise ValueError('Tool arguments must be a complete JSON object.') from exc
        if isinstance(raw, str):
            # Some providers encode the entire argument object twice. Unwrap only one extra layer.
            try:
                raw = json.loads(raw)
            except (ValueError, RecursionError) as exc:
                raise ValueError('Tool arguments must be a complete JSON object.') from exc
    if not isinstance(raw, dict):
        raise ValueError('Tool arguments must be a JSON object.')
    _check_json_value(raw)
    return raw


def _check_json_value(value, depth=0):
    if depth > 32:
        raise ValueError('Tool arguments are nested too deeply.')
    if isinstance(value, dict):
        for key, child in value.items():
            if not isinstance(key, str):
                raise ValueError('Tool argument keys must be strings.')
            _check_json_value(child, depth + 1)
    elif isinstance(value, list):
        for child in value:
            _check_json_value(child, depth + 1)
    elif isinstance(value, float) and not math.isfinite(value):
        raise ValueError('Tool arguments must contain finite numbers.')
    elif value is not None and not isinstance(value, (str, int, float, bool)):
        raise ValueError('Tool arguments must contain JSON values only.')


def _coerce_scalar(value, kind):
    if kind == 'string' and isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(value)
    if not isinstance(value, str):
        return value
    text = value.strip()
    if kind == 'boolean' and text.lower() in {'true', 'false'}:
        return text.lower() == 'true'
    if kind not in {'integer', 'number', 'object', 'array'}:
        return value
    try:
        parsed = json.loads(text)
    except (ValueError, RecursionError):
        return value
    if kind in {'object', 'array'}:
        return parsed if isinstance(parsed, dict if kind == 'object' else list) else value
    if type(parsed) is int or (kind == 'number' and type(parsed) is float and math.isfinite(parsed)):
        return parsed
    return value


def _coerce(value, schema, depth=0):
    if not isinstance(schema, dict) or depth > 32:
        return value
    # Ambiguous unions/references must be validated without guessing which branch was intended.
    if any(key in schema for key in ('$ref', 'oneOf', 'anyOf', 'allOf', 'if')):
        return value
    kind = schema.get('type')
    if isinstance(kind, list):
        kinds = [item for item in kind if item != 'null']
        kind = kinds[0] if len(kinds) == 1 else None
    value = _coerce_scalar(value, kind)
    if isinstance(value, dict):
        properties = schema.get('properties', {})
        return {key: _coerce(child, properties.get(key, {}), depth + 1) for key, child in value.items()}
    if isinstance(value, list) and isinstance(schema.get('items'), dict):
        return [_coerce(child, schema['items'], depth + 1) for child in value]
    return value


def normalize_arguments(raw, schema=None):
    params = parse_arguments(raw)
    if schema is not None:
        # Provider schemas strip nullability; use them for coercion, leaving validation to the tool.
        params = _coerce(params, schema)
    _check_json_value(params)
    return params


def split_tool_calls(calls):
    """Split complete concatenated objects, preserving each requested call."""
    expanded = []
    decoder = json.JSONDecoder()
    for call in calls:
        call = copy.deepcopy(call)
        function = call.setdefault('function', {})
        raw = function.get('arguments')
        raw = raw if isinstance(raw, str) else json.dumps(raw) if raw is not None else ''
        function['arguments'] = raw
        objects, position = [], 0
        try:
            while position < len(raw):
                if raw[position].isspace():
                    position += 1
                    continue
                value, position = decoder.raw_decode(raw, position)
                if not isinstance(value, dict):
                    raise ValueError('Expected an object')
                objects.append(value)
        except (ValueError, RecursionError):
            objects = []
        if len(objects) <= 1:
            expanded.append(call)
            continue
        for index, value in enumerate(objects):
            cloned = copy.deepcopy(call)
            if index:
                cloned['id'] = f'call_{uuid4().hex[:24]}'
            cloned['function']['arguments'] = json.dumps(value, ensure_ascii=False)
            expanded.append(cloned)
    return expanded


_CALL_BLOCK = re.compile(r'<tool_call>(.*?)</tool_call>|<function=([\w.\-]+)>(.*?)</function>', re.DOTALL)
_PARAMETER = re.compile(r'<parameter=([\w.\-]+)>(.*?)</parameter>', re.DOTALL)


def recover_tool_calls(text, allowed_names):
    """Recover a message consisting ONLY of complete call wrappers; examples and prose stay text."""
    if not isinstance(text, str) or len(text) > 65_536:
        return []
    calls, cursor = [], 0
    for match in _CALL_BLOCK.finditer(text):
        if text[cursor : match.start()].strip():
            return []
        try:
            if match[1] is not None:
                data = parse_arguments(match[1])
                function = data.get('function', data)
                name = function['name']
                arguments = function.get('arguments', function.get('parameters', function.get('args', {})))
            else:
                name, body = match[2], match[3]
                arguments, end = {}, 0
                for parameter in _PARAMETER.finditer(body):
                    if body[end : parameter.start()].strip() or parameter[1] in arguments:
                        return []
                    arguments[parameter[1]] = parameter[2]
                    end = parameter.end()
                if body[end:].strip():
                    return []
            if name not in allowed_names:
                return []
            arguments = parse_arguments(arguments)
        except (ValueError, TypeError, KeyError, AttributeError, RecursionError):
            return []
        calls.append(
            {
                'id': f'call_{uuid4().hex[:24]}',
                'type': 'function',
                'function': {'name': name, 'arguments': json.dumps(arguments, ensure_ascii=False)},
            }
        )
        cursor = match.end()
    return calls if not text[cursor:].strip() else []


def tool_call_key(call):
    """Compare calls by name and arguments, independently of provider IDs."""
    arguments = call.get('arguments', '{}')
    try:
        arguments = parse_arguments(arguments)
    except ValueError:
        arguments = arguments if isinstance(arguments, str) else repr(arguments)
    return call.get('name', ''), json.dumps(arguments, sort_keys=True, ensure_ascii=False)


def tool_repetition_error(call, previous_calls):
    """Stop unchanged retries after two consecutive failures; successful polls can repeat."""
    key = tool_call_key(call)
    recent = previous_calls[-2:]
    if len(recent) == 2 and all(tool_call_key(item) == key and item.get('status') == 'failed' for item in recent):
        return 'Error: the same tool call failed twice. Finish using the available results.'
    return None


def prepare_tool_call(call, schema=None, *, display_labels=False, approval_review=False):
    """Normalize a call before approval; return an actionable error for the model."""
    original_arguments = call.get('arguments', '{}')
    try:
        arguments = dict(parse_arguments(original_arguments))
        if display_labels and '__labels__' in arguments:
            labels = arguments.pop('__labels__')
            call.pop('display_labels', None)
            if isinstance(labels, dict) and all(
                isinstance(labels.get(key), str) and 0 < len(labels[key].strip()) <= 120
                for key in ('running', 'completed')
            ):
                call['display_labels'] = {key: labels[key].strip() for key in ('running', 'completed')}
        if approval_review and '__approval__' in arguments:
            approval = arguments.pop('__approval__')
            valid = isinstance(approval, dict) and set(approval) == {'required'} and type(approval['required']) is bool
            call['permission_review'] = {'engine': '', 'required': approval['required'] if valid else True}
        arguments = normalize_arguments(arguments, schema)
    except ValueError as exc:
        return f'Error: {exc} Correct the arguments before retrying.'
    normalized = json.dumps(arguments, ensure_ascii=False)
    if normalized != original_arguments:
        call.setdefault('original_arguments', original_arguments)
    call['arguments'] = normalized
    return None


def final_answer_payload(payload):
    """Make one OpenAI-compatible continuation request with tools disabled."""
    return {
        **payload,
        'tools': [],
        'tool_choice': 'none',
        'messages': [*payload.get('messages', []), {'role': 'system', 'content': FINAL_ANSWER_PROMPT}],
    }
