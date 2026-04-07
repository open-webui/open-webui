import { WEBUI_API_BASE_URL } from '$lib/constants';

export interface EntitySpan {
	start: number;
	end: number;
	entity_type: 'PERSON' | 'EMAIL' | 'ORGANIZATION' | string;
	text: string;
}

export interface AnalyzeResponse {
	entities: EntitySpan[];
	raw_text?: string;
}

/**
 * Call the privacy proxy /analyze endpoint to detect sensitive entities in the message
 */
export const analyzeMessageEntities = async (
	token: string,
	messageText: string
): Promise<EntitySpan[] | null> => {
	try {
		const res = await fetch(`${WEBUI_API_BASE_URL}/privacy/analyze`, {
			method: 'POST',
			headers: {
				Accept: 'application/json',
				'Content-Type': 'application/json',
				authorization: `Bearer ${token}`
			},
			body: JSON.stringify({
				text: messageText
			})
		});

		if (!res.ok) {
			console.error('Privacy analyze error:', await res.text());
			return null;
		}

		const response: AnalyzeResponse = await res.json();
		return response.entities || [];
	} catch (error) {
		console.error('Privacy analyze request failed:', error);
		return null;
	}
};
