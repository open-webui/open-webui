/**
 * Attention Check Bank Module
 *
 * Loads and manages attention check questions from the database via API.
 * Provides functions to randomly sample one attention check question.
 *
 * @module attentionCheckBank
 */

import {
	getRandomAttentionCheck as getRandomAttentionCheckAPI,
	type AttentionCheckResponse
} from '$lib/apis/moderation';

// Q&A Pair interface for attention checks (maintains backward compatibility)
export interface AttentionCheckQAPair {
	question: string;
	response: string;
}

/**
 * Randomly samples one attention check question from the database via API.
 *
 * @param token - Authentication token for API calls
 * @returns {Promise<AttentionCheckQAPair | null>} A randomly sampled Q&A pair, or null if none available
 * @throws {Error} If API call fails (except 404 which returns null)
 *
 * @example
 * // Get one random attention check question
 * const attentionCheck = await getRandomAttentionCheck(localStorage.token);
 */
export async function getRandomAttentionCheck(token: string): Promise<AttentionCheckQAPair | null> {
	try {
		const response: AttentionCheckResponse | null = await getRandomAttentionCheckAPI(token);

		if (!response) {
			console.warn('⚠️ No attention check questions available');
			return null;
		}

		// Convert API response to QAPair format
		const qaPair: AttentionCheckQAPair = {
			question: response.prompt_text,
			response: response.response_text
		};

		console.log(`✅ Loaded 1 random attention check question from database`);
		return qaPair;
	} catch (error) {
		console.error('Error loading attention check from API:', error);
		// Return null on error to gracefully handle failures
		return null;
	}
}
