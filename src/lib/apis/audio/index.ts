import { AUDIO_API_BASE_URL } from '$lib/constants';
import { doFormRequest, doGetRequest, doJSONRequest } from '$lib/apis/helpers';

export const getAudioConfig = async (token: string) => {
	return doGetRequest(`${AUDIO_API_BASE_URL}/config`, token);
};

type OpenAIConfigForm = {
	url: string;
	key: string;
	model: string;
	speaker: string;
};

export const updateAudioConfig = async (token: string, payload: OpenAIConfigForm) => {
	return doJSONRequest(`${AUDIO_API_BASE_URL}/config/update`, token, payload);
};

export const transcribeAudio = async (token: string, file: File) => {
	const data = new FormData();
	data.append('file', file);
	return doFormRequest(`${AUDIO_API_BASE_URL}/transcriptions`, token, data);
};

export const synthesizeOpenAISpeech = async (
	token: string = '',
	speaker: string = 'alloy',
	text: string = '',
	model: string = 'tts-1'
) => {
	return doJSONRequest(`${AUDIO_API_BASE_URL}/speech`, token, {
		model: model,
		input: text,
		voice: speaker
	});
};
