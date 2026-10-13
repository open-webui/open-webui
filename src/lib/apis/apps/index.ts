import { WEBUI_API_BASE_URL } from '$lib/constants';

export type Embed = {
	title?: string;
	description?: string;
	url?: string | null;
	color?: number | null;
	author?: { name: string } | null;
	footer?: { text: string } | null;
	thumbnail?: { url: string } | null;
	fields?: { name: string; value: string; inline?: boolean }[];
};

export type App = {
	connection_status: 'connecting' | 'connected' | 'disconnected';
	id: string;
	slug: string;
	name: string;
	is_active: boolean;
	configured: boolean;
	data: {
		url: string;
		manifest: {
			description: string;
			profile_image_url?: string | null;
		};
		granted_scopes: string[];
	};
};

export const getApps = async (token: string = ''): Promise<App[]> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/apps`, {
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
			error = err?.detail ?? err;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getAppById = async (token: string = '', app_id: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/apps/${encodeURIComponent(app_id)}`, {
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
			error = err?.detail ?? err;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const createNewApp = async (token: string = '', app: object) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/apps`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify(app)
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err?.detail ?? err;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const updateAppById = async (token: string = '', app_id: string, app: object) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/apps/${encodeURIComponent(app_id)}`, {
		method: 'PATCH',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify(app)
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err?.detail ?? err;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const deleteAppById = async (token: string = '', app_id: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/apps/${encodeURIComponent(app_id)}`, {
		method: 'DELETE',
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
			error = err?.detail ?? err;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const previewAppManifest = async (
	token: string = '',
	url: string,
	data: { api_key?: string; app_id?: string }
) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/apps/manifest/preview`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify({ url, ...data })
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err?.detail ?? err;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const connectAppById = async (
	token: string = '',
	app_id: string,
	data: { api_key?: string } = {}
) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/apps/${encodeURIComponent(app_id)}/connect`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify(data)
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err?.detail ?? err;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const createAppInteraction = async (
	token: string = '',
	app_id: string,
	interaction: object
) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/apps/${encodeURIComponent(app_id)}/interactions`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify(interaction)
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err?.detail ?? err;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};
