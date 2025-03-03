import asyncio
import json
import uuid
from typing import Optional

import httpx
import websockets


async def execute_code_jupyter(
    jupyter_url: str, code: str, token: str = None, password: str = None, timeout: int = 60
) -> Optional[dict]:
    """
    Executes Python code in a Jupyter kernel.
    Supports authentication with a token or password.
    :param jupyter_url: Jupyter server URL (e.g., "http://localhost:8888")
    :param code: Code to execute
    :param token: Jupyter authentication token (optional)
    :param password: Jupyter password (optional)
    :param timeout: WebSocket timeout in seconds (default: 10s)
    :return: Dictionary with stdout, stderr, and result
             - Images are prefixed with "base64:image/png," and separated by newlines if multiple.
    """

    jupyter_url = jupyter_url.rstrip("/")
    client = httpx.AsyncClient(base_url=jupyter_url, timeout=timeout, follow_redirects=True)
    headers = {}

    # password authentication
    if password and not token:
        try:
            response = await client.get("/login")
            response.raise_for_status()
            xsrf_token = response.cookies.get("_xsrf")
            if not xsrf_token:
                raise ValueError("_xsrf token not found")
            response = await client.post("/login", data={"_xsrf": xsrf_token, "password": password})
            response.raise_for_status()
            headers["X-XSRFToken"] = xsrf_token
        except Exception as e:
            return {"stdout": "", "stderr": f"Authentication Error: {str(e)}", "result": ""}

    # token authentication
    params = {"token": token} if token else {}

    kernel_id = ""
    try:
        response = await client.post(url="/api/kernels", params=params, headers=headers)
        response.raise_for_status()
        kernel_id = response.json()["id"]

        ws_base = jupyter_url.replace("http", "ws")
        websocket_url = f"{ws_base}/api/kernels/{kernel_id}/channels" + (f"?token={token}" if token else "")
        ws_headers = {}
        if password and not token:
            ws_headers = {
                "X-XSRFToken": client.cookies.get("_xsrf"),
                "Cookie": "; ".join([f"{name}={value}" for name, value in client.cookies.items()]),
            }

        async with websockets.connect(websocket_url, additional_headers=ws_headers) as ws:
            msg_id = str(uuid.uuid4())
            await ws.send(
                json.dumps(
                    {
                        "header": {
                            "msg_id": msg_id,
                            "msg_type": "execute_request",
                            "username": "user",
                            "session": str(uuid.uuid4()),
                            "date": "",
                            "version": "5.3",
                        },
                        "parent_header": {},
                        "metadata": {},
                        "content": {
                            "code": code,
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

            stdout, stderr, result = "", "", []

            while True:
                try:
                    message = await asyncio.wait_for(ws.recv(), timeout)
                    message_data = json.loads(message)
                    if message_data.get("parent_header", {}).get("msg_id") != msg_id:
                        continue

                    msg_type = message_data.get("msg_type")
                    match msg_type:
                        case "stream":
                            if message_data["content"]["name"] == "stdout":
                                stdout += message_data["content"]["text"]
                            elif message_data["content"]["name"] == "stderr":
                                stderr += message_data["content"]["text"]
                        case "execute_result" | "display_data":
                            data = message_data["content"]["data"]
                            if "image/png" in data:
                                result.append(f"data:image/png;base64,{data['image/png']}")
                            elif "text/plain" in data:
                                result.append(data["text/plain"])
                        case "error":
                            stderr += "\n".join(message_data["content"]["traceback"])
                        case "status":
                            if message_data["content"]["execution_state"] == "idle":
                                break

                except asyncio.TimeoutError:
                    stderr += "\nExecution timed out."
                    break

    except Exception as e:
        return {"stdout": "", "stderr": f"Error: {str(e)}", "result": ""}

    finally:
        if kernel_id:
            await client.delete(f"/api/kernels/{kernel_id}", headers=headers, params=params)
        await client.aclose()

    return {"stdout": stdout.strip(), "stderr": stderr.strip(), "result": "\n".join(result).strip() if result else ""}
