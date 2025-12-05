import { WEBUI_API_BASE_URL } from '$lib/constants';

export type UploadVisibility = 'public' | 'private';

export type UploadDocumentResponse = {
	bucket: string;
	key: string;
	url: string;
	visibility: UploadVisibility;
	original_filename: string;
	stored_filename: string;
	tenant_prefix: string;
	tenant_id: string;
};

export type UploadTenant = {
	id: string;
	name: string;
	s3_bucket: string;
};

export type StoredFile = {
	key: string;
	size: number;
	last_modified: string;
	url: string;
	tenant_id: string;
};

export const getUploadTenants = async (token: string): Promise<UploadTenant[]> => {
	let error: string | null = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/uploads/tenants`, {
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

export const uploadDocument = async (
	token: string,
	file: File,
	visibility: UploadVisibility,
	tenantId?: string | null
): Promise<UploadDocumentResponse> => {
	let error: string | null = null;

	const body = new FormData();
	body.append('file', file);
	body.append('visibility', visibility);
	if (tenantId) {
		body.append('tenant_id', tenantId);
	}

	const res = await fetch(`${WEBUI_API_BASE_URL}/uploads`, {
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
			error = err?.detail ?? 'Failed to upload document.';
			return null;
		});

	if (error || !res) {
		throw error ?? 'Failed to upload document.';
	}

	return res;
};

export const getFiles = async (
	token: string,
	path: string,
	tenantId?: string | null
): Promise<StoredFile[]> => {
	let error: string | null = null;
	const searchParams = new URLSearchParams();
	searchParams.set('path', path);
	if (tenantId) {
		searchParams.set('tenant_id', tenantId);
	}

	const res = await fetch(
		`${WEBUI_API_BASE_URL}/uploads/files?${searchParams.toString()}`,
		{
			method: 'GET',
			headers: {
				'Content-Type': 'application/json',
				Authorization: `Bearer ${token}`
			}
		}
	)
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			error = err?.detail ?? 'Failed to load files.';
			return null;
		});

	if (error || !res) {
		throw error ?? 'Failed to load files.';
	}

	return res;
};

export const ingestUploadedDocument = async (token: string, key: string) => {
	let error: string | null = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/uploads/ingest`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify({ key })
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			error = err?.detail ?? 'Failed to trigger ingestion.';
			return null;
		});

	if (error || !res) {
		throw error ?? 'Failed to trigger ingestion.';
	}

	return res;
};

export const deleteUpload = async (token: string, key: string) => {
	return postJsonWithAuth(token, '/uploads/delete', { key }, 'Failed to delete file.');
};

const postJsonWithAuth = async <T>(
	token: string,
	path: string,
	payload: Record<string, unknown>,
	defaultError: string
): Promise<T> => {
	let error: string | null = null;
	const res = await fetch(`${WEBUI_API_BASE_URL}${path}`, {
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
			error = err?.detail ?? defaultError;
			return null;
		});

	if (error || !res) {
		throw error ?? defaultError;
	}

	return res;
};

export const rebuildTenantArtifact = async (token: string, tenant: string) => {
	return postJsonWithAuth(token, '/uploads/rebuild-tenant', { tenant }, 'Failed to rebuild tenant artifact.');
};

export const rebuildUserArtifact = async (token: string, tenant: string, user: string) => {
	return postJsonWithAuth(
		token,
		'/uploads/rebuild-user',
		{ tenant, user },
		'Failed to rebuild private artifact.'
	);
};
