import { AUDIO_API_BASE_URL } from '$lib/constants';
import { toast } from 'svelte-sonner';
import { AllTalkConfigForm, Alltalk } from '$lib/apis/audio/providers/alltalk/Alltalk';

export const _alltalk: Alltalk = new Alltalk();

type TTSGeneralConfigForm = {
    ENGINE: string
    MODEL: string
    VOICE: string
}

type STTGeneralConfigForm = {
    ENGINE: string
    MODEL: string
}

type OpenAIConfigForm = {
	OPENAI_API_BASE_URL: string;
	OPENAI_API_KEY: string;
};

type TTSConfigForm = {
	openai : OpenAIConfigForm,
	alltalk: AllTalkConfigForm,
	general: TTSGeneralConfigForm
}

type STTConfigForm = {
	openai : OpenAIConfigForm,
	general: STTGeneralConfigForm
}

type AudioConfigUpdateForm = {
	tts: TTSConfigForm,
	stt: STTConfigForm
}

export enum ConfigMode {
	TTS = 'tts',
	STT = 'stt'
}

export const getAudioConfig  = async (token: string): Promise<AudioConfigUpdateForm> => {
	let error = null;

	const res = await fetch(`${AUDIO_API_BASE_URL}/config`, {
		method: 'GET',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			error = err.detail;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const updateAlltalkAudioConfig = async (token: string, alltalkInstance: Alltalk): Promise<AllTalkConfigForm> => {
	const res = updateAudioConfig('alltalk', ConfigMode.TTS, token, alltalkInstance.getConfigPayload());
	if(!res){
		const message = 'Alltalk Audio settings update failed';
		toast.error(message);
	}
	return res;
};

export const updateOpenAIAudioConfig = async (token: string, mode: ConfigMode, payload: OpenAIConfigForm) => {
	const res = updateAudioConfig('openai', mode, token, payload);
	if(!res){
		const message = `Open AI Audio ${mode} settings update failed`;
		toast.error(message);
	}
	return res;
};

export const updateGeneralAudioConfig = async (token: string, mode: ConfigMode, payload: TTSGeneralConfigForm | STTGeneralConfigForm) => {
	const res = updateAudioConfig('general', mode, token, payload);
	if(!res){
		const message = `General Audio ${mode} settings update failed`;
		toast.error(message);
	}
	return res;
};

export const updateAudioConfig = async (provider: string, mode: ConfigMode, token: string, payload: object) => {
	let error = null;

	console.log("updateAudioConfig: ", provider, token, payload);

	const res = await fetch(`${AUDIO_API_BASE_URL}/${provider}/${mode}/config/update`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			...payload
		})
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			error = err.detail;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const transcribeAudio = async (token: string, file: File) => {
	const data = new FormData();
	data.append('file', file);

	let error = null;
	const res = await fetch(`${AUDIO_API_BASE_URL}/transcriptions`, {
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
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const synthesizeOpenAISpeech = async (
	token: string = '',
	speaker: string = 'alloy',
	text: string = '',
	model?: string
) => {
	let error = null;

	const res = await fetch(`${AUDIO_API_BASE_URL}/openai/speech`, {
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
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};
