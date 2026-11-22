import asyncio
import hmac
import secrets
import time
from contextlib import suppress
from typing import Awaitable, Callable
from uuid import uuid4

from fastapi import Request
from fastapi.responses import HTMLResponse
from open_webui.env import CODE_MODE_TIMEOUT, REDIS_KEY_PREFIX
from open_webui.models.config import Config
from open_webui.utils.json_codec import JSONCodec
from open_webui.utils.mcp.apps import MCPAppResult

POLL_SECONDS = 30

WORKER_CHANNEL = f'{REDIS_KEY_PREFIX}:code_mode:worker:{uuid4()}'

runs: dict[str, dict] = {}
pending_calls: dict[str, asyncio.Future] = {}

# Runs on the machine with only the standard library, so any Python 3.9+ works.
BOOTSTRAP = """
import ast, asyncio, inspect, json, linecache, os, signal, urllib.error, urllib.request

os.remove(__file__)
URL, TOKEN, SOURCE, TIMEOUT = json.loads(PAYLOAD)
if hasattr(signal, "alarm"):
    signal.alarm(TIMEOUT)
del PAYLOAD


class ToolError(Exception):
    pass


def call(name, arguments):
    request = urllib.request.Request(
        URL,
        data=json.dumps({"name": name, "arguments": arguments}).encode(),
        headers={"Authorization": "Bearer " + TOKEN, "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request) as response:
            body = json.load(response)
    except urllib.error.HTTPError as error:
        raise ToolError(name + ": " + error.read().decode(errors="replace")) from None
    except urllib.error.URLError as error:
        raise ToolError(name + ": cannot reach Open WebUI at " + URL + ": " + str(error.reason)) from None
    if body["status"] == "failed":
        raise ToolError(name + ": " + str(body["result"]))
    try:
        return json.loads(body["result"])
    except (TypeError, ValueError):
        return body["result"]


class Tool:
    def __init__(self, name):
        self.name = name

    def __call__(self, **arguments):
        return call(self.name, arguments)

    async def run_async(self, **arguments):
        return await asyncio.to_thread(call, self.name, arguments)


class Tools:
    def __getattr__(self, name):
        return Tool(name)


linecache.cache["<code>"] = (len(SOURCE), None, SOURCE.splitlines(True), "<code>")
code = compile(SOURCE, "<code>", "exec", flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT)
result = eval(
    code, {"__name__": "__main__", "tools": Tools(), "ToolError": ToolError, "asyncio": asyncio, "json": json}
)
if inspect.iscoroutine(result):
    asyncio.run(result)
"""


async def answer_call(redis, run: dict, command: dict):
    result, status = await run['call'](command['name'], command['arguments'])
    await redis.publish(
        command['reply_channel'],
        JSONCodec.dumps({'action': 'code_reply', 'call_id': command['call_id'], 'result': result, 'status': status}),
    )


def handle_code_command(redis, command: dict):
    """Serve a call for a run on this worker, or deliver a reply to a call waiting here."""
    if command['action'] == 'code_reply':
        if future := pending_calls.get(command['call_id']):
            future.set_result({'result': command['result'], 'status': command['status']})
    elif run := runs.get(command['run_id']):
        start_run_task(run, answer_call(redis, run, command))


def get_script_result(result, tool_type: str) -> str:
    """A tool result as text for a script, kept whole since it never reaches the model."""
    if isinstance(result, MCPAppResult):
        result = result.context
    if isinstance(result, tuple):
        result = result[0]
    if isinstance(result, HTMLResponse):
        result = result.body.decode('utf-8', 'replace')
    if tool_type == 'mcp' and isinstance(result, list):
        result = '\n'.join(item.get('text', '') for item in result if isinstance(item, dict))
    if isinstance(result, (dict, list)):
        return JSONCodec.dumps(result)
    return result if isinstance(result, str) else str(result)


def start_run_task(run: dict, coroutine: Awaitable) -> asyncio.Task:
    """Start work that is cancelled when the run ends."""
    task = asyncio.create_task(coroutine)
    run['tasks'].add(task)
    task.add_done_callback(run['tasks'].discard)
    return task


async def run_code_on_machine(
    request: Request, tools: dict, code: str, call: Callable[[str, dict], Awaitable[tuple[str, str]]]
) -> dict:
    """Run a script on the chat's machine while its tool calls are served by `call`."""
    run_id = str(uuid4())
    token = secrets.token_urlsafe(32)
    base_url = (await Config.get('webui.url') or str(request.base_url)).rstrip('/')
    path = f'.open-webui-code-{run_id}.py'
    payload = JSONCodec.dumps([f'{base_url}/api/v1/tools/code/{run_id}/call', token, code, 2 * CODE_MODE_TIMEOUT])

    redis = request.app.state.redis
    runs[run_id] = {'token': token, 'call': call, 'tasks': set()}
    process_id = None
    status = None
    try:
        response, _ = await tools['write_file']['callable'](path=path, content=f'PAYLOAD = {payload!r}\n{BOOTSTRAP}')
        if 'error' in response:
            return response
        if redis:
            await redis.set(
                f'{REDIS_KEY_PREFIX}:code_mode:{run_id}',
                JSONCodec.dumps([token, WORKER_CHANNEL]),
                ex=2 * CODE_MODE_TIMEOUT,
            )
        deadline = time.monotonic() + CODE_MODE_TIMEOUT
        response, _ = await tools['run_command']['callable'](
            command=f'python3 {path}', env={'PYTHON_COLORS': '0'}, wait=0
        )
        output = ''
        while True:
            if 'error' in response:
                return response
            process_id = response['id']
            output += ''.join(entry['data'] for entry in response.get('output', []))
            status = response.get('status')
            if status != 'running' or time.monotonic() > deadline:
                break
            response, _ = await tools['get_process_status']['callable'](
                process_id=process_id, offset=response['next_offset'], wait=POLL_SECONDS
            )
        if status == 'running':
            output += f'\n[Stopped after {CODE_MODE_TIMEOUT} seconds]'
        return {'status': status, 'exit_code': response.get('exit_code'), 'output': output.replace('\r\n', '\n')}
    finally:
        for task in runs.pop(run_id)['tasks']:
            task.cancel()
        if redis:
            await redis.delete(f'{REDIS_KEY_PREFIX}:code_mode:{run_id}')
        if status in (None, 'running') and process_id:
            with suppress(Exception):
                await tools['kill_process']['callable'](process_id=process_id, force=True)


async def run_tool_call(request: Request, run_id: str, token: str, name: str, arguments: dict) -> dict | None:
    """Run a script's tool call on the worker that owns the run, or None if there is no such run."""
    run = runs.get(run_id)
    if run:
        if not hmac.compare_digest(run['token'].encode(), token.encode()):
            return None
        task = start_run_task(run, run['call'](name, arguments))
        await asyncio.wait({task})
        if task.cancelled():
            return None
        result, status = task.result()
        return {'result': result, 'status': status}

    redis = request.app.state.redis
    stored = await redis.get(f'{REDIS_KEY_PREFIX}:code_mode:{run_id}') if redis else None
    if not stored:
        return None
    stored_token, owner_channel = JSONCodec.loads(stored)
    if not hmac.compare_digest(stored_token.encode(), token.encode()):
        return None
    call_id = str(uuid4())
    pending_calls[call_id] = asyncio.get_running_loop().create_future()
    try:
        await redis.publish(
            owner_channel,
            JSONCodec.dumps(
                {
                    'action': 'code_call',
                    'run_id': run_id,
                    'call_id': call_id,
                    'name': name,
                    'arguments': arguments,
                    'reply_channel': WORKER_CHANNEL,
                }
            ),
        )
        while await redis.exists(f'{REDIS_KEY_PREFIX}:code_mode:{run_id}'):
            try:
                return await asyncio.wait_for(asyncio.shield(pending_calls[call_id]), 1)
            except TimeoutError:
                pass
        return None
    finally:
        pending_calls.pop(call_id)
