# Cypress Test Setup Guide

This document provides instructions for setting up and running Cypress end-to-end tests for the workflow API endpoints.

## Prerequisites

1. **Node.js and npm** - Ensure Node.js v20.x is installed (recommended for Cypress compatibility)
   - The project supports Node.js >=18.13.0 <=22.x.x (see `package.json` engines field)
   - **Node.js v20.x is recommended** for running Cypress tests reliably
   - Check your version: `node --version`
2. **Python 3** - Required for backend (Python 3.12+)
3. **System Dependencies** - For headless Cypress on Linux:
   ```bash
   sudo apt-get update
   sudo apt-get install -y xvfb libgtk-3-0 libgbm-dev libnotify-dev libnss3 libxss1
   ```

## Installation

1. **Install Node Dependencies**:

   ```bash
   npm install --legacy-peer-deps
   ```

   **Important**: `--legacy-peer-deps` is required due to peer dependency conflicts with @tiptap packages. This flag tells npm to use the legacy peer dependency resolution algorithm, which is more permissive and works better with Node.js v20.

2. **Install Backend Dependencies** (if not already installed):
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

## Running Services

### 1. Start Backend

The backend must be running on port 8080 (default):

```bash
cd backend
./start.sh
# Or manually:
PORT=8080 python -m uvicorn open_webui.main:app --host 0.0.0.0 --port 8080
```

Verify backend is running:

```bash
curl http://localhost:8080/health
```

### 2. Start Frontend

The frontend must be running (typically on port 5173 or 5174):

```bash
npm run dev
```

Note the port Vite prints (often `http://localhost:5173` or `5174` if 5173 is in use).

Verify frontend is running:

```bash
curl http://localhost:5173
```

## Test Account Setup

The tests require a test account in the backend. Default credentials:

- **Email**: `jjdrisco@ucsd.edu`
- **Password**: `0000`

You can override these with environment variables:

- `INTERVIEWEE_EMAIL` / `INTERVIEWEE_PASSWORD`
- `TEST_EMAIL` / `TEST_PASSWORD`

## Running Tests

### Workflow API Tests

Run the workflow endpoint tests:

```bash
# Set environment variables
export RUN_CHILD_PROFILE_TESTS=1
export CYPRESS_baseUrl=http://localhost:5173  # Use the port your frontend is running on

# Run tests (headless mode on Linux)
xvfb-run -a npx cypress run --headless --spec cypress/e2e/workflow.cy.ts

# Or run interactively (requires display)
npx cypress open
```

### All Child Profile Tests

Run all child profile related tests:

```bash
export RUN_CHILD_PROFILE_TESTS=1
export CYPRESS_baseUrl=http://localhost:5173
xvfb-run -a npx cypress run --headless --spec "cypress/e2e/kids-profile.cy.ts,cypress/e2e/parent-child-profile.cy.ts,cypress/e2e/workflow.cy.ts"
```

## Test Coverage

The `workflow.cy.ts` test suite covers:

1. **GET /workflow/state** - Workflow state and progress tracking
2. **GET /workflow/current-attempt** - Attempt number tracking
3. **GET /workflow/session-info** - Session information
4. **GET /workflow/completed-scenarios** - Completed scenario indices
5. **GET /workflow/study-status** - Study completion status
6. **POST /workflow/reset** - Reset entire workflow
7. **POST /workflow/reset-moderation** - Reset moderation workflow only
8. **POST /workflow/moderation/finalize** - Finalize moderation (with filters)
9. **Workflow State Transitions** - Logic validation
10. **Error Handling** - Authentication error handling

## Common Issues

### Cypress Fails to Start (Missing X Server)

**Error**: `Missing X server or $DISPLAY`

**Solution**:

- Install system dependencies (see Prerequisites)
- Use `xvfb-run -a` wrapper for headless execution
- Or set `DISPLAY=:99` and start a virtual display

### Frontend/Backend Not Running

**Error**: `Expected to find element: input#email, but never found it`

**Solution**:

- Ensure frontend is running on the port specified in `CYPRESS_baseUrl`
- Ensure backend is running on port 8080
- Check that Vite proxy is correctly forwarding `/api` requests to backend

### Authentication Failures

**Error**: `401 Unauthorized` or `403 Forbidden`

**Solution**:

- Verify test account exists in backend
- Check that credentials match `INTERVIEWEE_EMAIL`/`INTERVIEWEE_PASSWORD` or defaults
- Ensure token is being retrieved from localStorage after login

### Dependency Conflicts

**Error**: `ERESOLVE could not resolve` during `npm install`

**Solution**:

- Use `npm install --legacy-peer-deps` as documented
- This is expected due to @tiptap version conflicts
- Ensure you're using Node.js v20.x for best compatibility

### Cypress Crashes with Node.js v22

**Error**: Cypress crashes with `node:internal/modules/run_main` errors on Node.js v22

**Solution**:

- **Use Node.js v20.x instead** - Cypress has better compatibility with Node.js v20
- Install Node.js v20 using nvm: `nvm install 20 && nvm use 20`
- Then reinstall dependencies: `npm install --legacy-peer-deps`

## CI/CD Integration

For CI/CD pipelines, ensure:

1. System dependencies are installed
2. Backend and frontend services are started
3. Test account exists or is created during setup
4. Use `xvfb-run -a` for headless execution on Linux

Example CI script:

```bash
#!/bin/bash
set -e

# Install dependencies
npm install --legacy-peer-deps

# Start backend in background
cd backend && ./start.sh &
BACKEND_PID=$!
cd ..

# Start frontend in background
npm run dev &
FRONTEND_PID=$!

# Wait for services
sleep 10
curl -f http://localhost:8080/health || exit 1
curl -f http://localhost:5173 || exit 1

# Run tests
export RUN_CHILD_PROFILE_TESTS=1
export CYPRESS_baseUrl=http://localhost:5173
xvfb-run -a npx cypress run --headless --spec cypress/e2e/workflow.cy.ts

# Cleanup
kill $BACKEND_PID $FRONTEND_PID
```

## Additional Resources

- [Cypress Documentation](https://docs.cypress.io/)
- [Cypress Required Dependencies](https://on.cypress.io/required-dependencies)
- See `cypress/README_CHILD_PROFILE_TESTS.md` for child profile test details
