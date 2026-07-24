"""One-command GeoTeaser workflow exposed as an Open WebUI built-in tool."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable, Mapping
from typing import Any

from fastapi import Request

from open_webui.utils.geotizer_orchestration import (
    AgentTask,
    GeotizerOrchestrationError,
    build_batch_tasks,
    compact_batch_context,
    ensure_state_can_continue,
    extract_json_object,
    owner_submission,
    validate_owner_envelope,
    xlsx_download_path,
)

GIS_TOOL_IDS = ('server:mcpgis', 'server:mcp:mcpgis')
DELEGATOR_TOOL_ID = 'mainagent_tool_yulong'
SUB_AGENT_TOOL_ID = 'sub_agent'
SKILLED_MODEL_ID = 'skilledagent-sakana'
MAX_OWNER_ATTEMPTS = 3
MAX_BATCHES = 12

GisCall = Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]
AgentCall = Callable[
    [AgentTask, str, str, Mapping[str, Any] | None],
    Awaitable[str],
]


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
                    ),
                    object_name,
                    state.get('datacube'),
                )
                for task in contributors
            ]
        )
        evidence = [
            {
                'route_id': task.task_id,
                'producer': task.producer,
                'output': result,
            }
            for task, result in zip(contributors, contributor_results)
        ]
        context = compact_batch_context(
            next_batch,
            object_name=object_name,
            run_id=active_run_id,
            datacube=state.get('datacube'),
            contributor_evidence=evidence,
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
            envelope = extract_json_object(raw)
        except GeotizerOrchestrationError as exc:
            feedback = [str(exc)]
            continue

        envelope['run_id'] = run_id
        violations = validate_owner_envelope(next_batch, envelope)
        if violations:
            feedback = list(violations)
            continue

        submission = owner_submission(next_batch, envelope)
        result = await gis_call(submission)
        if result.get('workflow_status') != 'validation_failed':
            return result
        feedback = result.get('violations') or [result]

    error = GeotizerOrchestrationError(
        f'Owner {owner.producer} failed batch {owner.task_id} after '
        f'{MAX_OWNER_ATTEMPTS} attempts: '
        f'{json.dumps(feedback, ensure_ascii=False)}'
    )
    error.run_id = run_id
    raise error


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
        if task.kind == 'skilled':
            model = runtime['__request__'].app.state.MODELS.get(
                SKILLED_MODEL_ID,
                {'id': SKILLED_MODEL_ID},
            )
            result = await sub_agent.run_sub_agent(
                description=(f'GeoTeaser {task.task_id}: assemble owner batch'),
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

        return await delegator.ask_specialist_agent(
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
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


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
            ('Use only supplied or personally retrieved evidence; never ' 'infer an absent factual value.'),
            ('Register every positive and negative evidence source in ' 'source_inventory.'),
            'filled requires a non-empty value and exact source_locator.',
            'not_found/not_applicable/conflicted require value=null.',
            'For GIS evidence, the linked GIS project is already the object scope.',
            ('Do not call geotizer_fill; the orchestrator owns state ' 'transitions.'),
        ],
    }
    if feedback:
        prompt['repair_feedback'] = feedback
        prompt['previous_output'] = previous_output
    return json.dumps(prompt, ensure_ascii=False, indent=2)


def _raise_for_gis_error(state: Mapping[str, Any]) -> None:
    if state.get('error') and not state.get('workflow_status'):
        raise GeotizerOrchestrationError(json.dumps(state['error'], ensure_ascii=False))
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


def _error_result(code: str, message: str, *, run_id: str | None) -> str:
    return json.dumps(
        {
            'status': 'geotizer_failed',
            'code': code,
            'message': message,
            'run_id': run_id or None,
            'resumable': bool(run_id),
        },
        ensure_ascii=False,
        indent=2,
    )
