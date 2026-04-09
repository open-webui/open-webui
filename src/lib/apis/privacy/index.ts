
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
 * Call the privacy proxy /analyze endpoint via the OpenWebUI passthrough.
 * Proxies to: http://privacy-proxy:8080/analyze
 */
export const analyzeMessageEntities = async (
	token: string,
	messageText: string
): Promise<EntitySpan[] | null> => {
	try {
		const garnetToggles = JSON.parse(localStorage.getItem('garnet_entity_toggles') || '{}');
		const enabledEntities = Object.entries(garnetToggles)
			.filter(([_, on]) => on)
			.map(([k]) => k)
			.join(',');
		const res = await fetch(`/openai/privacy/analyze`, {
			method: 'POST',
			headers: {
				Accept: 'application/json',
				'Content-Type': 'application/json',
				authorization: `Bearer ${token}`,
				'x-garnet-entities': enabledEntities
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
