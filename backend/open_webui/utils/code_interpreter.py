import asyncio
import json
import logging
import uuid
from typing import Optional

import aiohttp
import websockets
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class ResultModel(BaseModel):
    """
    Execute Code Result Model
    """

    stdout: Optional[str] = ""
    stderr: Optional[str] = ""
    result: Optional[str] = ""


class JupyterCodeExecuter:
    """
    Execute code in jupyter notebook
    """

    def __init__(
        self,
        base_url: str,
        code: str,
        token: str = "",
        password: str = "",
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
        self.kernel_id = ""
        if self.base_url[-1] != "/":
            self.base_url += "/"
        self.session = aiohttp.ClientSession(trust_env=True, base_url=self.base_url)
        self.params = {}
        self.result = ResultModel()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.kernel_id:
            try:
                async with self.session.delete(
                    f"api/kernels/{self.kernel_id}", params=self.params
                ) as response:
                    response.raise_for_status()
            except Exception as err:
                logger.exception("close kernel failed, %s", err)
        await self.session.close()

    async def run(self) -> ResultModel:
        try:
            await self.sign_in()
            await self.init_kernel()
            await self.execute_code()
        except Exception as err:
            logger.exception("execute code failed, %s", err)
            self.result.stderr = f"Error: {err}"
        return self.result

    async def sign_in(self) -> None:
        # password authentication
        if self.password and not self.token:
            async with self.session.get("login") as response:
                response.raise_for_status()
                xsrf_token = response.cookies["_xsrf"].value
                if not xsrf_token:
                    raise ValueError("_xsrf token not found")
                self.session.cookie_jar.update_cookies(response.cookies)
                self.session.headers.update({"X-XSRFToken": xsrf_token})
            async with self.session.post(
                "login",
                data={"_xsrf": xsrf_token, "password": self.password},
                allow_redirects=False,
            ) as response:
                response.raise_for_status()
                self.session.cookie_jar.update_cookies(response.cookies)

        # token authentication
        if self.token:
            self.params.update({"token": self.token})

    async def init_kernel(self) -> None:
        async with self.session.post(url="api/kernels", params=self.params) as response:
            response.raise_for_status()
            kernel_data = await response.json()
            self.kernel_id = kernel_data["id"]

    def init_ws(self) -> (str, dict):
        ws_base = self.base_url.replace("http", "ws", 1)
        ws_params = "?" + "&".join([f"{key}={val}" for key, val in self.params.items()])
        websocket_url = f"{ws_base}api/kernels/{self.kernel_id}/channels{ws_params if len(ws_params) > 1 else ''}"
        ws_headers = {}
        if self.password and not self.token:
            ws_headers = {
                "Cookie": "; ".join(
                    [
                        f"{cookie.key}={cookie.value}"
                        for cookie in self.session.cookie_jar
                    ]
                ),
                **self.session.headers,
            }
        return websocket_url, ws_headers

    async def execute_code(self) -> None:
        # initialize ws
        websocket_url, ws_headers = self.init_ws()
        # execute
        async with websockets.connect(
            websocket_url, additional_headers=ws_headers
        ) as ws:
            await self.execute_in_jupyter(ws)

    async def execute_in_jupyter(self, ws) -> None:
        # Preamble: ensure a writable data directory exists and track existing
        # files so we can detect new outputs written by skills.
        # Try /mnt/data first (ChatGPT/Vercel convention), fall back to /tmp/data.
        preamble = (
            "import os as __owui_os, tempfile as __owui_tmp\n"
            "__owui_data_dir = '/mnt/data'\n"
            "try:\n"
            "    __owui_os.makedirs(__owui_data_dir, exist_ok=True)\n"
            "    # Verify it's writable\n"
            "    __owui_test = __owui_os.path.join(__owui_data_dir, '.owui_test')\n"
            "    open(__owui_test, 'w').close()\n"
            "    __owui_os.remove(__owui_test)\n"
            "except (PermissionError, OSError):\n"
            "    __owui_data_dir = __owui_os.path.join(__owui_tmp.gettempdir(), 'data')\n"
            "    __owui_os.makedirs(__owui_data_dir, exist_ok=True)\n"
            "__owui_pre_files = set(__owui_os.listdir(__owui_data_dir))\n"
            "del __owui_tmp\n"
        )
        code_with_preamble = preamble + self.code

        # send message
        msg_id = uuid.uuid4().hex
        await ws.send(
            json.dumps(
                {
                    "header": {
                        "msg_id": msg_id,
                        "msg_type": "execute_request",
                        "username": "user",
                        "session": uuid.uuid4().hex,
                        "date": "",
                        "version": "5.3",
                    },
                    "parent_header": {},
                    "metadata": {},
                    "content": {
                        "code": code_with_preamble,
                        "silent": False,
                        "store_history": True,
                        "user_expressions": {},
                        "allow_stdin": False,
                        "stop_on_error": True,
                    },
                    "channel": "shell",
                }
            )
        )
        # parse message
        stdout, stderr, result = "", "", []
        while True:
            try:
                # wait for message
                message = await asyncio.wait_for(ws.recv(), self.timeout)
                message_data = json.loads(message)
                # msg id not match, skip
                if message_data.get("parent_header", {}).get("msg_id") != msg_id:
                    continue
                # check message type
                msg_type = message_data.get("msg_type")
                match msg_type:
                    case "stream":
                        if message_data["content"]["name"] == "stdout":
                            stdout += message_data["content"]["text"]
                        elif message_data["content"]["name"] == "stderr":
                            stderr += message_data["content"]["text"]
                    case "execute_result" | "display_data":
                        data = message_data["content"]["data"]
                        handled = False
                        for mime_type in data:
                            if mime_type == "text/plain":
                                continue
                            if (
                                mime_type.startswith("image/")
                                or mime_type.startswith("application/")
                                or mime_type.startswith("audio/")
                            ):
                                result.append(
                                    f"data:{mime_type};base64,{data[mime_type]}"
                                )
                                handled = True
                                break
                        if not handled and "text/plain" in data:
                            result.append(data["text/plain"])
                    case "error":
                        stderr += "\n".join(message_data["content"]["traceback"])
                    case "status":
                        if message_data["content"]["execution_state"] == "idle":
                            break

            except asyncio.TimeoutError:
                stderr += "\nExecution timed out."
                break

        # Post-execution: scan the data directory for new files and emit as data URIs.
        # This allows skills that save files to deliver downloadable attachments.
        # Uses __owui_data_dir set by the preamble (either /mnt/data or /tmp/data).
        postamble = (
            "import os as __owui_os, base64 as __owui_b64, mimetypes as __owui_mt\n"
            "from IPython.display import display as __owui_display\n"
            "# Register common office MIME types (not always present in minimal containers)\n"
            "__owui_mt.add_type('application/vnd.openxmlformats-officedocument.presentationml.presentation', '.pptx')\n"
            "__owui_mt.add_type('application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', '.xlsx')\n"
            "__owui_mt.add_type('application/vnd.openxmlformats-officedocument.wordprocessingml.document', '.docx')\n"
            "__owui_mt.add_type('application/pdf', '.pdf')\n"
            "__owui_mt.add_type('text/csv', '.csv')\n"
            "if '__owui_pre_files' in dir() and '__owui_data_dir' in dir():\n"
            "    __owui_new = sorted(set(__owui_os.listdir(__owui_data_dir)) - __owui_pre_files)\n"
            "    for __owui_f in __owui_new:\n"
            "        __owui_p = __owui_os.path.join(__owui_data_dir, __owui_f)\n"
            "        if __owui_os.path.isfile(__owui_p):\n"
            "            __owui_ct = __owui_mt.guess_type(__owui_p)[0] or 'application/octet-stream'\n"
            "            with open(__owui_p, 'rb') as __owui_fh:\n"
            "                __owui_d = __owui_b64.b64encode(__owui_fh.read()).decode()\n"
            "            __owui_display({__owui_ct: __owui_d, 'text/plain': __owui_f}, raw=True)\n"
            "    del __owui_pre_files, __owui_data_dir\n"
        )
        post_msg_id = uuid.uuid4().hex
        await ws.send(
            json.dumps(
                {
                    "header": {
                        "msg_id": post_msg_id,
                        "msg_type": "execute_request",
                        "username": "user",
                        "session": uuid.uuid4().hex,
                        "date": "",
                        "version": "5.3",
                    },
                    "parent_header": {},
                    "metadata": {},
                    "content": {
                        "code": postamble,
                        "silent": False,
                        "store_history": False,
                        "user_expressions": {},
                        "allow_stdin": False,
                        "stop_on_error": False,
                    },
                    "channel": "shell",
                }
            )
        )
        # Capture only display_data from postamble (file outputs)
        while True:
            try:
                message = await asyncio.wait_for(ws.recv(), self.timeout)
                message_data = json.loads(message)
                if message_data.get("parent_header", {}).get("msg_id") != post_msg_id:
                    continue
                msg_type = message_data.get("msg_type")
                match msg_type:
                    case "display_data":
                        data = message_data["content"]["data"]
                        filename = data.get("text/plain", "")
                        for mime_type in data:
                            if mime_type == "text/plain":
                                continue
                            if (
                                mime_type.startswith("image/")
                                or mime_type.startswith("application/")
                                or mime_type.startswith("audio/")
                            ):
                                # Encode original filename into the data URI
                                # so downstream processors can use it
                                if filename:
                                    safe_name = filename.replace(";", "_")
                                    result.append(
                                        f"data:{mime_type};filename={safe_name};base64,{data[mime_type]}"
                                    )
                                else:
                                    result.append(
                                        f"data:{mime_type};base64,{data[mime_type]}"
                                    )
                                break
                    case "status":
                        if message_data["content"]["execution_state"] == "idle":
                            break
            except asyncio.TimeoutError:
                break

        self.result.stdout = stdout.strip()
        self.result.stderr = stderr.strip()
        self.result.result = "\n".join(result).strip() if result else ""


async def execute_code_jupyter(
    base_url: str, code: str, token: str = "", password: str = "", timeout: int = 60
) -> dict:
    async with JupyterCodeExecuter(
        base_url, code, token, password, timeout
    ) as executor:
        result = await executor.run()
        return result.model_dump()
