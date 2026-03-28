# Open-WebUI Session Memory

## Testing Rules
- Integration tests are only valid if testing directly through the tool interface.

## Current State (2026-02-22)
- Branch: fix/tool-server-connections-auto-init (2 commits ahead of main)
- Running in K8s (open-webui-7659bf4bff-fzsx4), NOT locally
- Version: 0.6.43
- Instance name: "Anomalous-Ventures AI (Open WebUI)"
- Auth: OIDC only via STAX SSO (password login disabled, signup disabled, API keys disabled)
- Working tree: clean

## Integration Test Results (2026-02-22) -- 9/9 PASS
- Version endpoint: PASS (v0.6.43)
- Health check: PASS
- Public config: PASS
- Auth flow: PASS (expected 405 -- password login disabled)
- Protected endpoints (models, ollama proxy, openai proxy): all return 401 correctly
- TLS: PASS (TLS 1.3, Let's Encrypt *.spooty.io, HTTP/2)
- Security headers: PASS (HSTS, CSP, X-Frame-Options, XSS protection)

## Branch Changes
- backend/open_webui/internal/db.py: fix UnboundLocalError when DB connection fails
- backend/open_webui/main.py: auto-initialize tool servers from TOOL_SERVER_CONNECTIONS env var

## Notes
- Backend tests fail with pre-existing upstream import error (ModuleNotFoundError: test.util)
- API keys are disabled in config -- prevents programmatic integration testing
- Remotes: origin (open-webui/open-webui), fork (SpootyMcSpoot/open-webui)
