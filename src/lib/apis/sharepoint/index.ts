import { WEBUI_API_BASE_URL } from '$lib/constants';

export interface SharePointAuthStatus {
	enabled: boolean;
	authenticated: boolean;
	provider: string;
	expires_at?: number;
	scopes?: string[];
	tenant_count?: number;
}

export interface TenantInfo {
	id: string;
	name: string;
}

export interface SharePointAuthUrl {
	url: string;
	state: string;
}

export interface DriveInfo {
	id: string;
	name: string;
	drive_type: string;
	web_url?: string;
	owner?: string;
}

export interface SiteInfo {
	id: string;
	name: string;
	display_name: string;
	web_url?: string;
}

export interface DriveItem {
	id: string;
	name: string;
	size?: number;
	is_folder: boolean;
	mime_type?: string;
	web_url?: string;
	modified_at?: string;
	drive_id?: string;
}

export interface DownloadedFile {
	id: string;
	filename: string;
	meta: Record<string, unknown>;
	created_at: number;
}

/**
 * Get SharePoint authentication status for the current user
 */
export const getSharepointAuthStatus = async (token: string): Promise<SharePointAuthStatus> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/sharepoint/auth/status`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err.detail || err.message || 'Failed to get SharePoint auth status';
			console.error('SharePoint auth status error:', err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

/**
 * Get the OAuth login URL for SharePoint
 * Returns a URL that should be opened with window.open()
 */
export const getSharepointAuthUrl = async (token: string): Promise<SharePointAuthUrl> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/sharepoint/auth/login`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err.detail || err.message || 'Failed to get SharePoint auth URL';
			console.error('SharePoint auth URL error:', err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

/**
 * Logout from SharePoint (delete OAuth session)
 */
export const logoutSharepoint = async (token: string): Promise<{ status: string }> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/sharepoint/auth/logout`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err.detail || err.message || 'Failed to logout from SharePoint';
			console.error('SharePoint logout error:', err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

/**
 * Get list of available tenants
 */
export const getSharepointTenants = async (token: string): Promise<TenantInfo[]> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/sharepoint/tenants`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err.detail || err.message || 'Failed to get SharePoint tenants';
			console.error('SharePoint tenants error:', err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res || [];
};

/**
 * Get list of SharePoint sites (departments)
 */
export const getSharepointSites = async (token: string, tenantId: string): Promise<SiteInfo[]> => {
	let error = null;

	const res = await fetch(
		`${WEBUI_API_BASE_URL}/sharepoint/tenants/${encodeURIComponent(tenantId)}/sites`,
		{
			method: 'GET',
			headers: {
				Accept: 'application/json',
				'Content-Type': 'application/json',
				authorization: `Bearer ${token}`
			}
		}
	)
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err.detail || err.message || 'Failed to get SharePoint sites';
			console.error('SharePoint sites error:', err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res || [];
};

/**
 * Get list of drives (document libraries) for a specific site
 */
export const getSharepointSiteDrives = async (
	token: string,
	tenantId: string,
	siteId: string
): Promise<DriveInfo[]> => {
	let error = null;

	const res = await fetch(
		`${WEBUI_API_BASE_URL}/sharepoint/tenants/${encodeURIComponent(tenantId)}/sites/${encodeURIComponent(siteId)}/drives`,
		{
			method: 'GET',
			headers: {
				Accept: 'application/json',
				'Content-Type': 'application/json',
				authorization: `Bearer ${token}`
			}
		}
	)
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err.detail || err.message || 'Failed to get site drives';
			console.error('SharePoint site drives error:', err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res || [];
};

/**
 * Get list of available drives (OneDrive + SharePoint document libraries)
 */
export const getSharepointDrives = async (
	token: string,
	tenantId: string
): Promise<DriveInfo[]> => {
	let error = null;

	const res = await fetch(
		`${WEBUI_API_BASE_URL}/sharepoint/tenants/${encodeURIComponent(tenantId)}/drives`,
		{
			method: 'GET',
			headers: {
				Accept: 'application/json',
				'Content-Type': 'application/json',
				authorization: `Bearer ${token}`
			}
		}
	)
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err.detail || err.message || 'Failed to get SharePoint drives';
			console.error('SharePoint drives error:', err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res || [];
};

/**
 * Get files and folders in a drive or folder
 */
export const getSharepointFiles = async (
	token: string,
	tenantId: string,
	driveId: string,
	folderId?: string
): Promise<DriveItem[]> => {
	let error = null;

	const params = new URLSearchParams();
	if (folderId) {
		params.append('folder_id', folderId);
	}

	const baseUrl = `${WEBUI_API_BASE_URL}/sharepoint/tenants/${encodeURIComponent(tenantId)}/drives/${encodeURIComponent(driveId)}/files`;
	const url = params.toString() ? `${baseUrl}?${params.toString()}` : baseUrl;

	const res = await fetch(url, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err.detail || err.message || 'Failed to get SharePoint files';
			console.error('SharePoint files error:', err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res || [];
};

/**
 * Recursively get all files in a folder (traverses subfolders)
 * Returns only files, not folders
 */
export const getSharepointFilesRecursive = async (
	token: string,
	tenantId: string,
	driveId: string,
	folderId?: string,
	maxDepth: number = 10,
	signal?: AbortSignal
): Promise<DriveItem[]> => {
	let error = null;

	const params = new URLSearchParams();
	if (folderId) {
		params.append('folder_id', folderId);
	}
	params.append('max_depth', maxDepth.toString());

	const baseUrl = `${WEBUI_API_BASE_URL}/sharepoint/tenants/${encodeURIComponent(tenantId)}/drives/${encodeURIComponent(driveId)}/files/recursive`;
	const url = `${baseUrl}?${params.toString()}`;

	const res = await fetch(url, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		signal
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err.detail || err.message || 'Failed to get SharePoint files recursively';
			console.error('SharePoint recursive files error:', err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res || [];
};

/**
 * Download a file from SharePoint and store it in OpenWebUI
 * Returns the created file model
 */
export const downloadSharepointFile = async (
	token: string,
	tenantId: string,
	driveId: string,
	fileId: string,
	filename?: string,
	signal?: AbortSignal
): Promise<DownloadedFile> => {
	let error = null;

	const url = `${WEBUI_API_BASE_URL}/sharepoint/tenants/${encodeURIComponent(tenantId)}/drives/${encodeURIComponent(driveId)}/files/${encodeURIComponent(fileId)}/download`;

	const res = await fetch(url, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: filename ? JSON.stringify({ filename }) : undefined,
		signal
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err.detail || err.message || 'Failed to download file from SharePoint';
			console.error('SharePoint download error:', err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};
