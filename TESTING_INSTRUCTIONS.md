# Testing Instructions for Workflow Navigation Implementation

## Prerequisites

1. **Backend must be running** on port 8080:

   ```bash
   cd backend
   ./start.sh
   # Or: PORT=8080 python -m uvicorn open_webui.main:app --host 0.0.0.0 --port 8080
   ```

2. **Frontend must be running** (typically on port 5173 or 5174):

   ```bash
   npm run dev
   ```

3. **Verify services are running**:
   ```bash
   curl http://localhost:8080/health  # Backend
   curl http://localhost:5173         # Frontend
   ```

## Running Cypress Tests

### 1. Run Workflow Navigation Tests

```bash
export RUN_CHILD_PROFILE_TESTS=1
export CYPRESS_baseUrl=http://localhost:5173  # Use your frontend port

# Run workflow navigation tests
xvfb-run -a npx cypress run --headless --spec cypress/e2e/workflow-navigation.cy.ts
```

### 2. Run All Workflow-Related Tests

```bash
export RUN_CHILD_PROFILE_TESTS=1
export CYPRESS_baseUrl=http://localhost:5173

# Run all workflow tests
xvfb-run -a npx cypress run --headless --spec "cypress/e2e/workflow.cy.ts,cypress/e2e/survey-sidebar.cy.ts,cypress/e2e/workflow-navigation.cy.ts"
```

### 3. Run Tests Interactively

```bash
export RUN_CHILD_PROFILE_TESTS=1
export CYPRESS_baseUrl=http://localhost:5173
npx cypress open
```

## Test Coverage

The `workflow-navigation.cy.ts` test suite covers:

1. **SurveySidebar Navigation**
   - Clickable workflow step buttons on exit-survey page
   - Navigation to workflow steps when clicking buttons
   - Correct step completion indicators

2. **Main Sidebar Navigation**
   - Workflow navigation section visibility for interviewee users
   - Navigation to workflow steps from main sidebar

3. **Workflow State Integration**
   - Backend state fetching and display
   - Disabled locked steps and enabled accessible steps

4. **Navigation Guard Integration**
   - Redirect to correct workflow step based on backend state

## Expected Test Results

All tests should pass when:

- Backend is running and accessible
- Frontend is running and accessible
- Test account exists (default: jjdrisco@ucsd.edu / 0000)
- User is an interviewee user (has study_id in whitelist)

## Troubleshooting

### Tests Fail with "Cannot connect to backend"

- Ensure backend is running on port 8080
- Check backend logs for errors
- Verify `/api/v1/workflow/state` endpoint is accessible

### Tests Fail with "Cannot connect to frontend"

- Ensure frontend is running (check the port - may be 5174 if 5173 is in use)
- Update `CYPRESS_baseUrl` to match the correct port
- Check frontend console for errors

### Tests Fail with "Element not found"

- Wait times may need adjustment
- Check that SurveySidebar/Sidebar is actually visible
- Verify user type is correct (interviewee)

### Authentication Failures

- Verify test account credentials
- Check that signup/login endpoints are working
- Ensure token is being set in localStorage

## Manual Testing Checklist

Before running automated tests, verify manually:

- [ ] SurveySidebar shows on `/exit-survey` and `/initial-survey` routes
- [ ] Workflow step buttons are clickable in SurveySidebar
- [ ] Clicking step buttons navigates to correct routes
- [ ] Main Sidebar shows workflow section for interviewee users
- [ ] Main Sidebar hides workflow section for parent/child users
- [ ] Step indicators show correct completion status
- [ ] Locked steps are disabled
- [ ] Navigation guard redirects to correct route based on backend state
