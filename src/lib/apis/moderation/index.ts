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
  scenario_prompt: string;
  original_response: string;
  initial_decision?: 'accept_original' | 'moderate' | 'not_applicable';
  strategies?: string[];
  custom_instructions?: string[];  // Simplified from {id, text}[] to string[]
  highlighted_texts?: string[];
  refactored_response?: string;
  is_final_version?: boolean;
  session_metadata?: Record<string, any>;
}

export interface ModerationSessionResponse {
  id: string;
  user_id: string;
  child_id: string;
  scenario_index: number;
  attempt_number: number;
  version_number: number;
  scenario_prompt: string;
  original_response: string;
  initial_decision?: string;
  is_final_version: boolean;
  strategies?: string[];
  custom_instructions?: string[];
  highlighted_texts?: string[];
  refactored_response?: string;
  session_metadata?: Record<string, any>;
  created_at: number;
  updated_at: number;
}

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
	childPrompt?: string,
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
			child_prompt: childPrompt || 'Who is Trump? Is he a good guy?',
			model: 'gpt-5-2025-08-07',
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