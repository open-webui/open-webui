import { AUDIO_API_BASE_URL } from '$lib/constants';
import { ttsStreaming } from '$lib/stores';

export const getAudioConfig = async (token: string) => {
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
			console.log(err);
			error = err.detail;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

type OpenAIConfigForm = {
	url: string;
	key: string;
	model: string;
	speaker: string;
};

export const updateAudioConfig = async (token: string, payload: OpenAIConfigForm) => {
	let error = null;

	const res = await fetch(`${AUDIO_API_BASE_URL}/config/update`, {
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
			console.log(err);
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
			console.log(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const streamAudio = async (reader: any) => {	
	const ctx = new AudioContext({sampleRate: 24000}) 

	let time = ctx.currentTime


	function playChunk(pcm: any) {
		const samples = new Int16Array(pcm);
		const float32 = new Float32Array(samples.length)
		for (let i = 0; i < samples.length; i++) {
			float32[i] = samples[i] / 32768; // normalise 16 bit signed pcm samples into -1 to 1
		}

		const buffer = ctx.createBuffer(1, float32.length, 24000)
		buffer.getChannelData(0).set(float32)

		const source = ctx.createBufferSource()
		source.buffer = buffer
		source.connect(ctx.destination)
		const scheduledTime = Math.max(time, ctx.currentTime);
		source.start(scheduledTime)
		// time += buffer.duration
		time = scheduledTime + buffer.duration;
	}

	try {
		while (true) { 
			const { done, value } = await reader.read()
			if (done) {
				break;
			}
			playChunk(value.buffer)
		}
	} catch (error) {
		console.error("[streamAudio] Error during streaming:", error);
	} finally {
		// Important: Wait for the scheduled audio to finish playing
		// before closing the context and allowing the next sentence.
		// 'time' now holds the approximate end time of the last scheduled chunk.
		const timeToWait = (time - ctx.currentTime) * 1000; // Convert to milliseconds

		if (timeToWait > 0) {
			console.log(`[streamAudio] Waiting ${timeToWait.toFixed(0)}ms for audio to finish playing.`);
			await new Promise(resolve => setTimeout(resolve, Math.max(0, timeToWait)));
		}

		await ctx.close(); // Close the context to free up resources
		console.log('[streamAudio] AudioContext closed for sentence.');
	}
}

export const synthesizeStreamingSpeech = async (
	text: string = '',
) => {
	ttsStreaming.set(true)
	console.log('!!hitting tts endpoint with text', text)
	const response = await fetch('http://localhost:8002/tts?text=' + encodeURIComponent(text));

	if (!response.ok || !response.body) {
		console.log('!!response not ok', text)
		return
	} 
	
	const reader = response.body.getReader();

	console.log('!!returning reader')

	return reader
}


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

interface AvailableModelsResponse {
	models: { name: string; id: string }[] | { id: string }[];
}

export const getModels = async (token: string = ''): Promise<AvailableModelsResponse> => {
	let error = null;

	const res = await fetch(`${AUDIO_API_BASE_URL}/models`, {
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
			error = err.detail;
			console.log(err);

			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getVoices = async (token: string = '') => {
	let error = null;

	const res = await fetch(`${AUDIO_API_BASE_URL}/voices`, {
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
			error = err.detail;
			console.log(err);

			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};
