from __future__ import annotations

import asyncio
import json

from open_webui.tools.geotizer import run_geotizer_workflow
from open_webui.utils.geotizer_vision import (
    apply_structured_visual_field_proposals,
    normalize_visual_field_proposals,
)


def batch():
    return {
        'batch_id': 'GIS-DC',
        'producer': 'GISagent_yulong',
        'policy_version': 'geotizer_assignments.v1',
        'template_version': 'geotizer_object.v1',
        'fields': [
            {'field_key': 'f1', 'row_id': 1},
            {'field_key': 'f2', 'row_id': 1},
        ],
        'evidence_routes': [],
    }


def envelope():
    return {
        'batch_id': 'GIS-DC',
        'producer': 'GISagent_yulong',
        'policy_version': 'geotizer_assignments.v1',
        'template_version': 'geotizer_object.v1',
        'source_inventory': [
            {
                'source_id': 's1',
                'source_type': 'gis',
                'title': 'linked project',
            }
        ],
        'patches': [
            {
                'field_key': 'f1',
                'value': 'direct value',
                'status': 'filled',
                'source_refs': ['s1'],
                'source_locator': {'layer': 'licence'},
            },
            {
                'field_key': 'f2',
                'value': None,
                'status': 'not_found',
                'value_origin': None,
                'source_refs': ['s1'],
                'source_locator': {'query': 'field f2'},
            },
        ],
    }


def visual_proposal(**overrides):
    value = {
        'field_key': 'f1',
        'value': 'Cu; Pb; Zn',
        'unit': None,
        'value_origin': 'calculated',
        'evidence_scope': 'visual_observation',
        'project_match': 'project_specific_source',
        'alignment_status': 'not_required',
        'source_id': 'map-1',
        'source_title': 'Project geological map',
        'source_sha256': 'a' * 64,
        'source_locator': {
            'project_id': 'project',
            'page_number': 1,
            'source_region': 'legend',
        },
        'extraction_method': 'vision_interpretation',
        'retrieval_note': (
            'РАСЧЕТНОЕ ЗНАЧЕНИЕ: interpreted from the project map.'
        ),
    }
    value.update(overrides)
    return value


def test_visual_proposal_requires_project_match_hash_and_exact_locator():
    valid = normalize_visual_field_proposals(
        {'field_proposals': [visual_proposal()]},
        allowed_field_keys=['f1'],
    )
    assert len(valid) == 1
    assert valid[0].value_origin == 'calculated'

    invalid = [
        visual_proposal(source_sha256='bad'),
        visual_proposal(project_match='unverified'),
        visual_proposal(source_locator={'page_number': 1}),
        visual_proposal(value_origin='direct'),
        visual_proposal(
            evidence_scope='spatial_derivation',
            alignment_status='not_required',
            extraction_method='spatial_measurement',
        ),
    ]
    for proposal in invalid:
        assert normalize_visual_field_proposals(
            {'field_proposals': [proposal]},
            allowed_field_keys=['f1'],
        ) == ()


def test_spatial_visual_proposal_requires_matched_aligned_project():
    proposal = visual_proposal(
        evidence_scope='spatial_derivation',
        project_match='matched',
        alignment_status='georeferenced',
        extraction_method='spatial_measurement',
    )

    normalized = normalize_visual_field_proposals(
        {'field_proposals': [proposal]},
        allowed_field_keys=['f1'],
    )

    assert len(normalized) == 1
    assert normalized[0].evidence_scope == 'spatial_derivation'


def test_visual_calculation_fills_gap_but_never_overrides_direct_fact():
    evidence = [
        {
            'source_domain': 'vision',
            'field_proposals': [visual_proposal()],
        }
    ]
    missing = envelope()
    missing['patches'][0] = {
        'field_key': 'f1',
        'value': None,
        'status': 'not_found',
        'value_origin': None,
        'source_refs': ['s1'],
        'source_locator': {'query': 'no direct fact'},
    }

    applied = apply_structured_visual_field_proposals(
        batch(),
        missing,
        evidence,
    )
    patch = applied['patches'][0]
    assert patch['status'] == 'filled'
    assert patch['value_origin'] == 'calculated'
    assert patch['source_locator']['source_sha256'] == 'a' * 64
    assert patch['source_locator']['evidence_authority'] == (
        'project_visual_evidence'
    )

    preserved = apply_structured_visual_field_proposals(
        batch(),
        envelope(),
        evidence,
    )
    assert preserved['patches'][0]['value'] == 'direct value'
    assert preserved['patches'][0].get('value_origin', 'direct') == 'direct'


def test_conflicting_visual_calculations_are_not_applied():
    evidence = [
        {
            'source_domain': 'vision',
            'field_proposals': [
                visual_proposal(value='Cu'),
                visual_proposal(value='Zn', source_id='map-2'),
            ],
        }
    ]
    missing = envelope()
    missing['patches'][0].update(
        {
            'value': None,
            'status': 'not_found',
            'value_origin': None,
        }
    )

    applied = apply_structured_visual_field_proposals(
        batch(),
        missing,
        evidence,
    )

    assert applied['patches'][0]['status'] == 'not_found'


def test_workflow_injects_and_applies_visual_evidence():
    submitted = []

    async def gis_call(payload):
        if payload['action'] == 'start':
            return {
                'workflow_status': 'collecting',
                'run_id': 'run-vision',
                'object_name': 'Object',
                'gis_project': {
                    'status': 'resolved',
                    'project_id': 'project',
                    'object_name': 'Object',
                },
                'datacube': {},
                'next_batch': batch(),
            }
        if payload['action'] == 'submit_batch':
            submitted.append(payload)
            return {
                'workflow_status': 'collecting',
                'run_id': 'run-vision',
                'next_batch': None,
            }
        return {
            'workflow_status': 'finalized',
            'run_id': 'run-vision',
            'xlsx': {
                'download_path': '/geotizer/files/run-vision/geotizer.xlsx'
            },
        }

    async def agent_call(task, prompt, object_name, datacube):
        if task.task_id == 'GIS-OBJECT-PROFILE':
            return json.dumps({'profile_status': 'unavailable'})
        request = json.loads(prompt)
        visual = next(
            item
            for item in request['context']['contributor_evidence']
            if item['source_domain'] == 'vision'
        )
        assert visual['evidence_authority'] == 'project_visual_evidence'
        value = envelope()
        value['patches'][0].update(
            {
                'value': None,
                'status': 'not_found',
                'value_origin': None,
            }
        )
        return json.dumps(value)

    async def vision_evidence_call(object_name, project_id, next_batch):
        assert object_name == 'Object'
        assert project_id == 'project'
        return {
            'project_match': 'project_specific_source',
            'field_proposals': [visual_proposal()],
        }

    asyncio.run(
        run_geotizer_workflow(
            object_name='Object',
            project_id=None,
            model_run_id=None,
            run_id=None,
            allow_draft=True,
            gis_call=gis_call,
            agent_call=agent_call,
            vision_evidence_call=vision_evidence_call,
        )
    )

    patch = next(
        patch
        for patch in submitted[0]['patches']
        if patch['field_key'] == 'f1'
    )
    assert patch['value'] == 'Cu; Pb; Zn'
    assert patch['value_origin'] == 'calculated'
    assert submitted[0]['source_inventory'][-1]['source_type'] == 'vision'
