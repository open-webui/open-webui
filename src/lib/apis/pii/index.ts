// PII Detection API using NENNA.ai
const NENNA_API_BASE_URL = 'https://api.nenna.ai/latest';

export interface PiiEntity {
	id: number;
	type: string;
	label: string;
	raw_text: string;
	occurrences: Array<{
		start_idx: number;
		end_idx: number;
	}>;
}

// Interface for known entities to send to API
export interface KnownPiiEntity {
	id: number;
	label: string;
	name: string;
}

export interface PiiMaskResponse {
	text: string[];
	pii: PiiEntity[][];
	session?: {
		session_id: string;
		ttl: string;
		created_at: string;
		expires_at?: string;
	};
}

export interface PiiUnmaskResponse {
	text: string[];
	pii?: PiiEntity[];
}

export interface PiiSession {
	session_id: string;
	ttl: string;
	created_at: string;
	expires_at?: string;
}

// Create a session for consistent masking/unmasking
export const createPiiSession = async (apiKey: string, ttl: string = '24h'): Promise<PiiSession> => {
	const response = await fetch(`${NENNA_API_BASE_URL}/sessions`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			'X-API-Key': apiKey
		},
		body: JSON.stringify({
			ttl,
			description: 'Open WebUI PII Detection Session'
		})
	});

	if (!response.ok) {
		throw new Error(`Failed to create PII session: ${response.statusText}`);
	}

	return response.json();
};

// Mask PII in text (ephemeral - without session)
export const maskPiiText = async (
	apiKey: string,
	text: string[],
	knownEntities: KnownPiiEntity[] = [],
	createSession: boolean = false,
	quiet: boolean = false
): Promise<PiiMaskResponse> => {
	const url = new URL(`${NENNA_API_BASE_URL}/text/mask`);
	if (createSession) url.searchParams.set('create_session', 'true');
	if (quiet) url.searchParams.set('quiet', 'true');

	const requestBody: any = {
		text,
		pii_labels: {
			detect: ['ALL']
		}
	};

	// Add known entities if provided
	if (knownEntities.length > 0) {
		requestBody.known_entities = knownEntities;
	}

	const response = await fetch(url.toString(), {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			'X-API-Key': apiKey
		},
		body: JSON.stringify(requestBody)
	});

	if (!response.ok) {
		throw new Error(`Failed to mask PII: ${response.statusText}`);
	}

	return response.json();
};

// Unmask PII in text (ephemeral - without session)
export const unmaskPiiText = async (
	apiKey: string,
	text: string[],
	entities: PiiEntity[]
): Promise<PiiUnmaskResponse> => {
	const response = await fetch(`${NENNA_API_BASE_URL}/text/unmask`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			'X-API-Key': apiKey
		},
		body: JSON.stringify({
			text,
			entities
		})
	});

	if (!response.ok) {
		throw new Error(`Failed to unmask PII: ${response.statusText}`);
	}

	return response.json();
};

// Mask PII using session
export const maskPiiTextWithSession = async (
	apiKey: string,
	sessionId: string,
	text: string[],
	knownEntities: KnownPiiEntity[] = [],
	quiet: boolean = false
): Promise<PiiMaskResponse> => {
	const url = new URL(`${NENNA_API_BASE_URL}/sessions/${sessionId}/text/mask`);
	if (quiet) url.searchParams.set('quiet', 'true');

	const requestBody: any = {
		text,
		pii_labels: {
			detect: ['ALL']
		}
	};

	// Add known entities if provided
	if (knownEntities.length > 0) {
		requestBody.known_entities = knownEntities;
	}

	const response = await fetch(url.toString(), {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			'X-API-Key': apiKey
		},
		body: JSON.stringify(requestBody)
	});

	if (!response.ok) {
		throw new Error(`Failed to mask PII with session: ${response.statusText}`);
	}

	return response.json();
};

// Unmask PII using session
export const unmaskPiiTextWithSession = async (
	apiKey: string,
	sessionId: string,
	text: string[]
): Promise<PiiUnmaskResponse> => {
	const response = await fetch(`${NENNA_API_BASE_URL}/sessions/${sessionId}/text/unmask`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			'X-API-Key': apiKey
		},
		body: JSON.stringify({
			text
		})
	});

	if (!response.ok) {
		throw new Error(`Failed to unmask PII with session: ${response.statusText}`);
	}

	return response.json();
};

// Delete session
export const deletePiiSession = async (apiKey: string, sessionId: string): Promise<void> => {
	const response = await fetch(`${NENNA_API_BASE_URL}/sessions/${sessionId}`, {
		method: 'DELETE',
		headers: {
			'X-API-Key': apiKey
		}
	});

	if (!response.ok) {
		throw new Error(`Failed to delete PII session: ${response.statusText}`);
	}
};

// Get session info
export const getPiiSession = async (apiKey: string, sessionId: string): Promise<PiiSession> => {
	const response = await fetch(`${NENNA_API_BASE_URL}/sessions/${sessionId}`, {
		method: 'GET',
		headers: {
			'X-API-Key': apiKey
		}
	});

	if (!response.ok) {
		throw new Error(`Failed to get PII session: ${response.statusText}`);
	}

	return response.json();
}; 