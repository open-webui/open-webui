# Playwright API Tests (Open WebUI)

This document explains how to run the Playwright API tests for Open WebUI locally and in CI.

Prerequisites

- Node 18-22 (recommended Node 20). If you have nvm installed:
  - `nvm install 20 && nvm use 20`
- npm >= 6
- GitHub Actions: secrets configured: BASE_URL, OPENWEBUI_API_KEY, TEST_EMAIL, TEST_PASSWORD

Local (recommended for quick iteration)

1. Switch Node to v20 (nvm):
   - `nvm install 20 && nvm use 20`
2. Install dependencies:
   - `npm ci`
3. Install Playwright browsers:
   - `npx playwright install --with-deps`
4. Run the API test file (example):
   - `BASE_URL="http://localhost:8080" OPENWEBUI_API_KEY="sk-..." TEST_EMAIL="admin@example.com" TEST_PASSWORD="..." npm run test:playwright -- playwright/tests/api/openwebui-api.spec.ts --project=chromium`

CI (GitHub Actions)

- A GitHub Actions workflow has been added at `.github/workflows/playwright-api.yml`.
- The workflow uses Node 20 and expects the following repository secrets:
  - `BASE_URL`, `OPENWEBUI_API_KEY`, `TEST_EMAIL`, `TEST_PASSWORD`

Notes and Troubleshooting

- If `npm install` fails due to engine mismatch, ensure your local Node version is within the supported range (>=18.13.0 <=22.x.x). Using the Action (CI) avoids local Node issues.
- The chat completions test will be skipped if no models are available.
- Do NOT commit secrets to the repo.
