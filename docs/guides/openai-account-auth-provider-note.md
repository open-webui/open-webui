# OpenAI Account Auth Provider Note

This branch adds an **OpenAI account-auth connection path** for supported Codex-compatible runtime requests.

## Reviewer Notes

- The browser/device authorization flow follows the de facto Codex account-auth runtime used by developer tooling and is separate from the standard OpenAI API-key path.
- The implementation currently depends on the observed device-auth issuer at `https://auth.openai.com`.
- The observed client identifier used for the device flow is `app_EMoamEEZ73f0CkXaXp7hrann`.
- Runtime requests for this connection path are routed to the observed Codex responses endpoint at `https://chatgpt.com/backend-api/codex/responses`.

## Runtime Scope

Because this mode is distinct from the public OpenAI API-key path, it is implemented as its own runtime mode. The upstream account-auth endpoints and client details are externally controlled, so maintainers should review this path as a Codex-compatible account runtime rather than as normal `/v1` API-key authentication.

## Scope Guardrails

- This mode is intentionally separate from the standard OpenAI API-key connection flow.
- Existing API-key-based OpenAI connections remain supported and should be preferred when stable API access is required.
