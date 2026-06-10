# Open WebUI for macOS

This directory contains the first native macOS desktop client for Open WebUI.
It keeps the existing FastAPI backend intact and adds a SwiftUI desktop client
that talks to Open WebUI through the backend API. The app still supervises a
local Open WebUI service, but the primary chat experience is native macOS UI,
not a `WKWebView` wrapper.

The target UI reference lives at:

```text
macos/design/open-webui-macos-native-target.png
```

## Current scope

- SwiftUI desktop window with a native three-pane chat workspace.
- Native chat sessions, message list, composer, model picker, and inspector.
- Open WebUI API client for `/api/models` and `/api/chat/completions`.
- Automatic local service startup using `open-webui serve`.
- Health/readiness polling via `/health` and `/ready`.
- Settings for host, port, API token, service command, Ollama URL, data
  directory, startup, and quit behavior.
- Managed service restart/stop commands and an in-app log viewer.
- Swift unit tests for settings normalization and launch command generation.

## Prerequisites

- macOS 13 or newer.
- Xcode Command Line Tools.
- Python 3.11 or 3.12 with Open WebUI installed:

  ```bash
  pip install open-webui
  ```

## Run from source

```bash
cd macos/OpenWebUIMac
swift run OpenWebUIMac
```

The default service command is:

```bash
open-webui serve --host 127.0.0.1 --port 8080
```

The default data directory is:

```text
~/Library/Application Support/Open WebUI Mac
```

## Build a local app bundle

```bash
cd macos/OpenWebUIMac
Scripts/package-app.sh
open ".build/Open WebUI.app"
```

The generated app bundle is unsigned and intended for local development. A
release-ready distribution still needs an embedded Python runtime, app signing,
notarization, and a DMG/pkg installer.

## Next release steps

- Persist native chat history through `/api/v1/chats` instead of in-memory
  sessions only.
- Add streaming response support and task cancellation.
- Wire the native Knowledge and Tools inspector controls to backend features.
- Bundle the built Open WebUI wheel and a standalone Python runtime.
- Add first-run dependency validation and migration/backup tooling.
- Add signed and notarized `.app`/DMG release automation.
- Add UI automation for onboarding, settings, logs, service lifecycle, and
  native chat flows.
