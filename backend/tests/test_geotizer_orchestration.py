from __future__ import annotations

import asyncio
import json
from itertools import permutations

import pytest
from open_webui.tools.geotizer import run_geotizer_workflow
from open_webui.utils.geotizer_orchestration import (
    GeotizerOrchestrationError,
    bounded_text,
    build_batch_tasks,
    extract_json_object,
    extract_output_message_text,
    extract_owner_envelope,
    merge_owner_envelopes,
    normalize_delegator_message,
    partition_owner_batch,
    repair_negative_provenance,
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


def test_partition_owner_batch_is_ordered_bounded_and_filters_routes():
    value = batch()
    value['fields'] = [
        {'field_key': f'f{index}', 'row_id': index // 2}
        for index in range(85)
    ]
    value['evidence_routes'] = [
        {
            'route_id': 'KB-EVIDENCE',
            'producer': 'KBagent_yulong',
            'satisfied_by': 'contributor_call',
            'field_keys': [f'f{index}' for index in range(85)],
            'row_ids': list(range(43)),
        }
    ]
    chunks = partition_owner_batch(value, max_fields=40)
    assert [chunk['field_count'] for chunk in chunks] == [40, 40, 5]
    assert [chunk['owner_chunk'] for chunk in chunks] == [
        {'index': 1, 'total': 3},
        {'index': 2, 'total': 3},
        {'index': 3, 'total': 3},
    ]
    assert [
        field['field_key']
        for chunk in chunks
        for field in chunk['fields']
    ] == [f'f{index}' for index in range(85)]
    assert chunks[-1]['evidence_routes'][0]['field_keys'] == [
        f'f{index}' for index in range(80, 85)
    ]


def test_partition_owner_batch_preserves_exact_field_partition():
    for field_count in range(1, 181):
        for max_fields in (1, 2, 3, 7, 17, 40, 59, 60):
            value = batch()
            value['fields'] = [
                {'field_key': f'f{index}', 'row_id': index}
                for index in range(field_count)
            ]
            chunks = partition_owner_batch(value, max_fields=max_fields)
            flattened = [
                field['field_key']
                for chunk in chunks
                for field in chunk['fields']
            ]
            assert flattened == [f'f{index}' for index in range(field_count)]
            assert all(
                1 <= chunk['field_count'] <= max_fields
                for chunk in chunks
            )
            assert len(flattened) == len(set(flattened))


def test_merge_owner_envelopes_namespaces_conflicting_source_ids():
    value = batch()
    chunks = partition_owner_batch(value, max_fields=1)
    envelopes = []
    for index, chunk in enumerate(chunks, start=1):
        envelopes.append(
            {
                'batch_id': value['batch_id'],
                'producer': value['producer'],
                'policy_version': value['policy_version'],
                'template_version': value['template_version'],
                'source_inventory': [
                    {
                        'source_id': 'source',
                        'source_type': 'gis',
                        'title': f'chunk {index}',
                    }
                ],
                'patches': [
                    {
                        'field_key': chunk['fields'][0]['field_key'],
                        'value': None,
                        'status': 'not_found',
                        'source_refs': ['source'],
                    }
                ],
            }
        )
    merged = merge_owner_envelopes(
        value,
        chunks,
        envelopes,
        run_id='run-1',
    )
    assert [source['source_id'] for source in merged['source_inventory']] == [
        'source',
        'source__part_2',
    ]
    assert [patch['source_refs'] for patch in merged['patches']] == [
        ['source'],
        ['source__part_2'],
    ]
    assert validate_owner_envelope(value, merged) == ()


def test_repair_negative_provenance_registers_actual_owner_execution():
    value = batch()
    raw = envelope()
    raw['source_inventory'] = []
    for patch in raw['patches']:
        patch['value'] = None
        patch['status'] = 'not_found'
        patch['source_refs'] = []
    repaired = repair_negative_provenance(
        value,
        raw,
        run_id='run-1',
        attempt=2,
    )
    assert validate_owner_envelope(value, repaired) == ()
    assert repaired['source_inventory'] == [
        {
            'source_id': 'derived-negative-gis-dc-part-1-attempt-2',
            'source_type': 'derived',
            'title': 'GISagent_yulong completed negative search for GIS-DC',
            'locator': (
                'run_id=run-1; batch_id=GIS-DC; '
                'owner_chunk=1/1; attempt=2'
            ),
            'url': None,
        }
    ]
    assert all(
        patch['source_refs']
        == ['derived-negative-gis-dc-part-1-attempt-2']
        for patch in repaired['patches']
    )
    assert raw['source_inventory'] == []
    assert all(patch['source_refs'] == [] for patch in raw['patches'])


def test_repair_negative_provenance_does_not_mask_positive_or_unknown_refs():
    value = batch()
    raw = envelope()
    raw['source_inventory'] = []
    raw['patches'][0]['source_refs'] = []
    raw['patches'][1]['source_refs'] = ['unknown']
    repaired = repair_negative_provenance(
        value,
        raw,
        run_id='run-1',
        attempt=1,
    )
    violations = validate_owner_envelope(value, repaired)
    assert any('source_refs must be non-empty' in item for item in violations)
    assert any('unregistered source_refs' in item for item in violations)
    assert repaired['source_inventory'] == []


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


def test_extract_owner_envelope_selects_only_exact_partition_candidate():
    evidence = {'status': 'searched', 'query': 'object'}
    incomplete = {
        **envelope(),
        'patches': envelope()['patches'][:1],
    }
    rendered = '\n'.join(
        [
            json.dumps(evidence),
            json.dumps(incomplete),
            json.dumps(envelope()),
        ]
    )
    selected = extract_owner_envelope(rendered, batch())
    assert selected == envelope()


def test_extract_owner_envelope_rejects_two_distinct_exact_candidates():
    first = envelope()
    second = envelope()
    second['patches'][0]['value'] = 'different'
    rendered = f'{json.dumps(first)}\n{json.dumps(second)}'
    with pytest.raises(
        GeotizerOrchestrationError,
        match='matching_candidates=2',
    ):
        extract_owner_envelope(rendered, batch())


def test_extract_owner_envelope_recovers_exact_candidate_from_json_array():
    rendered = json.dumps([{'status': 'searched'}, envelope()])
    assert extract_owner_envelope(rendered, batch()) == envelope()


def test_extract_output_message_text_reads_latest_openwebui_output_text():
    message = {
        'content': '',
        'done': True,
        'output': [
            {'type': 'message', 'content': [{'type': 'output_text', 'text': ''}]},
            {
                'type': 'message',
                'content': [{'type': 'output_text', 'text': '{"batch_id":"GIS-DC"}'}],
            },
        ],
    }
    assert extract_output_message_text(message) == '{"batch_id":"GIS-DC"}'


def test_extract_output_message_text_preserves_legacy_content():
    message = {
        'content': 'legacy final response',
        'output': [
            {
                'type': 'message',
                'content': [{'type': 'output_text', 'text': 'new response'}],
            }
        ],
    }
    assert extract_output_message_text(message) == 'legacy final response'


def test_normalize_delegator_message_is_non_mutating():
    message = {
        'content': '',
        'output': [
            {
                'type': 'message',
                'content': [{'type': 'text', 'text': 'final response'}],
            }
        ],
    }
    normalized = normalize_delegator_message(message)
    assert normalized == {**message, 'content': 'final response'}
    assert message['content'] == ''


def test_normalize_completed_message_without_final_text_returns_explicit_marker():
    message = {
        'content': '',
        'done': True,
        'output': [
            {'type': 'function_call_output', 'output': '{"matches": 0}'},
            {'type': 'reasoning', 'content': 'finished'},
        ],
    }
    normalized = normalize_delegator_message(message)
    recovered = json.loads(normalized['content'])
    assert recovered['status'] == 'completed_without_final_text'
    assert message['content'] == ''


def test_normalize_incomplete_message_without_text_keeps_polling():
    message = {'content': '', 'done': False, 'output': None}
    assert normalize_delegator_message(message) is message


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


def test_bounded_evidence_keeps_head_and_provenance_tail():
    value = 'A' * 100 + 'TAIL'
    result = bounded_text(value, max_chars=40)
    assert result.startswith('A' * 30)
    assert result.endswith('TAIL')
    assert 'omitted by orchestrator' in result


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


def test_workflow_chunks_large_owner_output_and_submits_one_atomic_batch():
    large = {
        'batch_id': 'KB-RESOURCE-TECH',
        'producer': 'KBagent_yulong',
        'policy_version': 'geotizer_assignments.v1',
        'template_version': 'geotizer_object.v1',
        'fields': [
            {'field_key': f'f{index}', 'row_id': index}
            for index in range(81)
        ],
        'evidence_routes': [],
    }
    owner_calls = 0
    submitted = []

    async def gis_call(payload):
        if payload['action'] == 'start':
            return {
                'workflow_status': 'collecting',
                'run_id': 'run-large',
                'object_name': 'Object',
                'datacube': {},
                'next_batch': large,
            }
        if payload['action'] == 'submit_batch':
            submitted.append(payload)
            return {
                'workflow_status': 'collecting',
                'run_id': 'run-large',
                'next_batch': None,
            }
        return {
            'workflow_status': 'finalized',
            'run_id': 'run-large',
            'xlsx': {
                'download_path': '/geotizer/files/run-large/geotizer.xlsx',
            },
        }

    async def agent_call(task, prompt, object_name, datacube):
        nonlocal owner_calls
        owner_calls += 1
        request = json.loads(prompt)
        chunk = request['context']['batch']
        source_id = 'shared-source'
        return json.dumps(
            {
                'batch_id': large['batch_id'],
                'producer': large['producer'],
                'policy_version': large['policy_version'],
                'template_version': large['template_version'],
                'source_inventory': [
                    {
                        'source_id': source_id,
                        'source_type': 'knowledge_base',
                        'title': f"chunk {chunk['owner_chunk']['index']}",
                    }
                ],
                'patches': [
                    {
                        'field_key': field['field_key'],
                        'value': None,
                        'status': 'not_found',
                        'source_refs': [source_id],
                    }
                    for field in chunk['fields']
                ],
            }
        )

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
    assert owner_calls == 3
    assert len(submitted) == 1
    assert len(submitted[0]['patches']) == 81
    assert len(submitted[0]['source_inventory']) == 3


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
