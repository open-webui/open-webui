from __future__ import annotations

import json
import re
from typing import Any


CHAT_VARIABLE_KEY_RE = re.compile(r'^[a-z][a-z0-9_]*$')
CHAT_VARIABLE_ANY_RE = re.compile(r'{{\s*chat\.variables\.([^\s|}]+)(?:\s*\|\s*([^}]*))?\s*}}')
MAX_VARIABLE_VALUE_LENGTH = 20_000
MAX_VARIABLES_JSON_LENGTH = 100_000


class ChatVariablesError(ValueError):
    pass


def split_properties(value: str, delimiter: str) -> list[str]:
    result: list[str] = []
    current = ''
    depth = 0
    in_string = False
    escape_next = False

    for char in value:
        if escape_next:
            current += char
            escape_next = False
            continue

        if char == '\\':
            current += char
            escape_next = True
            continue

        if char == '"' and not escape_next:
            in_string = not in_string
            current += char
            continue

        if not in_string:
            if char in ('{', '['):
                depth += 1
            elif char in ('}', ']'):
                depth -= 1

            if char == delimiter and depth == 0:
                result.append(current.strip())
                current = ''
                continue

        current += char

    if current.strip():
        result.append(current.strip())

    return result


def parse_json_value(value: str) -> Any:
    if value.startswith('"') and value.endswith('"'):
        return value[1:-1]

    if re.match(r'^[\[{]', value):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value

    return value


def parse_variable_definition(definition: str) -> dict[str, Any]:
    parts = split_properties(definition, ':')
    if not parts:
        return {'type': 'text'}

    first_part, *property_parts = parts
    field_type = first_part[5:] if first_part.startswith('type=') else first_part
    field_type = field_type.strip() or 'text'
    properties: dict[str, Any] = {}

    for part in property_parts:
        trimmed = part.strip()
        if not trimmed:
            continue

        equals_parts = split_properties(trimmed, '=')
        if len(equals_parts) == 1:
            properties[equals_parts[0].strip()] = True
            continue

        property_name, *value_parts = equals_parts
        properties[property_name.strip()] = parse_json_value('='.join(value_parts).strip())

    return {'type': field_type, **properties}


def _safe_field(key: str, definition: dict[str, Any]) -> dict[str, Any]:
    allowed_keys = {
        'default',
        'label',
        'max',
        'maxlength',
        'min',
        'minlength',
        'options',
        'placeholder',
        'required',
        'step',
        'type',
    }
    field = {'key': key}
    for field_key in allowed_keys:
        if field_key in definition:
            field[field_key] = definition[field_key]

    field.setdefault('type', 'text')
    if field.get('type') == 'select' and not isinstance(field.get('options'), list):
        field['options'] = []
    field['required'] = bool(field.get('required', False))

    return field


def get_chat_variables_schema(system_prompt: str | None) -> dict[str, list[dict[str, Any]]] | None:
    if not system_prompt:
        return None

    try:
        fields_by_key = collect_chat_variable_fields(system_prompt)
    except ChatVariablesError:
        fields_by_key = {}

    if not fields_by_key:
        return None

    return {'fields': list(fields_by_key.values())}


def collect_chat_variable_fields(system_prompt: str | None) -> dict[str, dict[str, Any]]:
    fields_by_key: dict[str, dict[str, Any]] = {}
    if not system_prompt:
        return fields_by_key

    typed_fields_by_key: dict[str, dict[str, Any]] = {}
    for match in CHAT_VARIABLE_ANY_RE.finditer(system_prompt):
        key = match.group(1).strip()
        definition = match.group(2)
        if not CHAT_VARIABLE_KEY_RE.match(key):
            raise ChatVariablesError(f'Invalid chat variable key: {key}')

        if definition is None or not definition.strip():
            fields_by_key.setdefault(key, _safe_field(key, {'type': 'text'}))
            continue

        field = _safe_field(key, parse_variable_definition(definition.strip()))

        if field.get('type') == 'select' and not field.get('options'):
            raise ChatVariablesError(f'Chat variable {key} select needs options.')
        previous = typed_fields_by_key.get(key)
        if previous and previous != field:
            raise ChatVariablesError(f'Chat variable {key} has conflicting definitions.')
        typed_fields_by_key[key] = field
        fields_by_key[key] = field

    return fields_by_key


def normalize_chat_variables(variables: Any) -> dict[str, Any]:
    if not isinstance(variables, dict):
        return {}
    return variables


def validate_chat_variables(
    system_prompt: str | None,
    variables: Any,
    *,
    required: bool = True,
) -> dict[str, Any]:
    field_map = collect_chat_variable_fields(system_prompt)
    variables = normalize_chat_variables(variables)

    try:
        if len(json.dumps(variables)) > MAX_VARIABLES_JSON_LENGTH:
            raise ChatVariablesError('Chat variables are too large.')
    except TypeError:
        raise ChatVariablesError('Chat variables must be JSON serializable.')

    validated: dict[str, Any] = {}
    for key, field in field_map.items():
        has_value = key in variables and variables[key] not in (None, '')
        value = variables.get(key)

        if not has_value:
            if field.get('default') not in (None, ''):
                value = field.get('default')
                has_value = True
            elif required and field.get('required'):
                label = field.get('label') or key
                raise ChatVariablesError(f'Missing required chat variable: {label}')
            else:
                value = ''

        if field.get('type') == 'select':
            options = field.get('options') or []
            if has_value and value not in options:
                label = field.get('label') or key
                raise ChatVariablesError(f'Invalid value for chat variable: {label}')

        if isinstance(value, str):
            value = value.replace('\r\n', '\n')
            if len(value) > MAX_VARIABLE_VALUE_LENGTH:
                label = field.get('label') or key
                raise ChatVariablesError(f'Chat variable is too long: {label}')

        validated[key] = value

    return validated


def render_chat_variables(
    system_prompt: str | None,
    variables: Any,
    *,
    required: bool = True,
) -> str | None:
    if not system_prompt:
        return system_prompt

    try:
        validated = validate_chat_variables(system_prompt, variables, required=required)
    except ChatVariablesError:
        validated = {}

    def replace(match: re.Match) -> str:
        key = match.group(1).strip()
        value = validated.get(key, '')
        return '' if value is None else str(value)

    return CHAT_VARIABLE_ANY_RE.sub(replace, system_prompt)
