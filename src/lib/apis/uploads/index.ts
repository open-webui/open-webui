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
