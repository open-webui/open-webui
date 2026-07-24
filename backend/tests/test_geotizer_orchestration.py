from __future__ import annotations

import asyncio
import json
from itertools import permutations

import pytest
from open_webui.tools.geotizer import run_geotizer_workflow
from open_webui.utils.geotizer_orchestration import (
    GeotizerOrchestrationError,
    build_batch_tasks,
    extract_json_object,
    validate_owner_envelope,
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
        'evidence_routes': [
            {
                'route_id': 'DATACUBE-EVIDENCE',
                'producer': 'DataCube Reviewer',
                'output': 'modeling_evidence',
                'satisfied_by': 'start.datacube',
            },
            {
                'route_id': 'KB-EVIDENCE',
                'producer': 'KBagent_yulong',
                'output': 'evidence_bundle',
                'satisfied_by': 'contributor_call',
            },
            {
                'route_id': 'WEB-EVIDENCE',
                'producer': 'WEBagent_yulong',
                'output': 'evidence_bundle',
                'satisfied_by': 'contributor_call',
            },
        ],
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
                'value': 'value',
                'status': 'filled',
                'source_refs': ['s1'],
                'source_locator': {'layer': 'licence'},
            },
            {
                'field_key': 'f2',
                'value': None,
                'status': 'not_found',
                'source_refs': ['s1'],
                'source_locator': {'query': 'field f2'},
            },
        ],
    }


def test_batch_plan_runs_contributors_before_exact_owner():
    tasks = build_batch_tasks(batch())
    assert [(task.role, task.producer) for task in tasks] == [
        ('contributor', 'KBagent_yulong'),
        ('contributor', 'WEBagent_yulong'),
        ('owner', 'GISagent_yulong'),
    ]


def test_batch_plan_owner_is_last_for_every_route_permutation():
    original = batch()
    for routes in permutations(original['evidence_routes']):
        value = {**original, 'evidence_routes': list(routes)}
        tasks = build_batch_tasks(value)
        assert tasks[-1].role == 'owner'
        assert tasks[-1].producer == value['producer']
        assert all(task.role == 'contributor' for task in tasks[:-1])
        assert all(task.producer != 'DataCube Reviewer' for task in tasks)


def test_batch_plan_rejects_unknown_owner():
    value = batch()
    value['producer'] = 'InventedAgent'
    with pytest.raises(GeotizerOrchestrationError, match='Unsupported'):
        build_batch_tasks(value)


@pytest.mark.parametrize(
    'rendered',
    [
        json.dumps(envelope()),
        f'```json\n{json.dumps(envelope())}\n```',
        f'Result:\n{json.dumps(envelope())}',
    ],
)
def test_extract_json_object_accepts_one_unambiguous_object(rendered):
    assert extract_json_object(rendered)['batch_id'] == 'GIS-DC'


def test_owner_envelope_requires_exact_field_partition():
    value = envelope()
    value['patches'][1]['field_key'] = 'foreign'
    violations = validate_owner_envelope(batch(), value)
    assert any('missing field_key' in item for item in violations)
    assert any('foreign field_key' in item for item in violations)


def test_owner_envelope_requires_registered_provenance_for_negative_result():
    value = envelope()
    value['patches'][1]['source_refs'] = ['missing']
    violations = validate_owner_envelope(batch(), value)
    assert any('unregistered source_refs' in item for item in violations)


def test_workflow_drives_start_contributors_owner_submit_finalize():
    calls = []
    current_batch = batch()

    async def gis_call(payload):
        calls.append(('gis', payload['action']))
        if payload['action'] == 'start':
            return {
                'workflow_status': 'collecting',
                'run_id': 'run-1',
                'object_name': 'Object',
                'datacube': {'workflow_status': 'ready'},
                'next_batch': current_batch,
            }
        if payload['action'] == 'submit_batch':
            assert payload['run_id'] == 'run-1'
            return {
                'workflow_status': 'collecting',
                'run_id': 'run-1',
                'object_name': 'Object',
                'datacube': {'workflow_status': 'ready'},
                'next_batch': None,
            }
        if payload['action'] == 'finalize':
            return {
                'workflow_status': 'finalized',
                'run_id': 'run-1',
                'object_name': 'Object',
                'counts': {'filled': 1, 'not_found': 1},
                'xlsx': {
                    'download_path': ('/geotizer/files/run-1/geotizer.xlsx'),
                    'sha256': 'abc',
                },
            }
        raise AssertionError(payload)

    async def agent_call(task, prompt, object_name, datacube):
        calls.append(('agent', task.role, task.producer))
        if task.role == 'owner':
            return json.dumps(envelope())
        return 'bounded evidence'

    final = asyncio.run(
        run_geotizer_workflow(
            object_name='Object',
            project_id=None,
            model_run_id=None,
            run_id=None,
            allow_draft=True,
            gis_call=gis_call,
            agent_call=agent_call,
        )
    )
    assert final['workflow_status'] == 'finalized'
    assert calls == [
        ('gis', 'start'),
        ('agent', 'contributor', 'KBagent_yulong'),
        ('agent', 'contributor', 'WEBagent_yulong'),
        ('agent', 'owner', 'GISagent_yulong'),
        ('gis', 'submit_batch'),
        ('gis', 'finalize'),
    ]


def test_workflow_repairs_invalid_owner_output_before_submission():
    owner_attempts = 0
    gis_actions = []

    async def gis_call(payload):
        gis_actions.append(payload['action'])
        if payload['action'] == 'start':
            return {
                'workflow_status': 'collecting',
                'run_id': 'run-1',
                'object_name': 'Object',
                'datacube': {},
                'next_batch': batch(),
            }
        if payload['action'] == 'submit_batch':
            return {
                'workflow_status': 'collecting',
                'run_id': 'run-1',
                'next_batch': None,
            }
        return {
            'workflow_status': 'finalized',
            'run_id': 'run-1',
            'xlsx': {'download_path': '/geotizer/files/run-1/geotizer.xlsx'},
        }

    async def agent_call(task, prompt, object_name, datacube):
        nonlocal owner_attempts
        if task.role == 'contributor':
            return 'evidence'
        owner_attempts += 1
        if owner_attempts == 1:
            return '{"patches": []}'
        return json.dumps(envelope())

    asyncio.run(
        run_geotizer_workflow(
            object_name='Object',
            project_id=None,
            model_run_id=None,
            run_id=None,
            allow_draft=True,
            gis_call=gis_call,
            agent_call=agent_call,
        )
    )
    assert owner_attempts == 2
    assert gis_actions.count('submit_batch') == 1
