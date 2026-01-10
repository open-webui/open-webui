import { WEBUI_API_BASE_URL } from '$lib/constants';

export interface ModerationRequest {
	moderation_types: string[];  // Changed to array for multiple selections
	child_prompt?: string;
	model?: string;
	max_chars?: number;
}

export interface ModerationResponse {
	moderation_types: string[];  // Updated to match Viki's new response structure
	refactored_response: string;
	system_prompt_rule: string;
	model: string;
	child_prompt: string;
}

export interface ModerationSessionPayload {
  session_id?: string;  // For updates
  user_id: string;
  child_id: string;
  scenario_index: number;
  attempt_number: number;
  version_number: number;
  session_number?: number;
  scenario_prompt: string;
  original_response: string;
  initial_decision?: 'accept_original' | 'moderate' | 'not_applicable';
  concern_level?: number;
  concern_reason?: string;
  satisfaction_level?: number;
  satisfaction_reason?: string;
  next_action?: 'try_again' | 'move_on';
  decided_at?: number;
  highlights_saved_at?: number;
  saved_at?: number;
  strategies?: string[];
  custom_instructions?: string[];  // Simplified from {id, text}[] to string[]
  highlighted_texts?: string[];
  refactored_response?: string;
  is_final_version?: boolean;
  session_metadata?: Record<string, any>;
  // Attention check tracking
  is_attention_check?: boolean;
  attention_check_selected?: boolean;
  attention_check_passed?: boolean;
}

export interface ModerationSessionResponse {
  id: string;
  user_id: string;
  child_id: string;
  scenario_index: number;
  attempt_number: number;
  version_number: number;
  session_number?: number;
  scenario_prompt: string;
  original_response: string;
  initial_decision?: string;
  is_final_version: boolean;
  concern_level?: number;
  concern_reason?: string;
  satisfaction_level?: number;
  satisfaction_reason?: string;
  next_action?: string;
  decided_at?: number;
  highlights_saved_at?: number;
  saved_at?: number;
  strategies?: string[];
  custom_instructions?: string[];
  highlighted_texts?: string[];
  refactored_response?: string;
  session_metadata?: Record<string, any>;
  is_attention_check: boolean;
  attention_check_selected: boolean;
  attention_check_passed: boolean;
  created_at: number;
  updated_at: number;
}

export interface SessionActivityPayload {
  user_id: string;
  child_id: string;
  session_number: number;
  active_ms_cumulative: number;
}

export interface SessionActivityResponse {
  id: string;
  user_id: string;
  child_id: string;
  session_number: number;
  active_ms_delta: number;
  cumulative_ms: number;
  created_at: number;
}

export const postSessionActivity = async (token: string, payload: SessionActivityPayload): Promise<SessionActivityResponse> => {
  const res = await fetch(`${WEBUI_API_BASE_URL}/moderation/session-activity`, {
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

// New simplified API functions
export const saveModerationSession = async (token: string, payload: ModerationSessionPayload): Promise<ModerationSessionResponse> => {
  const res = await fetch(`${WEBUI_API_BASE_URL}/moderation/sessions`, {
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

export const getModerationSessions = async (token: string, child_id?: string): Promise<ModerationSessionResponse[]> => {
  const url = new URL(`${WEBUI_API_BASE_URL}/moderation/sessions`);
  if (child_id) url.searchParams.set('child_id', child_id);

  const res = await fetch(url.toString(), {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`
    }
  });
  if (!res.ok) throw await res.json();
  return res.json();
};

export const getModerationSession = async (token: string, session_id: string): Promise<ModerationSessionResponse> => {
  const res = await fetch(`${WEBUI_API_BASE_URL}/moderation/sessions/${session_id}`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`
    }
  });
  if (!res.ok) throw await res.json();
  return res.json();
};

export const deleteModerationSession = async (token: string, session_id: string): Promise<void> => {
  const res = await fetch(`${WEBUI_API_BASE_URL}/moderation/sessions/${session_id}`, {
    method: 'DELETE',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`
    }
  });
  if (!res.ok) throw await res.json();
};

// Keep the existing moderation apply function for generating responses
export const applyModeration = async (
	token: string,
	moderationTypes: string[],  // Standard moderation types
	childPrompt: string,  // Required: child's prompt/question
	customInstructions?: string[],  // Optional custom instruction texts
	originalResponse?: string,  // For refactoring mode
	highlightedTexts?: string[],  // Phrases parent flagged
	childAge?: string  // Child's age for age-appropriate moderation
): Promise<ModerationResponse | null> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/moderation/apply`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			moderation_types: moderationTypes,
			child_prompt: childPrompt,
			model: 'gpt-5.2-pro-2025-12-11',
			max_chars: 600,
			custom_instructions: customInstructions || [],  // Send custom instructions array
			original_response: originalResponse || null,  // Optional: for refactoring mode
			highlighted_texts: highlightedTexts || [],  // Optional: flagged texts
			child_age: childAge || null  // Optional: child's age for "Tailor to Age Group" strategy
		})
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			error = err;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const generateFollowUpPrompt = async (
	token: string,
	originalPrompt: string,
	moderatedResponse: string
): Promise<string> => {
	const res = await fetch(`${WEBUI_API_BASE_URL}/moderation/generate-followup`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			original_prompt: originalPrompt,
			moderated_response: moderatedResponse
		})
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.then((data) => data.followup_prompt)
		.catch((err) => {
			console.error(err);
			throw err;
		});

	return res;
};

// New scenario assignment APIs

export interface ScenarioAssignRequest {
	participant_id: string;
	child_profile_id?: string;
	assignment_position?: number;
	alpha?: number;  // Weighted sampling alpha parameter (default: 1.0)
}

export interface ScenarioAssignResponse {
	assignment_id: string;
	scenario_id: string;
	prompt_text: string;
	response_text: string;
	assignment_position?: number;
	sampling_audit?: {
		eligible_pool_size: number;
		n_assigned_before: number;
		weight: number;
		sampling_prob: number;
	};
}

export interface ScenarioStatusUpdateRequest {
	assignment_id: string;
	skip_stage?: string;
	skip_reason?: string;
	skip_reason_text?: string;
}

export interface ScenarioStatusResponse {
	status: string;
	assignment_id: string;
	issue_any?: number;  // For completed status
	reassigned?: boolean;  // For abandoned status
	new_assignment_id?: string;  // For abandoned status with reassignment
	new_scenario_id?: string;  // For abandoned status with reassignment
	new_prompt_text?: string;  // For abandoned status with reassignment
	new_response_text?: string;  // For abandoned status with reassignment
	message?: string;  // For abandoned status without reassignment
}

export interface HighlightCreateRequest {
	assignment_id: string;
	selected_text: string;
	source: 'prompt' | 'response';
	start_offset?: number;
	end_offset?: number;
	context?: string;
}

export interface HighlightResponse {
	id: string;
	assignment_id: string;
	selected_text: string;
	source: string;
	start_offset?: number;
	end_offset?: number;
	created_at: number;
}

// Scenario assignment API functions

export const assignScenario = async (
	token: string,
	payload: ScenarioAssignRequest
): Promise<ScenarioAssignResponse> => {
	const res = await fetch(`${WEBUI_API_BASE_URL}/moderation/scenarios/assign`, {
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

export const startScenario = async (
	token: string,
	payload: ScenarioStatusUpdateRequest
): Promise<ScenarioStatusResponse> => {
	const res = await fetch(`${WEBUI_API_BASE_URL}/moderation/scenarios/start`, {
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

export const completeScenario = async (
	token: string,
	payload: ScenarioStatusUpdateRequest
): Promise<ScenarioStatusResponse> => {
	const res = await fetch(`${WEBUI_API_BASE_URL}/moderation/scenarios/complete`, {
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

export const skipScenario = async (
	token: string,
	payload: ScenarioStatusUpdateRequest
): Promise<ScenarioStatusResponse> => {
	const res = await fetch(`${WEBUI_API_BASE_URL}/moderation/scenarios/skip`, {
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

export const abandonScenario = async (
	token: string,
	payload: ScenarioStatusUpdateRequest
): Promise<ScenarioStatusResponse> => {
	const res = await fetch(`${WEBUI_API_BASE_URL}/moderation/scenarios/abandon`, {
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

export interface AttentionCheckResponse {
	scenario_id: string;
	prompt_text: string;
	response_text: string;
	trait_theme?: string;
	trait_phrase?: string;
	sentiment?: string;
}

export const getRandomAttentionCheck = async (
	token: string
): Promise<AttentionCheckResponse | null> => {
	const res = await fetch(`${WEBUI_API_BASE_URL}/moderation/attention-checks/random`, {
		method: 'GET',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		}
	});
	if (!res.ok) {
		if (res.status === 404) {
			return null; // No attention checks available
		}
		throw await res.json();
	}
	return res.json();
};

// Highlights API functions

export const createHighlight = async (
	token: string,
	payload: HighlightCreateRequest
): Promise<HighlightResponse> => {
	const res = await fetch(`${WEBUI_API_BASE_URL}/moderation/highlights`, {
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

export const getHighlights = async (
	token: string,
	assignment_id: string
): Promise<HighlightResponse[]> => {
	const res = await fetch(`${WEBUI_API_BASE_URL}/moderation/highlights/${assignment_id}`, {
		method: 'GET',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		}
	});
	if (!res.ok) throw await res.json();
	return res.json();
};

export interface AssignmentWithScenario {
	assignment_id: string;
	scenario_id: string;
	prompt_text: string;
	response_text: string;
	assignment_position: number;
	status: string;
	assigned_at: number;
	started_at?: number;
}

export const getAssignmentsForChild = async (
	token: string,
	childId: string
): Promise<AssignmentWithScenario[]> => {
	const res = await fetch(`${WEBUI_API_BASE_URL}/moderation/scenarios/assignments/${childId}`, {
		method: 'GET',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		}
	});
	if (!res.ok) throw await res.json();
	return res.json();
};

// ========== ADMIN API FUNCTIONS ==========

export interface ScenarioAdminListResponse {
	scenarios: ScenarioModel[];
	total: number;
	active_count: number;
	inactive_count: number;
}

export interface ScenarioModel {
	scenario_id: string;
	prompt_text: string;
	response_text: string;
	set_name?: string;
	trait?: string;
	polarity?: string;
	prompt_style?: string;
	domain?: string;
	source?: string;
	model_name?: string;
	is_active: boolean;
	n_assigned: number;
	n_completed: number;
	n_skipped: number;
	n_abandoned: number;
	created_at: number;
	updated_at: number;
}

export interface ScenarioStatsResponse {
	total_scenarios: number;
	active_scenarios: number;
	inactive_scenarios: number;
	total_assignments: number;
	total_completed: number;
	total_skipped: number;
	total_abandoned: number;
}

export interface ScenarioUploadResponse {
	status: string;
	loaded: number;
	updated: number;
	errors: number;
	total: number;
	error_details?: string[];
}

export interface AttentionCheckAdminListResponse {
	attention_checks: AttentionCheckAdminModel[];
	total: number;
	active_count: number;
	inactive_count: number;
}

export interface AttentionCheckAdminModel {
	scenario_id: string;
	prompt_text: string;
	response_text: string;
	trait_theme?: string;
	trait_phrase?: string;
	sentiment?: string;
	trait_index?: number;
	prompt_index?: number;
	set_name?: string;
	is_active: boolean;
	source?: string;
	created_at: number;
	updated_at: number;
}

export const uploadScenariosAdmin = async (
	token: string,
	file: File,
	setName: string = 'pilot',
	source: string = 'admin_upload'
): Promise<ScenarioUploadResponse> => {
	const formData = new FormData();
	formData.append('file', file);
	formData.append('set_name', setName);
	formData.append('source', source);

	const res = await fetch(`${WEBUI_API_BASE_URL}/admin/scenarios/upload`, {
		method: 'POST',
		headers: {
			Authorization: `Bearer ${token}`
		},
		body: formData
	});
	if (!res.ok) throw await res.json();
	return res.json();
};

export const listScenariosAdmin = async (
	token: string,
	options: {
		is_active?: boolean;
		trait?: string;
		polarity?: string;
		domain?: string;
		page?: number;
		page_size?: number;
	} = {}
): Promise<ScenarioAdminListResponse> => {
	const params = new URLSearchParams();
	if (options.is_active !== undefined) params.append('is_active', String(options.is_active));
	if (options.trait) params.append('trait', options.trait);
	if (options.polarity) params.append('polarity', options.polarity);
	if (options.domain) params.append('domain', options.domain);
	if (options.page) params.append('page', String(options.page));
	if (options.page_size) params.append('page_size', String(options.page_size));

	const res = await fetch(`${WEBUI_API_BASE_URL}/admin/scenarios?${params.toString()}`, {
		method: 'GET',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		}
	});
	if (!res.ok) throw await res.json();
	return res.json();
};

export const getScenarioStatsAdmin = async (token: string): Promise<ScenarioStatsResponse> => {
	const res = await fetch(`${WEBUI_API_BASE_URL}/admin/scenarios/stats`, {
		method: 'GET',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		}
	});
	if (!res.ok) throw await res.json();
	return res.json();
};

export const updateScenarioAdmin = async (
	token: string,
	scenarioId: string,
	is_active?: boolean
): Promise<{ status: string; scenario: ScenarioModel }> => {
	const res = await fetch(`${WEBUI_API_BASE_URL}/admin/scenarios/${scenarioId}`, {
		method: 'PATCH',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify({ is_active })
	});
	if (!res.ok) throw await res.json();
	return res.json();
};

export const uploadAttentionChecksAdmin = async (
	token: string,
	file: File,
	setName: string = 'default',
	source: string = 'admin_upload'
): Promise<ScenarioUploadResponse> => {
	const formData = new FormData();
	formData.append('file', file);
	formData.append('set_name', setName);
	formData.append('source', source);

	const res = await fetch(`${WEBUI_API_BASE_URL}/admin/attention-checks/upload`, {
		method: 'POST',
		headers: {
			Authorization: `Bearer ${token}`
		},
		body: formData
	});
	if (!res.ok) throw await res.json();
	return res.json();
};

export const listAttentionChecksAdmin = async (
	token: string,
	options: { is_active?: boolean; page?: number; page_size?: number } = {}
): Promise<AttentionCheckAdminListResponse> => {
	const params = new URLSearchParams();
	if (options.is_active !== undefined) params.append('is_active', String(options.is_active));
	if (options.page) params.append('page', String(options.page));
	if (options.page_size) params.append('page_size', String(options.page_size));

	const res = await fetch(`${WEBUI_API_BASE_URL}/admin/attention-checks?${params.toString()}`, {
		method: 'GET',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		}
	});
	if (!res.ok) throw await res.json();
	return res.json();
};

export const updateAttentionCheckAdmin = async (
	token: string,
	scenarioId: string,
	is_active?: boolean
): Promise<{ status: string; attention_check: AttentionCheckAdminModel }> => {
	const res = await fetch(`${WEBUI_API_BASE_URL}/admin/attention-checks/${scenarioId}`, {
		method: 'PATCH',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify({ is_active })
	});
	if (!res.ok) throw await res.json();
	return res.json();
};