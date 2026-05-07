# Deployment — Swept Open WebUI on GCP Cloud Run

Three Cloud Run environments mirror the `swept-workbench` setup, all in GCP project `production-472518`, region `us-central1`.

| Env | Cloud Run service | Public URL | Workbench (today) |
|---|---|---|---|
| production | `swept-chat` | https://chat.swept.ai | https://workbench.swept.ai |
| staging | `staging-swept-chat` | https://staging.chat.swept.ai | https://workbench.swept.ai *(TODO)* |
| demo | `demo-swept-chat` | https://demo.chat.swept.ai | https://workbench.swept.ai *(TODO)* |

> All three open-webui envs currently point `WORKBENCH_URL` at production workbench. Once `staging.workbench.swept.ai` and `demo.workbench.swept.ai` are mapped, edit `.github/workflows/build-deploy.yaml` to source the URL per env. See the `TODO(WORKBENCH_URL)` marker.

CI/CD lives in `.github/workflows/build-deploy.yaml`:

- Push to `main` → builds image, auto-deploys to **staging**.
- `workflow_dispatch` (Actions tab) → deploy to chosen env. Prod is gated by the `production` GitHub Environment (configure required reviewers in repo settings).

**This environment was provisioned manually with `gcloud`, not Terraform.** Pioneer (`pioneer-insurance` project) is Terraform-managed and is a separate story. Do not introduce `.tf` files here — they would drift from the manual source of truth. When changing infra, update this runbook *and* re-run the affected commands.

---

## Shared GCP coordinates

| Resource | Value |
|---|---|
| GCP project | `production-472518` |
| Project number | `964226336245` |
| Region | `us-central1` |
| Artifact Registry repo | `chat-releases` |
| Image | `us-central1-docker.pkg.dev/production-472518/chat-releases/open-webui` |
| Cloud SQL instance | `swept-chat-db` (Postgres 16) |
| Cloud SQL connection name | `production-472518:us-central1:swept-chat-db` |
| Runtime service account | `964226336245-compute@developer.gserviceaccount.com` |
| Deploy service account | `github-deploy@production-472518.iam.gserviceaccount.com` |
| WIF provider | `projects/964226336245/locations/global/workloadIdentityPools/github-actions/providers/github` |

Per-env naming convention (mirrors workbench: bare prod, env-prefix elsewhere):

| | prod | staging | demo |
|---|---|---|---|
| Cloud Run service | `swept-chat` | `staging-swept-chat` | `demo-swept-chat` |
| Cloud SQL database | `openwebui_prod` | `openwebui_staging` | `openwebui_demo` |
| Cloud SQL user | `openwebui_prod` | `openwebui_staging` | `openwebui_demo` |
| GCS uploads bucket | `swept-chat-uploads-prod` | `swept-chat-uploads-staging` | `swept-chat-uploads-demo` |
| Secret prefix | *(none)* | `STAGING_` | `DEMO_` |
| Custom domain | `chat.swept.ai` | `staging.chat.swept.ai` | `demo.chat.swept.ai` |

---

## One-time setup runbook

> **Shortcut:** `scripts/bootstrap-gcp.sh` runs every step below idempotently. Use `--dry-run` to preview, `--phase N` to resume at a step, `--update-wif` to also broaden the shared WIF condition (affects swept-workbench — read the script first). The manual commands stay here for reference and partial / out-of-band runs.

All commands assume `gcloud config set project production-472518` and an authenticated operator with `roles/owner` (or equivalent) on the project.

### 1. Enable APIs
```sh
gcloud services enable \
  artifactregistry.googleapis.com \
  run.googleapis.com \
  sqladmin.googleapis.com \
  secretmanager.googleapis.com \
  storage.googleapis.com \
  iam.googleapis.com \
  iamcredentials.googleapis.com
```

### 2. Artifact Registry repo
```sh
gcloud artifacts repositories create chat-releases \
  --repository-format=docker \
  --location=us-central1 \
  --description="Open WebUI container images for Swept chat envs"
```

### 3. Cloud SQL Postgres (one instance, three databases)
```sh
gcloud sql instances create swept-chat-db \
  --database-version=POSTGRES_16 \
  --tier=db-custom-1-3840 \
  --region=us-central1 \
  --storage-size=20GB \
  --storage-auto-increase \
  --backup --backup-start-time=08:00

for env in prod staging demo; do
  gcloud sql databases create openwebui_${env} --instance=swept-chat-db
  pw=$(openssl rand -base64 32 | tr -d '=+/' | cut -c1-32)
  gcloud sql users create openwebui_${env} --instance=swept-chat-db --password="${pw}"
  echo "${env} password: ${pw}"   # capture — used to assemble the DATABASE_URL secret in step 5
done
```

### 4. GCS upload buckets
```sh
for env in prod staging demo; do
  gcloud storage buckets create gs://swept-chat-uploads-${env} \
    --location=us-central1 \
    --uniform-bucket-level-access
  gcloud storage buckets add-iam-policy-binding gs://swept-chat-uploads-${env} \
    --member="serviceAccount:964226336245-compute@developer.gserviceaccount.com" \
    --role="roles/storage.objectAdmin"
done
```

The native GCS storage backend uses Application Default Credentials, so the runtime SA grant above is all that's needed — no JSON key.

### 5. Secret Manager — per-env secrets
Mirror workbench's prefix convention (`STAGING_` / `DEMO_`; prod has no prefix).

| Logical name | Prod secret | Staging secret | Demo secret |
|---|---|---|---|
| `WEBUI_SECRET_KEY` | `WEBUI_SECRET_KEY` | `STAGING_WEBUI_SECRET_KEY` | `DEMO_WEBUI_SECRET_KEY` |
| `DATABASE_URL` | `OPENWEBUI_DATABASE_URL` | `STAGING_OPENWEBUI_DATABASE_URL` | `DEMO_OPENWEBUI_DATABASE_URL` |

`*_OPENWEBUI_DATABASE_URL` format (Cloud SQL Unix socket — Cloud Run mounts at `/cloudsql/<connection-name>`):
```
postgresql://openwebui_<env>:<pw>@/openwebui_<env>?host=/cloudsql/production-472518:us-central1:swept-chat-db
```
(Open WebUI normalizes `postgres://` → `postgresql://` automatically; either prefix works.)

`WEBUI_SECRET_KEY`: `openssl rand -hex 32`. Pin one per env — rotating it invalidates all sessions.

Create each secret and grant the runtime SA read access:
```sh
echo -n "<value>" | gcloud secrets create WEBUI_SECRET_KEY \
  --data-file=- --replication-policy=automatic
gcloud secrets add-iam-policy-binding WEBUI_SECRET_KEY \
  --member="serviceAccount:964226336245-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

Repeat for each of the six secrets (`WEBUI_SECRET_KEY`, `STAGING_WEBUI_SECRET_KEY`, `DEMO_WEBUI_SECRET_KEY`, `OPENWEBUI_DATABASE_URL`, `STAGING_OPENWEBUI_DATABASE_URL`, `DEMO_OPENWEBUI_DATABASE_URL`).

Optional shared API keys (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`) likely already exist from workbench — if you want to wire them into open-webui too, grant the runtime SA `secretAccessor` and add a corresponding `--set-secrets` line in the workflow.

### 6. WIF — allow this repo
The existing provider currently restricts to `swept-ai/swept-workbench`. Broaden it to allow this repo as well:
```sh
gcloud iam workload-identity-pools providers update-oidc github \
  --location=global \
  --workload-identity-pool=github-actions \
  --attribute-condition="attribute.repository in ['swept-ai/swept-workbench','swept-ai/open-webui']"
```

Bind the existing deploy SA so this repo's workflows can impersonate it:
```sh
gcloud iam service-accounts add-iam-policy-binding \
  github-deploy@production-472518.iam.gserviceaccount.com \
  --role=roles/iam.workloadIdentityUser \
  --member="principalSet://iam.googleapis.com/projects/964226336245/locations/global/workloadIdentityPools/github-actions/attribute.repository/swept-ai/open-webui"
```

The deploy SA already has `roles/run.admin`, `roles/artifactregistry.admin`, `roles/iam.serviceAccountUser`, `roles/cloudsql.client`, `roles/secretmanager.secretAccessor`, `roles/storage.admin` from the workbench setup — no extra role grants required.

### 7. Initial Cloud Run service creation
The workflow uses `gcloud run services update`, which requires the service to already exist. Create empty placeholders pointing at Google's hello image:
```sh
for env in prod staging demo; do
  if [ "$env" = "prod" ]; then svc=swept-chat; else svc=${env}-swept-chat; fi
  gcloud run deploy "$svc" \
    --image=us-docker.pkg.dev/cloudrun/container/hello \
    --region=us-central1 \
    --platform=managed \
    --allow-unauthenticated \
    --service-account=964226336245-compute@developer.gserviceaccount.com
done
```

### 8. Custom domain mappings
```sh
gcloud beta run domain-mappings create --service=swept-chat \
  --domain=chat.swept.ai --region=us-central1
gcloud beta run domain-mappings create --service=staging-swept-chat \
  --domain=staging.chat.swept.ai --region=us-central1
gcloud beta run domain-mappings create --service=demo-swept-chat \
  --domain=demo.chat.swept.ai --region=us-central1
```
Each command returns a DNS record (CNAME `ghs.googlehosted.com.` for subdomains; A/AAAA for apex). Add them at the swept.ai DNS provider. Cert provisioning takes a few minutes.

### 9. GitHub Environment for prod gating
In repo Settings → Environments → New: `production`. Add required reviewers. The workflow's `deploy` job uses `environment: ${{ ... }}` so prod runs will block on approval.

---

## Operations

### Deploy
- **Staging:** push to `main`. The workflow auto-deploys.
- **Demo / prod:** GitHub Actions tab → "Build & Deploy" → Run workflow → choose env. Prod waits for the configured reviewer.

### Roll back
Cloud Run keeps prior revisions; route traffic back without re-deploying:
```sh
# List recent revisions
gcloud run revisions list --service=swept-chat --region=us-central1 --limit=5

# Send all traffic to a previous revision
gcloud run services update-traffic swept-chat \
  --region=us-central1 \
  --to-revisions=<revision-name>=100
```

### Tail logs
```sh
gcloud logging read \
  'resource.type=cloud_run_revision AND resource.labels.service_name="swept-chat"' \
  --limit=100 --format=json --project=production-472518
```

### Connect to Cloud SQL locally
```sh
gcloud sql connect swept-chat-db --user=openwebui_prod --database=openwebui_prod
```

### Rotate a secret
```sh
echo -n "<new-value>" | gcloud secrets versions add WEBUI_SECRET_KEY --data-file=-
# Trigger a redeploy so Cloud Run picks up the new latest version
gcloud run services update swept-chat \
  --region=us-central1 \
  --update-secrets=WEBUI_SECRET_KEY=WEBUI_SECRET_KEY:latest
```

### Add a shared API key to open-webui
1. Grant the runtime SA `secretAccessor` on the existing secret.
2. Add a corresponding entry to the workflow's `--set-secrets=...` line in `.github/workflows/build-deploy.yaml`.
3. Re-deploy.

---

## Gotchas

- **Image is large** — Open WebUI bakes embedding/whisper/tiktoken models at build time. First cold start can take 30–60s. Prod runs with `--min-instances=1` to keep one warm; bump if you see latency complaints.
- **Memory** — 4Gi works for typical use; bump to 8Gi if embedding workloads get heavy.
- **Migrations** — Alembic runs at startup (`ENABLE_DB_MIGRATIONS=true` by default in `backend/open_webui/env.py`). No separate migrate job is needed (unlike workbench).
- **Sticky sessions** — Open WebUI uses Socket.IO. Multiple Cloud Run instances will not share session state without Redis. If you scale beyond 1 instance and see auth flapping, add a Memorystore Redis and set `REDIS_URL`.
- **GCS auth** — uses ADC via the runtime SA. No `GOOGLE_APPLICATION_CREDENTIALS_JSON` needed in production. (`backend/open_webui/storage/provider.py:208-213`)
- **Cookie security** — `WEBUI_SESSION_COOKIE_SECURE=true` is set in the workflow; required because Cloud Run is always HTTPS at the edge.
