import { AUDIO_API_BASE_URL } from '$lib/constants';
import { formRequest, getRequest, jsonRequest } from '$lib/apis/helpers';

export const getAudioConfig = async (token: string) => {
	return getRequest(`${AUDIO_API_BASE_URL}/config`, token);
};

type OpenAIConfigForm = {
	url: string;
	key: string;
	model: string;
	speaker: string;
};

export const updateAudioConfig = async (token: string, payload: OpenAIConfigForm) => {
	return jsonRequest(`${AUDIO_API_BASE_URL}/config/update`, token, payload);
};

export const transcribeAudio = async (token: string, file: File) => {
	const data = new FormData();
	data.append('file', file);
	return formRequest(`${AUDIO_API_BASE_URL}/transcriptions`, token, data);
};

export const synthesizeOpenAISpeech = async (
	token: string = '',
	speaker: string = 'alloy',
	text: string = '',
	model?: string
) => {
	let error = null;

	const res = await fetch(`${AUDIO_API_BASE_URL}/speech`, {
		method: 'POST',
		headers: {
			Authorization: `Bearer ${token}`,
			'Content-Type': 'application/json'
		},
		body: JSON.stringify({
			input: text,
			voice: speaker,
			...(model && { model })
		})
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res;
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
