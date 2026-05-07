#!/usr/bin/env bash
# Bootstrap the Swept GCP infrastructure for open-webui's three-env Cloud Run
# deploy (chat.swept.ai / staging.chat.swept.ai / demo.chat.swept.ai).
#
# Idempotent: every step checks for existing resources and skips if present.
# Mirrors the runbook in DEPLOYMENT.md. Re-read that file before changing
# anything here — it is the source of truth.
#
# Usage:
#   scripts/bootstrap-gcp.sh                # interactive, runs all phases
#   scripts/bootstrap-gcp.sh --yes          # skip confirmation
#   scripts/bootstrap-gcp.sh --dry-run      # print commands, do not execute
#   scripts/bootstrap-gcp.sh --phase 3      # start at phase 3 (resume)
#   scripts/bootstrap-gcp.sh --update-wif   # also update the shared WIF
#                                           # provider condition (requires care
#                                           # — affects swept-workbench too)

set -euo pipefail

# ---- Constants (do not change without updating DEPLOYMENT.md and the workflow) ----
PROJECT="production-472518"
PROJECT_NUMBER="964226336245"
REGION="us-central1"
AR_REPO="chat-releases"
SQL_INSTANCE="swept-chat-db"
SQL_TIER="db-custom-1-3840"
SQL_VERSION="POSTGRES_16"
SQL_CONNECTION="${PROJECT}:${REGION}:${SQL_INSTANCE}"
RUNTIME_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
DEPLOY_SA="github-deploy@${PROJECT}.iam.gserviceaccount.com"
WIF_POOL="github-actions"
WIF_PROVIDER="github"
GH_REPO="swept-ai/open-webui"
WORKBENCH_REPO="swept-ai/swept-workbench"

ENVS=(prod staging demo)

# ---- Helpers ----
cyan()  { printf '\033[36m%s\033[0m\n' "$*"; }
green() { printf '\033[32m%s\033[0m\n' "$*"; }
yellow(){ printf '\033[33m%s\033[0m\n' "$*"; }
red()   { printf '\033[31m%s\033[0m\n' "$*" >&2; }
bold()  { printf '\033[1m%s\033[0m\n' "$*"; }

# `run` either executes a command or just prints it (under --dry-run).
DRY_RUN=0
ASSUME_YES=0
START_PHASE=1
UPDATE_WIF=0

run() {
    if [[ "${DRY_RUN}" == "1" ]]; then
        printf '\033[2m+ %s\033[0m\n' "$*"
    else
        "$@"
    fi
}

confirm() {
    local prompt="${1:-Continue?}"
    if [[ "${ASSUME_YES}" == "1" ]]; then return 0; fi
    read -r -p "$(yellow "${prompt} [y/N] ")" reply
    [[ "${reply}" =~ ^[Yy]$ ]]
}

service_name() {
    local env="$1"
    if [[ "${env}" == "prod" ]]; then echo "swept-chat"; else echo "${env}-swept-chat"; fi
}

secret_prefix() {
    local env="$1"
    case "${env}" in
        prod)    echo "" ;;
        staging) echo "STAGING_" ;;
        demo)    echo "DEMO_" ;;
    esac
}

bucket_name() { echo "swept-chat-uploads-$1"; }
db_name()     { echo "openwebui_$1"; }
db_user()     { echo "openwebui_$1"; }
domain_name() {
    local env="$1"
    if [[ "${env}" == "prod" ]]; then echo "chat.swept.ai"; else echo "${env}.chat.swept.ai"; fi
}

# Returns 0 if the secret already exists, 1 otherwise.
secret_exists() {
    gcloud secrets describe "$1" --project="${PROJECT}" >/dev/null 2>&1
}

# Create a secret with a given value, idempotently. If it already exists,
# leaves the value alone.
create_secret_if_missing() {
    local name="$1" value="$2"
    if secret_exists "${name}"; then
        yellow "  • Secret ${name} already exists — leaving value alone"
        return 0
    fi
    if [[ "${DRY_RUN}" == "1" ]]; then
        printf '\033[2m+ echo -n "<value>" | gcloud secrets create %s --data-file=- --replication-policy=automatic --project=%s\033[0m\n' "${name}" "${PROJECT}"
        return 0
    fi
    printf '%s' "${value}" | gcloud secrets create "${name}" \
        --data-file=- --replication-policy=automatic \
        --project="${PROJECT}" >/dev/null
    green "  • Created secret ${name}"
}

grant_secret_access() {
    local name="$1"
    run gcloud secrets add-iam-policy-binding "${name}" \
        --member="serviceAccount:${RUNTIME_SA}" \
        --role="roles/secretmanager.secretAccessor" \
        --project="${PROJECT}" \
        --quiet >/dev/null
}

# ---- Pre-flight ----
preflight() {
    bold "==> Pre-flight"
    command -v gcloud >/dev/null  || { red "gcloud not on PATH"; exit 1; }
    command -v openssl >/dev/null || { red "openssl not on PATH"; exit 1; }

    local current_project
    current_project="$(gcloud config get-value project 2>/dev/null || true)"
    if [[ "${current_project}" != "${PROJECT}" ]]; then
        yellow "  Current gcloud project is '${current_project}', not '${PROJECT}'."
        confirm "  Switch to ${PROJECT} for this run?" || { red "Aborted."; exit 1; }
        run gcloud config set project "${PROJECT}"
    fi

    local account
    account="$(gcloud config get-value account 2>/dev/null || true)"
    if [[ -z "${account}" || "${account}" == "(unset)" ]]; then
        red "No gcloud account. Run: gcloud auth login"
        exit 1
    fi
    green "  Project: ${PROJECT}"
    green "  Account: ${account}"
    if [[ "${DRY_RUN}" == "1" ]]; then yellow "  Mode:    DRY-RUN (no changes will be made)"; fi
    echo
}

# ---- Phase 1: Enable APIs ----
phase1_enable_apis() {
    bold "==> Phase 1: Enable required APIs"
    run gcloud services enable \
        artifactregistry.googleapis.com \
        run.googleapis.com \
        sqladmin.googleapis.com \
        secretmanager.googleapis.com \
        storage.googleapis.com \
        iam.googleapis.com \
        iamcredentials.googleapis.com \
        --project="${PROJECT}"
    green "  ✓ APIs enabled"
    echo
}

# ---- Phase 2: Artifact Registry repo ----
phase2_artifact_registry() {
    bold "==> Phase 2: Artifact Registry repo (${AR_REPO})"
    if gcloud artifacts repositories describe "${AR_REPO}" \
            --location="${REGION}" --project="${PROJECT}" >/dev/null 2>&1; then
        yellow "  • Repo ${AR_REPO} already exists"
    else
        run gcloud artifacts repositories create "${AR_REPO}" \
            --repository-format=docker \
            --location="${REGION}" \
            --description="Open WebUI container images for Swept chat envs" \
            --project="${PROJECT}"
        green "  ✓ Created ${AR_REPO}"
    fi
    echo
}

# ---- Phase 3: Cloud SQL instance + per-env DB/user/secrets ----
phase3_cloud_sql() {
    bold "==> Phase 3: Cloud SQL Postgres (${SQL_INSTANCE}, three databases)"
    if gcloud sql instances describe "${SQL_INSTANCE}" \
            --project="${PROJECT}" >/dev/null 2>&1; then
        yellow "  • Instance ${SQL_INSTANCE} already exists"
    else
        yellow "  Creating Postgres instance — this takes ~5–10 minutes."
        run gcloud sql instances create "${SQL_INSTANCE}" \
            --database-version="${SQL_VERSION}" \
            --tier="${SQL_TIER}" \
            --region="${REGION}" \
            --storage-size=20GB \
            --storage-auto-increase \
            --backup --backup-start-time=08:00 \
            --project="${PROJECT}"
        green "  ✓ Created ${SQL_INSTANCE}"
    fi

    for env in "${ENVS[@]}"; do
        local db user prefix db_secret
        db="$(db_name "${env}")"
        user="$(db_user "${env}")"
        prefix="$(secret_prefix "${env}")"
        db_secret="${prefix}OPENWEBUI_DATABASE_URL"

        # Database
        if gcloud sql databases describe "${db}" --instance="${SQL_INSTANCE}" \
                --project="${PROJECT}" >/dev/null 2>&1; then
            yellow "  • DB ${db} already exists"
        else
            run gcloud sql databases create "${db}" --instance="${SQL_INSTANCE}" --project="${PROJECT}"
            green "  ✓ Created DB ${db}"
        fi

        # User + DATABASE_URL secret are created together so the password
        # exists in exactly one place (Secret Manager). If the secret already
        # exists, we trust it — recovering a lost password requires resetting
        # the SQL user and rotating the secret manually.
        if secret_exists "${db_secret}"; then
            yellow "  • Secret ${db_secret} already exists — assuming SQL user ${user} matches"
        else
            local pw url
            pw="$(openssl rand -base64 32 | tr -d '=+/' | cut -c1-32)"
            url="postgresql://${user}:${pw}@/${db}?host=/cloudsql/${SQL_CONNECTION}"

            # Create or reset the SQL user with this fresh password.
            if gcloud sql users list --instance="${SQL_INSTANCE}" --project="${PROJECT}" \
                    --format='value(name)' 2>/dev/null | grep -qx "${user}"; then
                yellow "  • SQL user ${user} exists — resetting password to match new secret"
                run gcloud sql users set-password "${user}" \
                    --instance="${SQL_INSTANCE}" --password="${pw}" --project="${PROJECT}" >/dev/null
            else
                run gcloud sql users create "${user}" \
                    --instance="${SQL_INSTANCE}" --password="${pw}" --project="${PROJECT}" >/dev/null
                green "  ✓ Created SQL user ${user}"
            fi

            create_secret_if_missing "${db_secret}" "${url}"
        fi
        grant_secret_access "${db_secret}"
    done
    echo
}

# ---- Phase 4: GCS upload buckets ----
phase4_gcs_buckets() {
    bold "==> Phase 4: GCS upload buckets"
    for env in "${ENVS[@]}"; do
        local b="$(bucket_name "${env}")"
        if gcloud storage buckets describe "gs://${b}" --project="${PROJECT}" >/dev/null 2>&1; then
            yellow "  • Bucket gs://${b} already exists"
        else
            run gcloud storage buckets create "gs://${b}" \
                --location="${REGION}" \
                --uniform-bucket-level-access \
                --project="${PROJECT}"
            green "  ✓ Created gs://${b}"
        fi
        run gcloud storage buckets add-iam-policy-binding "gs://${b}" \
            --member="serviceAccount:${RUNTIME_SA}" \
            --role="roles/storage.objectAdmin" \
            --project="${PROJECT}" >/dev/null
    done
    green "  ✓ Runtime SA granted storage.objectAdmin on each bucket"
    echo
}

# ---- Phase 5: WEBUI_SECRET_KEY per env ----
phase5_webui_secrets() {
    bold "==> Phase 5: WEBUI_SECRET_KEY secrets"
    for env in "${ENVS[@]}"; do
        local prefix name
        prefix="$(secret_prefix "${env}")"
        name="${prefix}WEBUI_SECRET_KEY"
        create_secret_if_missing "${name}" "$(openssl rand -hex 32)"
        grant_secret_access "${name}"
    done
    echo
}

# ---- Phase 6: WIF — bind this repo to the existing deploy SA ----
phase6_wif() {
    bold "==> Phase 6: Workload Identity Federation"

    # The pool and provider already exist (created for swept-workbench). We
    # only need to (a) optionally broaden the provider's attribute condition
    # to include this repo, and (b) bind the deploy SA so this repo's
    # principal can impersonate it.

    local current_condition
    current_condition="$(gcloud iam workload-identity-pools providers describe "${WIF_PROVIDER}" \
        --location=global --workload-identity-pool="${WIF_POOL}" \
        --project="${PROJECT}" --format='value(attributeCondition)' 2>/dev/null || true)"

    cyan "  Current WIF attribute condition:"
    printf '    %s\n' "${current_condition:-<none>}"

    if echo "${current_condition}" | grep -q "${GH_REPO}"; then
        green "  ✓ Provider already allows ${GH_REPO}"
    else
        local new_condition="attribute.repository in ['${WORKBENCH_REPO}','${GH_REPO}']"
        yellow "  Provider does not allow ${GH_REPO} yet."
        cyan "  Proposed new condition:"
        printf '    %s\n' "${new_condition}"
        if [[ "${UPDATE_WIF}" == "1" ]]; then
            confirm "  Apply this change? (Affects swept-workbench too — make sure ${WORKBENCH_REPO} stays allowed.)" \
                || { red "  Skipping WIF update."; }
            run gcloud iam workload-identity-pools providers update-oidc "${WIF_PROVIDER}" \
                --location=global --workload-identity-pool="${WIF_POOL}" \
                --attribute-condition="${new_condition}" \
                --project="${PROJECT}"
            green "  ✓ Updated WIF provider condition"
        else
            yellow "  Skipping WIF condition update (re-run with --update-wif to apply)."
            yellow "  Manual command:"
            printf '    gcloud iam workload-identity-pools providers update-oidc %s \\\n' "${WIF_PROVIDER}"
            printf '      --location=global --workload-identity-pool=%s \\\n' "${WIF_POOL}"
            printf '      --attribute-condition="%s" \\\n' "${new_condition}"
            printf '      --project=%s\n' "${PROJECT}"
        fi
    fi

    # Bind the deploy SA to this repo's principal — always safe, additive.
    run gcloud iam service-accounts add-iam-policy-binding "${DEPLOY_SA}" \
        --role=roles/iam.workloadIdentityUser \
        --member="principalSet://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/${WIF_POOL}/attribute.repository/${GH_REPO}" \
        --project="${PROJECT}" \
        --quiet >/dev/null
    green "  ✓ Deploy SA bound to ${GH_REPO} principal"
    echo
}

# ---- Phase 7: Initial Cloud Run service placeholders ----
phase7_cloud_run_placeholders() {
    bold "==> Phase 7: Cloud Run service placeholders"
    for env in "${ENVS[@]}"; do
        local svc="$(service_name "${env}")"
        if gcloud run services describe "${svc}" --region="${REGION}" --project="${PROJECT}" >/dev/null 2>&1; then
            yellow "  • Service ${svc} already exists"
        else
            yellow "  Creating placeholder service ${svc} (hello image — workflow will replace it)"
            run gcloud run deploy "${svc}" \
                --image=us-docker.pkg.dev/cloudrun/container/hello \
                --region="${REGION}" \
                --platform=managed \
                --allow-unauthenticated \
                --service-account="${RUNTIME_SA}" \
                --project="${PROJECT}" \
                --quiet
            green "  ✓ Created ${svc}"
        fi
    done
    echo
}

# ---- Phase 8: Custom domain mappings ----
phase8_domain_mappings() {
    bold "==> Phase 8: Cloud Run custom domain mappings"
    for env in "${ENVS[@]}"; do
        local svc="$(service_name "${env}")"
        local domain="$(domain_name "${env}")"
        if gcloud beta run domain-mappings describe --domain="${domain}" \
                --region="${REGION}" --project="${PROJECT}" >/dev/null 2>&1; then
            yellow "  • Mapping ${domain} → ${svc} already exists"
        else
            run gcloud beta run domain-mappings create --service="${svc}" \
                --domain="${domain}" --region="${REGION}" --project="${PROJECT}"
            green "  ✓ Mapped ${domain} → ${svc}"
        fi
    done
    echo
}

# ---- Phase 9: Print DNS records to add ----
phase9_dns_instructions() {
    bold "==> Phase 9: DNS records to add at the swept.ai DNS provider"
    if [[ "${DRY_RUN}" == "1" ]]; then
        yellow "  (dry-run — skip; describe each mapping to see records)"
        return
    fi
    for env in "${ENVS[@]}"; do
        local domain="$(domain_name "${env}")"
        cyan "  ${domain}:"
        gcloud beta run domain-mappings describe --domain="${domain}" \
            --region="${REGION}" --project="${PROJECT}" \
            --format='value(status.resourceRecords)' 2>/dev/null \
            | sed 's/^/    /' || yellow "    (mapping not yet created)"
    done
    echo
}

# ---- Final summary ----
final_summary() {
    bold "==> Done"
    cat <<EOF

Next manual steps (cannot be automated by this script):

  1. Add the DNS records printed in Phase 9 at the swept.ai DNS provider.
     Cert provisioning takes a few minutes after DNS propagates.

  2. In GitHub repo settings → Environments, create environments named
     'staging', 'demo', and 'production'. Add required reviewers to
     'production' so prod deploys block on approval.

  3. (Optional) Grant the runtime SA secretmanager.secretAccessor on shared
     workbench API keys (OPENAI_API_KEY etc.) and add them to the
     --set-secrets line in .github/workflows/build-deploy.yaml.

  4. Push to main → first build runs and auto-deploys staging. Smoke check:
       curl https://staging.chat.swept.ai/health

EOF
}

# ---- CLI parsing ----
usage() {
    sed -n '2,17p' "$0" | sed 's/^# \?//'
    exit "${1:-0}"
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        -y|--yes)        ASSUME_YES=1; shift ;;
        --dry-run)       DRY_RUN=1; shift ;;
        --phase)         START_PHASE="$2"; shift 2 ;;
        --update-wif)    UPDATE_WIF=1; shift ;;
        -h|--help)       usage 0 ;;
        *)               red "Unknown flag: $1"; usage 1 ;;
    esac
done

# ---- Main ----
preflight

bold "About to run phases ${START_PHASE}–9 against project '${PROJECT}'."
yellow "This script is idempotent — safe to re-run if a phase fails."
confirm "Proceed?" || { red "Aborted."; exit 1; }
echo

PHASES=(
    phase1_enable_apis
    phase2_artifact_registry
    phase3_cloud_sql
    phase4_gcs_buckets
    phase5_webui_secrets
    phase6_wif
    phase7_cloud_run_placeholders
    phase8_domain_mappings
    phase9_dns_instructions
)

for ((i = START_PHASE - 1; i < ${#PHASES[@]}; i++)); do
    "${PHASES[$i]}"
done

final_summary
