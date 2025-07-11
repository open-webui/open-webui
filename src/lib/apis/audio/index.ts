import { AUDIO_API_BASE_URL } from '$lib/constants';
import { fillerEventStartTime, ttsSentenceQueue, ttsStreaming, ttsState, prefetchedReader } from '$lib/stores';
import { get } from 'svelte/store';

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

const ctx = new AudioContext({ sampleRate: DEFAULT_SAMPLE_RATE });


export const streamAudio = async (reader) => { // Removed isFirstSentenceInSequence, as each call is a "new stream"
    // Start scheduling slightly in the future to give context and gain ramp time
    let nextPlayTime = ctx.currentTime + 0.01; // Start scheduling 10ms into the future
    let firstChunkProcessed = false;
    let lastGainNode = null;
    let lastChunkEndTime = 0;

    console.log(`[streamAudio] New Stream START. Initial ctx.currentTime: ${ctx.currentTime.toFixed(3)}, Scheduling starts at: ${nextPlayTime.toFixed(3)}`);

    // Pre-set the destination gain to 0 if we anticipate a fade-in.
    // This helps ensure silence before the first sound if there's any scheduling delay.
    // However, gain nodes are per-source, so the main thing is the first source's gain.

	let firstChunk = true
    try {

		if (ctx.state === 'suspended') {
			await ctx.resume();
		}

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
			if (value && firstChunk) {
				console.log(`!!!timer: time taken from hitting TTS endpoint to getting first chunk TTFA ${(performance.now() - startTimeForHittingTTS) / 1000}s`)
				firstChunk = false
			}


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
		// leave ctx open, do not close ctx to allow multiple audio to be played seamlessly within a user session
        console.log(`[streamAudio] Stream END. Final scheduled time: ${nextPlayTime.toFixed(3)}`);
    }
};

let startTimeForHittingTTS = 0

export const synthesizeStreamingSpeech = async (
	text: string = '',
) => {
	console.log(`hitting tts endpoint with text: `, text)

	const response = await fetch('http://localhost:8002/deepdub', {
		method: 'POST',
		headers: {
		  'Content-Type': 'application/json',
		},
		body: JSON.stringify({ text: text }),
	  });


	if (!response.ok || !response.body) {
		console.log('!!response not ok', text)
		return
	} 
	
	const reader = response.body.getReader();

	return reader
}

const audioCache = new Map();

async function playFillerPhrase(content: string) {
	let audioBuffer = audioCache.get(content);

	if (!audioBuffer) {
		const res = await synthesizeOpenAISpeech(
			localStorage.token,
			'',
			content,
			''
		)
		if (res) {
			console.log("Server Content-Type:", res.headers.get('Content-Type'));
            const arrayBuffer = await res.blob().then(b => b.arrayBuffer());
			audioBuffer = await ctx.decodeAudioData(arrayBuffer);
			audioCache.set(content, audioBuffer);
		}
	} else {
		console.log('loaded audioBuffer from cache')
	}

	if (audioBuffer) {
        await new Promise(resolve => {
            const source = ctx.createBufferSource();
			source.buffer = audioBuffer;
			source.connect(ctx.destination);
			source.onended = resolve; // Resolve the promise when playback finishes
			source.start();
        });
	}
}


export async function processTTSQueue(filler: boolean = false) {
	// Use get() to read the current value of stores outside of component context or .subscribe
	const isStreaming = get(ttsStreaming);
	const queue = get(ttsSentenceQueue);

	console.log(`[TTS QUEUE STORE] processTTSQueue called. isStreaming: ${isStreaming}, queue length: ${queue.length}`);

	if (isStreaming || queue.length === 0) {
		return;
	}

	ttsStreaming.set(true); // Mark TTS as busy

	let taskToProcess;
	// Update the store to remove the first item (dequeue)
	ttsSentenceQueue.update(currentQueue => {
		taskToProcess = currentQueue[0]; // Get the first item
		return currentQueue.slice(1);     // Return a new array without the first item
	});

	if (!taskToProcess) { // Should only happen if queue became empty concurrently (unlikely here)
		ttsStreaming.set(false);
		return;
	}

	console.log(`[TTS QUEUE STORE] Dequeued task for message ${taskToProcess.id}: "${taskToProcess.content}"`);

	try {
		if (get(ttsState)=== 'idle' && queue.length > 0) {
			if (taskToProcess.isFiller) {
				console.log('playing filler')
				ttsState.set('playing_filler');
				const fillerPlaybackPromise = playFillerPhrase(taskToProcess.content)
				
				// TODO: is it possible to prefetch here already if queue.length > 1?
				fillerPlaybackPromise.then(async () => {
					const readerPromise = get(prefetchedReader);

					if (get(ttsState) === 'prefetching' && readerPromise) {
						console.log('[Watcher] Filler ended, pre-fetched audio is ready.');
						ttsState.set('playing_main');
						const reader = await readerPromise;
						if (reader) await streamAudio(reader);
						ttsState.set('idle');
						prefetchedReader.set(null);
					} else {
						console.log('[Watcher] Filler ended, nothing was pre-fetched.');
						ttsState.set('idle');
					}
				})
			} else {
				ttsState.set('playing_main');
				const reader = await synthesizeStreamingSpeech(taskToProcess.content);
				if (reader) await streamAudio(reader);
				ttsState.set('idle');
			}
		}

		if (get(ttsState) === 'playing_filler' && queue.length > 0 && !queue[0].isFiller) {
			console.log('[Watcher] OPPORTUNITY! Pre-fetching main sentence while filler plays.');
			ttsState.set('prefetching');
	
			// Start fetching and store the promise so the .then() block above can find it.
			prefetchedReader.set(synthesizeStreamingSpeech(taskToProcess.content));
		}
	} catch (error) {
		console.error(`[TTS QUEUE STORE] Error fetching/streaming audio for "${taskToProcess.content}":`, error);
	} finally {
		ttsStreaming.set(false);
		console.log('[TTS QUEUE STORE] TTS is now free.');
		// Call processTTSQueue again to check if there are more items
		// This is crucial to continue processing if items were added while this one was busy.
		processTTSQueue()
	}
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
