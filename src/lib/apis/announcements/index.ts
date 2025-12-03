import { WEBUI_API_BASE_URL } from '$lib/constants';

export type Announcement = {
	id: string;
	title: string;
	content: string;
	status: string;
	created_by: string;
	created_at: number;
	updated_at: number;
	meta?: Record<string, unknown> | null;
	author?: {
		id: string;
		name?: string;
		email?: string;
		image?: string | null;
		role?: string;
	};
};

export type AnnouncementUserView = Announcement & {
	is_read?: boolean;
	read_at?: number | null;
};

const headers = (token: string) => ({
	Accept: 'application/json',
	'Content-Type': 'application/json',
	Authorization: `Bearer ${token}`
});

const parseJsonSafe = async (res: Response) => {
	const text = await res.text();
	if (!text) return null;
	try {
		return JSON.parse(text);
	} catch (err) {
		throw new Error(
			typeof err === 'string' ? err : err?.message ?? 'Invalid JSON response from announcements API'
		);
	}
};

export const listAnnouncements = async (token: string, status?: string) => {
	let error: any = null;
	const searchParams = new URLSearchParams();
	if (status) searchParams.append('status', status);

	const res = await fetch(`${WEBUI_API_BASE_URL}/announcements?${searchParams.toString()}`, {
		method: 'GET',
		headers: headers(token)
	})
		.then(async (res) => {
			if (!res.ok) {
				let payload: any = null;
				try {
					payload = await res.json();
				} catch (_) {
					payload = await res.text();
				}
				throw payload;
			}
			return (await parseJsonSafe(res)) ?? [];
		})
		.catch((err) => {
			error = err;
			console.error(err);
			return null;
		});

	if (error) throw error;
	return res as Announcement[];
};

export const getLatestAnnouncements = async (
	token: string,
	options?: { since?: number; limit?: number }
) => {
	let error: any = null;
	const searchParams = new URLSearchParams();
	if (options?.since) searchParams.append('since', `${options.since}`);
	if (options?.limit) searchParams.append('limit', `${options.limit}`);

	const res = await fetch(`${WEBUI_API_BASE_URL}/announcements/latest?${searchParams.toString()}`, {
		method: 'GET',
		headers: headers(token)
	})
		.then(async (res) => {
			if (!res.ok) {
				let payload: any = null;
				try {
					payload = await res.json();
				} catch (_) {
					payload = await res.text();
				}
				throw payload;
			}
			return (await parseJsonSafe(res)) ?? [];
		})
		.catch((err) => {
			error = err;
			console.error(err);
			return null;
		});

	if (error) throw error;
	return res as AnnouncementUserView[];
};

export const createAnnouncement = async (
	token: string,
	payload: { title: string; content: string; status?: string; meta?: Record<string, unknown> }
) => {
	let error: any = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/announcements`, {
		method: 'POST',
		headers: headers(token),
		body: JSON.stringify(payload)
	})
		.then(async (res) => {
			if (!res.ok) {
				let payload: any = null;
				try {
					payload = await res.json();
				} catch (_) {
					payload = await res.text();
				}
				throw payload;
			}
			return parseJsonSafe(res);
		})
		.catch((err) => {
			error = err;
			console.error(err);
			return null;
		});

	if (error) throw error;
	return res as Announcement;
};

export const updateAnnouncement = async (
	token: string,
	id: string,
	payload: { title?: string; content?: string; status?: string; meta?: Record<string, unknown> }
) => {
	let error: any = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/announcements/${id}`, {
		method: 'PUT',
		headers: headers(token),
		body: JSON.stringify(payload)
	})
		.then(async (res) => {
			if (!res.ok) {
				let payload: any = null;
				try {
					payload = await res.json();
				} catch (_) {
					payload = await res.text();
				}
				throw payload;
			}
			return parseJsonSafe(res);
		})
		.catch((err) => {
			error = err;
			console.error(err);
			return null;
		});

	if (error) throw error;
	return res as Announcement;
};

export const deleteAnnouncement = async (token: string, id: string) => {
	let error: any = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/announcements/${id}`, {
		method: 'DELETE',
		headers: headers(token)
	})
		.then(async (res) => {
			if (!res.ok) {
				let payload: any = null;
				try {
					payload = await res.json();
				} catch (_) {
					payload = await res.text();
				}
				throw payload;
			}
			return parseJsonSafe(res);
		})
		.catch((err) => {
			error = err;
			console.error(err);
			return null;
		});

	if (error) throw error;
	return res as Announcement;
};

export const markAnnouncementsRead = async (token: string, ids: string[]) => {
	let error: any = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/announcements/read`, {
		method: 'POST',
		headers: headers(token),
		body: JSON.stringify({ ids })
	})
		.then(async (res) => {
			if (!res.ok) {
				let payload: any = null;
				try {
					payload = await res.json();
				} catch (_) {
					payload = await res.text();
				}
				throw payload;
			}
			return parseJsonSafe(res);
		})
		.catch((err) => {
			error = err;
			console.error(err);
			return null;
		});

	if (error) throw error;
	return res as { success: boolean; updated: number };
};

export const destroyAnnouncement = async (token: string, id: string) => {
	let error: any = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/announcements/${id}/hard`, {
		method: 'DELETE',
		headers: headers(token)
	})
		.then(async (res) => {
			if (!res.ok) {
				let payload: any = null;
				try {
					payload = await res.json();
				} catch (_) {
					payload = await res.text();
				}
				throw payload;
			}
			return parseJsonSafe(res);
		})
		.catch((err) => {
			error = err;
			console.error(err);
			return null;
		});

	if (error) throw error;
	return res as { success: boolean };
};
