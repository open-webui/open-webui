#!/usr/bin/env bash
# Set up local Vertex AI access via service-account impersonation (no SA key file).
# Use this when org policy `constraints/iam.disableServiceAccountKeyCreation` blocks
# `gcloud iam service-accounts keys create`. The resulting ADC file is read by both
# google-genai and anthropic[vertex] inside the open-webui container.
set -euo pipefail

PROJECT_ID="${VERTEX_PROJECT_ID:-pioneer-insurance}"
SA_NAME="${VERTEX_SA_NAME:-pioneer-chat-dev}"
SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
ADC_PATH="${HOME}/.config/gcloud/application_default_credentials.json"

cyan()  { printf '\033[36m%s\033[0m\n' "$*"; }
green() { printf '\033[32m%s\033[0m\n' "$*"; }
red()   { printf '\033[31m%s\033[0m\n' "$*" >&2; }

command -v gcloud >/dev/null || { red 'gcloud not found on PATH'; exit 1; }

USER_ACCOUNT="$(gcloud config get-value account 2>/dev/null || true)"
if [[ -z "${USER_ACCOUNT}" || "${USER_ACCOUNT}" == "(unset)" ]]; then
    red 'No gcloud user account set. Run: gcloud auth login'
    exit 1
fi

cyan "==> Project:       ${PROJECT_ID}"
cyan "==> Service acct:  ${SA_EMAIL}"
cyan "==> Impersonator:  ${USER_ACCOUNT}"
echo

cyan '==> Granting your user roles/iam.serviceAccountTokenCreator on the SA'
cyan '    (idempotent; needs SA-level IAM admin or roles/iam.serviceAccountAdmin)'
if ! gcloud iam service-accounts add-iam-policy-binding "${SA_EMAIL}" \
        --project="${PROJECT_ID}" \
        --member="user:${USER_ACCOUNT}" \
        --role='roles/iam.serviceAccountTokenCreator' \
        --condition=None \
        --quiet; then
    red 'Could not bind roles/iam.serviceAccountTokenCreator.'
    red "Ask a project IAM admin to grant ${USER_ACCOUNT} this role on ${SA_EMAIL}, then re-run."
    exit 1
fi
echo

cyan '==> Generating impersonated ADC (browser login)'
gcloud auth application-default login \
    --impersonate-service-account="${SA_EMAIL}" \
    --quiet

# NOTE: `gcloud auth application-default set-quota-project` does not work on
# impersonated ADC ("not user credentials"). With impersonation the quota
# project is implicitly the SA's own project (pioneer-insurance), which is
# what we want. If you ever need to override, set GOOGLE_CLOUD_QUOTA_PROJECT
# in the container env instead.

if [[ ! -f "${ADC_PATH}" ]]; then
    red "Expected ADC file at ${ADC_PATH} but did not find it. Aborting."
    exit 1
fi
green "==> ADC ready at ${ADC_PATH}"
echo

cyan '==> Smoke-testing token mint via gcloud'
if TOKEN="$(gcloud auth application-default print-access-token 2>&1)" && [[ "${TOKEN}" == ya29.* ]]; then
    green "==> Token mint OK (ya29.${TOKEN:5:8}...)"
else
    red 'Token mint failed:'
    red "  ${TOKEN}"
    red "Check that ${USER_ACCOUNT} has roles/iam.serviceAccountTokenCreator on ${SA_EMAIL}."
    red 'ADC at the path above will not work for Vertex calls.'
    exit 1
fi
echo

green 'Done. To run open-webui with this credential:'
echo
echo "  export VERTEX_SA_KEY_PATH=\"${ADC_PATH}\""
echo '  docker compose up -d --build'
echo
echo 'Then install plugins/functions/vertex_chat.py via Admin Panel > Functions.'
