import type { WorkflowStateResponse } from '$lib/apis/workflow/index';

/**
 * Get the route for a workflow step
 */
export function getStepRoute(step: number): string {
	switch (step) {
		case 0:
			return '/assignment-instructions';
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
	if (route.startsWith('/assignment-instructions')) return 0;
	if (route.startsWith('/kids/profile')) return 1;
	if (route.startsWith('/moderation-scenario')) return 2;
	if (route.startsWith('/exit-survey')) return 3;
	if (route.startsWith('/completion')) return 4;
	return 0;
}

/**
 * Determine if a step is accessible based on workflow state
 * Uses the backend workflow state response structure
 * Users can navigate to:
 * - Their current step (next_route)
 * - Any previous completed steps
 * - Not future steps
 */
export function canAccessStep(step: number, workflowState: WorkflowStateResponse): boolean {
	const progress = workflowState?.progress_by_section;
	const next_route = workflowState?.next_route ?? '';
	if (!progress || !next_route) return false;

	const stepRoute = getStepRoute(step);

	// If this is the next_route, it's always accessible
	if (next_route === stepRoute || next_route.startsWith(stepRoute)) {
		return true;
	}

	// Check if step is completed - completed steps are always accessible
	const isCompleted = isStepCompleted(step, workflowState);
	if (isCompleted) {
		return true;
	}

	// Step 0: Assignment Instructions - always accessible
	if (step === 0) {
		return true;
	}

	// Step 1: Child Profile - accessible when instructions completed OR if a child profile already exists
	if (step === 1) {
		return !!progress?.instructions_completed || !!progress?.has_child_profile;
	}

	// Step 2: Moderation - accessible if child profile is completed and (moderation is current/next or we're past it)
	if (step === 2) {
		if (!progress.has_child_profile) {
			return false;
		}
		return (
			next_route === '/moderation-scenario' ||
			next_route === '/exit-survey' ||
			next_route === '/completion'
		);
	}

	// Step 3: Exit Survey - only accessible after all moderation scenarios are done (or exit survey already completed)
	if (step === 3) {
		if (progress.exit_survey_completed) {
			return true;
		}
		const count = progress.moderation_completed_count ?? 0;
		const total = progress.moderation_total ?? 0;
		// Require at least one scenario and all completed before allowing exit survey
		if (total === 0 || count < total) {
			return false;
		}
		return next_route === '/exit-survey' || next_route === '/completion';
	}

	// Step 4: Completion - accessible if exit survey is completed
	if (step === 4) {
		return !!progress.exit_survey_completed || next_route === '/completion';
	}

	return false;
}

/**
 * Get step label for display
 */
export function getStepLabel(step: number): string {
	switch (step) {
		case 0:
			return 'Assignment Instructions';
		case 1:
			return 'Child Profile';
		case 2:
			return 'Scenario Review';
		case 3:
			return 'Exit Survey';
		case 4:
			return 'Completion';
		default:
			return 'Unknown';
	}
}

/**
 * Check if a step is completed based on workflow state
 */
export function isStepCompleted(step: number, workflowState: WorkflowStateResponse): boolean {
	const progress = workflowState?.progress_by_section;
	const next_route = workflowState?.next_route ?? '';

	if (step === 0) {
		// Instructions completed from backend
		return !!progress?.instructions_completed;
	}
	if (step === 1) {
		return !!progress?.has_child_profile;
	}
	if (step === 2) {
		// Step 2 is completed when the user has clicked "Done" (moderation_finalized)
		return !!(progress as any).moderation_finalized;
	}
	if (step === 3 || step === 4) {
		return !!progress.exit_survey_completed;
	}
	return false;
}
