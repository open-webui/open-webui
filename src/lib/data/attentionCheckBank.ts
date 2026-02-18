/**
 * Attention Check Bank Module
 *
 * Loads and manages attention check questions from the database via API.
 * Provides functions to randomly sample one attention check question.
 * Includes fallback to mock data when API is unavailable.
 *
 * @module attentionCheckBank
 */

import {
	getRandomAttentionCheck as getRandomAttentionCheckAPI,
	type AttentionCheckResponse
} from '$lib/apis/moderation';
import mockAttentionChecks from './mockAttentionChecks.json';

// Q&A Pair interface for attention checks (now includes scenarioId for identifier-based state)
export interface AttentionCheckQAPair {
	question: string;
	response: string;
	scenarioId?: string; // Identifier from API (scenario_id) or fallback (ac_fallback_*)
}

/**
 * Simple hash function to generate deterministic fallback IDs
 */
function hashString(str: string): string {
	let hash = 0;
	for (let i = 0; i < str.length; i++) {
		const char = str.charCodeAt(i);
		hash = (hash << 5) - hash + char;
		hash = hash & hash; // Convert to 32-bit integer
	}
	return Math.abs(hash).toString(36);
}

/**
 * Randomly samples one attention check question from the database via API.
 * Falls back to mock data if API is unavailable (404, no token, or error).
 *
 * @param token - Authentication token for API calls (optional for fallback)
 * @returns {Promise<AttentionCheckQAPair | null>} A randomly sampled Q&A pair with scenarioId, or null if none available
 *
 * @example
 * // Get one random attention check question
 * const attentionCheck = await getRandomAttentionCheck(localStorage.token);
 */
export async function getRandomAttentionCheck(
	token?: string
): Promise<AttentionCheckQAPair | null> {
	// Try API first if token is available
	if (token) {
		try {
			const response: AttentionCheckResponse | null = await getRandomAttentionCheckAPI(token);

			if (response) {
				// Convert API response to QAPair format with scenarioId
				const qaPair: AttentionCheckQAPair = {
					question: response.prompt_text,
					response: response.response_text,
					scenarioId: response.scenario_id // Use API-provided scenario_id
				};

				console.log(
					`✅ Loaded 1 random attention check question from database with ID: ${response.scenario_id}`
				);
				return qaPair;
			}
		} catch (error: any) {
			// Log error but continue to fallback
			console.warn(
				'⚠️ Error loading attention check from API, using fallback:',
				error?.message || error
			);
		}
	} else {
		console.warn('⚠️ No authentication token available, using fallback attention checks');
	}

	// Fallback to mock data
	try {
		if (!Array.isArray(mockAttentionChecks) || mockAttentionChecks.length === 0) {
			console.warn('⚠️ Mock attention checks data is empty or invalid');
			return null;
		}

		// Randomly select one from mock data
		const randomIndex = Math.floor(Math.random() * mockAttentionChecks.length);
		const mockCheck = mockAttentionChecks[randomIndex];

		// Generate deterministic fallback ID based on prompt + response
		const fallbackId = `ac_fallback_${hashString(mockCheck.prompt_text + mockCheck.response_text)}`;

		const qaPair: AttentionCheckQAPair = {
			question: mockCheck.prompt_text,
			response: mockCheck.response_text,
			scenarioId: fallbackId
		};

		console.log(`✅ Loaded 1 random attention check question from fallback with ID: ${fallbackId}`);
		return qaPair;
	} catch (error) {
		console.error('Error loading fallback attention check:', error);
		return null;
	}
}
