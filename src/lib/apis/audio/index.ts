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

const DEFAULT_SAMPLE_RATE = 48000; // 24000 for orpheus
const START_FADE_S = 0.03; // 30ms fade-in for the very start of a stream
const END_FADE_S = 0.03;   // 30ms fade-out for the very end of a stream
const GRACE_MS = 50;
const VERY_LOW_GAIN = 0.00001; // Closer to zero for exponential ramp
const DC_OFFSET_THRESHOLD = 0.005;

export const streamAudio = async (reader) => { // Removed isFirstSentenceInSequence, as each call is a "new stream"
    const ctx = new AudioContext({ sampleRate: DEFAULT_SAMPLE_RATE });
    // Start scheduling slightly in the future to give context and gain ramp time
    let nextPlayTime = ctx.currentTime + 0.01; // Start scheduling 10ms into the future
    let firstChunkProcessed = false;
    let lastGainNode = null;
    let lastChunkEndTime = 0;

    console.log(`[streamAudio] New Stream START. Initial ctx.currentTime: ${ctx.currentTime.toFixed(3)}, Scheduling starts at: ${nextPlayTime.toFixed(3)}`);

    // Pre-set the destination gain to 0 if we anticipate a fade-in.
    // This helps ensure silence before the first sound if there's any scheduling delay.
    // However, gain nodes are per-source, so the main thing is the first source's gain.

    try {
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const pcmData = value.buffer;
            let samples = new Int16Array(pcmData);
            let float32 = new Float32Array(samples.length);
            let sum = 0;
            for (let i = 0; i < samples.length; i++) {
                float32[i] = samples[i] / 32768;
                sum += float32[i];
            }

            const dcOffset = sum / float32.length;
            if (Math.abs(dcOffset) > DC_OFFSET_THRESHOLD) {
                for (let i = 0; i < float32.length; i++) float32[i] -= dcOffset;
            }

            const audioBuffer = ctx.createBuffer(1, float32.length, DEFAULT_SAMPLE_RATE);
            audioBuffer.getChannelData(0).set(float32);

            const sourceNode = ctx.createBufferSource();
            sourceNode.buffer = audioBuffer;
            const gainNode = ctx.createGain();
            sourceNode.connect(gainNode);
            gainNode.connect(ctx.destination);

            // 'scheduleTime' is when this specific chunk will start playing
            const scheduleTime = Math.max(nextPlayTime, ctx.currentTime); // Ensure not in past

            if (!firstChunkProcessed) {
                // **CRITICAL FADE-IN FOR THE VERY FIRST CHUNK OF THE STREAM**
                gainNode.gain.setValueAtTime(VERY_LOW_GAIN, ctx.currentTime); // Ensure gain is low NOW
                gainNode.gain.setValueAtTime(VERY_LOW_GAIN, scheduleTime);    // Explicitly set to VERY_LOW_GAIN at scheduled start
                gainNode.gain.exponentialRampToValueAtTime(1, scheduleTime + START_FADE_S);
                console.log(`[streamAudio] FIRST CHUNK FADE-IN: Scheduled at ${scheduleTime.toFixed(3)}, Ramp ends ${(scheduleTime + START_FADE_S).toFixed(3)}`);
                firstChunkProcessed = true;
            } else {
                gainNode.gain.setValueAtTime(1, scheduleTime); // Full gain for subsequent chunks
            }

            sourceNode.start(scheduleTime);
            nextPlayTime = scheduleTime + audioBuffer.duration;
            lastGainNode = gainNode;
            lastChunkEndTime = nextPlayTime;
        }

        // After loop: if we processed any chunks, apply fade-OUT to the last one
        if (lastGainNode) {
            const fadeOutStartTime = lastChunkEndTime - END_FADE_S;
            const now = ctx.currentTime;
            const effectiveRampStartTime = Math.max(now, fadeOutStartTime);
            const effectiveRampEndTime = effectiveRampStartTime + END_FADE_S;

            // Ensure gain is 1 before ramp starts
            lastGainNode.gain.setValueAtTime(1, effectiveRampStartTime);
            lastGainNode.gain.exponentialRampToValueAtTime(VERY_LOW_GAIN, effectiveRampEndTime);
            console.log(`[streamAudio] LAST CHUNK FADE-OUT: Ramp starts ${effectiveRampStartTime.toFixed(3)}, Ramp ends ${effectiveRampEndTime.toFixed(3)}`);
            nextPlayTime = Math.max(nextPlayTime, effectiveRampEndTime);
        }

    } catch (error) {
        console.error("[streamAudio] Error:", error);
    } finally {
        const timeToWaitMs = (nextPlayTime - ctx.currentTime) * 1000;
        if (timeToWaitMs > 0) {
            console.log(`[streamAudio] Waiting ${timeToWaitMs.toFixed(0)}ms for audio to complete.`);
            await new Promise(resolve => setTimeout(resolve, Math.max(0, timeToWaitMs)));
        }
        if (GRACE_MS > 0) {
             console.log(`[streamAudio] Grace period: ${GRACE_MS}ms.`);
            await new Promise(resolve => setTimeout(resolve, GRACE_MS));
        }
        await ctx.close();
        console.log(`[streamAudio] Stream END. Context closed. Final scheduled time: ${nextPlayTime.toFixed(3)}`);
    }
};


export const synthesizeStreamingSpeech = async (
	text: string = '',
) => {
	ttsStreaming.set(true)
	console.log('!!hitting tts endpoint with text', text)

	const response = await fetch('http://localhost:8002/deepdub', {
		method: 'POST',
		headers: {
		  'Content-Type': 'application/json',
		},
		body: JSON.stringify({ text: text }), // Send data in the body as a JSON string
	  });

	// const response = await fetch('http://localhost:8002/deepdub?text=' + encodeURIComponent(text));

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
