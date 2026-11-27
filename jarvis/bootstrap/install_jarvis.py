"""Register the JARVIS tools and the "JARVIS" assistant model inside Open WebUI.

Runs against the same DATA_DIR as the server (run.bat sets it). Idempotent:
existing tools are updated when the source file changed; nothing in Open
WebUI's code or UI is modified. The tools belong to the first admin account,
so this waits (with --wait) until you have created that account in the browser.

    python jarvis/bootstrap/install_jarvis.py            # one shot
    python jarvis/bootstrap/install_jarvis.py --wait 1800 # wait up to 30 min for the admin
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
JARVIS_DIR = HERE.parent
TOOLS_DIR = JARVIS_DIR / "tools"

TOOL_NAMES = {
    "jarvis_files": "JARVIS Files",
    "jarvis_shell": "JARVIS Shell",
    "jarvis_coding": "JARVIS Coding",
    "jarvis_github": "JARVIS GitHub",
    "jarvis_web": "JARVIS Web",
    "jarvis_barehands": "JARVIS Barehands",
}

MODEL_ID = "jarvis"
INSTALLER_VERSION = 2  # bump to refresh the JARVIS model preset on existing installs
PREFERRED_MODELS = ["qwen2.5:14b", "qwen2.5:7b", "qwen3:8b", "llama3.1:8b", "qwen2.5-coder:7b", "llama3.2:3b", "qwen2.5:3b"]

SYSTEM_PROMPT = """You are JARVIS, Joshua's local AI assistant running on his own Windows PC.
Be concise, capable and a little dry-witted; address him as "sir" now and then.
You have tools: JARVIS Files (read/list/search/write files), JARVIS Shell (cmd/PowerShell),
JARVIS Coding (code_search, read_code, edit_file, run_python, git_status, git_commit_push),
JARVIS GitHub (repos, files, issues, PRs, clone, open PR), JARVIS Web (web_search, web_fetch)
and JARVIS Barehands (hand-tracked glass stage).
Use a tool whenever it gives a better answer than guessing. Before editing code, read it first.
Never commit to main/master; use a feature branch and offer to open a pull request.
Anything that writes, runs commands or posts to GitHub will ask Joshua to approve in the chat."""


def ollama_models(base: str) -> list[str]:
    try:
        with urllib.request.urlopen(base.rstrip("/") + "/api/tags", timeout=5) as r:
            return [m["name"] for m in json.load(r).get("models", [])]
    except Exception:
        return []


def pick_base_model(base: str) -> str | None:
    want = os.environ.get("JARVIS_DEFAULT_MODEL", "").strip()
    have = ollama_models(base)
    if want and (want in have or not have):
        return want
    for m in PREFERRED_MODELS:
        if m in have:
            return m
    return have[0] if have else (want or None)


def wait_for_server(wait_s: int) -> None:
    """Let the server finish its own startup/migrations before we touch the DB."""
    if wait_s <= 0:
        return
    url = f"http://127.0.0.1:{os.environ.get('PORT', '8080')}/health"
    deadline = time.time() + wait_s
    while time.time() < deadline:
        try:
            urllib.request.urlopen(url, timeout=2)
            return
        except Exception:
            time.sleep(2)


async def install(wait_s: int) -> int:
    wait_for_server(wait_s)
    # Import late so DATA_DIR etc. from the environment are honoured.
    from open_webui.models.users import Users
    from open_webui.models.tools import ToolForm, ToolMeta, Tools
    from open_webui.models.models import ModelForm, ModelMeta, ModelParams, Models
    from open_webui.utils.plugin import load_tool_module_by_id, replace_imports
    from open_webui.utils.tools import get_tool_specs

    deadline = time.time() + wait_s
    admin = await Users.get_super_admin_user()
    while admin is None and time.time() < deadline:
        await asyncio.sleep(5)
        admin = await Users.get_super_admin_user()
    if admin is None:
        print("[jarvis] No admin account yet. Open http://localhost:8080, create your account, "
              "then run this again (run.bat does it automatically next start).")
        return 2

    installed = []
    for tool_id, name in TOOL_NAMES.items():
        src = (TOOLS_DIR / f"{tool_id}.py").read_text(encoding="utf-8")
        content = replace_imports(src)
        module, frontmatter, _ = await load_tool_module_by_id(tool_id, content=content)
        specs = get_tool_specs(module)
        meta = ToolMeta(description=frontmatter.get("description", name), manifest=frontmatter,
                        has_user_valves=hasattr(module, "UserValves"))
        existing = await Tools.get_tool_by_id(tool_id)
        if existing is None:
            await Tools.insert_new_tool(admin.id, ToolForm(id=tool_id, name=name, content=content, meta=meta,
                                                           commit_message="JARVIS install"), specs, module=module)
            installed.append(f"+ {name}")
        elif existing.content != content:
            await Tools.update_tool_by_id(tool_id, {"name": name, "content": content, "specs": specs,
                                                    "meta": meta.model_dump()}, user_id=admin.id, module=module)
            installed.append(f"~ {name} (updated)")
        else:
            installed.append(f"= {name}")

    base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
    current = await Models.get_model_by_id(MODEL_ID)
    current_ver = int(((current.meta.model_dump() if current else {}) or {}).get("jarvis_installer", 0) or 0)
    base_model = current.base_model_id if current else pick_base_model(base_url)

    def form() -> "ModelForm":
        return ModelForm(
            id=MODEL_ID, base_model_id=base_model, name="JARVIS",
            meta=ModelMeta(
                description=f"JARVIS assistant with PC, coding, GitHub, web and Barehands tools (on {base_model}).",
                # builtin_tools off: Open WebUI's own built-in tools would push small
                # local models past their context window (same idea as JARVIS lean mode).
                capabilities={"vision": False, "citations": True, "builtin_tools": False},
                toolIds=list(TOOL_NAMES), tags=[{"name": "jarvis"}], jarvis_installer=INSTALLER_VERSION),
            params=ModelParams(system=SYSTEM_PROMPT, function_calling="native", num_ctx=8192),
        )

    if current is None:
        if base_model:
            await Models.insert_new_model(form(), admin.id)
            installed.append(f"+ model JARVIS (based on {base_model})")
        else:
            installed.append("! model JARVIS skipped: no Ollama model found yet (pull one, then rerun)")
    elif 0 < current_ver < INSTALLER_VERSION:
        await Models.update_model_by_id(MODEL_ID, form(), user_id=admin.id)
        installed.append(f"~ model JARVIS (updated, still on {base_model})")
    else:
        installed.append("= model JARVIS (left as you configured it)" if current_ver == 0 else "= model JARVIS")

    print("[jarvis] " + "\n[jarvis] ".join(installed))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--wait", type=int, default=0, help="seconds to wait for the first admin account")
    ap.add_argument("--log", default="", help="append output to this file instead of the console")
    a = ap.parse_args()
    if a.log:
        Path(a.log).parent.mkdir(parents=True, exist_ok=True)
        sys.stdout = sys.stderr = open(a.log, "a", encoding="utf-8", buffering=1)
        print(f"--- {time.strftime('%Y-%m-%d %H:%M:%S')} ---")
    try:
        return asyncio.run(install(a.wait))
    except Exception as e:  # keep the launcher going even if this fails
        print(f"[jarvis] tool install failed: {e!r}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
