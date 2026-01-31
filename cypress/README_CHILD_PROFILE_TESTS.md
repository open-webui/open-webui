# Child-profile Cypress tests

`kids-profile.cy.ts` and `parent-child-profile.cy.ts` exercise the quiz (`/kids/profile`) and parent (`/parent/child-profile`) flows. They **do not** run `registerAdmin`; they sign in with an existing backend account.

## Prerequisites

1. **Frontend** running (e.g. `npm run dev`). Note the port Vite prints (often `http://localhost:5173` or `5174` if 5173 is in use).

2. **Backend** running and reachable from the frontend (Vite proxies `/api`, `/ollama`, `/openai`, `/ws` to `BACKEND_HOST:BACKEND_PORT`, default `localhost:8080`).

3. **Test account** `jjdrisco@ucsd.edu` / `0000` must exist in the backend. Override with:
   - `INTERVIEWEE_EMAIL` / `INTERVIEWEE_PASSWORD` (kids spec), or
   - `PARENT_EMAIL` / `PARENT_PASSWORD` (parent spec), or
   - `TEST_EMAIL` / `TEST_PASSWORD` (both).  
     Cypress reads `CYPRESS_*` automatically; for `RUN_CHILD_PROFILE_TESTS` and the above, the project’s `cypress.config.ts` also forwards `RUN_CHILD_PROFILE_TESTS`, `INTERVIEWEE_EMAIL`, etc. from `process.env` when not set via `CYPRESS_*`.

## Run

```bash
# 1) Start frontend (in one terminal)
npm run dev

# 2) Start backend (in another), e.g. from backend/ with DATABASE_URL, PORT=8080, etc.

# 3) Run the child-profile specs (from project root).
#    Use the same port as in step 1 (e.g. 5174 if Vite is on 5174).
RUN_CHILD_PROFILE_TESTS=1 CYPRESS_baseUrl=http://localhost:5173 npx cypress run --spec "cypress/e2e/kids-profile.cy.ts,cypress/e2e/parent-child-profile.cy.ts"
```

## Common failures

- **`Expected to find element: input#email, input[autocomplete="email"]`, but never found it**
  - Frontend not running on the URL in `CYPRESS_baseUrl`, or
  - Backend not running / not reachable: layout’s `getBackendConfig()` can block or fail, and the auth form depends on the app loading.
  - Fix: ensure `npm run dev` and the backend are running, and `CYPRESS_baseUrl` matches the dev server (e.g. `http://localhost:5174` if Vite is on 5174).

- **`expected 500 to be one of [ 200, 400 ]` in `before` (signup)**
  - `RUN_CHILD_PROFILE_TESTS` was not passed through, so `registerAdmin` ran and signup returned 500.
  - Fix: run with `RUN_CHILD_PROFILE_TESTS=1` (or `CYPRESS_RUN_CHILD_PROFILE_TESTS=1`). The repo’s `cypress.config.ts` maps `RUN_CHILD_PROFILE_TESTS` from `process.env` if `CYPRESS_RUN_CHILD_PROFILE_TESTS` is not set.

- **`Cannot read properties of null (reading 'default_locale')`**
  - Addressed in `+layout.svelte` by using `backendConfig?.default_locale` when `getBackendConfig()` fails and `backendConfig` is null.
