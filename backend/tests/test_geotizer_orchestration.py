from __future__ import annotations

import asyncio
import json
from itertools import permutations

import pytest
from open_webui.tools.geotizer import (
    _contributor_prompt,
    _gis_error_user_message,
    _owner_prompt,
    run_geotizer_workflow,
)
from open_webui.utils.geotizer_orchestration import (
    AgentTask,
    GeotizerOrchestrationError,
    apply_structured_gis_field_proposals,
    bounded_text,
    build_batch_tasks,
    build_knowledge_search_plan,
    correct_explicitly_derived_value_origins,
    execution_mode_for_task,
    extract_json_object,
    extract_output_message_text,
    extract_owner_envelope,
    merge_owner_envelopes,
    normalize_contributor_evidence,
    normalize_delegator_message,
    normalize_gis_field_proposals,
    normalize_gis_object_profile,
    owner_completion_valves,
    owner_failure_envelope,
    partition_owner_batch,
    repair_negative_provenance,
    validate_owner_envelope,
)


@pytest.mark.parametrize(
    ('retrieval_note', 'expected_origin'),
    [
        (
            'Тип переработки по аналогии с рудно-россыпными месторождениями',
            'analogue',
        ),
        (
            'Главные нерудные минералы по региональному геологическому контексту',
            'analogue',
        ),
        (
            'Второстепенные минералы-носители на основе региональной геологии',
            'analogue',
        ),
        (
            'Вредные примеси по геохимическим данным региона',
            'analogue',
        ),
        (
            'Категория сложности по модели prospectivity',
            'calculated',
        ),
        (
            'Тип отработки по типу месторождения',
            'calculated',
        ),
        (
            'Прямое значение атрибута объекта',
            'direct',
        ),
    ],
)
def test_explicit_derivation_note_corrects_false_direct_origin(
    retrieval_note,
    expected_origin,
):
    value = envelope()
    value['patches'][0].update(
        {
            'status': 'filled',
            'value': 'candidate',
            'value_origin': 'direct',
            'retrieval_note': retrieval_note,
        }
    )

    corrected = correct_explicitly_derived_value_origins(value)

    assert corrected['patches'][0]['value_origin'] == expected_origin
    assert value['patches'][0]['value_origin'] == 'direct'


@pytest.mark.parametrize('declared_origin', ['calculated', 'analogue'])
def test_explicit_origin_is_never_downgraded(declared_origin):
    value = envelope()
    value['patches'][0].update(
        {
            'status': 'filled',
            'value': 'candidate',
            'value_origin': declared_origin,
            'retrieval_note': 'Прямое значение атрибута объекта',
        }
    )

    corrected = correct_explicitly_derived_value_origins(value)

    assert corrected['patches'][0]['value_origin'] == declared_origin


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


def test_all_owners_are_tool_free_and_contributors_keep_specialist_tools():
    tasks = build_batch_tasks(batch())

    assert all(
        execution_mode_for_task(task) == 'specialist_contributor'
        for task in tasks[:-1]
    )
    assert (
        execution_mode_for_task(tasks[-1])
        == 'specialist_owner_completion'
    )


def test_skilled_owner_uses_existing_tool_free_subagent():
    task = AgentTask(
        kind='skilled',
        producer='SkilledAgent',
        role='owner',
        task_id='ASSEMBLE',
        payload={},
    )

    assert execution_mode_for_task(task) == 'tool_free_owner'


def test_owner_completion_valves_disable_all_retrieval_paths():
    values = owner_completion_valves(
        {
            'use_ui_compatible_flow_for_builtin_agents': True,
            'ui_flow_agents': 'kb,web,gis',
            'gis_tool_ids': 'server:mcpgis',
            'web_tool_ids': 'web',
            'kb_tool_ids': 'kb',
            'direct_tool_agents': 'gis',
            'gis_openapi_base_url': 'http://gis',
            'web_openapi_base_url': 'http://web',
            'kb_openapi_base_url': 'http://kb',
            'enable_web_search_feature': True,
            'execute_kb_builtin_tools_in_process': True,
            'gis_model': 'gisagentyulong',
        }
    )

    assert values['gis_model'] == 'gisagentyulong'
    assert values['use_ui_compatible_flow_for_builtin_agents'] is False
    assert values['ui_flow_agents'] == ''
    assert values['gis_tool_ids'] == ''
    assert values['web_tool_ids'] == ''
    assert values['kb_tool_ids'] == ''
    assert values['direct_tool_agents'] == ''
    assert values['gis_openapi_base_url'] == ''
    assert values['web_openapi_base_url'] == ''
    assert values['kb_openapi_base_url'] == ''
    assert values['enable_web_search_feature'] is False
    assert values['execute_kb_builtin_tools_in_process'] is False


def test_linked_project_gis_evidence_has_direct_authority():
    evidence = normalize_contributor_evidence(
        {
            'route_id': 'GIS-EVIDENCE',
            'producer': 'GISagent_yulong',
            'source_domain': 'gis',
            'relation_to_object': 'deposit_analogue',
            'output': (
                'geotizer_object.v1.r028.a01=1966; '
                'layer=IzuchA; feature=record-1'
            ),
        }
    )

    assert evidence['relation_to_object'] == 'direct'
    assert evidence['evidence_authority'] == 'linked_gis_project'
    assert 'cannot negate' in evidence['negative_search_precedence']


def test_non_gis_evidence_cannot_self_promote_to_linked_project_authority():
    evidence = normalize_contributor_evidence(
        {
            'producer': 'KBagent_yulong',
            'source_domain': 'kb',
            'relation_to_object': 'deposit_analogue',
            'evidence_authority': 'contributor',
            'output': 'regional analogue',
        }
    )

    assert evidence['relation_to_object'] == 'deposit_analogue'
    assert evidence['evidence_authority'] == 'contributor'


def test_gis_field_proposals_require_bounded_key_value_origin_and_locator():
    proposals = normalize_gis_field_proposals(
        json.dumps(
            {
                'field_proposals': [
                    {
                        'field_key': 'f1',
                        'value': 150,
                        'unit': 'km',
                        'value_origin': 'calculated',
                        'relation_to_object': 'direct',
                        'source_id': 'gis-calc',
                        'source_title': 'GIS calculation',
                        'source_locator': {
                            'project_id': 'project',
                            'layer_id': 'routes',
                            'feature_or_query': 'sum(length)',
                        },
                        'retrieval_note': 'Calculated from route geometry.',
                    },
                    {
                        'field_key': 'foreign',
                        'value': 'must be ignored',
                        'value_origin': 'direct',
                        'source_id': 'foreign',
                        'source_locator': {'layer_id': 'foreign'},
                    },
                    {
                        'field_key': 'f2',
                        'value': 'untraceable',
                        'value_origin': 'analogue',
                        'source_id': 'missing-locator',
                        'retrieval_note': 'Analogue transfer.',
                    },
                ]
            }
        ),
        allowed_field_keys=['f1', 'f2'],
    )

    assert len(proposals) == 1
    assert proposals[0].field_key == 'f1'
    assert proposals[0].value == 150
    assert proposals[0].value_origin == 'calculated'


@pytest.mark.parametrize(
    ('value_origin', 'expected_applied'),
    (
        ('direct', True),
        ('calculated', True),
        ('analogue', True),
    ),
)
def test_structured_gis_proposals_fill_negative_owner_alternatives(
    value_origin,
    expected_applied,
):
    raw = envelope()
    raw['patches'][0] = {
        'field_key': 'f1',
        'value': None,
        'status': 'not_found',
        'source_refs': ['s1'],
        'source_locator': {'query': 'negative owner result'},
    }
    relation = (
        'deposit_analogue'
        if value_origin == 'analogue'
        else 'direct'
    )
    proposal = {
        'field_key': 'f1',
        'value': 42,
        'unit': 'km',
        'value_origin': value_origin,
        'relation_to_object': relation,
        'source_id': f'gis-{value_origin}',
        'source_title': 'GIS proposal',
        'source_locator': {
            'project_id': 'project',
            'layer_id': 'layer',
            'feature_or_query': 'feature=1',
        },
        'retrieval_note': f'{value_origin} basis',
    }
    result = apply_structured_gis_field_proposals(
        batch(),
        raw,
        [
            {
                'source_domain': 'gis',
                'field_proposals': [proposal],
            }
        ],
    )

    assert (result['patches'][0]['status'] == 'filled') is expected_applied
    assert result['patches'][0]['value'] == 42
    assert result['patches'][0]['value_origin'] == value_origin
    assert (
        result['patches'][0]['source_locator']['value_origin']
        == value_origin
    )
    assert validate_owner_envelope(batch(), result) == ()


def test_calculated_gis_proposal_does_not_replace_direct_owner_fact():
    raw = envelope()
    raw['patches'][0]['value_origin'] = 'direct'
    result = apply_structured_gis_field_proposals(
        batch(),
        raw,
        [
            {
                'source_domain': 'gis',
                'field_proposals': [
                    {
                        'field_key': 'f1',
                        'value': 'alternative',
                        'value_origin': 'calculated',
                        'relation_to_object': 'direct',
                        'source_id': 'gis-calc',
                        'source_title': 'GIS calculation',
                        'source_locator': {'layer_id': 'layer'},
                        'retrieval_note': 'Calculated fallback.',
                    }
                ],
            }
        ],
    )

    assert result['patches'][0]['value'] == 'value'
    assert result['patches'][0]['value_origin'] == 'direct'
    assert {source['source_id'] for source in result['source_inventory']} == {
        's1'
    }


def test_owner_envelope_requires_explanation_for_derived_value():
    value = envelope()
    value['patches'][0]['value_origin'] = 'calculated'
    value['patches'][0].pop('retrieval_note', None)

    violations = validate_owner_envelope(batch(), value)

    assert any(
        'calculated requires retrieval_note' in violation
        for violation in violations
    )


def test_conflicting_equal_priority_gis_proposals_do_not_override_owner():
    raw = envelope()
    raw['patches'][0] = {
        'field_key': 'f1',
        'value': None,
        'status': 'not_found',
        'source_refs': ['s1'],
        'source_locator': {'query': 'negative owner result'},
    }
    proposals = [
        {
            'field_key': 'f1',
            'value': value,
            'value_origin': 'direct',
            'relation_to_object': 'direct',
            'source_id': f'gis-{value}',
            'source_title': 'GIS direct',
            'source_locator': {'layer_id': 'layer'},
            'retrieval_note': 'Direct fact.',
        }
        for value in ('left', 'right')
    ]
    result = apply_structured_gis_field_proposals(
        batch(),
        raw,
        [{'source_domain': 'gis', 'field_proposals': proposals}],
    )

    assert result['patches'][0]['status'] == 'not_found'
    assert len(result['source_inventory']) == 1


def test_prompts_make_direct_gis_precedence_explicit():
    tasks = build_batch_tasks(
        {
            **batch(),
            'evidence_routes': [
                {
                    'route_id': 'GIS-EVIDENCE',
                    'producer': 'GISagent_yulong',
                    'output': 'evidence_bundle',
                    'satisfied_by': 'contributor_call',
                }
            ],
        }
    )
    contributor = tasks[0]
    contributor_request = json.loads(
        _contributor_prompt(
            object_name='Нияюская площадь',
            run_id='run',
            task=contributor,
            next_batch=batch(),
            knowledge_search_plan={},
        )
    )
    assert any(
        'direct object evidence' in rule
        for rule in contributor_request['rules']
    )
    assert (
        contributor_request['output_contract']['field_proposals'][0][
            'value_origin'
        ]
        == 'direct|calculated|analogue'
    )

    context = {
        'batch': batch(),
        'knowledge_search_plan': {},
        'contributor_evidence': [
            normalize_contributor_evidence(
                {
                    'source_domain': 'gis',
                    'output': 'field_key=f1; value=1966; layer=IzuchA',
                }
            )
        ],
    }
    owner_request = json.loads(
        _owner_prompt(
            context=context,
            attempt=1,
            feedback=None,
            previous_output='',
        )
    )
    rules = '\n'.join(owner_request['rules'])
    assert 'knowledge-base or web miss cannot negate' in rules
    assert 'do not return not_found solely because' in rules
    assert 'Calculated or analogue alternatives are allowed' in rules


def test_workflow_marks_gis_contributor_evidence_as_direct():
    gis_batch = {
        **batch(),
        'evidence_routes': [
            {
                'route_id': 'GIS-EVIDENCE',
                'producer': 'GISagent_yulong',
                'output': 'evidence_bundle',
                'satisfied_by': 'contributor_call',
            }
        ],
    }

    async def gis_call(payload):
        if payload['action'] == 'start':
            return {
                'workflow_status': 'collecting',
                'run_id': 'run-gis-authority',
                'object_name': 'Нияюская площадь',
                'datacube': {},
                'next_batch': gis_batch,
            }
        if payload['action'] == 'submit_batch':
            return {
                'workflow_status': 'collecting',
                'run_id': 'run-gis-authority',
                'next_batch': None,
            }
        return {
            'workflow_status': 'finalized',
            'run_id': 'run-gis-authority',
            'xlsx': {
                'download_path': (
                    '/geotizer/files/run-gis-authority/geotizer.xlsx'
                )
            },
        }

    async def agent_call(task, prompt, object_name, datacube):
        if task.role == 'contributor':
            return 'field_key=f1; value=1966; layer=IzuchA; feature=1'
        request = json.loads(prompt)
        evidence = request['context']['contributor_evidence']
        assert evidence[0]['source_domain'] == 'gis'
        assert evidence[0]['relation_to_object'] == 'direct'
        assert evidence[0]['evidence_authority'] == 'linked_gis_project'
        return json.dumps(envelope())

    final = asyncio.run(
        run_geotizer_workflow(
            object_name='Нияюская площадь',
            project_id=None,
            model_run_id=None,
            run_id=None,
            allow_draft=True,
            gis_call=gis_call,
            agent_call=agent_call,
        )
    )

    assert final['workflow_status'] == 'finalized'


def test_workflow_applies_structured_calculated_gis_proposal_before_submit():
    submitted = []
    gis_batch = {
        **batch(),
        'evidence_routes': [
            {
                'route_id': 'GIS-EVIDENCE',
                'producer': 'GISagent_yulong',
                'output': 'evidence_bundle',
                'satisfied_by': 'contributor_call',
            }
        ],
    }

    async def gis_call(payload):
        if payload['action'] == 'start':
            return {
                'workflow_status': 'collecting',
                'run_id': 'run-gis-proposal',
                'object_name': 'Object',
                'datacube': {},
                'next_batch': gis_batch,
            }
        if payload['action'] == 'submit_batch':
            submitted.append(payload)
            return {
                'workflow_status': 'collecting',
                'run_id': 'run-gis-proposal',
                'next_batch': None,
            }
        return {
            'workflow_status': 'finalized',
            'run_id': 'run-gis-proposal',
            'xlsx': {
                'download_path': (
                    '/geotizer/files/run-gis-proposal/geotizer.xlsx'
                )
            },
        }

    async def agent_call(task, prompt, object_name, datacube):
        if task.role == 'contributor':
            return json.dumps(
                {
                    'field_proposals': [
                        {
                            'field_key': 'f1',
                            'value': 150,
                            'unit': 'km',
                            'value_origin': 'calculated',
                            'relation_to_object': 'direct',
                            'source_id': 'gis-routes',
                            'source_title': 'GIS route calculation',
                            'source_locator': {
                                'project_id': 'project',
                                'layer_id': 'routes',
                                'feature_or_query': 'sum(length)',
                            },
                            'retrieval_note': (
                                'Calculated from linked-project route '
                                'geometry.'
                            ),
                        }
                    ]
                }
            )
        value = envelope()
        value['patches'][0] = {
            'field_key': 'f1',
            'value': None,
            'status': 'not_found',
            'source_refs': ['s1'],
            'source_locator': {'query': 'owner negative result'},
        }
        return json.dumps(value)

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

    patch = next(
        patch
        for patch in submitted[0]['patches']
        if patch['field_key'] == 'f1'
    )
    assert patch['status'] == 'filled'
    assert patch['value'] == 150
    assert patch['value_origin'] == 'calculated'
    assert patch['source_locator']['evidence_authority'] == (
        'linked_gis_project'
    )


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
        'gis-dc__part_1__source',
        'gis-dc__part_2__source',
    ]
    assert [patch['source_refs'] for patch in merged['patches']] == [
        ['gis-dc__part_1__source'],
        ['gis-dc__part_2__source'],
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


def test_gis_profile_keeps_deterministic_project_resolution_and_deduplicates():
    profile = normalize_gis_object_profile(
        json.dumps(
            {
                'project_resolution': {'status': 'not_found'},
                'location_terms': ['ЯНАО', '  янао  ', 'Полярный Урал'],
                'commodity_terms': ['золото'],
                'deposit_type_terms': ['золото-кварцевый'],
                'geology_terms': ['зеленокаменный пояс'],
                'evidence': [
                    {
                        'source_id': 'gis-1',
                        'layer_id': 'NiyaU_PLG',
                        'feature_or_query': 'feature=0',
                        'fact': 'ЯНАО',
                    }
                ],
            },
            ensure_ascii=False,
        ),
        object_name='Нияюская площадь',
        project_id='Нияюская_площадь',
    )

    rendered = profile.as_dict()
    assert rendered['project_resolution'] == {
        'status': 'resolved',
        'project_id': 'Нияюская_площадь',
        'object_name': 'Нияюская площадь',
        'authority': 'geotizer_start',
    }
    assert rendered['location_terms'] == ['ЯНАО', 'Полярный Урал']
    assert rendered['profile_status'] == 'ready'


def test_knowledge_search_plan_preserves_authority_order_and_direct_queries():
    profile = normalize_gis_object_profile(
        json.dumps(
            {
                'location_terms': ['ЯНАО'],
                'commodity_terms': ['золото'],
                'deposit_type_terms': ['золото-кварцевый'],
                'geology_terms': ['Полярный Урал'],
                'evidence': [{'source_id': 'gis-1'}],
            },
            ensure_ascii=False,
        ),
        object_name='Нияюская площадь',
        project_id='Нияюская_площадь',
    )
    plan = build_knowledge_search_plan(profile)

    assert [
        tier['relation_to_object']
        for tier in plan['tiers']
    ] == ['direct', 'regional_context', 'deposit_analogue']
    assert plan['tiers'][0]['enabled'] is True
    assert 'Нияюская площадь' in plan['tiers'][0]['query_terms']
    assert 'Нияюская_площадь' in plan['tiers'][0]['query_terms']
    assert plan['tiers'][1]['query_terms'] == ['ЯНАО', 'Полярный Урал']
    assert plan['tiers'][2]['query_terms'] == [
        'золото',
        'золото-кварцевый',
        'Полярный Урал',
    ]


def test_unavailable_gis_profile_keeps_direct_knowledge_search_enabled():
    profile = normalize_gis_object_profile(
        'not JSON',
        object_name='Нияюская площадь',
        project_id='Нияюская_площадь',
    )
    plan = build_knowledge_search_plan(profile)

    assert profile.profile_status == 'unavailable'
    assert plan['tiers'][0]['enabled'] is True
    assert plan['tiers'][1]['enabled'] is False
    assert plan['tiers'][2]['enabled'] is False


def test_gis_descriptors_without_exact_evidence_do_not_enable_indirect_search():
    profile = normalize_gis_object_profile(
        json.dumps(
            {
                'location_terms': ['ЯНАО'],
                'commodity_terms': ['золото'],
                'deposit_type_terms': ['золото-кварцевый'],
                'evidence': [],
            },
            ensure_ascii=False,
        ),
        object_name='Нияюская площадь',
        project_id='Нияюская_площадь',
    )
    plan = build_knowledge_search_plan(profile)

    assert profile.profile_status == 'partial'
    assert profile.location_terms == ()
    assert profile.commodity_terms == ()
    assert plan['tiers'][1]['enabled'] is False
    assert plan['tiers'][2]['enabled'] is False
    assert 'exact GIS evidence locator' in profile.diagnostics[0]


def test_gis_error_message_never_calls_resolved_project_missing():
    message = _gis_error_user_message(
        {
            'violations': [
                {
                    'context': {
                        'gis_project': {
                            'status': 'resolved',
                            'project_id': 'Нияюская_площадь',
                        },
                        'failure_stage': 'licence_scope_binding',
                    }
                }
            ]
        },
        fallback='generic failure',
    )

    assert 'Нияюская_площадь' in message
    assert 'найден' in message
    assert 'не найден' not in message
    assert 'licence_scope_binding' in message


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


def test_workflow_derives_gis_profile_before_relation_aware_kb_owner():
    calls = []
    kb_batch = {
        **batch(),
        'batch_id': 'KB-GEO',
        'producer': 'KBagent_yulong',
        'evidence_routes': [],
    }

    async def gis_call(payload):
        calls.append(('gis', payload['action']))
        if payload['action'] == 'start':
            return {
                'workflow_status': 'collecting',
                'run_id': 'run-profile',
                'project_id': 'Нияюская_площадь',
                'object_name': 'Нияюская площадь',
                'gis_project': {
                    'status': 'resolved',
                    'project_id': 'Нияюская_площадь',
                    'object_name': 'Нияюская площадь',
                },
                'datacube': {},
                'next_batch': kb_batch,
            }
        if payload['action'] == 'submit_batch':
            return {
                'workflow_status': 'collecting',
                'run_id': 'run-profile',
                'next_batch': None,
            }
        return {
            'workflow_status': 'finalized',
            'run_id': 'run-profile',
            'xlsx': {
                'download_path': (
                    '/geotizer/files/run-profile/geotizer.xlsx'
                )
            },
        }

    async def agent_call(task, prompt, object_name, datacube):
        calls.append(('agent', task.task_id))
        request = json.loads(prompt)
        if task.task_id == 'GIS-OBJECT-PROFILE':
            assert request['gis_project']['status'] == 'resolved'
            return json.dumps(
                {
                    'location_terms': ['ЯНАО'],
                    'commodity_terms': ['золото'],
                    'deposit_type_terms': ['золото-кварцевый'],
                    'geology_terms': ['Полярный Урал'],
                    'evidence': [{'source_id': 'gis-profile'}],
                },
                ensure_ascii=False,
            )

        search_plan = request['context']['knowledge_search_plan']
        assert [
            tier['relation_to_object']
            for tier in search_plan['tiers']
        ] == ['direct', 'regional_context', 'deposit_analogue']
        value = envelope()
        value['batch_id'] = 'KB-GEO'
        value['producer'] = 'KBagent_yulong'
        return json.dumps(value)

    final = asyncio.run(
        run_geotizer_workflow(
            object_name='Нияюская площадь',
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
        ('agent', 'GIS-OBJECT-PROFILE'),
        ('agent', 'KB-GEO'),
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
    assert {
        source['source_id']
        for source in submitted[0]['source_inventory']
    } == {
        'kb-resource-tech__part_1__shared-source',
        'kb-resource-tech__part_2__shared-source',
        'kb-resource-tech__part_3__shared-source',
    }
    assert {
        patch['source_refs'][0]
        for patch in submitted[0]['patches']
    } == {
        'kb-resource-tech__part_1__shared-source',
        'kb-resource-tech__part_2__shared-source',
        'kb-resource-tech__part_3__shared-source',
    }


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


def test_workflow_fails_closed_after_invalid_owner_attempts():
    owner_attempts = 0
    submitted = []

    async def gis_call(payload):
        if payload['action'] == 'start':
            return {
                'workflow_status': 'collecting',
                'run_id': 'run-fail-closed',
                'object_name': 'Object',
                'datacube': {},
                'next_batch': batch(),
            }
        if payload['action'] == 'submit_batch':
            submitted.append(payload)
            return {
                'workflow_status': 'collecting',
                'run_id': 'run-fail-closed',
                'next_batch': None,
            }
        return {
            'workflow_status': 'finalized',
            'run_id': 'run-fail-closed',
            'xlsx': {
                'download_path': (
                    '/geotizer/files/run-fail-closed/geotizer.xlsx'
                ),
            },
        }

    async def agent_call(task, prompt, object_name, datacube):
        nonlocal owner_attempts
        if task.role == 'contributor':
            return 'bounded evidence'
        owner_attempts += 1
        return '{"patches": []}'

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
    assert owner_attempts == 3
    assert len(submitted) == 1
    assert {
        patch['status'] for patch in submitted[0]['patches']
    } == {'requires_expert_review'}
    assert submitted[0]['source_inventory'][0]['source_type'] == 'orchestration'
    assert validate_owner_envelope(batch(), submitted[0]) == ()


def test_owner_failure_envelope_is_deterministic_and_field_complete():
    first = owner_failure_envelope(
        batch(),
        run_id='run-1',
        attempts=3,
        feedback=['invalid patches'],
    )
    second = owner_failure_envelope(
        batch(),
        run_id='run-1',
        attempts=3,
        feedback=['invalid patches'],
    )
    assert first == second
    assert [patch['field_key'] for patch in first['patches']] == ['f1', 'f2']
    assert validate_owner_envelope(batch(), first) == ()
