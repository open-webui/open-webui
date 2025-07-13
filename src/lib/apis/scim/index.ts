import { WEBUI_API_BASE_URL } from '$lib/constants';

// SCIM API endpoints
const SCIM_BASE_URL = `${WEBUI_API_BASE_URL}/scim/v2`;

export interface SCIMConfig {
	enabled: boolean;
	token?: string;
	token_created_at?: string;
	token_expires_at?: string;
}

export interface SCIMStats {
	total_users: number;
	total_groups: number;
	last_sync?: string;
}

export interface SCIMToken {
	token: string;
	created_at: string;
	expires_at?: string;
}

// Get SCIM configuration
export const getSCIMConfig = async (token: string): Promise<SCIMConfig> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/configs/scim`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			error = err.detail;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

// Update SCIM configuration
export const updateSCIMConfig = async (token: string, config: Partial<SCIMConfig>): Promise<SCIMConfig> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/configs/scim`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify(config)
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			error = err.detail;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

// Generate new SCIM token
export const generateSCIMToken = async (token: string, expiresIn?: number): Promise<SCIMToken> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/configs/scim/token`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify({ expires_in: expiresIn })
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			error = err.detail;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

// Revoke SCIM token
export const revokeSCIMToken = async (token: string): Promise<boolean> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/configs/scim/token`, {
		method: 'DELETE',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return true;
		})
		.catch((err) => {
			console.error(err);
			error = err.detail;
			return false;
		});

	if (error) {
		throw error;
	}

	return res;
};

// Get SCIM statistics
export const getSCIMStats = async (token: string): Promise<SCIMStats> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/configs/scim/stats`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			error = err.detail;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

// Test SCIM connection
export const testSCIMConnection = async (token: string, scimToken: string): Promise<boolean> => {
	let error = null;

	// Test by calling the SCIM service provider config endpoint
	const res = await fetch(`${SCIM_BASE_URL}/ServiceProviderConfig`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			Authorization: `Bearer ${scimToken}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return true;
		})
		.catch((err) => {
			console.error(err);
			error = err.detail || 'Connection failed';
			return false;
		});

	if (error) {
		throw error;
	}

	return res;
};