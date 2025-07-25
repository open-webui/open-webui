// PII Detection API using NENNA.ai with auto-generated client
import { config } from '$lib/stores';
import { get } from 'svelte/store';
import {
	createSessionSessionsPost,
	deleteSessionSessionsSessionIdDelete,
	getSessionSessionsSessionIdGet,
	maskTextTextMaskPost,
	unmaskTextTextUnmaskPost,
	maskTextWithSessionSessionsSessionIdTextMaskPost,
	unmaskTextWithSessionSessionsSessionIdTextUnmaskPost,
	type PiiEntity,
	type Session,
	type SessionCreate,
	type TextMaskResponse,
	type TextUnmaskResponse
} from './generated';
import { client } from './generated/client.gen';

// Get the PII API base URL from the config store
const getPiiApiBaseUrl = (): string => {
	const configValue = get(config) as any;
	return configValue?.pii?.api_base_url || 'https://api.nenna.ai/latest';
};

// Configure the generated client
const configureClient = (apiKey: string) => {
	client.setConfig({
		baseUrl: getPiiApiBaseUrl(),
		headers: {
			'X-API-Key': apiKey
		}
	});
};

// Re-export types from generated client
export type { PiiEntity, Session };

// Legacy interface for backward compatibility
export interface KnownPiiEntity {
	id: number;
	label: string;
	name: string; // maps to raw_text in PiiEntity
}

// Response interfaces that match the API
export interface PiiMaskResponse {
	text: string[];
	pii: PiiEntity[][];
	session?: Session;
}

export interface PiiUnmaskResponse {
	text: string[];
	pii?: PiiEntity[];
}

// Legacy alias
export type PiiSession = Session;

// Create a session for consistent masking/unmasking
export const createPiiSession = async (apiKey: string, ttl: string = '24h'): Promise<Session> => {
	configureClient(apiKey);

	const response = await createSessionSessionsPost({
		body: {
			ttl,
			description: 'Open WebUI PII Detection Session'
		}
	});

	if (response.error) {
		throw new Error(`Failed to create PII session: ${response.error}`);
	}

	return response.data;
};

// Interface for Shield API modifiers
export interface ShieldApiModifier {
	action: 'ignore' | 'word-mask' | 'string-mask';
	entity: string;
	type?: string;
}

// Mask PII in text (ephemeral - without session)
export const maskPiiText = async (
	apiKey: string,
	text: string[],
	knownEntities: KnownPiiEntity[] = [],
	modifiers: ShieldApiModifier[] = [],
	createSession: boolean = false,
	quiet: boolean = false
): Promise<PiiMaskResponse> => {
	configureClient(apiKey);

	const requestBody: {
		text: string[];
		pii_labels: { detect: string[] };
		known_entities?: KnownPiiEntity[];
		modifiers?: ShieldApiModifier[];
	} = {
		text,
		pii_labels: {
			detect: ['ALL']
		}
	};

	// Add known entities if provided
	if (knownEntities.length > 0) {
		requestBody.known_entities = knownEntities;
	}

	// Add modifiers if provided
	if (modifiers.length > 0) {
		requestBody.modifiers = modifiers;
	}

	const response = await maskTextTextMaskPost({
		body: requestBody,
		query: {
			create_session: createSession,
			quiet: quiet
		}
	});

	if (response.error) {
		throw new Error(`Failed to mask PII: ${response.error}`);
	}

	return {
		text: response.data.text,
		pii: response.data.pii || [],
		session: response.data.session || undefined
	};
};

// Unmask PII in text (ephemeral - without session)
export const unmaskPiiText = async (
	apiKey: string,
	text: string[],
	entities: PiiEntity[]
): Promise<PiiUnmaskResponse> => {
	const response = await fetch(`${getPiiApiBaseUrl()}/text/unmask`, {
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
	modifiers: ShieldApiModifier[] = [],
	quiet: boolean = false
): Promise<PiiMaskResponse> => {
	const url = new URL(`${getPiiApiBaseUrl()}/sessions/${sessionId}/text/mask`);
	if (quiet) url.searchParams.set('quiet', 'true');

	const requestBody: {
		text: string[];
		pii_labels: { detect: string[] };
		known_entities?: KnownPiiEntity[];
		modifiers?: ShieldApiModifier[];
	} = {
		text,
		pii_labels: {
			detect: ['ALL']
		}
	};

	// Add known entities if provided
	if (knownEntities.length > 0) {
		requestBody.known_entities = knownEntities;
	}

	// Add modifiers if provided
	if (modifiers.length > 0) {
		requestBody.modifiers = modifiers;
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
	const response = await fetch(`${getPiiApiBaseUrl()}/sessions/${sessionId}/text/unmask`, {
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
	const response = await fetch(`${getPiiApiBaseUrl()}/sessions/${sessionId}`, {
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
	const response = await fetch(`${getPiiApiBaseUrl()}/sessions/${sessionId}`, {
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
