# Open WebUI Function plugins

Source-controlled "pipe" Functions that ship with this fork. Functions are runtime-loaded by Open WebUI at `Admin Panel > Functions` — committing them here keeps the code reviewable and reproducible across deployments.

## Files

- `vertex_chat.py` — manifold pipe exposing Google **Gemini** (via `google-genai`) and **Anthropic Claude on Vertex** (via `anthropic.AsyncAnthropicVertex`). Both auth via `GOOGLE_APPLICATION_CREDENTIALS`.

## Install (manual, one-off)

1. `Admin Panel > Functions > +` (top right).
2. Paste the contents of the `.py` file. Save.
3. Toggle the function **on**.
4. (Optional) Click the gear icon to override the default Valves (model allowlist, region, project).

## Install (idempotent, scripted)

For dev/CI, `POST /api/v1/functions/sync` (admin auth required) — see `backend/open_webui/routers/functions.py` for the exact payload shape. Wire this into a deploy step so a fresh database always has the Function present.

## Credentials

These Functions read secrets from the container environment, not from UI Valves. Required for `vertex_chat.py`:

| env var | example | notes |
|---|---|---|
| `GOOGLE_APPLICATION_CREDENTIALS` | `/run/secrets/vertex-sa.json` | Service-account JSON path; both SDKs pick this up automatically. |
| `VERTEX_PROJECT_ID` | `pioneer-insurance` | GCP project. |
| `VERTEX_LOCATION` | `us-central1` or `global` | Gemini region. |
| `VERTEX_CLAUDE_LOCATION` | `us-east5` | Claude-on-Vertex region (Anthropic models are only in specific regions). |

The `docker-compose.yaml` in the repo root mounts `./secrets/pioneer-chat-dev.json` → `/run/secrets/vertex-sa.json`. Override the host path by setting `VERTEX_SA_KEY_PATH` in your `.env`.

For the gcloud commands that provision the service account and key, see the original plan at `~/.claude/plans/i-need-you-to-sequential-pike.md` (or have an admin re-run them — `roles/aiplatform.user` is the only role needed).

### Local dev quickstart (impersonation, no SA key)

The `pioneer-insurance` project enforces `constraints/iam.disableServiceAccountKeyCreation`, so SA JSON keys can't be minted yet. To unblock local dev today, impersonate `pioneer-chat-dev` from your own gcloud user:

```bash
# 1. Run the helper (does the IAM binding + browser login + quota project + smoke test)
./scripts/vertex-impersonate.sh

# 2. Point docker compose at the impersonated ADC and start
export VERTEX_SA_KEY_PATH="$HOME/.config/gcloud/application_default_credentials.json"
docker compose up -d --build

# 3. Open Admin Panel > Functions, click +, paste plugins/functions/vertex_chat.py, enable
```

Prereqs: your gcloud user must hold `roles/iam.serviceAccountTokenCreator` on `pioneer-chat-dev@pioneer-insurance.iam.gserviceaccount.com`. The script tries to grant it; if you don't have IAM-admin rights on the SA, ask a project admin to grant the binding once. The SA itself needs `roles/aiplatform.user` on the project (already done as part of the original provisioning step).

Audit logs attribute calls to the SA, not your user, since the SDK presents the SA's impersonated token.

### Future state: SA key (once org policy exemption is granted)

For a long-lived key (no per-user gcloud login required), ask the org admin:

> Please add a conditional rule to `constraints/iam.disableServiceAccountKeyCreation` on project `pioneer-insurance` that exempts the service account `pioneer-chat-dev@pioneer-insurance.iam.gserviceaccount.com` so we can mint a long-lived key for the Open WebUI Vertex AI integration. Justification: the dev container needs ADC and is not yet running in a federation-eligible environment (GKE/Cloud Run). We will rotate the key on a defined schedule and migrate to Workload Identity Federation when the workload moves to GKE.

Once granted, run the original `gcloud iam service-accounts keys create ./pioneer-chat-dev.json --iam-account=…` command, drop the JSON at `./secrets/pioneer-chat-dev.json`, and unset (or update) `VERTEX_SA_KEY_PATH`.
