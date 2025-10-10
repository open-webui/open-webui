import { WEBUI_API_BASE_URL } from '$lib/constants';

export interface ModerationRequest {
	moderation_types: string[];  // Changed to array for multiple selections
	child_prompt?: string;
	model?: string;
	max_chars?: number;
	custom_instructions?: string[];
	original_response?: string;  // For refactoring mode
	highlighted_texts?: string[];  // Text selections parent flagged
}

export interface ModerationResponse {
	moderation_types: string[];  // Updated to match Viki's new response structure
	refactored_response: string;
	system_prompt_rule: string;
	model: string;
	child_prompt: string;
	original_response?: string;  // Echo back for reference
	highlighted_texts?: string[];  // Echo back for reference
}

export const applyModeration = async (
	token: string,
	moderationTypes: string[],  // Standard moderation types
	childPrompt?: string,
	customInstructions?: string[],  // Optional custom instruction texts
	originalResponse?: string,  // Optional original response to refactor
	highlightedTexts?: string[]  // Optional text selections
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
			original_response: originalResponse || undefined,  // Send original response if provided
			highlighted_texts: highlightedTexts || []  // Send highlighted texts
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


