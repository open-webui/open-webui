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


@dataclass(frozen=True)
class GisObjectSearchProfile:
    """Bounded GIS-derived descriptors used to expand knowledge retrieval."""

    object_name: str
    project_id: str
    profile_status: Literal['ready', 'partial', 'unavailable']
    location_terms: tuple[str, ...]
    commodity_terms: tuple[str, ...]
    deposit_type_terms: tuple[str, ...]
    geology_terms: tuple[str, ...]
    evidence: tuple[Mapping[str, Any], ...]
    diagnostics: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            'schema_version': 1,
            'profile_status': self.profile_status,
            'project_resolution': {
                'status': 'resolved',
                'project_id': self.project_id,
                'object_name': self.object_name,
                'authority': 'geotizer_start',
            },
            'location_terms': list(self.location_terms),
            'commodity_terms': list(self.commodity_terms),
            'deposit_type_terms': list(self.deposit_type_terms),
            'geology_terms': list(self.geology_terms),
            'evidence': [dict(item) for item in self.evidence],
            'diagnostics': list(self.diagnostics),
        }


def normalize_gis_object_profile(
    raw_output: str,
    *,
    object_name: str,
    project_id: str,
) -> GisObjectSearchProfile:
    """Decode optional GIS descriptors without reopening project resolution."""
    try:
        payload = extract_json_object(raw_output)
    except GeotizerOrchestrationError as exc:
        return GisObjectSearchProfile(
            object_name=object_name,
            project_id=project_id,
            profile_status='unavailable',
            location_terms=(),
            commodity_terms=(),
            deposit_type_terms=(),
            geology_terms=(),
            evidence=(),
            diagnostics=(str(exc),),
        )

    location_terms = _normalized_terms(payload.get('location_terms'))
    commodity_terms = _normalized_terms(payload.get('commodity_terms'))
    deposit_type_terms = _normalized_terms(payload.get('deposit_type_terms'))
    geology_terms = _normalized_terms(payload.get('geology_terms'))
    raw_evidence = payload.get('evidence')
    if (
        not isinstance(raw_evidence, Sequence)
        or isinstance(raw_evidence, str | bytes)
    ):
        raw_evidence = []
    evidence = tuple(
        dict(item)
        for item in raw_evidence[:20]
        if isinstance(item, Mapping)
    )
    diagnostics: tuple[str, ...] = ()
    if not evidence and any(
        (
            location_terms,
            commodity_terms,
            deposit_type_terms,
            geology_terms,
        )
    ):
        location_terms = ()
        commodity_terms = ()
        deposit_type_terms = ()
        geology_terms = ()
        diagnostics = (
            'GIS descriptors were ignored because no exact GIS evidence '
            'locator was supplied.',
        )
    has_descriptors = any(
        (
            location_terms,
            commodity_terms,
            deposit_type_terms,
            geology_terms,
        )
    )
    return GisObjectSearchProfile(
        object_name=object_name,
        project_id=project_id,
        profile_status='ready' if has_descriptors and evidence else 'partial',
        location_terms=location_terms,
        commodity_terms=commodity_terms,
        deposit_type_terms=deposit_type_terms,
        geology_terms=geology_terms,
        evidence=evidence,
        diagnostics=diagnostics,
    )


def build_knowledge_search_plan(
    profile: GisObjectSearchProfile,
) -> dict[str, Any]:
    """Plan direct, contextual and analogue retrieval in decreasing authority."""
    direct_terms = _normalized_terms(
        [
            profile.object_name,
            profile.object_name.replace('_', ' '),
            profile.project_id,
            profile.project_id.replace('_', ' '),
        ]
    )
    regional_terms = _normalized_terms(
        [*profile.location_terms, *profile.geology_terms]
    )
    analogue_terms = _normalized_terms(
        [
            *profile.commodity_terms,
            *profile.deposit_type_terms,
            *profile.geology_terms,
        ]
    )
    return {
        'schema_version': 1,
        'object_profile': profile.as_dict(),
        'tiers': [
            {
                'tier_id': 'direct',
                'relation_to_object': 'direct',
                'query_terms': list(direct_terms),
                'enabled': True,
                'allowed_use': (
                    'May support object-specific factual fields when the '
                    'source explicitly identifies this object.'
                ),
            },
            {
                'tier_id': 'regional_context',
                'relation_to_object': 'regional_context',
                'query_terms': list(regional_terms),
                'enabled': bool(regional_terms),
                'allowed_use': (
                    'May support regional setting and search hypotheses; '
                    'must not be presented as a measured object value.'
                ),
            },
            {
                'tier_id': 'deposit_analogue',
                'relation_to_object': 'deposit_analogue',
                'query_terms': list(analogue_terms),
                'enabled': bool(analogue_terms),
                'allowed_use': (
                    'May support analogue fields, expected types and expert '
                    'hypotheses; must not be copied as an object-specific '
                    'resource, grade, geometry or study result.'
                ),
            },
        ],
        'decision_rules': [
            (
                'Absence of a directly named collection is not proof that '
                'the knowledge base has no relevant evidence.'
            ),
            (
                'Search enabled tiers in order: direct, regional_context, '
                'deposit_analogue.'
            ),
            (
                'Record relation_to_object and the GIS descriptors used for '
                'every contextual or analogue source in retrieval_note and '
                'source_locator.'
            ),
            (
                'If only contextual or analogue evidence exists for an '
                'object-specific factual field, use '
                'requires_expert_review or not_found rather than inventing '
                'an object value.'
            ),
        ],
    }


def _normalized_terms(raw: Any) -> tuple[str, ...]:
    if isinstance(raw, str):
        values = [raw]
    elif isinstance(raw, Sequence):
        values = [value for value in raw if isinstance(value, str)]
    else:
        values = []
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        term = ' '.join(value.strip().split())
        canonical = term.casefold().replace('ё', 'е')
        if not term or canonical in seen:
            continue
        seen.add(canonical)
        result.append(term)
    return tuple(result)


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
        batch_namespace = str(next_batch.get('batch_id') or '').lower()
        for raw_source in envelope.get('source_inventory') or []:
            source = dict(raw_source)
            source_id = str(source.get('source_id') or '')
            candidate = (
                f'{batch_namespace}__part_{chunk_index}__{source_id}'
            )
            suffix = 2
            while candidate in source_by_id:
                candidate = (
                    f'{batch_namespace}__part_{chunk_index}__'
                    f'{source_id}__{suffix}'
                )
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


def owner_failure_envelope(
    next_batch: Mapping[str, Any],
    *,
    run_id: str,
    attempts: int,
    feedback: Sequence[Any],
) -> dict[str, Any]:
    """Fail closed after invalid owner output without aborting the whole run."""
    chunk = next_batch.get('owner_chunk') or {}
    chunk_index = int(chunk.get('index') or 1)
    chunk_total = int(chunk.get('total') or 1)
    batch_id = str(next_batch.get('batch_id') or '')
    producer = str(next_batch.get('producer') or '')
    source_id = (
        f'orchestration-review-{batch_id.lower()}-part-{chunk_index}'
    )
    locator = (
        f'run_id={run_id}; batch_id={batch_id}; '
        f'owner_chunk={chunk_index}/{chunk_total}; attempts={attempts}'
    )
    feedback_text = bounded_text(
        json.dumps(list(feedback), ensure_ascii=False),
        max_chars=1200,
    )
    return {
        'run_id': run_id,
        'batch_id': batch_id,
        'producer': producer,
        'policy_version': str(next_batch.get('policy_version') or ''),
        'template_version': str(next_batch.get('template_version') or ''),
        'source_inventory': [
            {
                'source_id': source_id,
                'source_type': 'orchestration',
                'title': (
                    f'{producer} owner output failed deterministic validation '
                    f'for {batch_id}'
                ),
                'locator': locator,
                'url': None,
            }
        ],
        'patches': [
            {
                'field_key': str(field.get('field_key') or ''),
                'value': None,
                'unit': None,
                'status': 'requires_expert_review',
                'source_refs': [source_id],
                'source_locator': {
                    'run_id': run_id,
                    'batch_id': batch_id,
                    'owner_chunk': f'{chunk_index}/{chunk_total}',
                    'attempts': attempts,
                },
                'retrieval_note': (
                    'Specialist evidence was requested, but the owner response '
                    'did not satisfy the deterministic field contract after '
                    f'{attempts} attempts. Validation feedback: {feedback_text}'
                ),
            }
            for field in next_batch.get('fields') or []
        ],
    }


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
    knowledge_search_plan: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the bounded context an owner needs; omit unrelated run state."""
    return {
        'object_name': object_name,
        'run_id': run_id,
        'batch': dict(next_batch),
        'datacube': dict(datacube or {}),
        'knowledge_search_plan': dict(knowledge_search_plan or {}),
        'contributor_evidence': [
            normalize_contributor_evidence(item)
            for item in contributor_evidence
        ],
    }


def normalize_contributor_evidence(
    item: Mapping[str, Any],
) -> dict[str, Any]:
    """Make evidence authority explicit before an LLM owner sees it."""
    normalized = dict(item)
    source_domain = str(item.get('source_domain') or '').strip().lower()
    normalized['source_domain'] = source_domain or 'unknown'
    if source_domain == 'gis':
        normalized['relation_to_object'] = 'direct'
        normalized['evidence_authority'] = 'linked_gis_project'
        normalized['negative_search_precedence'] = (
            'A knowledge-base or web miss cannot negate a confirmed GIS fact.'
        )
    else:
        normalized['relation_to_object'] = str(
            item.get('relation_to_object') or 'source_declared'
        )
        normalized['evidence_authority'] = str(
            item.get('evidence_authority') or 'contributor'
        )
    normalized['output'] = bounded_text(
        str(item.get('output') or ''),
        max_chars=MAX_CONTRIBUTOR_EVIDENCE_CHARS,
    )
    return normalized


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
