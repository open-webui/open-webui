---
name: preflight
description: Preflight health check for open-webui — Open WebUI clone (npm frontend + Python backend). Consider moving to vendor/ if unmodified.. Use before starting a session in this project, when the user runs /preflight, or asks whether the project is healthy/ready.
---

# Preflight — open-webui

Project root: `/Users/josh/IntelustryProjects/active/open-webui`

Run each check, record PASS / FAIL / WARN, then print the status table.

## Checks

**[1] Frontend deps**
```bash
[ -d /Users/josh/IntelustryProjects/active/open-webui/node_modules ] && echo "PASS node_modules present" || echo "FAIL run: npm install (102 deps)"
```

**[2] Backend env**
```bash
P=/Users/josh/IntelustryProjects/active/open-webui
[ -d "$P/.venv" ] && echo "PASS backend .venv" || echo "WARN backend venv missing (uv sync)"
```

**[3] Upstream drift**
```bash
cd /Users/josh/IntelustryProjects/active/open-webui && git status --short | head -3 && git log --oneline -1
```


## Status Table

After all checks, print a summary:

```
PREFLIGHT — OPEN-WEBUI
┌──────────────────────────┬────────┬──────────────────────────┐
│ Check                    │ Status │ Note                     │
├──────────────────────────┼────────┼──────────────────────────┤
│ ...                      │  ...   │ ...                      │
└──────────────────────────┴────────┴──────────────────────────┘
Overall: READY / DEGRADED / BLOCKED
```

- **READY** — all checks pass
- **DEGRADED** — non-critical failures (optional service down, missing dev deps)
- **BLOCKED** — a critical dependency is down (required env, API key, services needed to run)

If BLOCKED, list the exact fix commands before proceeding.

**BLOCKED when:** deps are missing and you need to run the app.
