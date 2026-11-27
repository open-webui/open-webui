# JARVIS on Open WebUI

This fork is upstream [Open WebUI](https://github.com/open-webui/open-webui) with Joshua's
[JARVIS](https://github.com/JoshTXWC/JARVIS) features added **next to it**. Open WebUI's own
code and UI are not modified: everything JARVIS lives in `jarvis/`, the three `.bat` files,
and a few `.gitignore` lines. Only the name changes (`WEBUI_NAME=JARVIS`, shown as
"JARVIS (Open WebUI)" as Open WebUI's license requires).

## Start it on Windows

1. Double-click **`setup.bat`** once. It installs what is missing (Python 3.12, Git, Ollama via
   winget), creates `.venv`, installs the backend, puts the web frontend in `build\`, sets up
   Barehands, pulls a starter model sized to your GPU (`qwen2.5:7b` with 6 GB+ VRAM, else
   `qwen2.5:3b`), and installs the Electron shell if Node.js is present.
2. Double-click **`run.bat`**. The browser opens at http://localhost:8080.
   - First time: create your account; it becomes the admin. A few seconds later the six
     JARVIS tools and the **JARVIS** model show up (log: `jarvis-data\jarvis-install.log`).
   - Or double-click **`run-desktop.bat`** for the desktop app (it starts `run.bat` hidden).

Settings live in `jarvis.env` (created by setup, never committed): `GITHUB_TOKEN`,
`JARVIS_DEFAULT_MODEL`, `PORT`. Data lives in `jarvis-data\`.

Models: Open WebUI already does what the Ollama app does. **Admin Panel > Settings > Models**
(the Ollama "Manage" button) pulls, updates and deletes local models, and the model picker at
the top of a chat switches between them. A model with 7B+ parameters is recommended for tool use.

## What was ported from JARVIS

| JARVIS feature | Here | Where |
|---|---|---|
| File tools | Open WebUI Tool **JARVIS Files** (list/read/search/write/delete) | `jarvis/tools/jarvis_files.py` |
| Shell tools | **JARVIS Shell** (cmd, PowerShell, which, system info) | `jarvis/tools/jarvis_shell.py` |
| Coding mode | **JARVIS Coding** (code_search, read_code, edit_file, run_python, git_status, git_commit_push) | `jarvis/tools/jarvis_coding.py` |
| GitHub tools | **JARVIS GitHub** (status, repos, read file, issues, PRs, clone, open PR) | `jarvis/tools/jarvis_github.py` |
| Web tools | **JARVIS Web** (web_search via DuckDuckGo, web_fetch) | `jarvis/tools/jarvis_web.py` |
| Barehands | **JARVIS Barehands** (open, present, add card, status, close) + Electron overlay | `jarvis/tools/jarvis_barehands.py` |
| JARVIS persona | Workspace model **JARVIS** (system prompt, native tool calling, all tools on) | `jarvis/bootstrap/install_jarvis.py` |
| Voice (TTS) | Edge neural voice `en-GB-RyanNeural` through Open WebUI's normal OpenAI TTS setting | `jarvis/bootstrap/tts_server.py` (port 7342) |
| Voice (STT) | Open WebUI's built-in local faster-whisper (`WHISPER_MODEL=base`) | config only |
| Electron app | Tray, Ctrl+Shift+J show/hide, Ctrl+Shift+H Barehands fullscreen, mic/camera for localhost | `jarvis/electron/` |
| One-click setup | `setup.bat`, `run.bat`, `run-desktop.bat` | repo root |

Safety, as in JARVIS: anything that writes files, runs a command, runs Python, commits or opens
a PR pops an **approve / cancel** dialog in the chat first (Open WebUI's confirmation event).
Secret files (`.env*`, keys, credentials, `.ssh`) are always refused, and file tools stay inside
`ALLOWED_ROOTS` (default: your user folder; change it in Workspace > Tools > valves).

Review fixes carried over from JARVIS PR #2 (tests in `jarvis/tests/`):
- `code_search` checks every file against the secret denylist, not just the folder.
- `run_shell` / `run_powershell` / `run_python` fail if the working folder does not exist
  instead of running somewhere else.
- `git_commit_push` switches to an existing branch (or creates a new one) and never uses
  `checkout -B`, so existing branch commits are never reset. Never commits to main/master,
  never force-pushes.
- `edit_file` reads the whole file (no 10 MB cut-off); above 50 MB it refuses rather than truncating.

## Barehands

[Barehands](https://github.com/jaredrhod/barehands) is AGPL-3.0 and is not vendored in this
repo. `setup.bat` copies it from `%USERPROFILE%\JARVIS\integrations\barehands` if you already
have it there (your original folder is left untouched), otherwise it clones it into
`integrations\barehands\` (gitignored).

## Developer notes

- Tests: `.venv\Scripts\python -m pytest jarvis\tests -q`
- Re-register tools after editing them: `.venv\Scripts\python jarvis\bootstrap\install_jarvis.py`
  (updates changed tools, leaves your edits to the JARVIS model alone).
- The frontend comes prebuilt from the official `open-webui` wheel of the same version
  (identical UI, no 12 GB Node build). `setup.bat /buildfrontend` builds from source instead
  (needs Node.js 18.13–22).
