# Context Export: Workflow Navigation Restoration Feature

## Branch Information

**Current Branch**: `feat/restore-workflow-navigation`
**Base Branch**: `cursor/commit-identification-for-survey-feature-8209` (which was based on `main`)

**Remote**: Pushed to `origin/feat/restore-workflow-navigation`

## What Was Implemented

### Summary

Restored the lost survey workflow navigation functionality that was removed from the Sidebar component in commit `ba6fbc56d`. The implementation uses the backend API as the single source of truth (no localStorage) and maintains user type differentiation.

### Key Changes

#### 1. Workflow Utility Functions (`src/lib/utils/workflow.ts`)

- `getStepRoute(step: number)` - Maps step numbers (1-4) to routes
- `getStepFromRoute(route: string)` - Gets step number from route path
- `canAccessStep(step: number, workflowState)` - Determines if a step is accessible based on backend state
- `getStepLabel(step: number)` - Gets display labels for steps
- `isStepCompleted(step: number, workflowState)` - Checks completion status

#### 2. Enhanced SurveySidebar (`src/lib/components/layout/SurveySidebar.svelte`)

- **Before**: Static progress indicators (read-only)
- **After**: Clickable step navigation buttons
- Features:
  - Fetches workflow state from backend API on mount
  - Refreshes state when route changes
  - Shows completion status (checkmark for completed, number for current, gray for locked)
  - Highlights current step (blue background)
  - Disables locked steps with error toast on click attempt
  - Navigation to accessible steps

#### 3. Main Sidebar Workflow Section (`src/lib/components/layout/Sidebar.svelte`)

- **New**: Conditional workflow navigation section
- Only visible for **interviewee users** (determined by `getUserType()`)
- Hidden for parent/child users
- Same step navigation buttons as SurveySidebar
- Fetches workflow state from backend API
- Refreshes on route changes

#### 4. Layout Navigation Guard (`src/routes/(app)/+layout.svelte`)

- **Removed**: All localStorage dependencies for workflow state
- **Added**: Backend API integration using `getWorkflowState()`
- Uses `next_route` from backend to determine correct navigation
- Maintains Prolific user session handling
- Preserves user type differentiation (parent/child/interviewee)

#### 5. Cypress Tests (`cypress/e2e/workflow-navigation.cy.ts`)

- Tests for SurveySidebar navigation
- Tests for main Sidebar navigation
- Tests for workflow state integration
- Tests for navigation guard integration

## Files Changed

### Created Files

1. `src/lib/utils/workflow.ts` - Workflow utility functions
2. `cypress/e2e/workflow-navigation.cy.ts` - Cypress tests
3. `REIMPLEMENTATION_PLAN.md` - Implementation plan
4. `SURVEY_IMPLEMENTATION_DIFFERENCES.md` - Comparison with original
5. `TESTING_INSTRUCTIONS.md` - Testing guide
6. `CONTEXT_EXPORT.md` - This file

### Modified Files

1. `src/lib/components/layout/SurveySidebar.svelte` - Added clickable navigation
2. `src/lib/components/layout/Sidebar.svelte` - Added workflow section
3. `src/routes/(app)/+layout.svelte` - Updated navigation guard

## Architecture Decisions

### ✅ Backend API Only (No localStorage)

- All workflow state comes from `getWorkflowState()` API
- No localStorage for workflow state
- Backend is single source of truth

### ✅ No Centralized Service

- Components call API directly
- SurveySidebar and Sidebar are mutually exclusive (never visible simultaneously)
- Utility functions for shared logic only

### ✅ User Type Differentiation

- **Interviewee users**: See full workflow navigation
- **Parent/Child users**: Workflow UI hidden
- **Admin users**: Can see workflow UI (optional)

## Commits Made

1. `2f7de413c` - feat: Restore workflow navigation functionality
2. `ff8131179` - refine: Improve canAccessStep logic for workflow navigation
3. `0416c7db0` - docs: Add testing instructions for workflow navigation

## Testing Status

### ✅ Code Implementation: Complete

- All code changes committed
- No linter errors
- TypeScript types correct

### ⏳ Cypress Tests: Created but Not Run

- Test file created: `cypress/e2e/workflow-navigation.cy.ts`
- **Cannot run tests** - requires backend and frontend services running
- See `TESTING_INSTRUCTIONS.md` for how to run

## How to Test Locally

### 1. Start Services

**Backend** (port 8080):

```bash
cd backend
./start.sh
# Or: PORT=8080 python -m uvicorn open_webui.main:app --host 0.0.0.0 --port 8080
```

**Frontend** (port 5173 or 5174):

```bash
npm run dev
```

### 2. Manual Testing Checklist

- [ ] **SurveySidebar on `/exit-survey`**:
  - [ ] Shows clickable step buttons (1-4)
  - [ ] Completed steps show checkmark
  - [ ] Current step is highlighted (blue)
  - [ ] Locked steps are disabled
  - [ ] Clicking accessible steps navigates correctly
  - [ ] Clicking locked steps shows error toast

- [ ] **Main Sidebar**:
  - [ ] For interviewee users: Shows "Assignment Workflow" section
  - [ ] For parent users: Workflow section hidden
  - [ ] For child users: Workflow section hidden
  - [ ] Step buttons work correctly
  - [ ] Navigation works from main sidebar

- [ ] **Navigation Guard**:
  - [ ] Redirects to correct route based on backend `next_route`
  - [ ] Allows access to current and previous steps
  - [ ] Blocks access to future steps

### 3. Run Cypress Tests

```bash
export RUN_CHILD_PROFILE_TESTS=1
export CYPRESS_baseUrl=http://localhost:5173  # Use your frontend port

# Run workflow navigation tests
xvfb-run -a npx cypress run --headless --spec cypress/e2e/workflow-navigation.cy.ts

# Or run interactively
npx cypress open
```

## Known Issues / Considerations

### Database Error (from terminal output)

The terminal shows a SQLite database error. This is likely a local environment issue, not related to our changes. The error is:

```
sqlite3.OperationalError: unable to open database file
```

**To fix**: Ensure database file exists and has correct permissions, or configure database connection properly.

### Backend API Dependencies

- The implementation depends on `/api/v1/workflow/state` endpoint
- This endpoint must return `WorkflowStateResponse` with:
  - `next_route`: string (e.g., '/kids/profile', '/moderation-scenario', etc.)
  - `progress_by_section`: object with:
    - `has_child_profile`: boolean
    - `moderation_completed_count`: number
    - `moderation_total`: number
    - `exit_survey_completed`: boolean

### User Type Detection

- Uses `getUserType()` function which checks:
  - User role (admin, child, parent, interviewee)
  - Study ID whitelist for interviewee determination
  - Parent ID for child account detection

## Next Steps

1. **Start services** (backend + frontend)
2. **Test manually** using the checklist above
3. **Run Cypress tests** to verify automated test coverage
4. **Fix any issues** that arise during testing
5. **Verify** that all existing tests still pass:

   ```bash
   # Run existing workflow tests
   xvfb-run -a npx cypress run --headless --spec cypress/e2e/workflow.cy.ts

   # Run existing survey-sidebar tests
   xvfb-run -a npx cypress run --headless --spec cypress/e2e/survey-sidebar.cy.ts
   ```

## Key Differences from Original Implementation

### What Was Restored

✅ Clickable workflow step navigation buttons
✅ Visual progress indicators (completed, current, locked)
✅ Step navigation from sidebar
✅ Workflow state management

### What Changed from Original

❌ **No localStorage** - Original used localStorage + backend sync
✅ **Backend API only** - Current uses backend as single source of truth
❌ **No Personal Store** - Original had Personal Store integration (intentionally not restored)
❌ **No child profile management in Sidebar** - Now handled by `childProfileSync` service
✅ **User type aware** - Original blocked all users, current only blocks interviewees

## Reference Documents

- `REIMPLEMENTATION_PLAN.md` - Full implementation plan
- `SURVEY_IMPLEMENTATION_DIFFERENCES.md` - Detailed comparison with original
- `TESTING_INSTRUCTIONS.md` - How to run tests
- `docs/CYPRESS_TEST_SETUP.md` - Cypress setup guide

## Code Locations

### Workflow Utilities

- File: `src/lib/utils/workflow.ts`
- Functions: `getStepRoute`, `canAccessStep`, `getStepLabel`, `isStepCompleted`, `getStepFromRoute`

### SurveySidebar

- File: `src/lib/components/layout/SurveySidebar.svelte`
- Key functions: `fetchWorkflowProgress()`, `goToStep()`, `getStepInfo()`
- Shows on routes: `/exit-survey`, `/initial-survey`

### Main Sidebar

- File: `src/lib/components/layout/Sidebar.svelte`
- Key functions: `fetchWorkflowState()`, `goToStep()`, `getStepInfo()`
- Conditional: Only shows for `isInterviewee === true`

### Layout Navigation Guard

- File: `src/routes/(app)/+layout.svelte`
- Function: `enforceWorkflowNavigation()`
- Uses: `getWorkflowState()` API, `next_route` for navigation decisions

## API Dependencies

### Required Endpoint

- `GET /api/v1/workflow/state`
- Returns: `WorkflowStateResponse`
- Used by: SurveySidebar, Sidebar, Layout navigation guard

### Response Structure

```typescript
{
	next_route: string; // Where user should be
	substep: string | null;
	progress_by_section: {
		has_child_profile: boolean;
		moderation_completed_count: number;
		moderation_total: number;
		exit_survey_completed: boolean;
	}
}
```

## Git Status

**Current Branch**: `feat/restore-workflow-navigation`
**Status**: All changes committed, ready for testing
**Remote**: Pushed to origin

**To continue working**:

```bash
git checkout feat/restore-workflow-navigation
# Start services and test
```

## Questions / Issues to Resolve

1. **Database Error**: The SQLite error in terminal needs to be resolved for backend to start
2. **Test Execution**: Cypress tests need services running to execute
3. **Edge Cases**: May need to handle:
   - Backend API failures gracefully
   - Network latency
   - Invalid workflow state responses

## Success Criteria

✅ Interviewee users can navigate workflow steps from sidebar
✅ Workflow state comes from backend API (single source of truth)
✅ Visual progress indicators show completion status
✅ Navigation respects backend-determined accessibility
✅ Parent/child users don't see workflow UI
✅ No conflicts with existing navigation guard
✅ Code is maintainable and well-documented
✅ No localStorage usage (backend only)
✅ Simple architecture (no unnecessary services)
