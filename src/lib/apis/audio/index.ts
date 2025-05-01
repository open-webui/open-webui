import { audioApiClient } from '../clients';

type OpenAIConfigForm = {
	url: string;
	key: string;
	model: string;
	speaker: string;
};

interface AvailableModelsResponse {
	models: { name: string; id: string }[] | { id: string }[];
}

export const getAudioConfig = async (token: string) =>
	await audioApiClient.get('/audio/config', { token });

export const updateAudioConfig = async (token: string, payload: OpenAIConfigForm) =>
	await audioApiClient.post('/audio/config/update', payload, { token });

export const transcribeAudio = async (token: string, file: File) => {
	const data = new FormData();
	data.append('file', file);
	return await audioApiClient.post('/audio/transcriptions', data, { token });
};

export const synthesizeOpenAISpeech = async (
	token: string = '',
	speaker: string = 'alloy',
	text: string = '',
	model?: string
) =>
	await audioApiClient.post(
		'/audio/speech',
		{ input: text, voice: speaker, ...(model && { model }) },
		{ token }
	);

export const getModels = async (token: string = ''): Promise<AvailableModelsResponse> =>
	await audioApiClient.get('/audio/models', { token });

export const getVoices = async (token: string = '') =>
	await audioApiClient.get('/audio/voices', { token });
