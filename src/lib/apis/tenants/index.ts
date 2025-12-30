import { WEBUI_API_BASE_URL } from '$lib/constants';

export type TenantInfo = {
	id: string;
	name: string;
	s3_bucket: string;
	table_name?: string | null;
	system_config_client_name?: string | null;
	logo_image_url?: string | null;
	created_at?: number;
	updated_at?: number;
};

export type TenantCreatePayload = {
	name: string;
	table_name?: string | null;
	system_config_client_name?: string | null;
	logo_image_url?: string | null;
};

export type TenantUpdatePayload = Partial<{
	name: string;
	s3_bucket: string;
	table_name: string | null;
	system_config_client_name: string | null;
	logo_image_url: string | null;
}>;

export type TenantPromptFile = {
	key: string;
	size: number;
	last_modified?: string;
	url: string;
};

export type TenantPromptUploadResponse = {
	bucket: string;
	key: string;
	url: string;
};

export const getTenants = async (token: string): Promise<TenantInfo[]> => {
	let error: string | null = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/tenants`, {
		method: 'GET',
		headers: {
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
			error = err?.detail ?? 'Failed to load tenants.';
			return null;
		});

	if (error || !res) {
		throw error ?? 'Failed to load tenants.';
	}

	return res;
};

export const getUploadTenants = getTenants;

export const createTenant = async (token: string, payload: TenantCreatePayload): Promise<TenantInfo> => {
	let error: string | null = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/tenants`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify(payload)
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			error = err?.detail ?? 'Failed to create tenant.';
			return null;
		});

	if (error || !res) {
		throw error ?? 'Failed to create tenant.';
	}

	return res;
};

export const updateTenant = async (
	token: string,
	tenantId: string,
	payload: TenantUpdatePayload
): Promise<TenantInfo> => {
	let error: string | null = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/tenants/${tenantId}`, {
		method: 'PATCH',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify(payload)
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			error = err?.detail ?? 'Failed to update tenant.';
			return null;
		});

	if (error || !res) {
		throw error ?? 'Failed to update tenant.';
	}

	return res;
};

export const deleteTenant = async (token: string, tenantId: string): Promise<void> => {
	let error: string | null = null;

	await fetch(`${WEBUI_API_BASE_URL}/tenants/${tenantId}`, {
		method: 'DELETE',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
		})
		.catch((err) => {
			console.error(err);
			error = err?.detail ?? 'Failed to delete tenant.';
		});

	if (error) {
		throw error;
	}
};

export const uploadTenantPrompt = async (
	token: string,
	tenantId: string,
	file: File
): Promise<TenantPromptUploadResponse> => {
	let error: string | null = null;

	const body = new FormData();
	body.append('file', file);

	const res = await fetch(`${WEBUI_API_BASE_URL}/tenants/${tenantId}/prompts`, {
		method: 'POST',
		headers: {
			Authorization: `Bearer ${token}`
		},
		body
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			error = err?.detail ?? 'Failed to upload prompt.';
			return null;
		});

	if (error || !res) {
		throw error ?? 'Failed to upload prompt.';
	}

	return res;
};

export const getTenantPromptFiles = async (
	token: string,
	tenantId: string
): Promise<TenantPromptFile[]> => {
	let error: string | null = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/tenants/${tenantId}/prompts`, {
		method: 'GET',
		headers: {
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
			error = err?.detail ?? 'Failed to load tenant prompts.';
			return null;
		});

	if (error || !res) {
		throw error ?? 'Failed to load tenant prompts.';
	}

	return res;
};

export const getTenantById = async (
	token: string,
	tenantId: string
): Promise<TenantInfo> => {
	let error: string | null = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/tenants/${tenantId}`, {
		method: 'GET',
		headers: {
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
			error = err?.detail ?? 'Failed to load tenant.';
			return null;
		});

	if (error || !res) {
		throw error ?? 'Failed to load tenant.';
	}

	return res;
};

export const deleteTenantPromptFile = async (token: string, tenantId: string, key: string): Promise<void> => {
	let error: string | null = null;

	await fetch(`${WEBUI_API_BASE_URL}/tenants/${tenantId}/prompts`, {
		method: 'DELETE',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify({ key })
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
		})
		.catch((err) => {
			console.error(err);
			error = err?.detail ?? 'Failed to delete prompt.';
		});

	if (error) {
		throw error;
	}
};
