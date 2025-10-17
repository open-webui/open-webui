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

export interface ScenarioPayload {
  scenario_id?: string;
  user_id: string;
  child_id: string;
  scenario_prompt: string;
  original_response: string;
}

export interface AnswerPayload {
  scenario_id: string;
  question_key: string;
  value: boolean | string | Record<string, any>;
  answered_at: number;
}

export interface VersionPayload {
  scenario_id: string;
  version_index: number;
  strategies: string[];
  custom_instructions: { id: string; text: string }[];
  highlighted_texts: string[];
  refactored_response: string;
}

export const upsertScenario = async (token: string, payload: ScenarioPayload) => {
  const res = await fetch(`${WEBUI_API_BASE_URL}/moderation/scenarios`, {
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

export const patchScenario = async (
  token: string,
  scenarioId: string,
  payload: Partial<{ is_applicable: boolean; decision: string; decided_at: number }>
) => {
  const res = await fetch(`${WEBUI_API_BASE_URL}/moderation/scenarios/${scenarioId}`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`
    },
    body: JSON.stringify(payload)
  });
  if (!res.ok) throw await res.json();
  return res.json();
};

export const upsertAnswer = async (token: string, scenarioId: string, payload: AnswerPayload) => {
  const res = await fetch(`${WEBUI_API_BASE_URL}/moderation/scenarios/${scenarioId}/answers`, {
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

export const createVersion = async (token: string, scenarioId: string, payload: VersionPayload) => {
  const res = await fetch(`${WEBUI_API_BASE_URL}/moderation/scenarios/${scenarioId}/versions`, {
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

export const confirmVersion = async (token: string, scenarioId: string, versionIndex: number) => {
  const res = await fetch(`${WEBUI_API_BASE_URL}/moderation/scenarios/${scenarioId}/confirm`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`
    },
    body: JSON.stringify({ version_index: versionIndex })
  });
  if (!res.ok) throw await res.json();
  return res.json();
};

export const applyModeration = async (
	token: string,
	moderationTypes: string[],  // Standard moderation types
	childPrompt?: string,
	customInstructions?: string[],  // Optional custom instruction texts
	originalResponse?: string,  // For refactoring mode
	highlightedTexts?: string[]  // Phrases parent flagged
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
			model: 'gpt-4o-mini',
			max_chars: 600,
			custom_instructions: customInstructions || [],  // Send custom instructions array
			original_response: originalResponse || null,  // Optional: for refactoring mode
			highlighted_texts: highlightedTexts || []  // Optional: flagged texts
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


