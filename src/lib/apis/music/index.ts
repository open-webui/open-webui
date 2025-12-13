import { MUSIC_API_BASE_URL } from '$lib/constants';

export type MusicStatus = {
	available: boolean;
	enabled: boolean;
	configured: boolean;
	redis_available: boolean;
	credits_required: boolean;
	default_model: string;
};

export type MusicGenerateResponse = {
	id: string;
	ext: string;
	media_type: string;
	data_url?: string | null;
	play_url: string;
	download_url: string;
	charged?: boolean;
};

export type MusicConfig = {
	ENABLE_MUSIC_GENERATION: boolean;
	MUSIC_API_BASE_URL: string;
	MUSIC_API_KEY: string;
	MUSIC_API_GENERATE_PATH: string;
	MUSIC_MODEL: string;
};

export const getMusicStatus = async (token: string = ''): Promise<MusicStatus> => {
	let error: string | null = null;

	const res = await fetch(`${MUSIC_API_BASE_URL}/status`, {
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

export const getMusicConfig = async (token: string = ''): Promise<MusicConfig> => {
	let error: string | null = null;

	const res = await fetch(`${MUSIC_API_BASE_URL}/config`, {
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

export const updateMusicConfig = async (token: string = '', payload: MusicConfig): Promise<MusicConfig> => {
	let error: string | null = null;

	const res = await fetch(`${MUSIC_API_BASE_URL}/config/update`, {
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

export const generateMusic = async (
	token: string = '',
	payload: { prompt: string; model?: string }
): Promise<MusicGenerateResponse> => {
	let error: string | null = null;

	const res = await fetch(`${MUSIC_API_BASE_URL}/generate`, {
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
