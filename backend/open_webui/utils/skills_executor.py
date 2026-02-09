"""
Skill Script Executor
=====================
Runs .py and .sh scripts discovered from mounted skill directories.
Scripts auto-execute when a skill with scripts is triggered (no toggle needed).

Security model:
  - Skill files are mounted read-only
  - subprocess with timeout (default 30s)
  - stdin = /dev/null (no interactive input)
  - stdout + stderr captured, truncated to max 10KB
  - Runs in /tmp sandbox cwd
"""

import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

# Defaults (can be overridden via env)
DEFAULT_TIMEOUT = int(os.environ.get("SKILL_EXEC_TIMEOUT", "30"))
DEFAULT_MAX_OUTPUT = int(os.environ.get("SKILL_EXEC_MAX_OUTPUT", "10240"))  # 10KB


def _get_interpreter(script_path: str) -> list[str]:
    """Determine the interpreter for a script based on extension."""
    lower = script_path.lower()
    if lower.endswith(".py"):
        return ["python3"]
    if lower.endswith(".sh"):
        return ["bash"]
    return []


def _build_env(user_message: str = "") -> dict:
    """Build a restricted environment for script execution.

    Passes through essential vars (PATH, HOME, LANG, TERM) plus any
    API keys / URLs the container already has (TAVILY, OPENAI, etc.).
    """
    passthrough_prefixes = (
        "PATH",
        "HOME",
        "LANG",
        "TERM",
        "TAVILY",
        "OPENAI",
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "NO_PROXY",
        "http_proxy",
        "https_proxy",
        "no_proxy",
    )

    env: dict[str, str] = {}
    for key, value in os.environ.items():
        if any(
            key.startswith(prefix) or key == prefix for prefix in passthrough_prefixes
        ):
            env[key] = value

    # Inject the user message so scripts can read it
    if user_message:
        env["SKILL_USER_MESSAGE"] = user_message

    return env


def execute_skill_script(
    script_path: str,
    user_message: str = "",
    timeout: int = DEFAULT_TIMEOUT,
    max_output: int = DEFAULT_MAX_OUTPUT,
) -> Optional[str]:
    """Execute a single skill script and return its stdout.

    Args:
        script_path: Absolute path to the script file.
        user_message: The user's chat message (passed as $1 arg and env var).
        timeout: Max seconds to wait.
        max_output: Max bytes of output to capture.

    Returns:
        Script stdout (truncated) or None if execution failed.
    """
    path = Path(script_path)
    if not path.exists() or not path.is_file():
        log.warning(f"Skill script not found: {script_path}")
        return None

    interpreter = _get_interpreter(script_path)
    if not interpreter:
        log.warning(f"No interpreter for script: {script_path}")
        return None

    # Check interpreter is available
    if not shutil.which(interpreter[0]):
        log.warning(f"Interpreter '{interpreter[0]}' not found in PATH")
        return None

    cmd = interpreter + [script_path]

    # Pass user_message as first argument (many scripts accept JSON arg)
    if user_message:
        cmd.append(user_message)

    sandbox_dir = tempfile.mkdtemp(prefix="skill_exec_")

    try:
        log.info(f"Executing skill script: {script_path}")
        result = subprocess.run(
            cmd,
            timeout=timeout,
            capture_output=True,
            text=True,
            stdin=subprocess.DEVNULL,
            cwd=sandbox_dir,
            env=_build_env(user_message),
        )

        output = result.stdout or ""
        if result.returncode != 0 and result.stderr:
            output += f"\n[exit code: {result.returncode}]\n{result.stderr}"

        # Truncate
        if len(output) > max_output:
            output = output[:max_output] + "\n... [output truncated]"

        return output.strip() if output.strip() else None

    except subprocess.TimeoutExpired:
        log.warning(f"Skill script timed out after {timeout}s: {script_path}")
        return f"[Script timed out after {timeout}s]"
    except Exception as e:
        log.exception(f"Error executing skill script {script_path}: {e}")
        return f"[Script execution error: {e}]"
    finally:
        # Cleanup sandbox
        try:
            shutil.rmtree(sandbox_dir, ignore_errors=True)
        except Exception:
            pass


def execute_skill_scripts(
    skill_meta: dict,
    user_message: str = "",
    timeout: int = DEFAULT_TIMEOUT,
    max_output: int = DEFAULT_MAX_OUTPUT,
) -> Optional[str]:
    """Execute all scripts for a skill and return combined output.

    Reads script paths from skill.meta.external_bridge.scripts and
    resolves them relative to the skill's source directory.

    Args:
        skill_meta: The skill's meta dict (contains external_bridge info).
        user_message: The user's chat message.
        timeout: Max seconds per script.
        max_output: Max bytes of output per script.

    Returns:
        Combined output string or None if no scripts or all failed.
    """
    bridge = (
        skill_meta.get("external_bridge", {}) if isinstance(skill_meta, dict) else {}
    )
    scripts = bridge.get("scripts", [])
    source_file = bridge.get("source_file", "")

    if not scripts or not source_file:
        return None

    # Resolve skill directory from the source SKILL.md path
    skill_dir = Path(source_file).parent

    outputs: list[str] = []

    for script_relpath in scripts:
        # Only execute .py and .sh files
        lower = script_relpath.lower()
        if not (lower.endswith(".py") or lower.endswith(".sh")):
            continue

        # Skip test files
        if "/tests/" in script_relpath or "/test_" in script_relpath:
            continue

        abs_path = str(skill_dir / script_relpath)
        result = execute_skill_script(
            abs_path,
            user_message=user_message,
            timeout=timeout,
            max_output=max_output,
        )

        if result:
            script_name = Path(script_relpath).name
            outputs.append(f"[{script_name}]\n{result}")

    if not outputs:
        return None

    combined = "\n\n".join(outputs)

    # Global truncation
    if len(combined) > max_output:
        combined = combined[:max_output] + "\n... [output truncated]"

    return combined
