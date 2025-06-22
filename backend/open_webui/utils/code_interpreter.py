import asyncio
import json
import logging
import os
import uuid
from typing import Optional, List, Dict, Any

import aiohttp
import websockets
from pydantic import BaseModel

from open_webui.env import SRC_LOG_LEVELS

# Import necessary models for chat and file operations
from open_webui.models.chats import Chats
from open_webui.models.files import Files

logger = logging.getLogger(__name__)
logger.setLevel(SRC_LOG_LEVELS["MAIN"])


def get_attached_files_from_chat(chat_id: str) -> List[Dict[str, Any]]:
    """
    Scan through all messages in a chat to find attached files.
    Returns a list of file metadata dictionaries.
    """
    logger.info(f"Scanning chat {chat_id} for attached files")

    try:
        # Get the chat data
        chat = Chats.get_chat_by_id(chat_id)
        if not chat:
            logger.warning(f"Chat {chat_id} not found")
            return []

        attached_files = []
        chat_data = chat.chat

        # Extract messages from chat history
        messages = chat_data.get("history", {}).get("messages", {})

        for message_id, message in messages.items():
            # Check if message has files attached
            files = message.get("files", [])

            for file_info in files:
                # Extract file metadata
                file_data = {
                    "id": file_info.get("id"),
                    "name": file_info.get("name", "unknown_file"),
                    "type": file_info.get("type", "file"),
                    "size": file_info.get("size"),
                    "url": file_info.get("url"),
                    "message_id": message_id,
                }

                # Only include files with valid IDs
                if file_data["id"]:
                    attached_files.append(file_data)
                    logger.debug(
                        f"Found attached file: {file_data['name']} (ID: {file_data['id']})"
                    )

        logger.info(f"Found {len(attached_files)} attached files in chat {chat_id}")
        return attached_files

    except Exception as e:
        logger.error(f"Error scanning chat {chat_id} for files: {str(e)}")
        return []


async def auto_prepare_chat_files(
    chat_id: str, data_dir: str = "data"
) -> Dict[str, Any]:
    """
    Automatically prepare files attached to chat messages for use in the Jupyter environment.
    Creates symbolic links in the Jupyter data directory pointing to the uploaded files.
    Falls back to copying files if symlinks don't work (e.g., Docker environments).

    Args:
        chat_id: The chat ID to prepare files for
        data_dir: Base data directory (default: "data")

    Returns:
        Dictionary with preparation results including success status, prepared files count, and any errors
    """
    logger.info(f"Auto-preparing files for chat {chat_id}")

    result = {
        "success": False,
        "chat_id": chat_id,
        "prepared_files": [],
        "skipped_files": [],
        "errors": [],
        "total_files": 0,
        "method": None,  # Will be "symlink" or "copy"
    }

    try:
        # Get attached files from chat
        attached_files = get_attached_files_from_chat(chat_id)
        result["total_files"] = len(attached_files)

        if not attached_files:
            logger.info(f"No files found in chat {chat_id}")
            result["success"] = True
            return result

        # Create chat-specific data directory
        chat_data_dir = os.path.join(data_dir, "uploads", chat_id)
        os.makedirs(chat_data_dir, exist_ok=True)
        logger.info(f"Created/verified chat data directory: {chat_data_dir}")

        # Test which method to use: symlink or copy
        # Force copy method for Docker compatibility - symlinks often fail in bind volumes
        use_symlinks = False
        # use_symlinks = await _test_symlink_accessibility(chat_data_dir, data_dir)
        method = "symlink" if use_symlinks else "copy"
        result["method"] = method
        logger.info(
            f"Using {method} method for file preparation (hardcoded for Docker compatibility)"
        )

        # Track successfully processed files to avoid duplicates
        processed_file_ids = set()

        for file_info in attached_files:
            file_id = file_info["id"]
            file_name = file_info["name"]

            try:
                # Skip if already processed (deduplication)
                if file_id in processed_file_ids:
                    logger.debug(f"Skipping duplicate file {file_name} (ID: {file_id})")
                    result["skipped_files"].append(
                        {"name": file_name, "id": file_id, "reason": "duplicate"}
                    )
                    continue

                # Get file from database
                file_record = Files.get_file_by_id(file_id)
                if not file_record:
                    logger.warning(f"File record not found for ID: {file_id}")
                    result["errors"].append(
                        f"File record not found: {file_name} (ID: {file_id})"
                    )
                    continue

                # Use the actual file path from the database
                if not file_record.path:
                    logger.warning(f"File path not found in record for ID: {file_id}")
                    result["errors"].append(
                        f"File path not found: {file_name} (ID: {file_id})"
                    )
                    continue

                # Get the actual file path (handles different storage providers)
                from open_webui.storage.provider import Storage

                source_file_path = Storage.get_file(file_record.path)

                # Check if source file exists
                if not os.path.exists(source_file_path):
                    logger.warning(f"Source file not found: {source_file_path}")
                    result["errors"].append(f"Source file not found: {file_name}")
                    continue

                # Create target path in chat data directory
                target_path = os.path.join(chat_data_dir, file_name)

                # Remove existing file/symlink if it exists
                if os.path.exists(target_path) or os.path.islink(target_path):
                    if os.path.islink(target_path):
                        os.unlink(target_path)
                        logger.debug(f"Removed existing symlink: {target_path}")
                    else:
                        os.remove(target_path)
                        logger.debug(f"Removed existing file: {target_path}")

                # Prepare file using the appropriate method
                if use_symlinks:
                    # Create symbolic link using absolute path to ensure it resolves correctly
                    source_file_path_abs = os.path.abspath(source_file_path)
                    os.symlink(source_file_path_abs, target_path)
                    logger.info(
                        f"Created symlink: {target_path} -> {source_file_path_abs}"
                    )
                else:
                    # Copy file
                    import shutil

                    shutil.copy2(source_file_path, target_path)
                    logger.info(f"Copied file: {source_file_path} -> {target_path}")

                # Record successful preparation
                result["prepared_files"].append(
                    {
                        "name": file_name,
                        "id": file_id,
                        "target_path": target_path,
                        "source_path": source_file_path,
                        "size": file_info.get("size"),
                        "type": file_info.get("type"),
                        "method": method,
                    }
                )

                processed_file_ids.add(file_id)

            except Exception as e:
                error_msg = f"Error preparing file {file_name}: {str(e)}"
                logger.error(error_msg)
                result["errors"].append(error_msg)

        # Set success if we prepared at least some files or if there were no errors
        result["success"] = (
            len(result["prepared_files"]) > 0 or len(result["errors"]) == 0
        )

        logger.info(
            f"Auto-prepare completed for chat {chat_id}: "
            f"{len(result['prepared_files'])} prepared using {method}, "
            f"{len(result['skipped_files'])} skipped, "
            f"{len(result['errors'])} errors"
        )

        return result

    except Exception as e:
        error_msg = f"Failed to auto-prepare files for chat {chat_id}: {str(e)}"
        logger.error(error_msg)
        result["errors"].append(error_msg)
        result["success"] = False
        return result


async def _test_symlink_accessibility(chat_data_dir: str, data_dir: str) -> bool:
    """
    Test whether symlinks will work in the target environment.
    This is especially important for Docker environments where symlinks may not be accessible.

    Args:
        chat_data_dir: The directory where files will be prepared
        data_dir: The base data directory

    Returns:
        True if symlinks should be used, False if files should be copied
    """
    test_dir = os.path.join(chat_data_dir, ".test_symlink")
    test_source = None
    test_symlink = None

    try:
        # Create test directory
        os.makedirs(test_dir, exist_ok=True)

        # Ensure uploads directory exists for source file
        uploads_dir = os.path.join(data_dir, "uploads")
        os.makedirs(uploads_dir, exist_ok=True)

        # Create a test source file in the uploads directory
        test_source = os.path.join(uploads_dir, ".test_source_file")
        with open(test_source, "w") as f:
            f.write("test_content_for_symlink_detection")

        # Create test symlink using absolute path to ensure it resolves correctly
        test_symlink = os.path.join(test_dir, "test_symlink")
        test_source_abs = os.path.abspath(test_source)
        os.symlink(test_source_abs, test_symlink)

        # Test 1: Can we create the symlink?
        if not os.path.islink(test_symlink):
            logger.warning("Symlink creation test failed - file is not a symlink")
            return False

        # Test 2: Can we read through the symlink?
        try:
            with open(test_symlink, "r") as f:
                content = f.read()
            if content != "test_content_for_symlink_detection":
                logger.warning("Symlink accessibility test failed - content mismatch")
                return False
        except Exception as e:
            logger.warning(
                f"Symlink accessibility test failed - cannot read through symlink: {e}"
            )
            return False

        # Test 3: Can we stat the symlink target?
        try:
            stat_result = os.stat(test_symlink)
            if not stat_result:
                logger.warning("Symlink stat test failed")
                return False
        except Exception as e:
            logger.warning(f"Symlink stat test failed: {e}")
            return False

        logger.info("Symlink accessibility test passed - using symlinks")
        return True

    except OSError as e:
        if "Operation not supported" in str(e) or "Function not implemented" in str(e):
            logger.info(
                "Symlinks not supported on this filesystem - using file copying"
            )
        else:
            logger.warning(
                f"Symlink test failed with OS error: {e} - using file copying"
            )
        return False
    except Exception as e:
        logger.warning(f"Symlink test failed: {e} - using file copying")
        return False
    finally:
        # Clean up test files
        try:
            if test_symlink and (
                os.path.exists(test_symlink) or os.path.islink(test_symlink)
            ):
                os.unlink(test_symlink)
            if test_source and os.path.exists(test_source):
                os.remove(test_source)
            if os.path.exists(test_dir):
                os.rmdir(test_dir)
        except Exception as e:
            logger.debug(f"Test cleanup failed (non-critical): {e}")


async def prepare_multiple_chats_files(
    chat_ids: List[str], data_dir: str = "data"
) -> Dict[str, Any]:
    """
    Prepare files for multiple chats at once (bulk operation).

    Args:
        chat_ids: List of chat IDs to prepare files for
        data_dir: Base data directory (default: "data")

    Returns:
        Dictionary with overall results and per-chat results
    """
    logger.info(f"Bulk preparing files for {len(chat_ids)} chats")

    overall_result = {
        "success": True,
        "total_chats": len(chat_ids),
        "successful_chats": 0,
        "failed_chats": 0,
        "chat_results": {},
        "summary": {
            "total_prepared_files": 0,
            "total_skipped_files": 0,
            "total_errors": 0,
        },
    }

    for chat_id in chat_ids:
        try:
            chat_result = await auto_prepare_chat_files(chat_id, data_dir)
            overall_result["chat_results"][chat_id] = chat_result

            if chat_result["success"]:
                overall_result["successful_chats"] += 1
            else:
                overall_result["failed_chats"] += 1
                overall_result["success"] = False

            # Update summary
            overall_result["summary"]["total_prepared_files"] += len(
                chat_result["prepared_files"]
            )
            overall_result["summary"]["total_skipped_files"] += len(
                chat_result["skipped_files"]
            )
            overall_result["summary"]["total_errors"] += len(chat_result["errors"])

        except Exception as e:
            error_msg = f"Failed to prepare chat {chat_id}: {str(e)}"
            logger.error(error_msg)
            overall_result["chat_results"][chat_id] = {
                "success": False,
                "errors": [error_msg],
            }
            overall_result["failed_chats"] += 1
            overall_result["success"] = False

    logger.info(
        f"Bulk prepare completed: {overall_result['successful_chats']}/{overall_result['total_chats']} successful"
    )
    return overall_result


def test_filesystem_support(data_dir: str = "data") -> Dict[str, Any]:
    """
    Test filesystem support for symlinks and file operations.
    Helps identify permission problems and symlink support issues.

    Args:
        data_dir: Base data directory to test in

    Returns:
        Dictionary with test results
    """
    logger.info(f"Testing filesystem support in {data_dir}")

    test_result = {"success": True, "tests": {}, "errors": [], "recommendations": []}

    test_dir = os.path.join(data_dir, "test_auto_prepare")

    try:
        # Test 1: Directory creation
        try:
            os.makedirs(test_dir, exist_ok=True)
            test_result["tests"]["directory_creation"] = True
            logger.debug("✓ Directory creation test passed")
        except Exception as e:
            test_result["tests"]["directory_creation"] = False
            test_result["errors"].append(f"Directory creation failed: {str(e)}")
            test_result["success"] = False

        # Test 2: File creation
        test_file = os.path.join(test_dir, "test_file.txt")
        try:
            with open(test_file, "w") as f:
                f.write("test content")
            test_result["tests"]["file_creation"] = True
            logger.debug("✓ File creation test passed")
        except Exception as e:
            test_result["tests"]["file_creation"] = False
            test_result["errors"].append(f"File creation failed: {str(e)}")
            test_result["success"] = False

        # Test 3: Symlink creation
        test_symlink = os.path.join(test_dir, "test_symlink.txt")
        try:
            if os.path.exists(test_file):
                # Use absolute path for symlink target to ensure it resolves correctly
                test_file_abs = os.path.abspath(test_file)
                os.symlink(test_file_abs, test_symlink)
                test_result["tests"]["symlink_creation"] = True
                logger.debug("✓ Symlink creation test passed")
            else:
                test_result["tests"]["symlink_creation"] = False
                test_result["errors"].append(
                    "Cannot test symlink: source file doesn't exist"
                )
        except Exception as e:
            test_result["tests"]["symlink_creation"] = False
            test_result["errors"].append(f"Symlink creation failed: {str(e)}")
            test_result["success"] = False
            if "Operation not permitted" in str(e) or "not supported" in str(e).lower():
                test_result["recommendations"].append(
                    "Filesystem may not support symlinks. Consider using file copies instead."
                )

        # Test 4: Path resolution
        try:
            if os.path.exists(test_symlink):
                resolved_path = os.path.realpath(test_symlink)
                if resolved_path == os.path.realpath(test_file):
                    test_result["tests"]["path_resolution"] = True
                    logger.debug("✓ Path resolution test passed")
                else:
                    test_result["tests"]["path_resolution"] = False
                    test_result["errors"].append("Symlink path resolution incorrect")
            else:
                test_result["tests"]["path_resolution"] = False
                test_result["errors"].append(
                    "Cannot test path resolution: symlink doesn't exist"
                )
        except Exception as e:
            test_result["tests"]["path_resolution"] = False
            test_result["errors"].append(f"Path resolution test failed: {str(e)}")

        # Test 5: Docker symlink accessibility (new test)
        if test_result["tests"].get("symlink_creation", False):
            try:
                # Test if we can read the symlink (this often fails in Docker environments)
                with open(test_symlink, "r") as f:
                    content = f.read()
                if content == "test content":
                    test_result["tests"]["symlink_accessibility"] = True
                    logger.debug("✓ Symlink accessibility test passed")
                else:
                    test_result["tests"]["symlink_accessibility"] = False
                    test_result["errors"].append(
                        "Symlink content mismatch - possible Docker volume issue"
                    )
                    test_result["recommendations"].append(
                        "Symlinks may not work in Docker environment. Auto-prepare will use file copying."
                    )
            except Exception as e:
                test_result["tests"]["symlink_accessibility"] = False
                test_result["errors"].append(f"Symlink accessibility failed: {str(e)}")
                test_result["recommendations"].append(
                    "Symlinks not accessible - likely Docker environment. Auto-prepare will use file copying."
                )
        else:
            test_result["tests"]["symlink_accessibility"] = False

    finally:
        # Cleanup test files
        try:
            if os.path.exists(test_symlink) or os.path.islink(test_symlink):
                os.unlink(test_symlink)
            if os.path.exists(test_file):
                os.unlink(test_file)
            if os.path.exists(test_dir):
                os.rmdir(test_dir)
            logger.debug("✓ Test cleanup completed")
        except Exception as e:
            logger.warning(f"Test cleanup failed: {str(e)}")

    # Add recommendations based on test results
    if not test_result["tests"].get("symlink_creation", False):
        test_result["recommendations"].append(
            "Consider implementing file copying as fallback for symlink failures"
        )

    if test_result["success"]:
        logger.info("✓ All filesystem tests passed")
    else:
        logger.warning(
            f"⚠ Some filesystem tests failed: {len(test_result['errors'])} errors"
        )

    return test_result


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

    def init_ws(self) -> tuple[str, dict]:
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
                        "code": self.code,
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
        self.result.stdout = stdout.strip()
        self.result.stderr = stderr.strip()
        self.result.result = "\n".join(result).strip() if result else ""


class EnterpriseGatewayCodeExecutor:
    """
    Execute code in Jupyter Enterprise Gateway
    """

    def __init__(
        self,
        base_url: str,
        code: str,
        token: str = "",
        password: str = "",
        timeout: int = 60,
        kernel_name: str = "python",
        username: str = "code-interpreter",
        chat_id: str = "",
        data_dir: str = "data",
    ):
        """
        :param base_url: Enterprise Gateway server URL (e.g., "http://gateway:8888")
        :param code: Code to execute
        :param token: Authentication token (optional)
        :param password: Password (optional, not typically used with Enterprise Gateway)
        :param timeout: WebSocket timeout in seconds (default: 60s)
        :param kernel_name: Kernel name to use (default: from configuration)
        :param username: Username for the kernel (default: from configuration)
        :param chat_id: Chat ID for path replacement and auto-prepare (optional)
        :param data_dir: Base data directory path (default: "data")
        """
        self.base_url = base_url
        self.original_code = code
        self.token = token
        self.password = password
        self.timeout = timeout
        self.kernel_name = kernel_name
        self.username = username
        self.chat_id = chat_id
        self.data_dir = data_dir

        # Modify code to replace /mnt/data with chat-specific path
        self.code = self._prepare_code_with_path_replacement(code)

        # Auto-prepare files for this chat before code execution
        self.prepare_result = None
        if self.chat_id:
            logger.info(
                f"Auto-preparing files for chat {self.chat_id} before code execution"
            )
            try:
                # Note: This is synchronous but auto_prepare_chat_files is async
                # We'll need to handle this in the run() method instead
                self._auto_prepare_needed = True
                logger.debug(f"Marked auto-prepare as needed for chat {self.chat_id}")
            except Exception as e:
                logger.error(
                    f"Failed to mark auto-prepare for chat {self.chat_id}: {str(e)}"
                )
                self._auto_prepare_needed = False
        else:
            self._auto_prepare_needed = False

        if self.base_url[-1] != "/":
            self.base_url += "/"

        logger.info(
            f"Initializing Enterprise Gateway connection to {self.base_url} with kernel {self.kernel_name}"
        )
        if self.chat_id:
            logger.info(f"Using chat ID {self.chat_id} for path replacement")
        self.session = aiohttp.ClientSession(trust_env=True, base_url=self.base_url)
        self.headers = {}
        self.result = ResultModel()

    async def _auto_prepare_files(self) -> None:
        """Auto-prepare files for this chat if needed"""
        if not self._auto_prepare_needed or not self.chat_id:
            return

        try:
            self.prepare_result = await auto_prepare_chat_files(
                self.chat_id, self.data_dir
            )
            if self.prepare_result["success"]:
                prepared_count = len(self.prepare_result["prepared_files"])
                if prepared_count > 0:
                    logger.info(
                        f"Successfully prepared {prepared_count} files for chat {self.chat_id}"
                    )
                else:
                    logger.debug(f"No files to prepare for chat {self.chat_id}")
            else:
                logger.warning(
                    f"File preparation had issues for chat {self.chat_id}: {self.prepare_result['errors']}"
                )
        except Exception as e:
            logger.error(
                f"Failed to auto-prepare files for chat {self.chat_id}: {str(e)}"
            )
            # Continue with execution even if file preparation fails

    def _prepare_code_with_path_replacement(self, code: str) -> str:
        """
        Replace /mnt/data with chat-specific path before execution
        Similar to the logic in app.py: modified_code = response.replace(MNT_DATA_DIR, session_dir_path)
        """
        if not self.chat_id:
            logger.debug("No chat_id provided, using code as-is")
            return code

        # Create chat-specific path
        chat_data_path = f"{self.data_dir}/uploads/{self.chat_id}"

        # Ensure the directory exists
        os.makedirs(chat_data_path, exist_ok=True)
        logger.info(f"Ensured chat data path exists: {chat_data_path}")

        # Replace /mnt/data with the chat-specific path
        modified_code = code.replace("/mnt/data", chat_data_path)

        if modified_code != code:
            logger.debug(f"Replaced '/mnt/data' with '{chat_data_path}' in code")
            logger.debug(f"Original code: {code}")
            logger.debug(f"Modified code: {modified_code}")

        return modified_code

    def _prepare_results_with_path_replacement(self, text: str) -> str:
        """
        Replace chat-specific paths back to /mnt/data in output for user display
        This ensures users see familiar /mnt/data paths in results and error messages
        """
        if not self.chat_id or not text:
            return text

        # Create chat-specific path
        chat_data_path = f"{self.data_dir}/uploads/{self.chat_id}"

        # Replace the chat-specific path back to /mnt/data for user display
        modified_text = text.replace(chat_data_path, "/mnt/data")

        if modified_text != text:
            logger.debug(f"Replaced '{chat_data_path}' back to '/mnt/data' in output")

        return modified_text

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.kernel_id:
            try:
                async with self.session.delete(
                    f"api/kernels/{self.kernel_id}", headers=self.headers
                ) as response:
                    response.raise_for_status()
                    logger.info(f"Closed kernel {self.kernel_id}")
            except Exception as err:
                logger.exception("close kernel failed, %s", err)
        await self.session.close()

    async def run(self) -> ResultModel:
        try:
            # Auto-prepare files first if needed
            await self._auto_prepare_files()

            await self.setup_auth()
            await self.init_kernel()
            await self.execute_code()
        except Exception as err:
            logger.exception("execute code failed, %s", err)
            self.result.stderr = f"Error: {err}"
        return self.result

    async def setup_auth(self) -> None:
        if self.token:
            self.headers.update({"Authorization": f"token {self.token}"})
            logger.debug("Set up authorization header with token")

    async def init_kernel(self) -> None:
        payload = {
            "name": self.kernel_name,
            "env": {
                "KERNEL_USERNAME": self.username,
                "KERNEL_ID": str(uuid.uuid4()),
            },
        }

        logger.info(f"Starting {self.kernel_name} kernel for user {self.username}")
        try:
            async with self.session.post(
                url="api/kernels",
                json=payload,
                headers=self.headers,
            ) as response:
                response.raise_for_status()
                kernel_data = await response.json()
                self.kernel_id = kernel_data["id"]
                logger.info(f"Created kernel {self.kernel_id} for user {self.username}")
        except Exception as e:
            logger.error(f"Failed to create kernel: {str(e)}")
            raise

    def init_ws(self) -> tuple[str, dict]:
        ws_base = self.base_url.replace("http", "ws", 1)
        websocket_url = f"{ws_base}api/kernels/{self.kernel_id}/channels"
        logger.debug(f"Connecting to WebSocket at {websocket_url}")
        return websocket_url, self.headers

    async def execute_code(self) -> None:
        websocket_url, headers = self.init_ws()
        try:
            async with websockets.connect(
                websocket_url, additional_headers=headers
            ) as ws:
                await self.execute_in_gateway(ws)
        except websockets.exceptions.WebSocketException as e:
            logger.error(f"WebSocket error: {e}")
            self.result.stderr = f"WebSocket connection error: {e}"

    async def execute_in_gateway(self, ws) -> None:
        # Log the code that will be executed
        logger.debug(f"Original code: {self.original_code}")
        logger.debug(f"Modified code (after path replacement): {self.code}")
        if self.chat_id:
            logger.debug(f"Chat ID: {self.chat_id}, Data dir: {self.data_dir}")
            chat_data_path = f"{self.data_dir}/uploads/{self.chat_id}"
            logger.debug(f"Replacing '/mnt/data' with '{chat_data_path}'")

        # Send message using Enterprise Gateway format
        msg_id = str(uuid.uuid4())
        request = {
            "header": {
                "msg_id": msg_id,
                "msg_type": "execute_request",
                "username": self.username,
                "session": str(uuid.uuid4()),
                "version": "5.4",
            },
            "parent_header": {},
            "metadata": {},
            "content": {
                "code": self.code,
                "silent": False,
                "store_history": True,
                "user_expressions": {},
                "allow_stdin": False,
                "stop_on_error": True,
            },
            "buffers": [],
            "channel": "shell",
        }

        logger.debug(f"Sending execute request with msg_id {msg_id}")
        logger.debug(f"Code to execute: {self.code}")
        await ws.send(json.dumps(request))

        # Parse responses
        outputs, results = [], []
        stdout_content, stderr_content = "", ""
        error = None

        while True:
            try:
                # Wait for message
                message = await asyncio.wait_for(ws.recv(), self.timeout)
                response = json.loads(message)

                # Check if this message is a response to our request
                if response.get("parent_header", {}).get("msg_id") != msg_id:
                    continue

                msg_type = response.get("msg_type")
                logger.debug(f"Received message of type {msg_type}")

                if msg_type == "stream":
                    if response["content"]["name"] == "stdout":
                        stdout_content += response["content"]["text"]
                        logger.debug(f"STDOUT: {response['content']['text']}")
                    elif response["content"]["name"] == "stderr":
                        stderr_content += response["content"]["text"]
                        logger.debug(f"STDERR: {response['content']['text']}")

                elif msg_type == "execute_result":
                    logger.debug(f"Execute result: {response['content']}")
                    if "data" in response["content"]:
                        if "text/plain" in response["content"]["data"]:
                            result_text = response["content"]["data"]["text/plain"]
                            results.append(result_text)
                            logger.debug(f"Result text: {result_text}")
                        if "image/png" in response["content"]["data"]:
                            results.append(
                                f"data:image/png;base64,{response['content']['data']['image/png']}"
                            )
                            logger.debug("Added image result")

                elif msg_type == "display_data":
                    logger.debug(f"Display data: {response['content']}")
                    if "data" in response["content"]:
                        if "text/plain" in response["content"]["data"]:
                            result_text = response["content"]["data"]["text/plain"]
                            results.append(result_text)
                            logger.debug(f"Display text: {result_text}")
                        if "image/png" in response["content"]["data"]:
                            results.append(
                                f"data:image/png;base64,{response['content']['data']['image/png']}"
                            )
                            logger.debug("Added image display")

                elif msg_type == "error":
                    error = {
                        "ename": response["content"]["ename"],
                        "evalue": response["content"]["evalue"],
                        "traceback": response["content"]["traceback"],
                    }
                    stderr_content += "\n".join(error["traceback"])
                    logger.debug(f"Execution error: {error}")

                elif msg_type == "execute_reply":
                    logger.debug(
                        f"Execute reply status: {response['content']['status']}"
                    )
                    if response["content"]["status"] == "ok":
                        logger.debug("Received execute_reply with status=ok")
                        break
                    elif response["content"]["status"] == "error":
                        if (
                            not error
                        ):  # Only add if we haven't already processed an error message
                            error = {
                                "ename": response["content"]["ename"],
                                "evalue": response["content"]["evalue"],
                                "traceback": response["content"]["traceback"],
                            }
                            stderr_content += "\n".join(error["traceback"])
                        logger.debug("Received execute_reply with status=error")
                        break

                elif msg_type == "status":
                    if response["content"]["execution_state"] == "idle":
                        # We still wait for execute_reply before breaking out
                        logger.debug("Kernel is idle")

            except asyncio.TimeoutError:
                stderr_content += "\nExecution timed out."
                logger.warning(f"Execution timed out after {self.timeout}s")
                break

        self.result.stdout = self._prepare_results_with_path_replacement(
            stdout_content.strip()
        )
        self.result.stderr = self._prepare_results_with_path_replacement(
            stderr_content.strip()
        )
        self.result.result = self._prepare_results_with_path_replacement(
            "\n".join(results).strip() if results else ""
        )

        logger.debug(f"Final result - stdout: {self.result.stdout}")
        logger.debug(f"Final result - stderr: {self.result.stderr}")
        logger.debug(f"Final result - result: {self.result.result}")
        logger.info("Code execution completed")


async def deprecated_execute_code_jupyter(
    base_url: str, code: str, token: str = "", password: str = "", timeout: int = 60
) -> dict:
    async with JupyterCodeExecuter(
        base_url, code, token, password, timeout
    ) as executor:
        result = await executor.run()
        return result.model_dump()


async def execute_code_jupyter(
    base_url: str,
    code: str,
    token: str = "",
    password: str = "",
    timeout: int = 60,
    chat_id: str = "",
    data_dir: str = "data",
) -> dict:
    async with EnterpriseGatewayCodeExecutor(
        base_url, code, token, password, timeout, chat_id=chat_id, data_dir=data_dir
    ) as executor:
        result = await executor.run()
        return result.model_dump()


def generate_dynamic_code_interpreter_prompt(
    base_prompt: str,
    chat_id: str = "",
    attached_files: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """
    Generate a dynamic code interpreter prompt that includes information about attached files.

    Args:
        base_prompt: The base code interpreter prompt template
        chat_id: Chat ID for context
        attached_files: List of attached file information

    Returns:
        Enhanced prompt with file information
    """
    if not attached_files:
        if chat_id:
            # Try to get attached files from chat
            attached_files = get_attached_files_from_chat(chat_id)

    if not attached_files:
        # No files attached, return base prompt
        return base_prompt

    # Create file information section
    file_info_lines = []
    file_info_lines.append("\n#### Available Files")
    file_info_lines.append(
        "The following files have been attached to this conversation and are available in `/mnt/data/`:"
    )
    file_info_lines.append("")

    for file_info in attached_files:
        file_name = file_info.get("name", "unknown_file")
        file_type = file_info.get("type", "file")
        file_size = file_info.get("size")

        # Format file size if available
        size_str = ""
        if file_size:
            if file_size < 1024:
                size_str = f" ({file_size} bytes)"
            elif file_size < 1024 * 1024:
                size_str = f" ({file_size / 1024:.1f} KB)"
            else:
                size_str = f" ({file_size / (1024 * 1024):.1f} MB)"

        file_info_lines.append(
            f"- **{file_name}**{size_str} - Available at `/mnt/data/{file_name}`"
        )

        # Add file type specific suggestions
        if file_name.lower().endswith((".csv", ".tsv")):
            file_info_lines.append(
                f"  - Data file - Use `pd.read_csv('/mnt/data/{file_name}')` to load"
            )
        elif file_name.lower().endswith((".xlsx", ".xls")):
            file_info_lines.append(
                f"  - Excel file - Use `pd.read_excel('/mnt/data/{file_name}')` to load"
            )
        elif file_name.lower().endswith((".json", ".jsonl")):
            file_info_lines.append(
                f"  - JSON file - Use `pd.read_json('/mnt/data/{file_name}')` or `json.load()` to load"
            )
        elif file_name.lower().endswith((".txt", ".md", ".py", ".js", ".html", ".css")):
            file_info_lines.append(
                f"  - Text file - Use `open('/mnt/data/{file_name}', 'r').read()` to load"
            )
        elif file_name.lower().endswith(
            (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff")
        ):
            file_info_lines.append(
                f"  - Image file - Use `PIL.Image.open('/mnt/data/{file_name}')` or `cv2.imread()` to load"
            )
        elif file_name.lower().endswith((".pdf")):
            file_info_lines.append(
                f"  - PDF file - Use `PyPDF2` or `pdfplumber` to extract text/data"
            )

    file_info_lines.append("")
    file_info_lines.append(
        "**Important**: These files are immediately ready to use - no upload needed. Reference them directly by their paths above."
    )

    # Insert file information after the main code interpreter description but before the final note
    file_info_section = "\n".join(file_info_lines)

    # Find a good insertion point in the base prompt
    prompt_lines = base_prompt.split("\n")

    # Look for the line about /mnt/data and insert file info after it
    insertion_point = -1
    for i, line in enumerate(prompt_lines):
        if "drive at '/mnt/data'" in line.lower():
            insertion_point = i + 1
            break

    if insertion_point > 0:
        # Insert file information after the /mnt/data line
        enhanced_lines = (
            prompt_lines[:insertion_point]
            + file_info_section.split("\n")
            + prompt_lines[insertion_point:]
        )
        return "\n".join(enhanced_lines)
    else:
        # Fallback: append file information at the end
        return base_prompt + "\n" + file_info_section
