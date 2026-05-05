# Vertex AI on Open WebUI: Function-plugin pattern

This doc covers two things at once:

1. **The concrete integration** — how Gemini and Claude on Vertex are wired into this fork via `plugins/functions/vertex_chat.py`.
2. **The reusable pattern** — how to add any managed-cloud LLM provider (AWS Bedrock, Azure OpenAI, etc.) to Open WebUI when the provider needs short-lived OAuth tokens instead of a long-lived API key.

If you only need to ship the Vertex feature, the tl;dr is in [Quickstart](#quickstart). The rest of the doc is for the next person who has to add a similar provider.

---

## When to reach for a Function (vs alternatives)

Open WebUI supports three ways to add a model provider:

| Approach | When to use | Tradeoffs |
|---|---|---|
| **OpenAI-compatible connection** (Admin > Connections) | Provider exposes `/v1/chat/completions` _and_ accepts a static API key in `Authorization: Bearer …`. | Zero code. But useless for any provider that requires short-lived OAuth tokens (Vertex, Bedrock, Azure with managed identity). Token-refresh cron workarounds exist but are brittle. |
| **Function plugin** (Admin > Functions) | Provider has a custom auth flow, multiple sub-models you want to expose under one entry, or per-request payload conversion. | Single Python file lives in the DB (or in source control + auto-installed). Hot-loadable. SDK pip-installs at first load via `requirements:` frontmatter. |
| **First-class backend module** (`backend/open_webui/utils/<provider>.py` + router hook) | Provider is "official enough" that it should always be available, never disabled, with full backend integration. | Modifies fork internals; conflicts on every upstream rebase; forces every deployment to ship it. |

**For Vertex, the Function path wins** because the Vertex SDKs handle OAuth refresh transparently, and the same Function can speak both Gemini (via `google-genai`) and Claude on Vertex (via `anthropic.AsyncAnthropicVertex`) — surfacing both as selectable models in one manifold.

---

## The manifold pipe shape

A "pipe" Function exposes a single model to the picker. A **manifold** pipe exposes _N_ models from one Function. Here's the minimum shape — see `plugins/functions/vertex_chat.py` for the full version:

```python
"""
title: Vertex AI (Gemini + Claude)
requirements: google-genai>=1.0.0, anthropic[vertex]>=0.40.0
version: 0.1.0
"""
from pydantic import BaseModel, Field

class Pipe:
    class Valves(BaseModel):
        VERTEX_PROJECT_ID: str = Field(default_factory=lambda: os.getenv('VERTEX_PROJECT_ID', ''))
        # ... more valves ...

    def __init__(self):
        self.type = 'manifold'   # <-- this makes it a manifold
        self.id = 'vertex'
        self.name = 'Vertex / '   # <-- prefix for sub-pipe names in the picker
        self.valves = self.Valves()

    def pipes(self) -> list[dict]:
        # Return [{'id': 'sub-id', 'name': 'Display Name'}, ...]
        return [
            {'id': 'gemini::gemini-2.5-flash', 'name': 'Gemini gemini-2.5-flash'},
            {'id': 'claude::claude-haiku-4-5', 'name': 'Claude claude-haiku-4-5'},
        ]

    async def pipe(self, body: dict, __user__: dict | None = None):
        # body['model'] is 'vertex.<sub-id>'. Strip the manifold prefix to dispatch.
        sub_id = body['model'].split('.', 1)[-1]
        # ... route to the right backend SDK ...
```

The loader at `backend/open_webui/functions.py:77` walks every `pipe`-typed Function, calls `pipes()` if present, and registers each sub-id as `{function_id}.{sub_id}`. When a chat request comes in for that model, it strips the `{function_id}.` prefix and calls `pipe(body=...)`.

### Streaming contract

`pipe()` may return any of:
- `str` — wrapped into a single OpenAI chunk + `[DONE]`
- `dict` — yielded raw as one SSE frame (assumed to already match the OpenAI shape)
- `Generator` / `Iterator` — each item processed via `process_line` (lines starting with `data:` are passed through; others get wrapped)
- `AsyncGenerator` — same processing, async
- `StreamingResponse` — body iterator forwarded directly
- `BaseModel` — `model_dump_json()` then SSE-wrapped

**Easiest production-quality shape**: an `async def` that returns an async generator yielding **plain text strings**. The loader handles SSE wrapping and the terminal `[DONE]` marker for you. This is what `vertex_chat.py` does.

See `backend/open_webui/functions.py:295-333` for the exact dispatch logic.

---

## Auth pattern: env-driven, not Valve-driven

Don't put secrets in Valves. Valves are stored as a plain JSON column in the database — fine for an allowlist or a region name, **bad for a service-account JSON or long-lived token**.

Instead:

1. **Mount the credential into the container** via a bind volume.
2. **Set an env var** pointing at the mount path.
3. Read it in the Function via `os.getenv(...)` inside a `Field(default_factory=...)`.
4. Use Valves only for non-secret runtime config (region, model allowlist, behavioral toggles).

`vertex_chat.py` follows this:

```python
class Valves(BaseModel):
    VERTEX_PROJECT_ID: str = Field(
        default_factory=lambda: os.getenv('VERTEX_PROJECT_ID', ''),
    )
```

The SDK reads `GOOGLE_APPLICATION_CREDENTIALS` itself — no Valve needed for the credential path. The Valve only mirrors the project/region knobs so an admin can override per-environment without redeploying.

### The Valves-stomp gotcha

The loader at `backend/open_webui/functions.py:61-72` does this:

```python
valves = await Functions.get_function_valves_by_id(pipe_id)
if valves:
    function_module.valves = Valves(**{k: v for k, v in valves.items() if v is not None})
else:
    function_module.valves = Valves()
```

The filter is `if v is not None`, so an **empty string is preserved**. If an admin opens the gear icon and clicks Save before the env var is set inside the container, the empty string `""` gets persisted to the DB and from then on overrides the env-var default.

**Mitigations:**
- Document the env vars in the README so admins set them before opening the Valves panel.
- Optional: in `__init__`, raise if a required Valve is empty AND the env var is also empty, with a clear message pointing the admin at the env var.
- If you hit this, the fix is one click: open the gear icon, type the value, save.

---

## Local dev when org policy blocks SA keys

Many GCP orgs enforce `constraints/iam.disableServiceAccountKeyCreation`, which makes `gcloud iam service-accounts keys create` fail with `FAILED_PRECONDITION`. The same pattern exists on AWS (SCP denying `iam:CreateAccessKey`) and Azure (managed-identity-only policies).

**The pattern: impersonate the SA from your own user's ADC, then mount the user ADC into the container.**

This works because:
- Your user account has `roles/iam.serviceAccountTokenCreator` on the SA.
- `gcloud auth application-default login --impersonate-service-account=…` writes an ADC file at `~/.config/gcloud/application_default_credentials.json` of type `impersonated_service_account`.
- The Google SDKs (and `anthropic[vertex]`, which uses `google-auth` under the hood) recognise that file via `GOOGLE_APPLICATION_CREDENTIALS` and call `iamcredentials.googleapis.com:generateAccessToken` for every request — short-lived tokens, refreshed automatically, attributed to the SA in audit logs.
- Bind-mount the file into the container at the path `GOOGLE_APPLICATION_CREDENTIALS` points at, and the container's SDK behaves identically to the host.

### What goes in the container env

```yaml
# docker-compose.yaml
services:
  open-webui:
    volumes:
      - ${VERTEX_SA_KEY_PATH:-./secrets/sa-key.json}:/run/secrets/vertex-sa.json:ro
    environment:
      - GOOGLE_APPLICATION_CREDENTIALS=/run/secrets/vertex-sa.json
      - VERTEX_PROJECT_ID=pioneer-insurance
      - VERTEX_LOCATION=us-central1
      - VERTEX_CLAUDE_LOCATION=us-east5
```

Then on the host:

```bash
export VERTEX_SA_KEY_PATH="$HOME/.config/gcloud/application_default_credentials.json"
docker compose up -d --build
```

The env var override sends the host path of the impersonated ADC into the bind mount instead of the (nonexistent) SA key. Same compose file, two credential sources.

### Footgun: `set-quota-project` doesn't work on impersonated ADC

`gcloud auth application-default set-quota-project` errors out with `The application default credentials are not user credentials, quota project cannot be added` when the ADC is impersonation-based. **You don't need to set it** — with impersonation, the quota project is implicitly the SA's own project. If you ever do need to override, set `GOOGLE_CLOUD_QUOTA_PROJECT` in the container env.

### Production migration path

When the workload moves to a federation-eligible runtime, drop the bind mount and let the metadata server handle ADC:

| Runtime | Replacement |
|---|---|
| GKE | Workload Identity Federation: bind the K8s SA to the GCP SA. Remove `GOOGLE_APPLICATION_CREDENTIALS`. |
| Cloud Run / Cloud Functions / GCE | Set the runtime SA on the deployment. Remove `GOOGLE_APPLICATION_CREDENTIALS`. |
| GitHub Actions | WIF via `google-github-actions/auth`. |

The Function code does not change in any of these — that's the point of using `google-auth`'s ADC discovery.

---

## Quickstart

Concrete steps to bring up Vertex on a laptop today:

```bash
# 1. (One-time) impersonation setup
./scripts/vertex-impersonate.sh

# 2. Start the stack
export VERTEX_SA_KEY_PATH="$HOME/.config/gcloud/application_default_credentials.json"
OPEN_WEBUI_PORT=3030 docker compose up -d --build   # OPEN_WEBUI_PORT only if 3000 is taken

# 3. Install the Function
#    Open http://localhost:3030 > Admin Panel > Functions > +
#    Paste plugins/functions/vertex_chat.py > Save (waits ~30s for pip install)
#    Toggle the Function on

# 4. (Claude only) Enable each Anthropic model in GCP Console > Vertex AI > Model Garden
#    The Gemini path needs no per-model EULA.

# 5. Verify
docker compose exec open-webui env | grep VERTEX
gcloud auth application-default print-access-token   # should print ya29....
# Then in the chat UI, model picker > "Vertex / Gemini gemini-2.5-flash" > "hello"
```

Full prereqs and gcloud commands (SA creation, IAM bindings) are in `~/.claude/plans/i-need-you-to-sequential-pike.md` and `plugins/functions/README.md`.

---

## Adding a different provider (Bedrock, Azure OpenAI, …)

Reuse the pattern:

1. **Pick the env var.** AWS = `AWS_PROFILE` + `AWS_WEB_IDENTITY_TOKEN_FILE`. Azure = `AZURE_CLIENT_ID` + managed identity. Mount whatever the SDK reads.
2. **Write the manifold pipe.** Frontmatter `requirements:` should list the cloud SDK (e.g. `boto3`, `azure-ai-inference`).
3. **One sub-pipe id per model.** Use a `provider::model` convention in the sub-id so future-you can dispatch to multiple SDKs from one Function.
4. **Streaming as async generator yielding strings.** Convert provider-native chunk format to plain text inside `pipe()`.
5. **Local dev**: if the cloud blocks long-lived secrets, look for an impersonation/assume-role/managed-identity equivalent. The pattern is always: short-lived token, mounted credential file, no rotation in your code.

The Vertex Function is ~200 lines. A second-cloud Function should land in roughly the same.
