import { WEBUI_API_BASE_URL } from '$lib/constants';

export type PluginPage = {
	id: string;
	title: string;
	path: string;
	entrypoint: string;
	sidebar: boolean;
	order: number;
	icon: string | null;
};

export type PluginApp = {
	id: string;
	title: string;
	version: string;
	default_page: string;
	pages: PluginPage[];
	revision: string;
};

const authHeaders = (token: string) => ({
	Accept: 'application/json',
	...(token ? { authorization: `Bearer ${token}` } : {})
});

export const getPluginApps = async (token = ''): Promise<PluginApp[]> => {
	const response = await fetch(`${WEBUI_API_BASE_URL}/functions/apps`, {
		headers: authHeaders(token)
	});

	if (!response.ok) {
		throw new Error((await response.json().catch(() => null))?.detail ?? 'Failed to load plugin apps');
	}

	return response.json();
};

export const getPluginApp = async (token: string, id: string): Promise<PluginApp | null> => {
	const apps = await getPluginApps(token);
	return apps.find((app) => app.id === id) ?? null;
};

export const getPluginPage = (app: PluginApp, pageId: string) =>
	app.pages.find((page) => page.id === pageId || page.path === pageId) ?? null;

export const pluginAssetUrl = (app: PluginApp, path: string) =>
	`${WEBUI_API_BASE_URL}/functions/apps/${encodeURIComponent(app.id)}/assets/${encodeURIComponent(app.revision)}/${path
		.split('/')
		.map((part) => encodeURIComponent(part))
		.join('/')}`;
