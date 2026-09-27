import asyncio
import logging
import uuid
from typing import Optional

import aiohttp
import websockets
from open_webui.env import AIOHTTP_CLIENT_ALLOW_REDIRECTS
from open_webui.utils.json_codec import JSONCodec
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class ResultModel(BaseModel):
    """
    Execute Code Result Model
    """

    stdout: Optional[str] = ''
    stderr: Optional[str] = ''
    result: Optional[str] = ''


class JupyterCodeExecuter:
    """
    Execute code in jupyter notebook
    """

    def __init__(
        self,
        base_url: str,
        code: str,
        token: str = '',
        password: str = '',
        timeout: int = 60,
    ):
        """
        :param base_url: Jupyter server URL (e.g., "http://localhost:8888")
        :param code: Code to execute
        :param token: Jupyter authentication token (optional)
        :param password: Jupyter password (optional)
        :param timeout: WebSocket timeout in seconds (default: 60s)
        """
        self.base_url = base_url
        self.code = code
        self.token = token
        self.password = password
        self.timeout = timeout
        self.kernel_id = ''
        if self.base_url[-1] != '/':
            self.base_url += '/'
        self.session = aiohttp.ClientSession(trust_env=True, base_url=self.base_url)
        self.params = {}
        self.result = ResultModel()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.kernel_id:
            try:
                async with self.session.delete(f'api/kernels/{self.kernel_id}', params=self.params) as response:
                    response.raise_for_status()
            except Exception as err:
                logger.exception('close kernel failed, %s', err)
        await self.session.close()

    async def run(self) -> ResultModel:
        try:
            await self.sign_in()
            await self.init_kernel()
            await self.execute_code()
        except Exception as err:
            logger.exception('execute code failed, %s', err)
            self.result.stderr = f'Error: {err}'
        return self.result

    async def sign_in(self) -> None:
        # password authentication
        if self.password and not self.token:
            async with self.session.get('login') as response:
                response.raise_for_status()
                xsrf_token = response.cookies['_xsrf'].value
                if not xsrf_token:
                    raise ValueError('_xsrf token not found')
                self.session.cookie_jar.update_cookies(response.cookies)
                self.session.headers.update({'X-XSRFToken': xsrf_token})
            async with self.session.post(
                'login',
                data={'_xsrf': xsrf_token, 'password': self.password},
                allow_redirects=AIOHTTP_CLIENT_ALLOW_REDIRECTS,
            ) as response:
                response.raise_for_status()
                self.session.cookie_jar.update_cookies(response.cookies)

        # token authentication
        if self.token:
            self.params.update({'token': self.token})

    async def init_kernel(self) -> None:
        async with self.session.post(url='api/kernels', params=self.params) as response:
            response.raise_for_status()
            kernel_data = await response.json()
            self.kernel_id = kernel_data['id']

    def init_ws(self) -> (str, dict):
        ws_base = self.base_url.replace('http', 'ws', 1)
        ws_params = '?' + '&'.join([f'{key}={val}' for key, val in self.params.items()])
        websocket_url = f'{ws_base}api/kernels/{self.kernel_id}/channels{ws_params if len(ws_params) > 1 else ""}'
        ws_headers = {}
        if self.password and not self.token:
            ws_headers = {
                'Cookie': '; '.join([f'{cookie.key}={cookie.value}' for cookie in self.session.cookie_jar]),
                **self.session.headers,
            }
        return websocket_url, ws_headers

    async def execute_code(self) -> None:
        # initialize ws
        websocket_url, ws_headers = self.init_ws()
        # execute
        async with websockets.connect(websocket_url, additional_headers=ws_headers) as ws:
            await self.execute_in_jupyter(ws)

    async def execute_in_jupyter(self, ws) -> None:
        # send message
        msg_id = uuid.uuid4().hex
        await ws.send(
            JSONCodec.dumps(
                {
                    'header': {
                        'msg_id': msg_id,
                        'msg_type': 'execute_request',
                        'username': 'user',
                        'session': uuid.uuid4().hex,
                        'date': '',
                        'version': '5.3',
                    },
                    'parent_header': {},
                    'metadata': {},
                    'content': {
                        'code': self.code,
                        'silent': False,
                        'store_history': True,
                        'user_expressions': {},
                        'allow_stdin': False,
                        'stop_on_error': True,
                    },
                    'channel': 'shell',
                }
            )
        )
        # parse message
        stdout, stderr, result = '', '', []
        while True:
            try:
                # wait for message
                message = await asyncio.wait_for(ws.recv(), self.timeout)
                message_data = JSONCodec.loads(message)
                # msg id not match, skip
                if message_data.get('parent_header', {}).get('msg_id') != msg_id:
                    continue
                # check message type
                msg_type = message_data.get('msg_type')
                match msg_type:
                    case 'stream':
                        if message_data['content']['name'] == 'stdout':
                            stdout += message_data['content']['text']
                        elif message_data['content']['name'] == 'stderr':
                            stderr += message_data['content']['text']
                    case 'execute_result' | 'display_data':
                        data = message_data['content']['data']
                        if 'image/png' in data:
                            result.append(f'data:image/png;base64,{data["image/png"]}')
                        elif 'text/plain' in data:
                            result.append(data['text/plain'])
                    case 'error':
                        stderr += '\n'.join(message_data['content']['traceback'])
                    case 'status':
                        if message_data['content']['execution_state'] == 'idle':
                            break

            except asyncio.TimeoutError:
                stderr += '\nExecution timed out.'
                break
        self.result.stdout = stdout.strip()
        self.result.stderr = stderr.strip()
        self.result.result = '\n'.join(result).strip() if result else ''


async def execute_code_jupyter(
    base_url: str, code: str, token: str = '', password: str = '', timeout: int = 60
) -> dict:
    async with JupyterCodeExecuter(base_url, code, token, password, timeout) as executor:
        result = await executor.run()
        return result.model_dump()


async def execute_code_sandbox(
    base_url: str, code: str, token: str = '', timeout: int = 60
) -> dict:
    """Execute code in a custom REST code execution sandbox."""
    if not base_url:
        return {'stderr': 'Sandbox URL is not configured.', 'stdout': '', 'result': ''}

    headers = {'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = f'Bearer {token}'

    endpoint = base_url.rstrip('/')
    if not endpoint.endswith('/execute'):
        endpoint = f'{endpoint}/execute'

    try:
        async with aiohttp.ClientSession(trust_env=True) as session:
            async with session.post(
                endpoint,
                json={'code': code, 'language': 'python'},
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=timeout),
            ) as response:
                if response.status >= 400:
                    err_text = await response.text()
                    return {'stderr': f'Sandbox error ({response.status}): {err_text}', 'stdout': '', 'result': ''}
                data = await response.json()
                stdout = data.get('stdout', data.get('output', ''))
                stderr = data.get('stderr', data.get('error', ''))
                result = data.get('result', '')
                return {
                    'stdout': str(stdout).strip() if stdout else '',
                    'stderr': str(stderr).strip() if stderr else '',
                    'result': str(result).strip() if result else '',
                }
    except Exception as err:
        logger.exception('Sandbox code execution failed: %s', err)
        return {'stderr': f'Sandbox execution error: {err}', 'stdout': '', 'result': ''}


async def execute_code_docker(
    docker_url: str = '', code: str = '', image: str = 'python:3.11-slim', timeout: int = 60
) -> dict:
    """Execute code in an isolated Docker container."""
    image = image or 'python:3.11-slim'

    if docker_url and docker_url.startswith(('http://', 'https://')):
        try:
            base = docker_url.rstrip('/')
            async with aiohttp.ClientSession(trust_env=True) as session:
                create_payload = {
                    'Image': image,
                    'Cmd': ['python3', '-c', code],
                    'NetworkDisabled': True,
                    'HostConfig': {'AutoRemove': True, 'Memory': 512 * 1024 * 1024},
                }
                async with session.post(f'{base}/containers/create', json=create_payload) as resp:
                    if resp.status >= 400:
                        err = await resp.text()
                        return {'stderr': f'Docker container create error: {err}', 'stdout': '', 'result': ''}
                    container = await resp.json()
                    cid = container.get('Id')

                async with session.post(f'{base}/containers/{cid}/start') as resp:
                    pass

                async with session.post(f'{base}/containers/{cid}/wait', timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
                    pass

                async with session.get(f'{base}/containers/{cid}/logs?stdout=1&stderr=1') as resp:
                    logs = await resp.text()
                    return {'stdout': logs.strip(), 'stderr': '', 'result': ''}
        except Exception as err:
            logger.exception('Docker REST execution error: %s', err)
            return {'stderr': f'Docker execution error: {err}', 'stdout': '', 'result': ''}

    try:
        proc = await asyncio.create_subprocess_exec(
            'docker',
            'run',
            '--rm',
            '-i',
            '--net=none',
            '--memory=512m',
            image,
            'python3',
            '-c',
            code,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        return {
            'stdout': stdout.decode('utf-8', errors='replace').strip(),
            'stderr': stderr.decode('utf-8', errors='replace').strip(),
            'result': '',
        }
    except asyncio.TimeoutError:
        try:
            proc.kill()
        except Exception:
            pass
        return {'stderr': 'Docker execution timed out.', 'stdout': '', 'result': ''}
    except Exception as err:
        logger.exception('Docker subprocess execution failed: %s', err)
        return {'stderr': f'Docker execution error: {err}', 'stdout': '', 'result': ''}


async def execute_code_e2b(api_key: str, code: str, timeout: int = 60) -> dict:
    """Execute code in an E2B cloud sandbox."""
    if not api_key:
        return {'stderr': 'E2B API Key is not configured.', 'stdout': '', 'result': ''}

    try:
        try:
            from e2b_code_interpreter import Sandbox
            sbx = Sandbox(api_key=api_key)
            execution = sbx.run_code(code)
            results = []
            for r in execution.results:
                if hasattr(r, 'text') and r.text:
                    results.append(r.text)
                elif hasattr(r, 'png') and r.png:
                    results.append(f'data:image/png;base64,{r.png}')
            stdout = '\n'.join(execution.logs.stdout)
            stderr = '\n'.join(execution.logs.stderr)
            if execution.error:
                stderr += f'\n{execution.error.name}: {execution.error.value}'
            sbx.kill()
            return {
                'stdout': stdout.strip(),
                'stderr': stderr.strip(),
                'result': '\n'.join(results).strip(),
            }
        except ImportError:
            pass

        headers = {
            'X-API-KEY': api_key,
            'Content-Type': 'application/json',
        }
        async with aiohttp.ClientSession(trust_env=True) as session:
            async with session.post(
                'https://api.e2b.dev/sandboxes',
                json={'template': 'code-interpreter'},
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=timeout),
            ) as resp:
                if resp.status >= 400:
                    err = await resp.text()
                    return {'stderr': f'E2B sandbox creation error: {err}', 'stdout': '', 'result': ''}
                sbx_data = await resp.json()
                sbx_id = sbx_data.get('sandboxId', sbx_data.get('id'))

            exec_url = f'https://api.e2b.dev/sandboxes/{sbx_id}/commands'
            async with session.post(
                exec_url,
                json={'cmd': f'python3 -c "{code}"'},
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=timeout),
            ) as resp:
                data = await resp.json() if resp.status == 200 else {}
                stdout = data.get('stdout', '')
                stderr = data.get('stderr', '')

            try:
                await session.delete(f'https://api.e2b.dev/sandboxes/{sbx_id}', headers=headers)
            except Exception:
                pass

            return {
                'stdout': str(stdout).strip(),
                'stderr': str(stderr).strip(),
                'result': '',
            }
    except Exception as err:
        logger.exception('E2B code execution failed: %s', err)
        return {'stderr': f'E2B execution error: {err}', 'stdout': '', 'result': ''}
