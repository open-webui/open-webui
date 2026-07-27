"""Pure validation and application of Geological Vision evidence."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal

from open_webui.utils.geotizer_orchestration import (
    GeotizerOrchestrationError,
    extract_json_object,
)


@dataclass(frozen=True)
class VisualFieldProposal:
    """Typed proposal derived from a traceable geological image."""

    field_key: str
    value: Any
    unit: str | None
    value_origin: Literal['calculated', 'analogue']
    evidence_scope: Literal[
        'visual_observation',
        'spatial_derivation',
        'domain_analogy',
    ]
    project_match: Literal[
        'project_specific_source',
        'matched',
        'analogue',
    ]
    alignment_status: Literal[
        'not_required',
        'georeferenced',
        'aligned_by_control_points',
    ]
    source_id: str
    source_title: str
    source_sha256: str
    source_locator: Mapping[str, Any]
    extraction_method: Literal[
        'ocr_verbatim',
        'vision_interpretation',
        'spatial_measurement',
        'analogue_transfer',
    ]
    retrieval_note: str

    def as_dict(self) -> dict[str, Any]:
        return {
            'field_key': self.field_key,
            'value': self.value,
            'unit': self.unit,
            'value_origin': self.value_origin,
            'evidence_scope': self.evidence_scope,
            'project_match': self.project_match,
            'alignment_status': self.alignment_status,
            'source_id': self.source_id,
            'source_title': self.source_title,
            'source_sha256': self.source_sha256,
            'source_locator': dict(self.source_locator),
            'extraction_method': self.extraction_method,
            'retrieval_note': self.retrieval_note,
        }


def normalize_visual_field_proposals(
    raw_output: str | Mapping[str, Any],
    *,
    allowed_field_keys: Sequence[str],
) -> tuple[VisualFieldProposal, ...]:
    """Decode only project-bound, locator-complete visual proposals."""
    if isinstance(raw_output, Mapping):
        payload = dict(raw_output)
    else:
        try:
            payload = extract_json_object(raw_output)
        except GeotizerOrchestrationError:
            return ()
    raw_proposals = payload.get('field_proposals')
    if (
        not isinstance(raw_proposals, Sequence)
        or isinstance(raw_proposals, str | bytes)
    ):
        return ()

    allowed = {str(field_key) for field_key in allowed_field_keys}
    proposals: list[VisualFieldProposal] = []
    seen: set[str] = set()
    for raw in raw_proposals:
        if not isinstance(raw, Mapping):
            continue
        proposal = _normalize_visual_proposal(raw, allowed)
        if proposal is None:
            continue
        identity = json.dumps(
            proposal.as_dict(),
            ensure_ascii=False,
            sort_keys=True,
        )
        if identity not in seen:
            seen.add(identity)
            proposals.append(proposal)
    return tuple(proposals)


def _normalize_visual_proposal(
    raw: Mapping[str, Any],
    allowed_field_keys: set[str],
) -> VisualFieldProposal | None:
    values = {
        'field_key': str(raw.get('field_key') or ''),
        'value': raw.get('value'),
        'value_origin': str(raw.get('value_origin') or ''),
        'evidence_scope': str(raw.get('evidence_scope') or ''),
        'project_match': str(raw.get('project_match') or ''),
        'alignment_status': str(raw.get('alignment_status') or ''),
        'source_id': str(raw.get('source_id') or ''),
        'source_sha256': str(raw.get('source_sha256') or '').lower(),
        'source_locator': raw.get('source_locator'),
        'extraction_method': str(raw.get('extraction_method') or ''),
        'retrieval_note': str(raw.get('retrieval_note') or '').strip(),
    }
    if not _visual_proposal_shape_is_valid(
        values,
        allowed_field_keys,
    ):
        return None
    if not _visual_proposal_semantics_are_valid(values):
        return None
    source_locator = values['source_locator']
    assert isinstance(source_locator, Mapping)
    return VisualFieldProposal(
        field_key=str(values['field_key']),
        value=values['value'],
        unit=(
            str(raw.get('unit'))
            if raw.get('unit') is not None
            else None
        ),
        value_origin=str(values['value_origin']),  # type: ignore[arg-type]
        evidence_scope=str(values['evidence_scope']),  # type: ignore[arg-type]
        project_match=str(values['project_match']),  # type: ignore[arg-type]
        alignment_status=str(values['alignment_status']),  # type: ignore[arg-type]
        source_id=str(values['source_id']),
        source_title=str(
            raw.get('source_title') or values['source_id']
        ),
        source_sha256=str(values['source_sha256']),
        source_locator=dict(source_locator),
        extraction_method=str(values['extraction_method']),  # type: ignore[arg-type]
        retrieval_note=str(values['retrieval_note']),
    )


def _visual_proposal_shape_is_valid(
    values: Mapping[str, Any],
    allowed_field_keys: set[str],
) -> bool:
    source_locator = values['source_locator']
    return bool(
        values['field_key'] in allowed_field_keys
        and values['value'] not in (None, '')
        and values['value_origin'] in {'calculated', 'analogue'}
        and values['evidence_scope']
        in {
            'visual_observation',
            'spatial_derivation',
            'domain_analogy',
        }
        and values['project_match']
        in {'project_specific_source', 'matched', 'analogue'}
        and values['alignment_status']
        in {
            'not_required',
            'georeferenced',
            'aligned_by_control_points',
        }
        and values['source_id']
        and _is_sha256(str(values['source_sha256']))
        and isinstance(source_locator, Mapping)
        and _visual_locator_is_complete(source_locator)
        and values['extraction_method']
        in {
            'ocr_verbatim',
            'vision_interpretation',
            'spatial_measurement',
            'analogue_transfer',
        }
        and values['retrieval_note']
    )


def _visual_proposal_semantics_are_valid(
    values: Mapping[str, Any],
) -> bool:
    value_origin = values['value_origin']
    evidence_scope = values['evidence_scope']
    project_match = values['project_match']
    alignment_status = values['alignment_status']
    extraction_method = values['extraction_method']
    source_locator = values['source_locator']
    if (
        value_origin == 'calculated'
        and project_match not in {'project_specific_source', 'matched'}
    ):
        return False
    if (
        value_origin == 'analogue'
        and (
            project_match != 'analogue'
            or not source_locator.get('analogue_project_id')
        )
    ):
        return False
    if (
        evidence_scope == 'domain_analogy'
        and value_origin != 'analogue'
    ):
        return False
    if evidence_scope == 'spatial_derivation':
        return bool(
            project_match == 'matched'
            and alignment_status
            in {'georeferenced', 'aligned_by_control_points'}
            and extraction_method == 'spatial_measurement'
        )
    return alignment_status == 'not_required'


def _is_sha256(value: str) -> bool:
    return len(value) == 64 and all(
        character in '0123456789abcdef'
        for character in value
    )


def _visual_locator_is_complete(
    locator: Mapping[str, Any],
) -> bool:
    page_number = locator.get('page_number')
    if not isinstance(page_number, int) or page_number < 1:
        return False
    bbox = locator.get('bbox')
    region = str(locator.get('source_region') or '').strip()
    return bool(
        region
        or (
            isinstance(bbox, Mapping | list)
            and bbox not in ({}, [])
        )
    )


def apply_structured_visual_field_proposals(
    next_batch: Mapping[str, Any],
    envelope: Mapping[str, Any],
    contributor_evidence: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Apply unambiguous visual proposals without promoting them to facts."""
    proposals_by_key = _visual_proposals_by_field(
        next_batch,
        contributor_evidence,
    )
    result = {
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
    sources_by_id = {
        str(source.get('source_id') or ''): source
        for source in result['source_inventory']
    }
    patch_by_key = {
        str(patch.get('field_key') or ''): patch
        for patch in result['patches']
    }
    for field_key, proposals in proposals_by_key.items():
        proposal = _select_unambiguous_visual_proposal(proposals)
        patch = patch_by_key.get(field_key)
        if (
            proposal is None
            or patch is None
            or not _proposal_may_replace_patch(proposal, patch)
        ):
            continue

        source_id = (
            f"{str(proposal['source_id'])}__vision__{field_key}"
        )
        source_locator = dict(proposal['source_locator'])
        source = {
            'source_id': source_id,
            'source_type': 'vision',
            'title': str(proposal.get('source_title') or source_id),
            'locator': json.dumps(
                {
                    **source_locator,
                    'source_sha256': proposal['source_sha256'],
                    'extraction_method': proposal['extraction_method'],
                    'evidence_scope': proposal['evidence_scope'],
                    'project_match': proposal['project_match'],
                    'alignment_status': proposal['alignment_status'],
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
            'url': None,
        }
        existing = sources_by_id.get(source_id)
        if existing is None:
            result['source_inventory'].append(source)
            sources_by_id[source_id] = source
        elif existing != source:
            continue

        patch.update(
            {
                'value': proposal['value'],
                'unit': proposal.get('unit'),
                'status': 'filled',
                'value_origin': proposal['value_origin'],
                'source_refs': [source_id],
                'source_locator': {
                    **source_locator,
                    'source_sha256': proposal['source_sha256'],
                    'proposal_source_id': proposal['source_id'],
                    'evidence_authority': 'project_visual_evidence',
                    'evidence_scope': proposal['evidence_scope'],
                    'project_match': proposal['project_match'],
                    'alignment_status': proposal['alignment_status'],
                    'extraction_method': proposal['extraction_method'],
                    'value_origin': proposal['value_origin'],
                },
                'retrieval_note': str(proposal['retrieval_note']),
            }
        )
    return result


def _visual_proposals_by_field(
    next_batch: Mapping[str, Any],
    contributor_evidence: Sequence[Mapping[str, Any]],
) -> dict[str, list[Mapping[str, Any]]]:
    allowed_keys = {
        str(field.get('field_key') or '')
        for field in next_batch.get('fields') or []
    }
    proposals_by_key: dict[str, list[Mapping[str, Any]]] = {}
    for evidence in contributor_evidence:
        if str(evidence.get('source_domain') or '').lower() != 'vision':
            continue
        for proposal in evidence.get('field_proposals') or []:
            if not isinstance(proposal, Mapping):
                continue
            field_key = str(proposal.get('field_key') or '')
            if field_key in allowed_keys:
                proposals_by_key.setdefault(field_key, []).append(proposal)
    return proposals_by_key


def _proposal_may_replace_patch(
    proposal: Mapping[str, Any],
    patch: Mapping[str, Any],
) -> bool:
    return not (
        proposal.get('value_origin') in {'calculated', 'analogue'}
        and patch.get('status') == 'filled'
        and str(patch.get('value_origin') or 'direct') == 'direct'
    )


def _select_unambiguous_visual_proposal(
    proposals: Sequence[Mapping[str, Any]],
) -> Mapping[str, Any] | None:
    priority = {'calculated': 0, 'analogue': 1}
    ranked = [
        proposal
        for proposal in proposals
        if str(proposal.get('value_origin') or '') in priority
    ]
    if not ranked:
        return None
    best_priority = min(
        priority[str(proposal.get('value_origin'))]
        for proposal in ranked
    )
    best = [
        proposal
        for proposal in ranked
        if priority[str(proposal.get('value_origin'))] == best_priority
    ]
    unique_values = {
        json.dumps(
            {
                'value': proposal.get('value'),
                'unit': proposal.get('unit'),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        for proposal in best
    }
    if len(unique_values) != 1:
        return None
    return best[0]
