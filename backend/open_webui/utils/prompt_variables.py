"""Prompt input variables, `{{name}}` / `{{name | type:prop=value}}`. Mirrors extractInputVariables in src/lib/utils."""

import json
import re
from typing import Any, Optional

VARIABLE_PATTERN = re.compile(r'{{\s*([^|}\s]+)\s*(?:\|\s*([^}]+?)\s*)?}}')

NUMBER_TYPES = {'number', 'range'}


class PromptVariableError(ValueError):
    pass


def _split_properties(value: str, delimiter: str) -> list[str]:
    parts, current, depth, in_string, escape = [], '', 0, False, False
    for char in value:
        if escape:
            current += char
            escape = False
            continue
        if char == '\\':
            current += char
            escape = True
            continue
        if char == '"':
            in_string = not in_string
            current += char
            continue
        if not in_string:
            if char in '{[':
                depth += 1
            elif char in '}]':
                depth -= 1
            if char == delimiter and depth == 0:
                parts.append(current)
                current = ''
                continue
        current += char
    if current:
        parts.append(current)
    return parts


def _parse_value(value: str) -> Any:
    if value.startswith('"') and value.endswith('"'):
        return value[1:-1]
    try:
        return json.loads(value)
    except ValueError:
        return value


def parse_definition(definition: Optional[str]) -> dict[str, Any]:
    if not definition:
        return {'type': 'text'}
    first, *props = _split_properties(definition, ':')
    first = first.strip()
    result: dict[str, Any] = {'type': first[5:] if first.startswith('type=') else first}
    for prop in props:
        prop = prop.strip()
        if not prop:
            continue
        name, *rest = _split_properties(prop, '=')
        name = name.strip()
        if not name:
            continue
        result[name] = _parse_value('='.join(rest).strip()) if rest else True
    return result


def extract_variables(template: str) -> dict[str, dict[str, Any]]:
    variables: dict[str, dict[str, Any]] = {}
    for match in VARIABLE_PATTERN.finditer(template):
        name, definition = match.group(1), match.group(2)
        if definition or name not in variables:
            variables[name] = parse_definition(definition)
    return variables


def _lookup(values: dict[str, Any], name: str) -> Any:
    if name in values:
        return values[name]
    current: Any = values
    for part in name.split('.'):
        if isinstance(current, dict) and part in current:
            current = current[part]
        elif isinstance(current, list) and part.isdigit() and int(part) < len(current):
            current = current[int(part)]
        else:
            return None
    return current


def _to_text(value: Any) -> str:
    if isinstance(value, bool):
        return 'true' if value else 'false'
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def _check(name: str, definition: dict[str, Any], value: Any) -> None:
    kind = definition.get('type')
    if kind in NUMBER_TYPES and not isinstance(value, bool):
        try:
            float(value)
        except (TypeError, ValueError):
            raise PromptVariableError(f'Variable "{name}" must be a number')
    options = definition.get('options')
    if kind == 'select' and isinstance(options, list) and options and _to_text(value) not in map(_to_text, options):
        raise PromptVariableError(f'Variable "{name}" must be one of: {", ".join(map(_to_text, options))}')


def fill_variables(template: str, values: Optional[dict[str, Any]] = None, *, strict: bool = True) -> str:
    """Unmatched variables without a default stay as written."""
    values = values or {}
    variables = extract_variables(template)
    resolved: dict[str, str] = {}
    missing = []
    for name, definition in variables.items():
        value = _lookup(values, name)
        if value is None:
            value = definition.get('default')
        if value is None:
            if definition.get('required'):
                missing.append(name)
            continue
        if strict:
            _check(name, definition, value)
        resolved[name] = _to_text(value)
    if strict and missing:
        raise PromptVariableError(f'Missing required variable(s): {", ".join(missing)}')
    # Single pass: values are never re-expanded.
    return VARIABLE_PATTERN.sub(lambda m: resolved.get(m.group(1), m.group(0)), template)
