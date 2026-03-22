import { WEBUI_API_BASE_URL } from '$lib/constants';

export interface GoogleDriveStatus {
	configured: boolean;
	message: string;
}

export interface FolderValidation {
	valid: boolean;
	folder_id?: string;
	folder_name?: string;
	file_count: number;
	message: string;
}

export interface ExternalResource {
	id: string;
	user_id: string;
	knowledge_id: string;
	resource_type: string;
	resource_link: string;
	resource_name?: string;
	sync_enabled: boolean;
	sync_interval_minutes: number;
	page_token?: string;
	last_synced_at?: number;
	last_sync_status?: string;
	last_sync_error?: string;
	created_at: number;
	updated_at: number;
}

export interface SyncResult {
	success: boolean;
	files_added: number;
	files_failed: number;
	errors: string[];
	message: string;
}

/**
 * Check if Google Drive integration is configured
 */
export const getGoogleDriveStatus = async (token: string): Promise<GoogleDriveStatus> => {
	const res = await fetch(`${WEBUI_API_BASE_URL}/google-drive/status`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	});

	if (!res.ok) {
		const error = await res.json();
		throw new Error(error.detail || 'Failed to get Google Drive status');
	}

	return res.json();
};

/**
 * Validate a Google Drive folder URL
 */
export const validateGoogleDriveFolder = async (
	token: string,
	folderUrl: string
): Promise<FolderValidation> => {
	const res = await fetch(`${WEBUI_API_BASE_URL}/google-drive/validate-folder`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify({ folder_url: folderUrl })
	});

	if (!res.ok) {
		const error = await res.json();
		throw new Error(error.detail || 'Failed to validate folder');
	}

	return res.json();
};

/**
 * Link a Google Drive folder to a knowledge base
 */
export const linkGoogleDriveFolder = async (
	token: string,
	knowledgeId: string,
	resourceLink: string,
	resourceName?: string,
	syncEnabled: boolean = true,
	syncIntervalMinutes: number = 60
): Promise<ExternalResource> => {
	const res = await fetch(`${WEBUI_API_BASE_URL}/google-drive/link`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			knowledge_id: knowledgeId,
			resource_type: 'google_drive',
			resource_link: resourceLink,
			resource_name: resourceName,
			sync_enabled: syncEnabled,
			sync_interval_minutes: syncIntervalMinutes
		})
	});

	if (!res.ok) {
		const error = await res.json();
		throw new Error(error.detail || 'Failed to link Google Drive folder');
	}

	return res.json();
};

/**
 * Get all external resources for a knowledge base
 */
export const getKnowledgeExternalResources = async (
	token: string,
	knowledgeId: string
): Promise<{ items: ExternalResource[]; total: number }> => {
	const res = await fetch(`${WEBUI_API_BASE_URL}/google-drive/resources/${knowledgeId}`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	});

	if (!res.ok) {
		const error = await res.json();
		throw new Error(error.detail || 'Failed to get external resources');
	}

	return res.json();
};

/**
 * Get a specific external resource
 */
export const getExternalResource = async (
	token: string,
	resourceId: string
): Promise<ExternalResource> => {
	const res = await fetch(`${WEBUI_API_BASE_URL}/google-drive/resource/${resourceId}`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	});

	if (!res.ok) {
		const error = await res.json();
		throw new Error(error.detail || 'Failed to get external resource');
	}

	return res.json();
};

/**
 * Update an external resource
 */
export const updateExternalResource = async (
	token: string,
	resourceId: string,
	updates: {
		resource_name?: string;
		sync_enabled?: boolean;
		sync_interval_minutes?: number;
	}
): Promise<ExternalResource> => {
	const res = await fetch(`${WEBUI_API_BASE_URL}/google-drive/resource/${resourceId}`, {
		method: 'PATCH',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify(updates)
	});

	if (!res.ok) {
		const error = await res.json();
		throw new Error(error.detail || 'Failed to update external resource');
	}

	return res.json();
};

/**
 * Delete an external resource
 */
export const deleteExternalResource = async (
	token: string,
	resourceId: string
): Promise<{ success: boolean; message: string }> => {
	const res = await fetch(`${WEBUI_API_BASE_URL}/google-drive/resource/${resourceId}`, {
		method: 'DELETE',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	});

	if (!res.ok) {
		const error = await res.json();
		throw new Error(error.detail || 'Failed to delete external resource');
	}

	return res.json();
};

/**
 * Sync files from a Google Drive folder
 */
export const syncExternalResource = async (
	token: string,
	resourceId: string
): Promise<SyncResult> => {
	const res = await fetch(`${WEBUI_API_BASE_URL}/google-drive/resource/${resourceId}/sync`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	});

	if (!res.ok) {
		const error = await res.json();
		throw new Error(error.detail || 'Failed to sync external resource');
	}

	return res.json();
};
