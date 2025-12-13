import { VIDEO_API_BASE_URL } from '$lib/constants';

export type VideoStatus = {
	available: boolean;
	enabled: boolean;
	configured: boolean;
	redis_available: boolean;
	credits_required: boolean;
	default_model: string;
};

export type VideoGenerateResponse = {
	id: string;
	ext: string;
	media_type: string;
	data_url?: string | null;
	play_url: string;
	download_url: string;
	charged?: boolean;
};

export type VideoConfig = {
	ENABLE_VIDEO_GENERATION: boolean;
	VIDEO_API_BASE_URL: string;
	VIDEO_API_KEY: string;
	VIDEO_API_GENERATE_PATH: string;
	VIDEO_MODEL: string;
};

export const getVideoStatus = async (token: string = ''): Promise<VideoStatus> => {
	let error: string | null = null;

	const res = await fetch(`${VIDEO_API_BASE_URL}/status`, {
		method: 'GET',
		credentials: 'include',
		headers: {
			'Content-Type': 'application/json',
			...(token && { Authorization: `Bearer ${token}` })
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			error = err?.detail ?? 'Server connection failed';
			return null;
		});

	if (error) throw error;
	return res;
};

export const getVideoConfig = async (token: string = ''): Promise<VideoConfig> => {
	let error: string | null = null;

	const res = await fetch(`${VIDEO_API_BASE_URL}/config`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			...(token && { Authorization: `Bearer ${token}` })
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			error = err?.detail ?? 'Server connection failed';
			return null;
		});

	if (error) throw error;
	return res;
};

export const updateVideoConfig = async (token: string = '', payload: VideoConfig): Promise<VideoConfig> => {
	let error: string | null = null;

	const res = await fetch(`${VIDEO_API_BASE_URL}/config/update`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			...(token && { Authorization: `Bearer ${token}` })
		},
		body: JSON.stringify(payload)
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			error = err?.detail ?? 'Server connection failed';
			return null;
		});

	if (error) throw error;
	return res;
};

export const generateVideo = async (
	token: string = '',
	payload: { prompt: string; model?: string }
): Promise<VideoGenerateResponse> => {
	let error: string | null = null;

	const res = await fetch(`${VIDEO_API_BASE_URL}/generate`, {
		method: 'POST',
		credentials: 'include',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			...(token && { Authorization: `Bearer ${token}` })
		},
		body: JSON.stringify(payload)
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			error = err?.detail ?? 'Server connection failed';
			return null;
		});

	if (error) throw error;
	return res;
};
