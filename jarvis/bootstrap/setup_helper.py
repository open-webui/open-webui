"""Steps of setup.bat that are easier in Python than in batch.

    python jarvis/bootstrap/setup_helper.py all
    python jarvis/bootstrap/setup_helper.py frontend [--from-source]
    python jarvis/bootstrap/setup_helper.py barehands | model | envfile | secret | check

Nothing here edits Open WebUI's source; it only fills in build/, jarvis.env,
integrations/barehands/ (gitignored) and pulls an Ollama model.
"""
from __future__ import annotations

import json
import os
import secrets
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BUILD = ROOT / "build"
DATA = ROOT / "jarvis-data"
ENV_FILE = ROOT / "jarvis.env"
BAREHANDS = ROOT / "integrations" / "barehands"
OLLAMA = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")


def say(msg: str) -> None:
    print(f"[jarvis-setup] {msg}", flush=True)


def version() -> str:
    return json.loads((ROOT / "package.json").read_text(encoding="utf-8"))["version"]


# ---------------------------------------------------------------- frontend ---
def frontend(from_source: bool = False) -> bool:
    if (BUILD / "index.html").exists() and not from_source:
        say(f"frontend already present in {BUILD}")
        return True
    if not from_source and prebuilt_frontend():
        return True
    return source_frontend()


def prebuilt_frontend() -> bool:
    """The fork keeps Open WebUI's UI unchanged, so the official wheel of the
    same version ships the identical compiled frontend. Much faster and
    lighter than a local Vite build (which wants ~12 GB of Node heap)."""
    v = version()
    say(f"downloading the prebuilt Open WebUI {v} frontend from PyPI ...")
    tmp = Path(tempfile.mkdtemp(prefix="owui-wheel-"))
    try:
        r = subprocess.run([sys.executable, "-m", "pip", "download", f"open-webui=={v}", "--no-deps",
                            "--only-binary=:all:", "-d", str(tmp), "-q"])
        wheels = list(tmp.glob("open_webui-*.whl"))
        if r.returncode or not wheels:
            say("prebuilt frontend not available for this version")
            return False
        with zipfile.ZipFile(wheels[0]) as z:
            names = [n for n in z.namelist() if n.startswith("open_webui/frontend/")]
            if not names:
                say("wheel has no frontend folder")
                return False
            if BUILD.exists():
                shutil.rmtree(BUILD)
            for n in names:
                rel = n[len("open_webui/frontend/"):]
                if not rel or n.endswith("/"):
                    continue
                dest = BUILD / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                with z.open(n) as src, open(dest, "wb") as out:
                    shutil.copyfileobj(src, out)
        ok = (BUILD / "index.html").exists()
        say("frontend ready" if ok else "frontend extract failed")
        return ok
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def source_frontend() -> bool:
    npm = shutil.which("npm") or shutil.which("npm.cmd")
    if not npm:
        say("Node.js (npm) not found - install Node 22 LTS (winget install OpenJS.NodeJS.LTS may be newer than 22; "
            "Open WebUI needs 18.13-22.x) and rerun setup.bat")
        return False
    say("building the frontend from source (npm ci + npm run build) - this takes a while ...")
    for args in (["ci"], ["run", "build"]):
        if subprocess.run([npm, *args], cwd=str(ROOT)).returncode:
            say(f"npm {' '.join(args)} failed")
            return False
    return (BUILD / "index.html").exists()


# --------------------------------------------------------------- barehands ---
def barehands() -> bool:
    if (BAREHANDS / "server.py").exists():
        say(f"barehands present at {BAREHANDS}")
        return True
    # Reuse the copy from the JARVIS repo on this PC if there is one (read-only:
    # we copy it, the original folder is never modified).
    candidates = [Path(os.environ.get("JARVIS_REPO_DIR", "")) / "integrations" / "barehands",
                  Path.home() / "JARVIS" / "integrations" / "barehands"]
    for c in candidates:
        if str(c) not in ("", ".") and (c / "server.py").exists():
            say(f"copying barehands from {c}")
            shutil.copytree(c, BAREHANDS, ignore=shutil.ignore_patterns(".git", "__pycache__", "*.log"))
            return True
    git = shutil.which("git")
    if not git:
        say("git not found; skipping barehands (install Git for Windows and rerun)")
        return False
    say("cloning barehands (AGPL-3.0, github.com/jaredrhod/barehands)")
    BAREHANDS.parent.mkdir(parents=True, exist_ok=True)
    return subprocess.run([git, "clone", "--depth", "1", "https://github.com/jaredrhod/barehands.git",
                           str(BAREHANDS)]).returncode == 0


# ------------------------------------------------------------------ ollama ---
def ollama_up() -> bool:
    try:
        with urllib.request.urlopen(OLLAMA + "/api/version", timeout=3):
            return True
    except Exception:
        return False


def ollama_exe() -> str | None:
    found = shutil.which("ollama")
    if found:
        return found
    p = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Ollama" / "ollama.exe"
    return str(p) if p.exists() else None


def gpu_vram_gb() -> float:
    try:
        out = subprocess.run(["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"],
                             capture_output=True, text=True, timeout=10).stdout
        return max(float(x) for x in out.split()) / 1024
    except Exception:
        return 0.0


def model() -> bool:
    exe = ollama_exe()
    if not exe:
        say("Ollama is not installed (setup.bat installs it with winget). Get it at https://ollama.com/download")
        return False
    if not ollama_up():
        say("starting ollama serve ...")
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        subprocess.Popen([exe, "serve"], env={**os.environ, "OLLAMA_CONTEXT_LENGTH": "8192"}, creationflags=flags,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(40):
            if ollama_up():
                break
            time.sleep(0.5)
    try:
        with urllib.request.urlopen(OLLAMA + "/api/tags", timeout=5) as r:
            have = [m["name"] for m in json.load(r).get("models", [])]
    except Exception:
        have = []
    want = read_env().get("JARVIS_DEFAULT_MODEL") or ("qwen2.5:7b" if gpu_vram_gb() >= 6 else "qwen2.5:3b")
    if want in have:
        say(f"model {want} already pulled")
        return True
    say(f"pulling {want} (one-time download; you can browse/pull more in Admin Settings > Models) ...")
    ok = subprocess.run([exe, "pull", want]).returncode == 0
    if ok:
        write_env({"JARVIS_DEFAULT_MODEL": want})
    return ok


# ---------------------------------------------------------------- env file ---
ENV_TEMPLATE = """# JARVIS settings for run.bat (this file stays on your PC; it is gitignored).
# GitHub token for the JARVIS GitHub/Coding tools (fine-grained PAT, repo contents + pull requests).
GITHUB_TOKEN=
# Ollama model the "JARVIS" assistant is based on.
JARVIS_DEFAULT_MODEL=
# Port for the web UI.
PORT=8080
"""


def read_env() -> dict:
    out = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                out[k.strip()] = v.strip()
    return out


def write_env(updates: dict) -> None:
    if not ENV_FILE.exists():
        ENV_FILE.write_text(ENV_TEMPLATE, encoding="utf-8")
    lines = ENV_FILE.read_text(encoding="utf-8").splitlines()
    for k, v in updates.items():
        for i, line in enumerate(lines):
            if line.split("=", 1)[0].strip() == k:
                if not line.split("=", 1)[1].strip():
                    lines[i] = f"{k}={v}"
                break
        else:
            lines.append(f"{k}={v}")
    ENV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def envfile() -> bool:
    if not ENV_FILE.exists():
        ENV_FILE.write_text(ENV_TEMPLATE, encoding="utf-8")
        say(f"created {ENV_FILE.name} (put your GITHUB_TOKEN there if you want GitHub tools)")
    return True


def secret() -> bool:
    DATA.mkdir(parents=True, exist_ok=True)
    key = DATA / ".webui_secret_key"
    if not key.exists():
        key.write_text(secrets.token_urlsafe(32), encoding="utf-8")
    return True


def check() -> bool:
    rows = {
        "python": sys.version.split()[0],
        "frontend": (BUILD / "index.html").exists(),
        "barehands": (BAREHANDS / "server.py").exists(),
        "ollama installed": bool(ollama_exe()),
        "ollama running": ollama_up(),
        "jarvis.env": ENV_FILE.exists(),
    }
    for k, v in rows.items():
        say(f"{k:17} {v}")
    return bool(rows["frontend"])


def main() -> int:
    args = sys.argv[1:] or ["all"]
    step = args[0]
    if step == "frontend":
        return 0 if frontend("--from-source" in args) else 1
    steps = {"barehands": barehands, "model": model, "envfile": envfile, "secret": secret, "check": check}
    if step in steps:
        return 0 if steps[step]() else 1
    if step == "all":
        results = {"envfile": envfile(), "secret": secret(), "frontend": frontend(),
                   "barehands": barehands(), "model": model()}
        check()
        if not results["frontend"]:
            return 1
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
