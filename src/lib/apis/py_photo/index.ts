import { PY_PHOTO_API_BASE_URL } from '$lib/constants';

export type PyPhotoGenerateResponse = {
	id: string;
	media_type: string;
	data_url: string;
	view_url: string;
	download_url: string;
};

export const generatePyPhoto = async (
	token: string = '',
	payload: { input: string; size?: number }
): Promise<PyPhotoGenerateResponse> => {
	let error: string | null = null;

	const res = await fetch(`${PY_PHOTO_API_BASE_URL}/generate`, {
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

