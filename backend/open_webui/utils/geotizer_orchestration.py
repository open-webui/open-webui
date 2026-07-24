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


def partition_owner_batch(
    next_batch: Mapping[str, Any],
    *,
    max_fields: int,
) -> tuple[dict[str, Any], ...]:
    """Split one GIS-owned batch into bounded LLM calls without changing ownership."""
    if max_fields < 1:
        raise GeotizerOrchestrationError('max_fields must be positive')
    fields = [dict(field) for field in next_batch.get('fields') or []]
    if not fields:
        return (dict(next_batch),)

    total = (len(fields) + max_fields - 1) // max_fields
    chunks: list[dict[str, Any]] = []
    for offset in range(0, len(fields), max_fields):
        chunk_fields = fields[offset : offset + max_fields]
        field_keys = {str(field.get('field_key') or '') for field in chunk_fields}
        row_ids = {field.get('row_id') for field in chunk_fields}
        evidence_routes = []
        for route in next_batch.get('evidence_routes') or []:
            route_keys = [
                str(field_key)
                for field_key in route.get('field_keys') or []
                if str(field_key) in field_keys
            ]
            if not route_keys:
                continue
            evidence_routes.append(
                {
                    **dict(route),
                    'field_keys': route_keys,
                    'row_ids': [
                        row_id
                        for row_id in route.get('row_ids') or []
                        if row_id in row_ids
                    ],
                }
            )
        index = len(chunks) + 1
        chunks.append(
            {
                **dict(next_batch),
                'fields': chunk_fields,
                'field_count': len(chunk_fields),
                'evidence_routes': evidence_routes,
                'owner_chunk': {'index': index, 'total': total},
            }
        )
    return tuple(chunks)


def merge_owner_envelopes(
    next_batch: Mapping[str, Any],
    chunks: Sequence[Mapping[str, Any]],
    envelopes: Sequence[Mapping[str, Any]],
    *,
    run_id: str,
) -> dict[str, Any]:
    """Merge validated chunk envelopes into one atomic GIS batch submission."""
    if len(chunks) != len(envelopes) or not chunks:
        raise GeotizerOrchestrationError(
            'Owner chunks and envelopes must form one non-empty partition'
        )

    sources: list[dict[str, Any]] = []
    source_by_id: dict[str, dict[str, Any]] = {}
    patches: list[dict[str, Any]] = []
    for chunk_index, (chunk, envelope) in enumerate(
        zip(chunks, envelopes),
        start=1,
    ):
        violations = validate_owner_envelope(chunk, envelope)
        if violations:
            raise GeotizerOrchestrationError('; '.join(violations))

        renamed_refs: dict[str, str] = {}
        for raw_source in envelope.get('source_inventory') or []:
            source = dict(raw_source)
            source_id = str(source.get('source_id') or '')
            existing = source_by_id.get(source_id)
            if existing is None:
                source_by_id[source_id] = source
                sources.append(source)
                renamed_refs[source_id] = source_id
                continue
            if existing == source:
                renamed_refs[source_id] = source_id
                continue

            candidate = f'{source_id}__part_{chunk_index}'
            suffix = 2
            while candidate in source_by_id:
                candidate = f'{source_id}__part_{chunk_index}_{suffix}'
                suffix += 1
            source['source_id'] = candidate
            source_by_id[candidate] = source
            sources.append(source)
            renamed_refs[source_id] = candidate

        for raw_patch in envelope.get('patches') or []:
            patch = dict(raw_patch)
            patch['source_refs'] = [
                renamed_refs.get(str(source_ref), str(source_ref))
                for source_ref in patch.get('source_refs') or []
            ]
            patches.append(patch)

    merged = {
        'run_id': run_id,
        'batch_id': next_batch['batch_id'],
        'producer': next_batch['producer'],
        'policy_version': next_batch['policy_version'],
        'template_version': next_batch['template_version'],
        'source_inventory': sources,
        'patches': patches,
    }
    violations = validate_owner_envelope(next_batch, merged)
    if violations:
        raise GeotizerOrchestrationError('; '.join(violations))
    return merged


def repair_negative_provenance(
    next_batch: Mapping[str, Any],
    envelope: Mapping[str, Any],
    *,
    run_id: str,
    attempt: int,
) -> dict[str, Any]:
    """Register the actual specialist execution for unreferenced not-found patches."""
    repaired = {
        **dict(envelope),
        'source_inventory': [
            dict(source)
            for source in envelope.get('source_inventory') or []
        ],
        'patches': [
            dict(patch)
            for patch in envelope.get('patches') or []
        ],
    }
    missing = [
        patch
        for patch in repaired['patches']
        if patch.get('status') == 'not_found'
        and patch.get('source_refs') == []
    ]
    if not missing:
        return repaired

    chunk = next_batch.get('owner_chunk') or {}
    chunk_index = int(chunk.get('index') or 1)
    chunk_total = int(chunk.get('total') or 1)
    batch_id = str(next_batch.get('batch_id') or '')
    producer = str(next_batch.get('producer') or '')
    source_id = (
        f'derived-negative-{batch_id.lower()}-'
        f'part-{chunk_index}-attempt-{attempt}'
    )
    existing_ids = {
        str(source.get('source_id') or '')
        for source in repaired['source_inventory']
    }
    suffix = 2
    candidate = source_id
    while candidate in existing_ids:
        candidate = f'{source_id}-{suffix}'
        suffix += 1
    source_id = candidate
    repaired['source_inventory'].append(
        {
            'source_id': source_id,
            'source_type': 'derived',
            'title': f'{producer} completed negative search for {batch_id}',
            'locator': (
                f'run_id={run_id}; batch_id={batch_id}; '
                f'owner_chunk={chunk_index}/{chunk_total}; attempt={attempt}'
            ),
            'url': None,
        }
    )
    for patch in missing:
        patch['source_refs'] = [source_id]
    return repaired


def extract_json_object(text: str) -> dict[str, Any]:
    """Extract exactly one JSON object from a model response."""
    if not isinstance(text, str) or not text.strip():
        raise GeotizerOrchestrationError('Agent returned an empty response')

    stripped = _strip_json_fence(text)

    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError:
        parsed = _decode_embedded_object(stripped)
    if not isinstance(parsed, dict):
        raise GeotizerOrchestrationError('Agent response must be a JSON object')
    return parsed


def extract_owner_envelope(
    text: str,
    next_batch: Mapping[str, Any],
) -> dict[str, Any]:
    """Select one structurally exact owner envelope among incidental JSON objects."""
    try:
        return extract_json_object(text)
    except GeotizerOrchestrationError as original_error:
        if not isinstance(text, str) or not text.strip():
            raise
        candidates = _decode_embedded_objects(_strip_json_fence(text))
        expected_keys = [
            str(field.get('field_key') or '')
            for field in next_batch.get('fields') or []
        ]
        matching = []
        for candidate in candidates:
            violations = _contract_violations(next_batch, candidate)
            patches = candidate.get('patches')
            if not isinstance(patches, list):
                continue
            violations.extend(_partition_violations(expected_keys, patches))
            if not violations:
                matching.append(candidate)
        unique = {
            json.dumps(item, ensure_ascii=False, sort_keys=True): item
            for item in matching
        }
        if len(unique) == 1:
            return next(iter(unique.values()))
        raise GeotizerOrchestrationError(
            'Agent response must contain exactly one structurally exact '
            f'owner JSON object; matching_candidates={len(unique)}'
        ) from original_error


def _strip_json_fence(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith('```'):
        first_newline = stripped.find('\n')
        last_fence = stripped.rfind('```')
        if first_newline >= 0 and last_fence > first_newline:
            return stripped[first_newline + 1 : last_fence].strip()
    return stripped


def _decode_embedded_object(text: str) -> dict[str, Any]:
    objects = _decode_embedded_objects(text)
    if len(objects) != 1:
        raise GeotizerOrchestrationError(
            'Agent response must contain exactly one unambiguous JSON object'
        )
    return objects[0]


def _decode_embedded_objects(text: str) -> tuple[dict[str, Any], ...]:
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
    return tuple(unique.values())


def extract_output_message_text(message: Mapping[str, Any]) -> str:
    """Normalize Open WebUI 0.10 output arrays into legacy message content."""
    content = message.get('content')
    if isinstance(content, str) and content.strip():
        return content.strip()

    output = message.get('output')
    if not isinstance(output, list):
        return ''
    for item in reversed(output):
        if not isinstance(item, Mapping) or item.get('type') != 'message':
            continue
        parts = item.get('content')
        if isinstance(parts, str) and parts.strip():
            return parts.strip()
        if not isinstance(parts, list):
            continue
        texts = [
            str(part.get('text')).strip()
            for part in parts
            if isinstance(part, Mapping)
            and part.get('type') in {'output_text', 'text'}
            and isinstance(part.get('text'), str)
            and str(part.get('text')).strip()
        ]
        if texts:
            return '\n'.join(texts)
    return ''


def normalize_delegator_message(message: Mapping[str, Any] | None) -> Mapping[str, Any] | None:
    """Expose persisted output text where older delegators expect content."""
    if not isinstance(message, Mapping):
        return message
    recovered = extract_output_message_text(message)
    if recovered:
        if recovered == message.get('content'):
            return message
    else:
        if message.get('done') is not True:
            return message
        recovered = json.dumps(
            {
                'status': 'completed_without_final_text',
                'note': (
                    'The specialist completed without a final textual message; '
                    'function-call output remains in the persisted output array.'
                ),
            },
            ensure_ascii=False,
        )
    return {**message, 'content': recovered}


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
