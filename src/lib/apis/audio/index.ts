import { AUDIO_API_BASE_URL } from '$lib/constants';

export const transcribeAudio = async (token: string, file: File) => {
	const data = new FormData();
	data.append('file', file);

	let error = null;
	const res = await fetch(`${AUDIO_API_BASE_URL}/transcribe`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			authorization: `Bearer ${token}`
		},
		body: data
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err.detail;
			console.log(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};
