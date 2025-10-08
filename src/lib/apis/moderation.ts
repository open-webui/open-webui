import { WEBUI_API_BASE_URL } from '$lib/constants';

export type ModerationResponse = {
	model: string;
	child_prompt: string;
	original_response?: string;
	highlighted_texts?: string[];
	moderation_types: string[];
	refactored_response: string;
	system_prompt_rule: string;
};

export type FollowUpPromptResponse = {
	child_followup_prompt: string;
};

/**
 * Apply moderation strategies to a child's prompt (with optional original response to refactor)
 */
export const applyModeration = async (
	token: string,
	moderationTypes: string[],
	childPrompt: string,
	customInstructions?: string[],
	originalResponse?: string,
	highlightedTexts?: string[]
): Promise<ModerationResponse | null> => {
	try {
		const res = await fetch(`${WEBUI_API_BASE_URL}/moderation/apply`, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json',
				Authorization: `Bearer ${token}`
			},
			body: JSON.stringify({
				child_prompt: childPrompt,
				moderation_types: moderationTypes,
				custom_instructions: customInstructions || [],
				original_response: originalResponse || null,
				highlighted_texts: highlightedTexts || []
			})
		});

		if (!res.ok) {
			const error = await res.json();
			throw new Error(error.detail || 'Failed to apply moderation');
		}

		return await res.json();
	} catch (error) {
		console.error('Error in applyModeration:', error);
		throw error;
	}
};

/**
 * Generate a follow-up prompt based on initial conversation
 */
export const generateFollowUpPrompt = async (
	token: string,
	initialPrompt: string,
	initialResponse: string
): Promise<string> => {
	try {
		const res = await fetch(`${WEBUI_API_BASE_URL}/moderation/generate-followup`, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json',
				Authorization: `Bearer ${token}`
			},
			body: JSON.stringify({
				initial_prompt: initialPrompt,
				initial_response: initialResponse
			})
		});

		if (!res.ok) {
			const error = await res.json();
			throw new Error(error.detail || 'Failed to generate follow-up prompt');
		}

		const data: FollowUpPromptResponse = await res.json();
		return data.child_followup_prompt;
	} catch (error) {
		console.error('Error in generateFollowUpPrompt:', error);
		throw error;
	}
};

