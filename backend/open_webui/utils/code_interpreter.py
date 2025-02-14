import asyncio
import json
import uuid
import websockets
import requests
from urllib.parse import urljoin


async def execute_code_jupyter(
    jupyter_url, code, token=None, password=None, timeout=10
):
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
    session = requests.Session()  # Maintain cookies
    headers = {}  # Headers for requests

    # Authenticate using password
    if password and not token:
        try:
            login_url = urljoin(jupyter_url, "/login")
            response = session.get(login_url)
            response.raise_for_status()
            xsrf_token = session.cookies.get("_xsrf")
            if not xsrf_token:
                raise ValueError("Failed to fetch _xsrf token")

            login_data = {"_xsrf": xsrf_token, "password": password}
            login_response = session.post(
                login_url, data=login_data, cookies=session.cookies
            )
            login_response.raise_for_status()
            headers["X-XSRFToken"] = xsrf_token
        except Exception as e:
            return {
                "stdout": "",
                "stderr": f"Authentication Error: {str(e)}",
                "result": "",
            }

    # Construct API URLs with authentication token if provided
    params = f"?token={token}" if token else ""
    kernel_url = urljoin(jupyter_url, f"/api/kernels{params}")

    try:
        response = session.post(kernel_url, headers=headers, cookies=session.cookies)
        response.raise_for_status()
        kernel_id = response.json()["id"]

        websocket_url = urljoin(
            jupyter_url.replace("http", "ws"),
            f"/api/kernels/{kernel_id}/channels{params}",
        )

        ws_headers = {}
        if password and not token:
            ws_headers["X-XSRFToken"] = session.cookies.get("_xsrf")
            cookies = {name: value for name, value in session.cookies.items()}
            ws_headers["Cookie"] = "; ".join(
                [f"{name}={value}" for name, value in cookies.items()]
            )

        async with websockets.connect(
            websocket_url, additional_headers=ws_headers
        ) as ws:
            msg_id = str(uuid.uuid4())
            execute_request = {
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
            await ws.send(json.dumps(execute_request))

            stdout, stderr, result = "", "", []

            while True:
                try:
                    message = await asyncio.wait_for(ws.recv(), timeout)
                    message_data = json.loads(message)
                    if message_data.get("parent_header", {}).get("msg_id") == msg_id:
                        msg_type = message_data.get("msg_type")

                        if msg_type == "stream":
                            if message_data["content"]["name"] == "stdout":
                                stdout += message_data["content"]["text"]
                            elif message_data["content"]["name"] == "stderr":
                                stderr += message_data["content"]["text"]

                        elif msg_type in ("execute_result", "display_data"):
                            data = message_data["content"]["data"]
                            if "image/png" in data:
                                result.append(
                                    f"data:image/png;base64,{data['image/png']}"
                                )
                            elif "text/plain" in data:
                                result.append(data["text/plain"])

                        elif msg_type == "error":
                            stderr += "\n".join(message_data["content"]["traceback"])

                        elif (
                            msg_type == "status"
                            and message_data["content"]["execution_state"] == "idle"
                        ):
                            break

                except asyncio.TimeoutError:
                    stderr += "\nExecution timed out."
                    break

    except Exception as e:
        return {"stdout": "", "stderr": f"Error: {str(e)}", "result": ""}

    finally:
        if kernel_id:
            requests.delete(
                f"{kernel_url}/{kernel_id}", headers=headers, cookies=session.cookies
            )

    return {
        "stdout": stdout.strip(),
        "stderr": stderr.strip(),
        "result": "\n".join(result).strip() if result else "",
    }
