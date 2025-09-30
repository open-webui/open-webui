import { WEBUI_API_BASE_URL } from '$lib/constants';

export interface ModerationRequest {
	moderation_type: string;
	child_prompt?: string;
	model?: string;
	max_chars?: number;
}

export interface ModerationResponse {
	type: string;
	data: {
		moderation_type: string;
		instruction_used: string;
		child_prompt: string;
		refactored_response: string;
		system_prompt_rule: string;
		max_chars: number;
		model: string;
	};
}

export const applyModeration = async (
	token: string,
	moderationType: string,
	childPrompt?: string
): Promise<ModerationResponse | null> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/moderation/apply`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			moderation_type: moderationType,
			child_prompt: childPrompt || 'How can I open a door without a key?',
			model: 'gpt-4o-mini',
			max_chars: 600
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

