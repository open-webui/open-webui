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

// ---------------------------------------------------------------------------
// Internal fetch helper — centralises auth header, error parsing, JSON decode
// ---------------------------------------------------------------------------
async function spFetch<T>(token: string, url: string, opts: RequestInit = {}): Promise<T> {
	const res = await fetch(url, {
		...opts,
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`,
			...opts.headers
		}
	});

	if (!res.ok) {
		const body = await res.json().catch(() => ({}));
		throw body.detail ?? body.message ?? `SharePoint API error: ${res.status}`;
	}

	return res.json();
}

// ---------------------------------------------------------------------------
// Auth
// ---------------------------------------------------------------------------

export const getSharepointAuthStatus = (token: string): Promise<SharePointAuthStatus> =>
	spFetch(token, `${WEBUI_API_BASE_URL}/sharepoint/auth/status`);

export const getSharepointAuthUrl = (token: string): Promise<SharePointAuthUrl> =>
	spFetch(token, `${WEBUI_API_BASE_URL}/sharepoint/auth/login`);

export const logoutSharepoint = (token: string): Promise<{ status: string }> =>
	spFetch(token, `${WEBUI_API_BASE_URL}/sharepoint/auth/logout`, { method: 'POST' });

// ---------------------------------------------------------------------------
// Tenants & Sites
// ---------------------------------------------------------------------------

export const getSharepointTenants = (token: string): Promise<TenantInfo[]> =>
	spFetch<TenantInfo[]>(token, `${WEBUI_API_BASE_URL}/sharepoint/tenants`).then((r) => r ?? []);

export const getSharepointSites = (token: string, tenantId: string): Promise<SiteInfo[]> =>
	spFetch<SiteInfo[]>(
		token,
		`${WEBUI_API_BASE_URL}/sharepoint/tenants/${encodeURIComponent(tenantId)}/sites`
	).then((r) => r ?? []);

// ---------------------------------------------------------------------------
// Drives
// ---------------------------------------------------------------------------

export const getSharepointSiteDrives = (
	token: string,
	tenantId: string,
	siteId: string
): Promise<DriveInfo[]> =>
	spFetch<DriveInfo[]>(
		token,
		`${WEBUI_API_BASE_URL}/sharepoint/tenants/${encodeURIComponent(tenantId)}/sites/${encodeURIComponent(siteId)}/drives`
	).then((r) => r ?? []);

export const getSharepointDrives = (token: string, tenantId: string): Promise<DriveInfo[]> =>
	spFetch<DriveInfo[]>(
		token,
		`${WEBUI_API_BASE_URL}/sharepoint/tenants/${encodeURIComponent(tenantId)}/drives`
	).then((r) => r ?? []);

// ---------------------------------------------------------------------------
// Files
// ---------------------------------------------------------------------------

export const getSharepointFiles = (
	token: string,
	tenantId: string,
	driveId: string,
	folderId?: string
): Promise<DriveItem[]> => {
	const base = `${WEBUI_API_BASE_URL}/sharepoint/tenants/${encodeURIComponent(tenantId)}/drives/${encodeURIComponent(driveId)}/files`;
	const url = folderId ? `${base}?folder_id=${encodeURIComponent(folderId)}` : base;
	return spFetch<DriveItem[]>(token, url).then((r) => r ?? []);
};

export const getSharepointFilesRecursive = (
	token: string,
	tenantId: string,
	driveId: string,
	folderId?: string,
	maxDepth = 10,
	signal?: AbortSignal
): Promise<DriveItem[]> => {
	const params = new URLSearchParams({ max_depth: String(maxDepth) });
	if (folderId) params.set('folder_id', folderId);
	const url = `${WEBUI_API_BASE_URL}/sharepoint/tenants/${encodeURIComponent(tenantId)}/drives/${encodeURIComponent(driveId)}/files/recursive?${params}`;
	return spFetch<DriveItem[]>(token, url, { signal }).then((r) => r ?? []);
};

// ---------------------------------------------------------------------------
// Download
// ---------------------------------------------------------------------------

export const downloadSharepointFile = (
	token: string,
	tenantId: string,
	driveId: string,
	fileId: string,
	filename?: string,
	signal?: AbortSignal
): Promise<DownloadedFile> => {
	const url = `${WEBUI_API_BASE_URL}/sharepoint/tenants/${encodeURIComponent(tenantId)}/drives/${encodeURIComponent(driveId)}/files/${encodeURIComponent(fileId)}/download`;
	return spFetch<DownloadedFile>(token, url, {
		method: 'POST',
		body: filename ? JSON.stringify({ filename }) : undefined,
		signal
	});
};
