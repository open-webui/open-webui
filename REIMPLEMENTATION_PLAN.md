# Re-Implementation Plan: Restoring Lost Survey Workflow Functionality

## Overview

This plan outlines how to restore the survey workflow management functionality that was removed from the Sidebar component, while maintaining the current architecture's user type differentiation and non-blocking behavior for parent/child users.

## Goals

1. **Restore workflow navigation** - Allow users to navigate between workflow steps from the sidebar
2. **Restore workflow state management** - Track assignment steps, unlock flags, and completion status
3. **Restore visual progress indicators** - Show clickable workflow steps with completion indicators
4. **Maintain current architecture** - Work with user type differentiation, SurveySidebar, and existing services
5. **Preserve non-blocking behavior** - Only show workflow UI for interviewee users

---

## Architecture Decisions

### 1. Where to Implement

**Option A: Enhance SurveySidebar (Recommended)**

- ✅ Already shows progress indicators
- ✅ Only displayed on survey routes
- ✅ Has workflow state fetching
- ❌ Currently only shows on survey routes, not in main Sidebar

**Option B: Add to Main Sidebar**

- ✅ Always visible for interviewee users
- ✅ Can show workflow steps alongside chat list
- ❌ Would need conditional rendering based on user type
- ❌ Might clutter sidebar for non-interviewee users

**Option C: Hybrid Approach (RECOMMENDED)**

- Add workflow navigation to **SurveySidebar** (for survey routes)
- Add workflow navigation section to **main Sidebar** (for interviewee users on non-survey routes)
- Both use shared workflow state management service

**Decision: Option C - Hybrid Approach**

### 2. State Management Strategy

**Decision: Backend API Only (No localStorage)**

- ✅ **Backend is the single source of truth** - No sync issues
- ✅ Always accurate and up-to-date
- ✅ Cross-device synchronization
- ✅ Simpler architecture (no localStorage management)
- ⚠️ Requires network connection
- ⚠️ May need caching strategy to avoid excessive API calls

**No localStorage usage** - All state comes from backend API calls to `getWorkflowState()`.

### 3. User Type Handling

- **Interviewee users**: Show full workflow navigation and state management
- **Parent/Child users**: Hide workflow UI (they have separate workflows)
- **Admin users**: Can see workflow UI if needed (optional)

---

## Implementation Plan

## Phase 1: Determine if Centralized Service is Needed

### 1.1 Analysis: Do We Need a Service?

**Current Situation:**

- SurveySidebar already calls `getWorkflowState()` API directly
- Each component manages its own state
- No shared state between components

**Question: Do we need a centralized service?**

**Arguments FOR a service:**

1. **Avoid duplicate API calls** - If both SurveySidebar and Sidebar are visible simultaneously, they'd both call the API
2. **Shared reactive store** - Multiple components could react to state changes
3. **Centralized helper functions** - `getStepRoute()`, `canAccessStep()`, etc. in one place
4. **Caching** - Service could cache API response and refresh when needed

**Arguments AGAINST a service:**

1. **Components are mutually exclusive** - SurveySidebar shows on survey routes, Sidebar shows on other routes. They're never visible at the same time.
2. **Simplicity** - Each component calling API directly is simpler
3. **No shared state needed** - If components aren't visible simultaneously, no need to share state
4. **Less abstraction** - Easier to understand and maintain

**Decision: NO SERVICE NEEDED (Use Utility Functions Instead)**

### Why No Service is Needed:

1. **Components are Mutually Exclusive**
   - SurveySidebar only shows on survey routes (`/exit-survey`, `/initial-survey`)
   - Main Sidebar shows on all other routes
   - They are **never visible at the same time**
   - Therefore, no need to share state between them

2. **Backend is Source of Truth**
   - Each component can call `getWorkflowState()` API directly
   - Backend always has the latest state
   - No risk of state getting out of sync
   - Simpler than managing local state + sync

3. **No Cross-Component Reactivity Needed**
   - Since components aren't visible simultaneously, one component doesn't need to react to changes in the other
   - Each component manages its own state independently
   - No need for reactive Svelte stores

4. **What We DO Need: Utility Functions**
   - Shared navigation logic: `getStepRoute()`, `canAccessStep()`, etc.
   - These are pure functions, not state management
   - Can be in a simple utility file

### When Would We Need a Service?

A service would be beneficial if:

- Both sidebars were visible simultaneously
- We needed cross-tab synchronization
- We needed to cache API responses to avoid duplicate calls
- Multiple components needed to react to the same state changes

**Since none of these apply, utility functions are sufficient.**

### Alternative: Simple Caching (If Needed Later)

If we later find we're making too many API calls, we could add a simple caching layer:

```typescript
// Simple cache, not a full service
let cachedState: WorkflowStateResponse | null = null;
let cacheTimestamp = 0;
const CACHE_TTL = 5000; // 5 seconds

export async function getCachedWorkflowState(token: string): Promise<WorkflowStateResponse> {
	const now = Date.now();
	if (cachedState && now - cacheTimestamp < CACHE_TTL) {
		return cachedState;
	}

	cachedState = await getWorkflowState(token);
	cacheTimestamp = now;
	return cachedState;
}
```

But this is only needed if we see performance issues. Start simple.

### 1.2 Create Workflow Navigation Utilities

**Location**: `src/lib/utils/workflow.ts`

**Purpose**: Shared utility functions for workflow navigation logic. No state management - just helper functions.

**Implementation**:

```typescript
// src/lib/utils/workflow.ts

/**
 * Get the route for a workflow step
 */
export function getStepRoute(step: number): string {
	switch (step) {
		case 1:
			return '/kids/profile';
		case 2:
			return '/moderation-scenario';
		case 3:
			return '/exit-survey';
		case 4:
			return '/completion';
		default:
			return '/assignment-instructions';
	}
}

/**
 * Get step number from route
 */
export function getStepFromRoute(route: string): number {
	if (route.startsWith('/kids/profile')) return 1;
	if (route.startsWith('/moderation-scenario')) return 2;
	if (route.startsWith('/exit-survey')) return 3;
	if (route.startsWith('/completion')) return 4;
	return 0;
}

/**
 * Determine if a step is accessible based on workflow state
 * Note: This uses the backend workflow state response structure
 */
export function canAccessStep(
	step: number,
	workflowState: {
		progress_by_section: {
			has_child_profile: boolean;
			moderation_completed_count: number;
			moderation_total: number;
			exit_survey_completed: boolean;
		};
		next_route: string;
	}
): boolean {
	const { progress_by_section, next_route } = workflowState;

	// Step 1: Child Profile - accessible if instructions completed
	if (step === 1) {
		// Check if next_route indicates step 1 is available
		return next_route === '/kids/profile' || progress_by_section.has_child_profile;
	}

	// Step 2: Moderation - accessible if child profile completed
	if (step === 2) {
		return progress_by_section.has_child_profile;
	}

	// Step 3: Exit Survey - accessible if moderation completed
	if (step === 3) {
		return progress_by_section.moderation_completed_count >= progress_by_section.moderation_total;
	}

	// Step 4: Completion - accessible if exit survey completed
	if (step === 4) {
		return progress_by_section.exit_survey_completed;
	}

	return false;
}

/**
 * Get step label for display
 */
export function getStepLabel(step: number): string {
	switch (step) {
		case 1:
			return 'Child Profile';
		case 2:
			return 'Moderation';
		case 3:
			return 'Exit Survey';
		case 4:
			return 'Completion';
		default:
			return 'Unknown';
	}
}
```

**Tasks**:

- [ ] Create utility file
- [ ] Implement navigation helpers
- [ ] Add step accessibility logic
- [ ] Write unit tests

---

## Phase 2: Enhance SurveySidebar with Navigation

### 2.1 Add Clickable Step Navigation

**Location**: `src/lib/components/layout/SurveySidebar.svelte`

**Changes**:

1. Import `workflowStateService`
2. Make progress indicators clickable
3. Add navigation functions
4. Show step numbers and completion status
5. Add visual indicators for current step

**Implementation**:

```svelte
<script lang="ts">
	// ... existing imports ...
	import { getWorkflowState } from '$lib/apis/workflow';
	import { getStepRoute, canAccessStep, getStepLabel } from '$lib/utils/workflow';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { toast } from 'svelte-sonner';

	// ... existing code ...

	// Workflow state from backend API (already exists)
	let workflowProgress: WorkflowStateResponse | null = null;
	let loadingProgress = true;

	// Refresh workflow state
	async function refreshWorkflowState() {
		try {
			if (!localStorage.token) return;
			const state = await getWorkflowState(localStorage.token);
			workflowProgress = state;
		} catch (error) {
			console.error('Failed to fetch workflow progress:', error);
			workflowProgress = null;
		} finally {
			loadingProgress = false;
		}
	}

	// Navigation function
	async function goToStep(step: number) {
		if (!workflowProgress) {
			await refreshWorkflowState();
		}

		if (!workflowProgress || !canAccessStep(step, workflowProgress)) {
			toast.error('This step is not yet available');
			return;
		}

		const route = getStepRoute(step);
		await goto(route);

		// Refresh state after navigation
		await refreshWorkflowState();
	}

	// Get step display info
	function getStepInfo(step: number) {
		if (!workflowProgress) {
			return {
				route: getStepRoute(step),
				isCurrentStep: false,
				isCompleted: false,
				canAccess: false,
				label: getStepLabel(step)
			};
		}

		const route = getStepRoute(step);
		const currentRoute = $page.url.pathname;
		const isCurrentStep = route === currentRoute || currentRoute.startsWith(route);
		const canAccess = canAccessStep(step, workflowProgress);

		// Determine completion status from workflow progress
		let isCompleted = false;
		if (step === 1) {
			isCompleted = workflowProgress.progress_by_section.has_child_profile;
		} else if (step === 2) {
			isCompleted =
				workflowProgress.progress_by_section.moderation_completed_count >=
				workflowProgress.progress_by_section.moderation_total;
		} else if (step === 3) {
			isCompleted = workflowProgress.progress_by_section.exit_survey_completed;
		} else if (step === 4) {
			isCompleted = workflowProgress.progress_by_section.exit_survey_completed;
		}

		return {
			route,
			isCurrentStep,
			isCompleted,
			canAccess,
			label: getStepLabel(step)
		};
	}

	// Refresh on mount and when route changes
	onMount(() => {
		refreshWorkflowState();
	});

	// Refresh when route changes
	$: if ($page.url.pathname) {
		refreshWorkflowState();
	}
</script>

<!-- In template, replace static progress indicators with clickable buttons -->
<div class="space-y-3">
	<!-- Step 1: Child Profile -->
	{@const step1 = getStepInfo(1)}
	<button
		on:click={() => goToStep(1)}
		disabled={!step1.canAccess}
		class="flex items-center gap-2 w-full px-3 py-2 rounded-xl transition {step1.isCurrentStep
			? 'bg-blue-100 dark:bg-blue-900'
			: step1.canAccess
				? 'hover:bg-gray-50 dark:hover:bg-gray-800'
				: 'opacity-50 cursor-not-allowed'}"
	>
		<div
			class="size-5 rounded-full flex items-center justify-center {step1.isCompleted
				? 'bg-green-500'
				: step1.isCurrentStep
					? 'bg-blue-500'
					: 'bg-gray-300 dark:bg-gray-600'}"
		>
			{#if step1.isCompleted}
				<svg class="size-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"
					></path>
				</svg>
			{:else}
				<span class="text-xs font-bold text-white">1</span>
			{/if}
		</div>
		<span class="text-sm text-gray-700 dark:text-gray-300">{$i18n.t('Child Profile')}</span>
	</button>

	<!-- Repeat for steps 2, 3, 4 -->
</div>
```

**Tasks**:

- [ ] Import workflowStateService
- [ ] Add user type check
- [ ] Make progress indicators clickable
- [ ] Add navigation functions
- [ ] Add visual indicators (current step, completed, locked)
- [ ] Add step labels
- [ ] Test navigation flow

---

## Phase 3: Add Workflow Navigation to Main Sidebar

### 3.1 Conditional Workflow Section

**Location**: `src/lib/components/layout/Sidebar.svelte`

**Changes**:

1. Import `workflowStateService` and `getUserType`
2. Add conditional workflow section (only for interviewee users)
3. Add workflow step navigation buttons
4. Show workflow progress

**Implementation**:

```svelte
<script lang="ts">
	// ... existing imports ...
	import { getWorkflowState } from '$lib/apis/workflow';
	import { getStepRoute, canAccessStep, getStepLabel } from '$lib/utils/workflow';
	import { getUserType } from '$lib/utils';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { toast } from 'svelte-sonner';

	// ... existing code ...

	// User type and workflow state
	let userType = 'user';
	let workflowProgress: WorkflowStateResponse | null = null;
	let loadingWorkflow = false;
	$: isInterviewee = userType === 'interviewee';

	// Fetch workflow state from backend
	async function fetchWorkflowState() {
		if (!isInterviewee || !localStorage.token) return;

		loadingWorkflow = true;
		try {
			workflowProgress = await getWorkflowState(localStorage.token);
		} catch (error) {
			console.error('Failed to fetch workflow state:', error);
			workflowProgress = null;
		} finally {
			loadingWorkflow = false;
		}
	}

	// Navigation function
	async function goToStep(step: number) {
		if (!workflowProgress) {
			await fetchWorkflowState();
		}

		if (!workflowProgress || !canAccessStep(step, workflowProgress)) {
			toast.error('This step is not yet available');
			return;
		}

		const route = getStepRoute(step);
		await goto(route);

		// Refresh state after navigation
		await fetchWorkflowState();
	}

	// Get step info (same as SurveySidebar)
	function getStepInfo(step: number) {
		// ... same implementation as SurveySidebar ...
	}

	onMount(async () => {
		if ($user) {
			userType = await getUserType($user);
			if (isInterviewee) {
				await fetchWorkflowState();
			}
		}
	});

	// Refresh when route changes
	$: if (isInterviewee && $page.url.pathname) {
		fetchWorkflowState();
	}
</script>

<!-- In template, add workflow section after header, before chat list -->
{#if isInterviewee}
	<div class="px-4 py-3 border-b border-gray-200 dark:border-gray-800">
		<div
			class="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-3"
		>
			{$i18n.t('Assignment Workflow')}
		</div>
		<div class="space-y-2">
			<!-- Step navigation buttons (same as SurveySidebar) -->
		</div>
	</div>
{/if}
```

**Tasks**:

- [ ] Import workflow utilities and API
- [ ] Add user type detection
- [ ] Add conditional workflow section
- [ ] Fetch workflow state from backend
- [ ] Add step navigation buttons
- [ ] Style to match existing sidebar
- [ ] Test with interviewee users
- [ ] Verify hidden for parent/child users

---

## Phase 4: Integrate with Layout Navigation Guard

### 4.1 Update `enforceWorkflowNavigation`

**Location**: `src/routes/(app)/+layout.svelte`

**Changes**:

1. Use `workflowStateService` instead of direct localStorage access
2. Sync state when navigation occurs
3. Update step based on route

**Implementation**:

```typescript
import { getWorkflowState } from '$lib/apis/workflow';
import { getStepFromRoute } from '$lib/utils/workflow';

const enforceWorkflowNavigation = async () => {
	// ... existing guard logic ...

	// Get workflow state from backend API
	let workflowState = null;
	try {
		if (localStorage.token) {
			workflowState = await getWorkflowState(localStorage.token);
		}
	} catch (error) {
		console.error('Failed to fetch workflow state:', error);
	}

	// Use backend state for navigation decisions
	// The backend API already provides next_route, so we can use that
	if (workflowState?.next_route) {
		const currentPath = $page.url.pathname;
		const nextRoute = workflowState.next_route;

		// If user is not on the correct route, redirect
		if (currentPath !== nextRoute && !currentPath.startsWith(nextRoute)) {
			await goto(nextRoute);
			return;
		}
	}

	// ... rest of navigation logic using workflowState ...
};
```

**Note**: The backend API's `next_route` field already tells us where the user should be, so we don't need to track steps locally.

**Tasks**:

- [ ] Import workflow API and utilities
- [ ] Replace localStorage reads with backend API calls
- [ ] Use `next_route` from backend for navigation
- [ ] Test navigation flow
- [ ] Verify backend state is source of truth

---

## Phase 5: Restore Child Profile Management (Optional)

### 5.1 Add Child Profile Display to Sidebar

**Location**: `src/lib/components/layout/Sidebar.svelte`

**Note**: Child profiles are already managed by `childProfileSync` service. We just need to display them in the sidebar for interviewee users.

**Implementation**:

```svelte
<script lang="ts">
	import { childProfileSync } from '$lib/services/childProfileSync';

	let childProfiles: ChildProfile[] = [];
	let currentChild: ChildProfile | null = null;

	onMount(async () => {
		if (isInterviewee) {
			childProfiles = await childProfileSync.getChildProfiles();
			const currentChildId = childProfileSync.getCurrentChildId();
			currentChild = childProfiles.find((c) => c.id === currentChildId) || null;
		}
	});
</script>

<!-- In workflow section -->
{#if isInterviewee && currentChild}
	<div class="mb-3 p-2 bg-gray-50 dark:bg-gray-800 rounded-lg">
		<div class="text-xs text-gray-500 dark:text-gray-400 mb-1">Current Child Profile</div>
		<div class="text-sm font-medium">{currentChild.name}</div>
	</div>
{/if}
```

**Tasks**:

- [ ] Import childProfileSync
- [ ] Load child profiles for interviewee users
- [ ] Display current child profile
- [ ] Add child profile selector (if needed)
- [ ] Test child profile display

---

## Phase 6: Restore Personal Store (If Needed)

### 6.1 Determine if Personal Store is Still Needed

**Decision Point**: Check if Personal Store functionality is still used elsewhere in the codebase.

**If Needed**:

- Add Personal Store button to Sidebar
- Integrate with existing Personal Store component (if it exists)
- Or create new Personal Store component

**If Not Needed**:

- Document that this feature was intentionally removed
- Skip this phase

**Tasks**:

- [ ] Search codebase for Personal Store usage
- [ ] Determine if feature is still needed
- [ ] If needed, implement Personal Store integration
- [ ] If not needed, document removal

---

## Implementation Status

✅ **Phase 1**: Workflow utility functions created
✅ **Phase 2**: SurveySidebar enhanced with clickable navigation
✅ **Phase 3**: Main Sidebar workflow navigation added
✅ **Phase 4**: Layout navigation guard updated to use backend API
✅ **Phase 7**: Cypress tests created

## Phase 7: Cypress Testing

### 7.1 Cypress Test Setup

**Reference**: See `docs/CYPRESS_TEST_SETUP.md` for complete setup instructions.

**Prerequisites**:

- Node.js v20.x (recommended for Cypress compatibility)
- Backend running on port 8080
- Frontend running (typically port 5173 or 5174)
- Test account credentials (default: `jjdrisco@ucsd.edu` / `0000`)

**Running Tests**:

```bash
# Set environment variables
export RUN_CHILD_PROFILE_TESTS=1
export CYPRESS_baseUrl=http://localhost:5173  # Use your frontend port

# Run workflow tests
xvfb-run -a npx cypress run --headless --spec cypress/e2e/workflow.cy.ts

# Run survey sidebar tests
xvfb-run -a npx cypress run --headless --spec cypress/e2e/survey-sidebar.cy.ts

# Run all workflow-related tests
xvfb-run -a npx cypress run --headless --spec "cypress/e2e/workflow.cy.ts,cypress/e2e/survey-sidebar.cy.ts"
```

### 7.2 New Cypress Tests to Create

**File**: `cypress/e2e/workflow-navigation.cy.ts`

**Test Coverage**:

1. **Workflow Step Navigation from SurveySidebar**
   - [ ] Can click on Child Profile step when accessible
   - [ ] Can click on Moderation step when accessible
   - [ ] Can click on Exit Survey step when accessible
   - [ ] Cannot click on locked steps (shows error toast)
   - [ ] Navigation updates URL correctly
   - [ ] Step indicators update after navigation

2. **Workflow Step Navigation from Main Sidebar**
   - [ ] Workflow section appears for interviewee users
   - [ ] Workflow section hidden for parent/child users
   - [ ] Can navigate to steps from main sidebar
   - [ ] Step indicators show correct state

3. **Workflow State Display**
   - [ ] Progress indicators show completion status
   - [ ] Current step is highlighted
   - [ ] Completed steps show checkmark
   - [ ] Locked steps are disabled

4. **Backend API Integration**
   - [ ] Workflow state fetched from backend on mount
   - [ ] State refreshes after navigation
   - [ ] State updates when completing steps
   - [ ] Error handling when backend unavailable

### 7.3 Update Existing Tests

**File**: `cypress/e2e/workflow.cy.ts`

- [ ] Verify workflow state API returns correct `next_route`
- [ ] Verify workflow state transitions work correctly
- [ ] Verify navigation respects backend state

**File**: `cypress/e2e/survey-sidebar.cy.ts`

- [ ] Verify clickable step buttons exist
- [ ] Verify step navigation works
- [ ] Verify progress indicators update

### 7.4 Test Implementation Pattern

Following the existing test patterns from `workflow.cy.ts`:

```typescript
// cypress/e2e/workflow-navigation.cy.ts
describe('Workflow Navigation', () => {
	function getCredentials() {
		return {
			email: Cypress.env('INTERVIEWEE_EMAIL') || 'jjdrisco@ucsd.edu',
			password: Cypress.env('INTERVIEWEE_PASSWORD') || '0000'
		};
	}

	function authenticate() {
		// Use same authentication pattern as workflow.cy.ts
		// ...
	}

	beforeEach(() => {
		authenticate();
		cy.visit('/');
	});

	it('should navigate to workflow steps from SurveySidebar', () => {
		// Navigate to exit-survey page
		cy.visit('/exit-survey');

		// Wait for SurveySidebar to load
		cy.get('#survey-sidebar-nav', { timeout: 10000 }).should('exist');

		// Click on Child Profile step (if accessible)
		cy.get('[data-step="1"]').should('exist');
		// ... test navigation
	});

	it('should show workflow navigation in main Sidebar for interviewee users', () => {
		cy.visit('/');

		// Open sidebar
		cy.get('#sidebar-toggle-button').click();

		// Check for workflow section
		cy.contains('Assignment Workflow').should('exist');

		// Verify step buttons exist
		cy.get('[data-step="1"]').should('exist');
	});
});
```

### 7.5 Manual Test Cases

1. **Workflow State Management**
   - [ ] State fetched from backend on component mount
   - [ ] State refreshes after navigation
   - [ ] State updates when completing workflow steps
   - [ ] Error handling when backend unavailable

2. **Navigation**
   - [ ] Can navigate to accessible steps
   - [ ] Cannot navigate to locked steps (shows error)
   - [ ] Navigation updates URL correctly
   - [ ] Navigation works from both sidebars

3. **User Type Differentiation**
   - [ ] Interviewee users see workflow UI
   - [ ] Parent users don't see workflow UI
   - [ ] Child users don't see workflow UI

4. **Visual Indicators**
   - [ ] Completed steps show checkmark
   - [ ] Current step is highlighted
   - [ ] Locked steps are disabled
   - [ ] Step numbers display correctly

5. **Integration**
   - [ ] Works with layout navigation guard
   - [ ] Works with SurveySidebar
   - [ ] Works with main Sidebar
   - [ ] No conflicts between components

### 7.6 Edge Cases

- [ ] What happens if backend is unavailable? (Show error state, allow navigation to accessible routes)
- [ ] What happens if user switches tabs mid-navigation? (State should refresh)
- [ ] What happens if workflow state is invalid? (Handle gracefully)
- [ ] What happens if user is logged out mid-workflow? (Redirect to auth)

### 7.7 Running All Tests

```bash
# Ensure backend and frontend are running
# Backend: cd backend && ./start.sh
# Frontend: npm run dev

# Set environment
export RUN_CHILD_PROFILE_TESTS=1
export CYPRESS_baseUrl=http://localhost:5173

# Run all workflow-related tests
xvfb-run -a npx cypress run --headless --spec "cypress/e2e/workflow.cy.ts,cypress/e2e/survey-sidebar.cy.ts,cypress/e2e/workflow-navigation.cy.ts"
```

---

## Phase 8: Documentation

### 8.1 Update Documentation

- [ ] Document workflowStateService API
- [ ] Document workflow navigation patterns
- [ ] Update user guide for workflow navigation
- [ ] Add code comments
- [ ] Update architecture docs

---

## Implementation Order

1. **Phase 1** - Create workflow utility functions (Foundation - no service needed)
2. **Phase 2** - Enhance SurveySidebar (Quick win, already exists)
3. **Phase 3** - Add to main Sidebar (User-facing feature)
4. **Phase 4** - Integrate with layout (Use backend API)
5. **Phase 5** - Child profile display (Nice to have)
6. **Phase 6** - Personal Store (If needed)
7. **Phase 7** - Testing
8. **Phase 8** - Documentation

---

## Success Criteria

✅ Interviewee users can navigate workflow steps from sidebar
✅ Workflow state comes from backend API (single source of truth)
✅ Visual progress indicators show completion status
✅ Navigation respects backend-determined accessibility
✅ State is always accurate (no sync issues)
✅ Parent/child users don't see workflow UI
✅ No conflicts with existing navigation guard
✅ Code is maintainable and well-documented
✅ No localStorage usage (backend only)
✅ Simple architecture (no unnecessary services)

---

## Risks & Mitigations

| Risk                       | Impact | Mitigation                                                                                                         |
| -------------------------- | ------ | ------------------------------------------------------------------------------------------------------------------ |
| Excessive API calls        | Medium | Each component calls API independently, but they're mutually exclusive. Consider simple in-memory cache if needed. |
| Network latency            | Medium | Show loading states, cache responses in component state                                                            |
| User confusion             | Medium | Clear visual indicators, tooltips                                                                                  |
| Breaking existing features | High   | Thorough testing, gradual rollout                                                                                  |
| Backend unavailable        | Medium | Show error state, allow navigation to accessible routes                                                            |

---

## Estimated Timeline

- **Phase 1**: 1 day (utility functions only, no service)
- **Phase 2**: 1-2 days
- **Phase 3**: 2-3 days
- **Phase 4**: 1 day (simpler without localStorage)
- **Phase 5**: 1 day (optional)
- **Phase 6**: 1-2 days (if needed)
- **Phase 7**: 2-3 days
- **Phase 8**: 1 day

**Total**: 9-14 days (excluding optional phases)

**Reduced timeline** because:

- No service to build and maintain
- No localStorage sync logic
- Simpler architecture

---

## Notes

- **No localStorage usage** - Backend API is the single source of truth
- **No centralized service** - Components call API directly (they're mutually exclusive)
- **Utility functions only** - Shared navigation helpers, no state management
- This plan maintains backward compatibility
- All changes are additive (no breaking changes)
- User type differentiation is preserved
- Non-blocking behavior for parent/child users is maintained
- The implementation can be done incrementally
- Simpler architecture than original plan (no service, no localStorage)
