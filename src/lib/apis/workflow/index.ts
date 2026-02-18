import { WEBUI_API_BASE_URL } from '$lib/constants';

export interface WorkflowResetResponse {
	status: string;
	new_attempt: number;
	message: string;
}

export interface CurrentAttemptResponse {
	current_attempt: number;
	moderation_attempt: number;
	child_attempt: number;
	exit_attempt: number;
}

export const resetUserWorkflow = async (token: string): Promise<WorkflowResetResponse> => {
	const res = await fetch(`${WEBUI_API_BASE_URL}/workflow/reset`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		}
	});
	if (!res.ok) throw await res.json();
	return res.json();
};

export const getCurrentAttempt = async (token: string): Promise<CurrentAttemptResponse> => {
	const res = await fetch(`${WEBUI_API_BASE_URL}/workflow/current-attempt`, {
		method: 'GET',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		}
	});
	if (!res.ok) throw await res.json();
	return res.json();
};

export interface ModerationResetResponse {
	status: string;
	new_attempt: number;
	completed_scenario_indices: number[];
	message: string;
}

export interface CompletedScenariosResponse {
	completed_scenario_indices: number[];
	count: number;
}

export interface StudyStatusResponse {
	completed_at: number | null;
	completion_date: string | null;
	can_retake: boolean;
	current_attempt: number;
	message: string;
}

export interface UserSubmissionsResponse {
	user_info: { id: string; name: string; email: string };
	child_profiles: any[];
	moderation_sessions: any[];
	exit_quiz_responses: any[];
	session_activity_totals?: Record<string, number>;
	assignment_time_totals?: Record<string, number>;
}

export interface WorkflowStateResponse {
	next_route: string;
	substep: string | null;
	progress_by_section: {
		instructions_completed?: boolean;
		has_child_profile: boolean;
		moderation_completed_count: number;
		moderation_total: number;
		exit_survey_completed: boolean;
	};
}

export const getWorkflowState = async (token: string): Promise<WorkflowStateResponse> => {
	const res = await fetch(`${WEBUI_API_BASE_URL}/workflow/state`, {
		method: 'GET',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		}
	});
	if (!res.ok) throw await res.json();
	return res.json();
};

export const markInstructionsComplete = async (
	token: string
): Promise<{ status: string; message: string }> => {
	const res = await fetch(`${WEBUI_API_BASE_URL}/workflow/instructions-complete`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		}
	});
	if (!res.ok) throw await res.json();
	return res.json();
};

export interface WorkflowDraftResponse {
	data: Record<string, unknown> | null;
	updated_at: number | null;
}

export const getWorkflowDraft = async (
	token: string,
	childId: string,
	draftType: 'exit_survey' | 'moderation'
): Promise<WorkflowDraftResponse> => {
	const res = await fetch(
		`${WEBUI_API_BASE_URL}/workflow/draft?child_id=${encodeURIComponent(childId)}&draft_type=${encodeURIComponent(draftType)}`,
		{
			method: 'GET',
			headers: {
				'Content-Type': 'application/json',
				Authorization: `Bearer ${token}`
			}
		}
	);
	const text = await res.text();
	if (!res.ok) {
		let msg = 'Failed to get draft';
		try {
			const err = JSON.parse(text) as { detail?: string };
			if (err.detail) msg = err.detail;
		} catch {
			// Server may have returned HTML (e.g. 500 error page)
		}
		throw new Error(msg);
	}
	try {
		return JSON.parse(text) as WorkflowDraftResponse;
	} catch {
		// Response was not JSON (e.g. HTML); return empty so callers don't break
		return { data: null, updated_at: null };
	}
};

export const saveWorkflowDraft = async (
	token: string,
	childId: string,
	draftType: 'exit_survey' | 'moderation',
	data: Record<string, unknown>
): Promise<WorkflowDraftResponse> => {
	const res = await fetch(`${WEBUI_API_BASE_URL}/workflow/draft`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify({ child_id: childId, draft_type: draftType, data })
	});
	const text = await res.text();
	if (!res.ok) {
		let msg = 'Failed to save draft';
		try {
			const err = JSON.parse(text) as { detail?: string };
			if (err.detail) msg = err.detail;
		} catch {
			// Server may have returned HTML (e.g. 500 error page)
		}
		throw new Error(msg);
	}
	try {
		return JSON.parse(text) as WorkflowDraftResponse;
	} catch {
		throw new Error('Invalid response from server');
	}
};

export const deleteWorkflowDraft = async (
	token: string,
	childId: string,
	draftType: 'exit_survey' | 'moderation'
): Promise<{ status: string; deleted: boolean }> => {
	const res = await fetch(
		`${WEBUI_API_BASE_URL}/workflow/draft?child_id=${encodeURIComponent(childId)}&draft_type=${encodeURIComponent(draftType)}`,
		{
			method: 'DELETE',
			headers: {
				'Content-Type': 'application/json',
				Authorization: `Bearer ${token}`
			}
		}
	);
	if (!res.ok) throw await res.json();
	return res.json();
};

export const finalizeModeration = async (
	token: string,
	payload: { child_id?: string; session_number?: number }
): Promise<{ updated: number }> => {
	const res = await fetch(`${WEBUI_API_BASE_URL}/workflow/moderation/finalize`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify(payload)
	});
	if (!res.ok) throw await res.json();
	return res.json();
};

export const resetModerationWorkflow = async (token: string): Promise<ModerationResetResponse> => {
	const res = await fetch(`${WEBUI_API_BASE_URL}/workflow/reset-moderation`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		}
	});
	if (!res.ok) throw await res.json();
	return res.json();
};

export const getCompletedScenarios = async (token: string): Promise<CompletedScenariosResponse> => {
	const res = await fetch(`${WEBUI_API_BASE_URL}/workflow/completed-scenarios`, {
		method: 'GET',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		}
	});
	if (!res.ok) throw await res.json();
	return res.json();
};

export const getStudyStatus = async (token: string): Promise<StudyStatusResponse> => {
	const res = await fetch(`${WEBUI_API_BASE_URL}/workflow/study-status`, {
		method: 'GET',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		}
	});
	if (!res.ok) throw await res.json();
	return res.json();
};

export const getUserSubmissions = async (
	token: string,
	userId: string
): Promise<UserSubmissionsResponse> => {
	const res = await fetch(`${WEBUI_API_BASE_URL}/workflow/admin/user-submissions/${userId}`, {
		method: 'GET',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		}
	});
	if (!res.ok) throw await res.json();
	return res.json();
};
