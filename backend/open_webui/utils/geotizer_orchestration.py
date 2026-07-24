"""Pure planning and validation for the GeoTeaser orchestration loop."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal

AgentKind = Literal['gis', 'kb', 'web', 'skilled']

PRODUCER_AGENT_KIND: Mapping[str, AgentKind] = {
    'GISagent_yulong': 'gis',
    'KBagent_yulong': 'kb',
    'WEBagent_yulong': 'web',
    'SkilledAgent': 'skilled',
}

ALLOWED_FIELD_STATUSES = frozenset(
    {
        'filled',
        'not_found',
        'not_applicable',
        'conflicted',
        'requires_expert_review',
    }
)
MAX_CONTRIBUTOR_EVIDENCE_CHARS = 20_000


class GeotizerOrchestrationError(ValueError):
    """Raised when the deterministic orchestration contract is violated."""


@dataclass(frozen=True)
class AgentTask:
    kind: AgentKind
    producer: str
    role: Literal['contributor', 'owner']
    task_id: str
    payload: Mapping[str, Any]


def agent_kind_for_producer(producer: str) -> AgentKind:
    try:
        return PRODUCER_AGENT_KIND[producer]
    except KeyError as exc:
        raise GeotizerOrchestrationError(f'Unsupported GeoTeaser producer: {producer}') from exc


def build_batch_tasks(next_batch: Mapping[str, Any]) -> tuple[AgentTask, ...]:
    """Plan contributor calls before the single exact owner call."""
    batch_id = str(next_batch.get('batch_id') or '')
    owner = str(next_batch.get('producer') or '')
    if not batch_id or not owner:
        raise GeotizerOrchestrationError('next_batch must contain batch_id and producer')

    tasks: list[AgentTask] = []
    seen_routes: set[str] = set()
    for route in next_batch.get('evidence_routes') or []:
        if route.get('satisfied_by') != 'contributor_call':
            continue
        route_id = str(route.get('route_id') or '')
        producer = str(route.get('producer') or '')
        if not route_id or route_id in seen_routes:
            raise GeotizerOrchestrationError(f'Invalid or duplicate evidence route in batch {batch_id}')
        seen_routes.add(route_id)
        tasks.append(
            AgentTask(
                kind=agent_kind_for_producer(producer),
                producer=producer,
                role='contributor',
                task_id=route_id,
                payload=dict(route),
            )
        )

    tasks.append(
        AgentTask(
            kind=agent_kind_for_producer(owner),
            producer=owner,
            role='owner',
            task_id=batch_id,
            payload=dict(next_batch),
        )
    )
    return tuple(tasks)


def extract_json_object(text: str) -> dict[str, Any]:
    """Extract exactly one JSON object from a model response."""
    if not isinstance(text, str) or not text.strip():
        raise GeotizerOrchestrationError('Agent returned an empty response')

    stripped = text.strip()
    if stripped.startswith('```'):
        first_newline = stripped.find('\n')
        last_fence = stripped.rfind('```')
        if first_newline >= 0 and last_fence > first_newline:
            stripped = stripped[first_newline + 1 : last_fence].strip()

    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError:
        parsed = _decode_embedded_object(stripped)
    if not isinstance(parsed, dict):
        raise GeotizerOrchestrationError('Agent response must be a JSON object')
    return parsed


def _decode_embedded_object(text: str) -> dict[str, Any]:
    decoder = json.JSONDecoder()
    objects: list[tuple[int, int, dict[str, Any]]] = []
    for index, char in enumerate(text):
        if char != '{':
            continue
        try:
            value, consumed = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            objects.append((index, index + consumed, value))
    top_level = [
        candidate
        for candidate in objects
        if not any(other_start < candidate[0] and candidate[1] <= other_end for other_start, other_end, _ in objects)
    ]
    unique = {json.dumps(item, ensure_ascii=False, sort_keys=True): item for _, _, item in top_level}
    if len(unique) != 1:
        raise GeotizerOrchestrationError('Agent response must contain exactly one unambiguous JSON object')
    return next(iter(unique.values()))


def validate_owner_envelope(
    next_batch: Mapping[str, Any],
    envelope: Mapping[str, Any],
) -> tuple[str, ...]:
    """Return deterministic preflight violations for an owner envelope."""
    violations = _contract_violations(next_batch, envelope)
    patches = envelope.get('patches')
    if not isinstance(patches, list):
        return tuple([*violations, 'patches must be an array'])

    expected_keys = [str(field.get('field_key') or '') for field in next_batch.get('fields') or []]
    violations.extend(_partition_violations(expected_keys, patches))
    source_ids, inventory_violations = _source_inventory(envelope.get('source_inventory'))
    violations.extend(inventory_violations)
    for index, patch in enumerate(patches):
        violations.extend(_patch_violations(index, patch, source_ids))
    return tuple(violations)


def _contract_violations(
    next_batch: Mapping[str, Any],
    envelope: Mapping[str, Any],
) -> list[str]:
    violations: list[str] = []
    expected = {
        'batch_id': str(next_batch.get('batch_id') or ''),
        'producer': str(next_batch.get('producer') or ''),
        'policy_version': str(next_batch.get('policy_version') or ''),
        'template_version': str(next_batch.get('template_version') or ''),
    }
    for key, value in expected.items():
        if envelope.get(key) != value:
            violations.append(f'{key}: expected {value!r}, got {envelope.get(key)!r}')
    return violations


def _partition_violations(
    expected_keys: Sequence[str],
    patches: Sequence[Any],
) -> list[str]:
    violations: list[str] = []
    actual_keys = [str(patch.get('field_key') or '') for patch in patches if isinstance(patch, Mapping)]
    duplicates = sorted(key for key in set(actual_keys) if actual_keys.count(key) > 1)
    if duplicates:
        violations.append(f'duplicate field_key values: {duplicates}')
    missing = sorted(set(expected_keys) - set(actual_keys))
    extra = sorted(set(actual_keys) - set(expected_keys))
    if missing:
        violations.append(f'missing field_key values: {missing}')
    if extra:
        violations.append(f'foreign field_key values: {extra}')
    if len(patches) != len(expected_keys):
        violations.append(f'patch count: expected {len(expected_keys)}, got {len(patches)}')
    return violations


def _source_inventory(inventory: Any) -> tuple[set[str], list[str]]:
    if not isinstance(inventory, list):
        return set(), ['source_inventory must be an array']
    source_ids = {str(source.get('source_id') or '') for source in inventory if isinstance(source, Mapping)}
    source_ids.discard('')
    return source_ids, []


def _patch_violations(
    index: int,
    patch: Any,
    source_ids: set[str],
) -> list[str]:
    if not isinstance(patch, Mapping):
        return [f'patches[{index}] must be an object']
    violations: list[str] = []
    status = str(patch.get('status') or '')
    if status not in ALLOWED_FIELD_STATUSES:
        violations.append(f'patches[{index}].status is unsupported: {status}')
    value = patch.get('value')
    if status == 'filled' and value in (None, ''):
        violations.append(f'patches[{index}] filled without value')
    if status in {'not_found', 'not_applicable', 'conflicted'} and value is not None:
        violations.append(f'patches[{index}] {status} must use value=null')
    refs = patch.get('source_refs')
    if not isinstance(refs, list) or not refs:
        violations.append(f'patches[{index}].source_refs must be non-empty')
        return violations
    unknown_refs = sorted({str(ref) for ref in refs} - source_ids)
    if unknown_refs:
        violations.append(f'patches[{index}] has unregistered source_refs: {unknown_refs}')
    if status == 'filled' and patch.get('source_locator') in (
        None,
        '',
        {},
        [],
    ):
        violations.append(f'patches[{index}] filled without source_locator')
    return violations


def owner_submission(
    next_batch: Mapping[str, Any],
    envelope: Mapping[str, Any],
) -> dict[str, Any]:
    violations = validate_owner_envelope(next_batch, envelope)
    if violations:
        raise GeotizerOrchestrationError('; '.join(violations))
    return {
        'action': 'submit_batch',
        'run_id': envelope['run_id'],
        'batch_id': envelope['batch_id'],
        'producer': envelope['producer'],
        'policy_version': envelope['policy_version'],
        'template_version': envelope['template_version'],
        'patches': envelope['patches'],
        'source_inventory': envelope['source_inventory'],
    }


def xlsx_download_path(state: Mapping[str, Any]) -> str:
    xlsx = state.get('xlsx')
    if not isinstance(xlsx, Mapping):
        raise GeotizerOrchestrationError('Final state has no XLSX artifact')
    path = str(xlsx.get('download_path') or '')
    if not path.startswith('/geotizer/files/') or not path.endswith('/geotizer.xlsx'):
        raise GeotizerOrchestrationError('Final state has an invalid XLSX path')
    return path


def ensure_state_can_continue(state: Mapping[str, Any]) -> None:
    status = state.get('workflow_status')
    if status == 'needs_input':
        raise GeotizerOrchestrationError(json.dumps(state.get('error') or state, ensure_ascii=False))
    if status == 'validation_failed':
        raise GeotizerOrchestrationError(json.dumps(state.get('violations') or state, ensure_ascii=False))
    if status not in {'collecting', 'finalized'}:
        raise GeotizerOrchestrationError(f'Unsupported GeoTeaser workflow_status: {status!r}')


def compact_batch_context(
    next_batch: Mapping[str, Any],
    *,
    object_name: str,
    run_id: str,
    datacube: Mapping[str, Any] | None,
    contributor_evidence: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Build the bounded context an owner needs; omit unrelated run state."""
    return {
        'object_name': object_name,
        'run_id': run_id,
        'batch': dict(next_batch),
        'datacube': dict(datacube or {}),
        'contributor_evidence': [
            {
                **dict(item),
                'output': bounded_text(
                    str(item.get('output') or ''),
                    max_chars=MAX_CONTRIBUTOR_EVIDENCE_CHARS,
                ),
            }
            for item in contributor_evidence
        ],
    }


def bounded_text(value: str, *, max_chars: int) -> str:
    """Keep the beginning and provenance-rich tail of oversized evidence."""
    if len(value) <= max_chars:
        return value
    tail_chars = min(4_000, max_chars // 4)
    head_chars = max_chars - tail_chars
    removed = len(value) - max_chars
    return (
        f'{value[:head_chars]}\n\n'
        f'[... {removed} evidence characters omitted by orchestrator ...]\n\n'
        f'{value[-tail_chars:]}'
    )
