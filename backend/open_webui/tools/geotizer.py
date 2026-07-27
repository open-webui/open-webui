"""One-command GeoTeaser workflow exposed as an Open WebUI built-in tool."""

from __future__ import annotations

import asyncio
import copy
import json
from collections.abc import Awaitable, Callable, Mapping, Sequence
from typing import Any

from fastapi import Request

from open_webui.utils.geotizer_orchestration import (
    AgentTask,
    GeotizerOrchestrationError,
    apply_structured_gis_field_proposals,
    build_batch_tasks,
    build_knowledge_search_plan,
    compact_batch_context,
    correct_explicitly_derived_value_origins,
    ensure_state_can_continue,
    execution_mode_for_task,
    extract_json_object,
    extract_owner_envelope,
    merge_owner_envelopes,
    normalize_delegator_message,
    normalize_gis_field_proposals,
    normalize_gis_object_profile,
    owner_completion_valves,
    owner_failure_envelope,
    owner_submission,
    partition_owner_batch,
    repair_negative_provenance,
    validate_owner_envelope,
    xlsx_download_path,
)

GIS_TOOL_IDS = ('server:mcpgis', 'server:mcp:mcpgis')
DELEGATOR_TOOL_ID = 'mainagent_tool_yulong'
SUB_AGENT_TOOL_ID = 'sub_agent'
SKILLED_MODEL_ID = 'skilledagent-sakana'
MAX_OWNER_ATTEMPTS = 3
MAX_BATCHES = 12
MAX_OWNER_FIELDS_PER_CALL = 40

GisCall = Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]
AgentCall = Callable[
    [AgentTask, str, str, Mapping[str, Any] | None],
    Awaitable[str],
]


class GeotizerGisError(GeotizerOrchestrationError):
    """Structured GIS failure that must not be reinterpreted by the parent LLM."""

    def __init__(self, details: Mapping[str, Any]):
        self.details = dict(details)
        super().__init__(json.dumps(self.details, ensure_ascii=False))


async def fill_geotizer(
    object_name: str,
    project_id: str = '',
    model_run_id: str = '',
    run_id: str = '',
    allow_draft: bool = True,
    __request__: Request = None,
    __user__: dict = None,
    __event_emitter__=None,
    __event_call__=None,
    __metadata__: dict = None,
    __chat_id__: str = None,
    __message_id__: str = None,
    __model_knowledge__: list[dict] = None,
) -> str:
    """Fill GeoTeaser Object through the deterministic GIS state machine.

    Use this function for a user request such as "Заполни Геотизер для ...".
    It is the only tool the parent model should call for the complete workflow:
    the function resolves the GIS project, collects bounded KB/WEB/GIS evidence,
    submits all exact-owner batches, runs the final audit and returns a download
    link for the rendered XLSX. Do not call specialist or Excel tools manually
    before or after this function.

    :param object_name: Geological object or licence-area name.
    :param project_id: Optional exact linked GIS project ID.
    :param model_run_id: Optional exact DataCube run ID.
    :param run_id: Optional existing GeoTeaser run ID to resume.
    :param allow_draft: Allow final XLSX with explicit data gaps.
    :return: Markdown result with completeness counts and XLSX download link.
    """
    if __request__ is None or __user__ is None:
        return _error_result(
            'missing_runtime_context',
            'Open WebUI request and user context are required.',
            run_id=run_id,
        )
    if not object_name.strip():
        return _error_result(
            'missing_object_name',
            'object_name is required.',
            run_id=run_id,
        )

    user = await _user_model(__user__)
    runtime = {
        '__request__': __request__,
        '__user__': __user__,
        '__event_emitter__': __event_emitter__,
        '__event_call__': __event_call__,
        '__metadata__': __metadata__ or {},
        '__chat_id__': __chat_id__,
        '__message_id__': __message_id__,
        '__model_knowledge__': __model_knowledge__ or [],
    }
    try:
        gis_call = await _resolve_geotizer_callable(
            __request__,
            user,
            runtime,
        )
        agent_call = await _build_agent_caller(runtime)
        final = await run_geotizer_workflow(
            object_name=object_name.strip(),
            project_id=project_id.strip() or None,
            model_run_id=model_run_id.strip() or None,
            run_id=run_id.strip() or None,
            allow_draft=allow_draft,
            gis_call=gis_call,
            agent_call=agent_call,
            event_emitter=__event_emitter__,
        )
    except Exception as exc:
        current_run_id = getattr(exc, 'run_id', None) or run_id
        return _error_result(
            type(exc).__name__,
            str(exc),
            run_id=current_run_id,
            details=getattr(exc, 'details', None),
        )

    proxy_path = _proxy_download_path(final)
    counts = final.get('counts') or {}
    xlsx = final.get('xlsx') or {}
    return (
        f"GeoTeaser для **{final.get('object_name') or object_name}** заполнен "
        "и прошёл финальный audit.\n\n"
        f"- Заполнено: {counts.get('filled', 0)}\n"
        f"- Не найдено: {counts.get('not_found', 0)}\n"
        "- Требует экспертной проверки: "
        f"{counts.get('requires_expert_review', 0)}\n"
        f"- Run ID: `{final.get('run_id')}`\n"
        f"- SHA-256: `{xlsx.get('sha256', '')}`\n\n"
        f"[Скачать заполненный GeoTeaser XLSX]({proxy_path})"
    )


async def run_geotizer_workflow(
    *,
    object_name: str,
    project_id: str | None,
    model_run_id: str | None,
    run_id: str | None,
    allow_draft: bool,
    gis_call: GisCall,
    agent_call: AgentCall,
    event_emitter=None,
) -> dict[str, Any]:
    """Effect shell around the pure GeoTeaser planner and validators."""
    if run_id:
        state = await gis_call({'action': 'get', 'run_id': run_id})
    else:
        state = await gis_call(
            {
                'action': 'start',
                'object_name': object_name,
                'project_id': project_id,
                'model_run_id': model_run_id,
                'linked_gis_project_is_object_scope': True,
            }
        )
    _raise_for_gis_error(state)
    active_run_id = str(state.get('run_id') or run_id or '')
    knowledge_search_plan: Mapping[str, Any] = {}
    gis_project = state.get('gis_project')
    if (
        isinstance(gis_project, Mapping)
        and gis_project.get('status') == 'resolved'
        and gis_project.get('project_id')
        and state.get('next_batch')
    ):
        await _emit_status(
            event_emitter,
            'GeoTeaser: derive GIS profile for related knowledge search',
            done=False,
        )
        profile_task = AgentTask(
            kind='gis',
            producer='GISagent_yulong',
            role='contributor',
            task_id='GIS-OBJECT-PROFILE',
            payload=dict(gis_project),
        )
        try:
            raw_profile = await agent_call(
                profile_task,
                _object_profile_prompt(
                    object_name=object_name,
                    run_id=active_run_id,
                    gis_project=gis_project,
                ),
                object_name,
                state.get('datacube'),
            )
        except Exception as exc:
            raw_profile = json.dumps(
                {
                    'profile_status': 'unavailable',
                    'diagnostics': [f'{type(exc).__name__}: {exc}'],
                },
                ensure_ascii=False,
            )
        profile = normalize_gis_object_profile(
            raw_profile,
            object_name=str(gis_project.get('object_name') or object_name),
            project_id=str(gis_project['project_id']),
        )
        knowledge_search_plan = build_knowledge_search_plan(profile)

    for batch_index in range(MAX_BATCHES):
        next_batch = state.get('next_batch')
        if not next_batch:
            break
        await _emit_status(
            event_emitter,
            (f"GeoTeaser: batch {batch_index + 1} " f"{next_batch.get('batch_id')} ({next_batch.get('producer')})"),
            done=False,
        )
        tasks = build_batch_tasks(next_batch)
        contributors = tuple(task for task in tasks if task.role == 'contributor')
        owner = next(task for task in tasks if task.role == 'owner')

        contributor_results = await asyncio.gather(
            *[
                agent_call(
                    task,
                    _contributor_prompt(
                        object_name=object_name,
                        run_id=active_run_id,
                        task=task,
                        next_batch=next_batch,
                        knowledge_search_plan=knowledge_search_plan,
                    ),
                    object_name,
                    state.get('datacube'),
                )
                for task in contributors
            ]
        )
        allowed_field_keys = [
            str(field.get('field_key') or '')
            for field in next_batch.get('fields') or []
        ]
        evidence = await _deterministic_infrastructure_evidence(
            next_batch=next_batch,
            run_id=active_run_id,
            allowed_field_keys=allowed_field_keys,
            gis_call=gis_call,
        )
        for task, result in zip(contributors, contributor_results):
            item = {
                'route_id': task.task_id,
                'producer': task.producer,
                'source_domain': task.kind,
                'relation_to_object': (
                    'direct'
                    if task.kind == 'gis'
                    else 'source_declared'
                ),
                'output': result,
            }
            if task.kind == 'gis':
                item['field_proposals'] = [
                    proposal.as_dict()
                    for proposal in normalize_gis_field_proposals(
                        result,
                        allowed_field_keys=allowed_field_keys,
                    )
                ]
            evidence.append(item)
        context = compact_batch_context(
            next_batch,
            object_name=object_name,
            run_id=active_run_id,
            datacube=state.get('datacube'),
            contributor_evidence=evidence,
            knowledge_search_plan=knowledge_search_plan,
        )

        state = await _produce_and_submit_owner_batch(
            owner=owner,
            context=context,
            next_batch=next_batch,
            object_name=object_name,
            run_id=active_run_id,
            gis_call=gis_call,
            agent_call=agent_call,
            datacube=state.get('datacube'),
        )
        _raise_for_gis_error(state)
    else:
        raise GeotizerOrchestrationError(f'GeoTeaser exceeded the bounded limit of {MAX_BATCHES} owner batches')

    if state.get('next_batch'):
        raise GeotizerOrchestrationError('GeoTeaser stopped before all owner batches')
    await _emit_status(
        event_emitter,
        'GeoTeaser: final audit and XLSX rendering',
        done=False,
    )
    final = await gis_call(
        {
            'action': 'finalize',
            'run_id': active_run_id,
            'allow_draft': allow_draft,
        }
    )
    _raise_for_gis_error(final)
    if final.get('workflow_status') != 'finalized':
        raise GeotizerOrchestrationError('GIS service did not finalize the run')
    xlsx_download_path(final)
    await _emit_status(
        event_emitter,
        'GeoTeaser: XLSX is ready',
        done=True,
    )
    return final


async def _produce_and_submit_owner_batch(
    *,
    owner: AgentTask,
    context: Mapping[str, Any],
    next_batch: Mapping[str, Any],
    object_name: str,
    run_id: str,
    gis_call: GisCall,
    agent_call: AgentCall,
    datacube: Mapping[str, Any] | None,
) -> dict[str, Any]:
    chunks = partition_owner_batch(
        next_batch,
        max_fields=MAX_OWNER_FIELDS_PER_CALL,
    )
    envelopes = []
    for chunk in chunks:
        chunk_context = {**dict(context), 'batch': chunk}
        envelopes.append(
            await _produce_valid_owner_envelope(
                owner=owner,
                context=chunk_context,
                next_batch=chunk,
                object_name=object_name,
                run_id=run_id,
                agent_call=agent_call,
                datacube=datacube,
            )
        )

    envelope = merge_owner_envelopes(
        next_batch,
        chunks,
        envelopes,
        run_id=run_id,
    )
    return await gis_call(owner_submission(next_batch, envelope))


async def _produce_valid_owner_envelope(
    *,
    owner: AgentTask,
    context: Mapping[str, Any],
    next_batch: Mapping[str, Any],
    object_name: str,
    run_id: str,
    agent_call: AgentCall,
    datacube: Mapping[str, Any] | None,
) -> dict[str, Any]:
    previous_output = ''
    feedback: Any = None
    for attempt in range(1, MAX_OWNER_ATTEMPTS + 1):
        prompt = _owner_prompt(
            context=context,
            attempt=attempt,
            feedback=feedback,
            previous_output=previous_output,
        )
        raw = await agent_call(owner, prompt, object_name, datacube)
        previous_output = raw
        try:
            envelope = extract_owner_envelope(raw, next_batch)
        except GeotizerOrchestrationError as exc:
            feedback = [str(exc)]
            continue

        envelope = repair_negative_provenance(
            next_batch,
            envelope,
            run_id=run_id,
            attempt=attempt,
        )
        envelope = apply_structured_gis_field_proposals(
            next_batch,
            envelope,
            context.get('contributor_evidence') or [],
        )
        envelope = correct_explicitly_derived_value_origins(envelope)
        envelope['run_id'] = run_id
        violations = validate_owner_envelope(next_batch, envelope)
        if not violations:
            return envelope
        feedback = list(violations)

    return owner_failure_envelope(
        next_batch,
        run_id=run_id,
        attempts=MAX_OWNER_ATTEMPTS,
        feedback=feedback or [],
    )


async def _resolve_geotizer_callable(request, user, runtime) -> GisCall:
    from open_webui.utils.tools import get_tools

    tools: dict[str, dict] = {}
    for tool_id in GIS_TOOL_IDS:
        resolved = await get_tools(
            request,
            [tool_id],
            user,
            {
                '__user__': runtime['__user__'],
                '__event_emitter__': runtime['__event_emitter__'],
                '__event_call__': runtime['__event_call__'],
                '__metadata__': runtime['__metadata__'],
                '__request__': request,
                '__chat_id__': runtime['__chat_id__'],
                '__message_id__': runtime['__message_id__'],
                '__model__': {},
                '__messages__': [],
                '__files__': [],
            },
        )
        tools.update(resolved)
        if any(name == 'geotizer_fill' or name.endswith('_geotizer_fill') for name in tools):
            break

    entry = next(
        (value for name, value in tools.items() if name == 'geotizer_fill' or name.endswith('_geotizer_fill')),
        None,
    )
    if entry is None:
        raise GeotizerOrchestrationError('Configured GIS tool server does not expose geotizer_fill')
    callable_ = entry['callable']

    async def call(payload: dict[str, Any]) -> dict[str, Any]:
        raw = await callable_(**payload)
        if isinstance(raw, tuple | list) and raw:
            raw = raw[0]
        if isinstance(raw, str):
            raw = json.loads(raw)
        if not isinstance(raw, dict):
            raise GeotizerOrchestrationError(f'geotizer_fill returned {type(raw).__name__}, expected object')
        return raw

    return call


async def _build_agent_caller(runtime) -> AgentCall:
    from open_webui.models.tools import Tools
    from open_webui.utils.plugin import load_tool_module_by_id

    delegator, _ = await load_tool_module_by_id(DELEGATOR_TOOL_ID)
    delegator_valves = await Tools.get_tool_valves_by_id(DELEGATOR_TOOL_ID) or {}
    if hasattr(delegator, 'Valves'):
        delegator.valves = delegator.Valves(**delegator_valves)
    owner_delegator = copy.copy(delegator)
    if hasattr(delegator, 'Valves'):
        owner_delegator.valves = delegator.Valves(
            **owner_completion_valves(
                delegator.valves.model_dump(),
            )
        )
    original_extract_message = getattr(delegator, '_extract_chat_history_message', None)
    if callable(original_extract_message):

        def extract_normalized_message(chat_data, message_id):
            return normalize_delegator_message(original_extract_message(chat_data, message_id))

        delegator._extract_chat_history_message = extract_normalized_message

    sub_agent, _ = await load_tool_module_by_id(SUB_AGENT_TOOL_ID)
    sub_agent_valves = await Tools.get_tool_valves_by_id(SUB_AGENT_TOOL_ID) or {}
    if hasattr(sub_agent, 'Valves'):
        sub_agent.valves = sub_agent.Valves(**sub_agent_valves)
        sub_agent.valves.DEFAULT_MODEL = SKILLED_MODEL_ID
        sub_agent.valves.AVAILABLE_TOOL_IDS = '__geotizer_no_external_tools__'
        for name in (
            'ENABLE_TIME_TOOLS',
            'ENABLE_WEB_TOOLS',
            'ENABLE_IMAGE_TOOLS',
            'ENABLE_KNOWLEDGE_TOOLS',
            'ENABLE_CHAT_TOOLS',
            'ENABLE_MEMORY_TOOLS',
            'ENABLE_NOTES_TOOLS',
            'ENABLE_CHANNELS_TOOLS',
            'ENABLE_TERMINAL_TOOLS',
            'ENABLE_CODE_INTERPRETER_TOOLS',
            'ENABLE_SKILLS_TOOLS',
            'ENABLE_TASK_TOOLS',
            'ENABLE_AUTOMATION_TOOLS',
            'ENABLE_CALENDAR_TOOLS',
        ):
            if hasattr(sub_agent.valves, name):
                setattr(sub_agent.valves, name, False)

    async def call(
        task: AgentTask,
        prompt: str,
        object_name: str,
        datacube: Mapping[str, Any] | None,
    ) -> str:
        execution_mode = execution_mode_for_task(task)
        if execution_mode == 'tool_free_owner':
            model = runtime['__request__'].app.state.MODELS.get(
                SKILLED_MODEL_ID,
                {'id': SKILLED_MODEL_ID},
            )
            result = await sub_agent.run_sub_agent(
                description=(
                    f'GeoTeaser {task.task_id}: '
                    f'{task.producer} tool-free owner decision'
                ),
                prompt=prompt,
                __user__=runtime['__user__'],
                __request__=runtime['__request__'],
                __model__=model,
                __metadata__=runtime['__metadata__'],
                __id__='builtin:fill_geotizer',
                __event_emitter__=runtime['__event_emitter__'],
                __event_call__=runtime['__event_call__'],
                __chat_id__=runtime['__chat_id__'],
                __message_id__=runtime['__message_id__'],
                __messages__=[],
            )
            outer = extract_json_object(result)
            return str(outer.get('result') or result)

        active_delegator = (
            owner_delegator
            if execution_mode == 'specialist_owner_completion'
            else delegator
        )
        return await active_delegator.ask_specialist_agent(
            agent=task.kind,
            task=prompt,
            original_user_request=f'Заполнить GeoTeaser для {object_name}',
            expected_output=('Follow the exact JSON-only output contract in specialist_task.'),
            __event_emitter__=runtime['__event_emitter__'],
            __event_call__=runtime['__event_call__'],
            __request__=runtime['__request__'],
            __user__=runtime['__user__'],
            __metadata__=runtime['__metadata__'],
            __chat_id__=runtime['__chat_id__'],
            __message_id__=runtime['__message_id__'],
        )

    return call


async def _user_model(user_data: dict):
    from open_webui.models.users import UserModel

    return UserModel(**user_data)


def _contributor_prompt(
    *,
    object_name: str,
    run_id: str,
    task: AgentTask,
    next_batch: Mapping[str, Any],
    knowledge_search_plan: Mapping[str, Any],
) -> str:
    payload = {
        'operation': 'geotizer_evidence_contribution',
        'object_name': object_name,
        'run_id': run_id,
        'route': dict(task.payload),
        'bounded_fields': list(next_batch.get('fields') or []),
        'rules': [
            'Search only your source domain.',
            (
                'The linked GIS project is accepted as the object scope; do '
                'not reject a relevant linked-project layer for lack of a '
                'second spatial-membership proof.'
            ),
            ('Return evidence only. Do not create field patches and do not ' 'call geotizer_fill.'),
            (
                'Preserve source IDs, titles, URLs, collection/file/chunk/page '
                'or GIS layer/feature locators, units, conflicts and '
                'negative-search notes.'
            ),
            (
                'Keep the evidence report under 12000 characters; prioritize '
                'exact locators and facts for bounded_fields.'
            ),
        ],
    }
    if task.kind == 'gis':
        payload['output_contract'] = {
            'field_proposals': [
                {
                    'field_key': 'exact bounded field_key',
                    'value': 'typed proposed value',
                    'unit': None,
                    'value_origin': 'direct|calculated|analogue',
                    'relation_to_object': (
                        'direct|regional_context|deposit_analogue'
                    ),
                    'source_id': 'stable GIS source ID',
                    'source_title': 'GIS project/layer title',
                    'source_locator': {
                        'project_id': 'exact project ID',
                        'layer_id': 'exact layer ID',
                        'feature_or_query': 'exact feature/query locator',
                    },
                    'retrieval_note': (
                        'basis or calculation/analogue explanation'
                    ),
                }
            ],
            'negative_search_notes': [
                {
                    'field_key': 'exact bounded field_key',
                    'query': 'performed GIS query',
                    'result': 'not_found',
                }
            ],
        }
        payload['rules'].extend(
            [
                'Return one JSON object only, without Markdown.',
                (
                    'A relevant record from the linked GIS project is direct '
                    'object evidence, not regional or analogue evidence.'
                ),
                (
                    'For every supported bounded field, state the exact '
                    'field_key, value and GIS layer/feature/query locator; '
                    'mark it confirmed_by_linked_gis_project.'
                ),
                (
                    'Use value_origin=direct for an extracted object fact, '
                    'calculated for an object estimate derived from GIS, and '
                    'analogue for an alternative transferred from a stated '
                    'analogue.'
                ),
                (
                    'Calculated and analogue proposals are allowed, but must '
                    'include the derivation basis in retrieval_note. The XLSX '
                    'renderer will label them РАСЧЕТНОЕ ЗНАЧЕНИЕ.'
                ),
                (
                    'Do not emit a proposal without an exact source_locator. '
                    'Use negative_search_notes when a bounded field cannot be '
                    'supported.'
                ),
            ]
        )
        payload['rules'].extend(_gis_infrastructure_rules(next_batch))
    if task.kind == 'kb':
        payload['knowledge_search_plan'] = dict(knowledge_search_plan)
        payload['rules'].extend(
            [
                (
                    'Do not stop after an object-name or collection-name miss; '
                    'execute every enabled tier in knowledge_search_plan.'
                ),
                (
                    'Label each result as direct, regional_context or '
                    'deposit_analogue and preserve the GIS descriptors used '
                    'to establish that relation.'
                ),
            ]
        )
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _needs_deterministic_infrastructure(
    next_batch: Mapping[str, Any],
) -> bool:
    if str(next_batch.get('batch_id') or '') != 'GIS-DC':
        return False
    prefixes = (
        'geotizer_object.v1.r078.',
        'geotizer_object.v1.r081.',
        'geotizer_object.v1.r084.',
        'geotizer_object.v1.r085.',
        'geotizer_object.v1.r088.',
    )
    return any(
        str(field.get('field_key') or '').startswith(prefixes)
        for field in next_batch.get('fields') or []
    )


async def _deterministic_infrastructure_evidence(
    *,
    next_batch: Mapping[str, Any],
    run_id: str,
    allowed_field_keys: Sequence[str],
    gis_call: GisCall,
) -> list[dict[str, Any]]:
    if not _needs_deterministic_infrastructure(next_batch):
        return []
    deterministic = await gis_call(
        {
            'action': 'infrastructure_proposals',
            'run_id': run_id,
        }
    )
    _raise_for_gis_error(deterministic)
    return [
        {
            'route_id': 'GIS-INFRASTRUCTURE-DETERMINISTIC',
            'producer': 'gis_service',
            'source_domain': 'gis',
            'relation_to_object': 'direct',
            'output': json.dumps(
                deterministic,
                ensure_ascii=False,
            ),
            'field_proposals': [
                proposal.as_dict()
                for proposal in normalize_gis_field_proposals(
                    deterministic,
                    allowed_field_keys=allowed_field_keys,
                )
            ],
        }
    ]


def _gis_infrastructure_rules(
    next_batch: Mapping[str, Any],
) -> list[str]:
    """Require deterministic spatial calls for the infrastructure owner batch."""
    if str(next_batch.get('batch_id') or '') != 'GIS-DC':
        return []
    return [
        (
            'This is the infrastructure batch. Do not infer that distance '
            'data are absent until you have called list_layers and '
            'describe_layer for the linked project.'
        ),
        (
            'Resolve the single licence polygon as the source feature, then '
            'use nearest_features or features_within_distance with a '
            'projected metre CRS and full feature geometries. Never estimate '
            'distance from layer extents, map scale or centroids.'
        ),
        (
            'For geotizer_object.v1.r078.a01 calculate the minimum distance '
            'to the nearest settlement feature. For '
            'geotizer_object.v1.r081.a01, when only a power-line layer is '
            'available, return distance to the nearest power line as an '
            'explicit proxy for the energy node, not as a direct energy-node '
            'fact.'
        ),
        (
            'For rows r084 and r085 inspect settlements, railway stations, '
            'railway lines, roads and power lines. Build deterministic '
            'distance-ranked proposals inside 50 km and 100 km respectively, '
            'deduplicated by infrastructure type and stable feature ID, and '
            'fill no more than the bounded object slots.'
        ),
        (
            'For row r088 compare the nearest road and railway evidence and '
            'propose the supported access character, mode and minimum '
            'distance. A line intersecting the licence polygon has distance '
            'zero, not an unknown distance.'
        ),
        (
            'Every spatially computed value must use '
            'value_origin=calculated. Its source_locator must include the '
            'operation, project_id, source and target layer IDs, stable '
            'feature IDs, calculation CRS, raw distance in metres and radius '
            'threshold where applicable.'
        ),
        (
            'Do not fill federal centre, GOK/ZIF, port, state border or '
            'subsoil-user fields from a semantically different layer. Return '
            'a negative_search_note only after checking the relevant layer '
            'inventory and attributes.'
        ),
    ]


def _object_profile_prompt(
    *,
    object_name: str,
    run_id: str,
    gis_project: Mapping[str, Any],
) -> str:
    return json.dumps(
        {
            'operation': 'geotizer_gis_object_search_profile',
            'object_name': object_name,
            'run_id': run_id,
            'gis_project': dict(gis_project),
            'output_contract': {
                'location_terms': ['region', 'district', 'tectonic structure'],
                'commodity_terms': ['commodity or target mineral'],
                'deposit_type_terms': [
                    'geological-genetic or mineral-system type'
                ],
                'geology_terms': [
                    'host rocks, structures, age or geological setting'
                ],
                'evidence': [
                    {
                        'source_id': 'stable GIS source ID',
                        'layer_id': 'exact layer ID',
                        'feature_or_query': 'exact locator',
                        'fact': 'descriptor supported by the GIS project',
                    }
                ],
            },
            'rules': [
                (
                    'Return one JSON object only, without Markdown or '
                    'commentary.'
                ),
                (
                    'The GIS project is already deterministically resolved '
                    'and linked to the object. Never report it as missing.'
                ),
                (
                    'Inspect relevant linked-project layers and attributes to '
                    'derive only evidence-backed location, commodity, deposit '
                    'type and geological search descriptors.'
                ),
                (
                    'Do not invent descriptors; use empty arrays when the '
                    'linked GIS project does not support them.'
                ),
                (
                    'This profile expands knowledge retrieval and does not '
                    'itself fill GeoTeaser fields.'
                ),
            ],
        },
        ensure_ascii=False,
        indent=2,
    )


def _owner_prompt(
    *,
    context: Mapping[str, Any],
    attempt: int,
    feedback: Any,
    previous_output: str,
) -> str:
    batch = context['batch']
    contract = {
        'batch_id': batch['batch_id'],
        'producer': batch['producer'],
        'policy_version': batch['policy_version'],
        'template_version': batch['template_version'],
        'source_inventory': [
            {
                'source_id': 'stable unique ID',
                'source_type': 'knowledge_base|web|gis|datacube|derived',
                'title': 'source title',
                'locator': 'human-readable locator',
                'url': None,
            }
        ],
        'patches': [
            {
                'field_key': 'exact field_key from batch.fields',
                'value': None,
                'unit': None,
                'status': ('filled|not_found|not_applicable|conflicted|' 'requires_expert_review'),
                'value_origin': 'direct|calculated|analogue|null',
                'source_refs': ['registered source_id'],
                'source_locator': {'page_or_chunk_or_layer_or_feature_or_query': 'exact locator'},
                'retrieval_note': 'short evidence decision note',
            }
        ],
    }
    prompt = {
        'operation': 'geotizer_owner_decision',
        'attempt': attempt,
        'context': context,
        'output_contract': contract,
        'rules': [
            'Return one JSON object only, without Markdown fences or commentary.',
            ('Echo batch_id, producer, policy_version and template_version ' 'exactly.'),
            ('Return exactly one patch for every field in batch.fields and ' 'no other fields.'),
            (
                'Use direct evidence for factual values. Calculated or '
                'analogue alternatives are allowed only with '
                'value_origin=calculated|analogue and an explicit derivation '
                'basis in retrieval_note.'
            ),
            ('Register every positive and negative evidence source in ' 'source_inventory.'),
            'filled requires a non-empty value and exact source_locator.',
            (
                'filled requires value_origin=direct|calculated|analogue. '
                'Non-filled statuses use value_origin=null.'
            ),
            'not_found/not_applicable/conflicted require value=null.',
            'For GIS evidence, the linked GIS project is already the object scope.',
            (
                'Treat contributor_evidence with source_domain=gis, '
                'relation_to_object=direct and '
                'evidence_authority=linked_gis_project as direct object '
                'evidence.'
            ),
            (
                'A knowledge-base or web miss cannot negate a fact confirmed '
                'by an exact linked-project GIS layer/feature/query locator.'
            ),
            (
                'For every bounded field explicitly supported by direct GIS '
                'evidence, use that GIS value unless conflicting direct '
                'evidence exists; do not return not_found solely because the '
                'knowledge base has no match.'
            ),
            ('Do not call geotizer_fill; the orchestrator owns state ' 'transitions.'),
        ],
    }
    if context.get('knowledge_search_plan'):
        prompt['rules'].extend(
            [
                (
                    'Follow knowledge_search_plan even when there is no '
                    'collection directly named after the object.'
                ),
                (
                    'For contextual or analogue evidence, record '
                    'relation_to_object and GIS matching descriptors in '
                    'retrieval_note and source_locator.'
                ),
                (
                    'An analogue may provide an alternative object value only '
                    'with value_origin=analogue, the analogue identity, exact '
                    'locator and transfer rationale. Never present it as a '
                    'direct object fact.'
                ),
            ]
        )
    if feedback:
        prompt['repair_feedback'] = feedback
        prompt['previous_output'] = previous_output
    return json.dumps(prompt, ensure_ascii=False, indent=2)


def _raise_for_gis_error(state: Mapping[str, Any]) -> None:
    if state.get('error') and not state.get('workflow_status'):
        raise GeotizerGisError(state['error'])
    if state.get('workflow_status') == 'needs_input':
        raise GeotizerGisError(state.get('error') or state)
    if state.get('workflow_status') == 'validation_failed':
        raise GeotizerGisError(
            {
                'code': 'gis_validation_failed',
                'violations': list(state.get('violations') or []),
            }
        )
    ensure_state_can_continue(state)


def _proxy_download_path(final: Mapping[str, Any]) -> str:
    path = xlsx_download_path(final)
    return f'/api/v1{path}'


async def _emit_status(emitter, description: str, *, done: bool) -> None:
    if emitter:
        await emitter(
            {
                'type': 'status',
                'data': {
                    'description': description,
                    'done': done,
                },
            }
        )


def _error_result(
    code: str,
    message: str,
    *,
    run_id: str | None,
    details: Mapping[str, Any] | None = None,
) -> str:
    structured_details = dict(details or {})
    return json.dumps(
        {
            'status': 'geotizer_failed',
            'code': code,
            'message': message,
            'user_message': _gis_error_user_message(
                structured_details,
                fallback=message,
            ),
            'details': structured_details or None,
            'run_id': run_id or None,
            'resumable': bool(run_id),
        },
        ensure_ascii=False,
        indent=2,
    )


def _gis_error_user_message(
    details: Mapping[str, Any],
    *,
    fallback: str,
) -> str:
    resolution = details.get('project_resolution')
    if isinstance(resolution, Mapping):
        status = resolution.get('status')
        if status == 'not_found':
            return 'Связанный GIS-проект действительно не найден.'
        if status == 'ambiguous':
            return 'Найдено несколько подходящих GIS-проектов; нужен точный project_id.'

    for violation in details.get('violations') or []:
        if not isinstance(violation, Mapping):
            continue
        context = violation.get('context')
        if not isinstance(context, Mapping):
            continue
        project = context.get('gis_project')
        if isinstance(project, Mapping) and project.get('status') == 'resolved':
            project_id = project.get('project_id')
            return (
                f"Связанный GIS-проект {project_id!r} найден. "
                'Ошибка возникла на последующем этапе '
                f"{context.get('failure_stage') or 'GIS processing'}."
            )
    return fallback
