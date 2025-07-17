import { AUDIO_API_BASE_URL } from '$lib/constants';
import { fillerEventStartTime, ttsSentenceQueue, ttsStreaming, ttsState, prefetchedReader, readyToPlayQueue } from '$lib/stores';
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


export const streamAudio = async (reader, timestamp) => { // Removed isFirstSentenceInSequence, as each call is a "new stream"
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

			if (firstChunk && value) {
				console.log(`[Processor] Starting to stream from ready queue with delay of ${Date.now() - timestamp}`)
				firstChunk = false
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

	const response = await fetch(`${AUDIO_API_BASE_URL}/speech/deepdub`, {
		method: 'POST',
		headers: {
			Authorization: `Bearer ${localStorage.token}`,
			'Content-Type': 'application/json'
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

let isPlaying = false;

// first process processReadyToPlayQueue2
//     1     streamAudio -> processReadyToPlayQueue2, isplaying = false -> processReadyToPlayQueue2 and dies
//     2          processReadyToPlayQueue2 -> dies
//     3

// get(readyToPlayQueue).length === 0
export async function processReadyToPlayQueue() {
	if (isPlaying) return;
	isPlaying = true;

	try {
		const audioToPlay = get(readyToPlayQueue)?.[0]; // index 0 because we want to get the first item
		if (!audioToPlay) return;

		console.log(`[Processor] Playing from ready queue: "${audioToPlay.content}"`);
		await streamAudio(audioToPlay.reader, Date.now());
		console.log(`[Processor] Finished: "${audioToPlay.content}"`);
		readyToPlayQueue.update(q => q.slice(1));
	} finally {
		isPlaying = false;

		if (get(readyToPlayQueue).length > 0) {
			await processReadyToPlayQueue();
		}
	}
}

/**
 * - check if there is anything to play
 * - read from readyToPlayQueue
 * - play audio
 */


// queue: ['this is my filler text',]
// queue: []
// queue: ['hello my name is serena']
// queue: []
export async function processTTSQueue() {
	try {
		// if (isProcessing) return;
		// isProcessing = true;

		console.log(`processTTSQueue get(ttsSentenceQueue).length ${get(ttsSentenceQueue).length} get(readyToPlayQueue).length ${get(readyToPlayQueue).length}`)
		const textQueue = get(ttsSentenceQueue);

		if (textQueue.length) {
			// always begin by playing filler
			const textToPlay = textQueue[0]

			if (textToPlay.isFiller) {
				ttsSentenceQueue.update(q => q.slice(1)); // dequeue chunk to be processed - do we want to do this _after_ we've processed in case of failed generations?
				console.log(`[Processor] Playing standalone filler: "${textToPlay.content}"`);
				// await playFillerPhrase(fillerText.content) // this is currently blocking
				isPlaying = true
				await playFillerPhrase(textToPlay.content)
				console.log("yay we're done")
				isPlaying = false
				processReadyToPlayQueue()
				// return
			} else {
				// backup: if we have a single audio 
				synthesizeAudioIfExists()
			}

		}
	} catch (error) {
		console.error("[Processor] An error occurred in the processing loop:", error);
	} finally {
		console.log("[Processor] All work is done. Processor is now idle.");
		// isProcessing = false;
	}
}

export async function synthesizeAudioIfExists() {
	const textQueue = get(ttsSentenceQueue);
	console.log(`[Processor] synthesizeaudioifexists "${textQueue}"`);

	if (!textQueue.length) {
		return
	}

	const textToPlay = textQueue[0]

	if (textToPlay.isFiller) {
		return
	}

	ttsSentenceQueue.update(q => q.slice(1));
	console.log(`[Processor] Priming pipeline with: "${textToPlay.content}"`);
	const reader = await synthesizeStreamingSpeech(textToPlay.content);
	if (reader) {
		// make the update to the readyToPlayQueue to get the processReadyToPlayQueue function reacting
		readyToPlayQueue.update(q => [...q, { reader, content: textToPlay.content }]);
	}
}

// this tries to address the pause in between sentences by prefetching every sentence if possible but it makes the audio overlap
// export async function processTTSQueue(state, currentQueue, readyQueue) {

//     // --- HIGH-PRIORITY ACTION: Handle Fillers ---
//     // If there's a filler phrase at the front of the queue, play it immediately,
//     if (currentQueue.length > 0 && currentQueue[0].isFiller) {
//         ttsState.set('playing_filler'); 

//         const fillerTask = currentQueue[0];
//         ttsSentenceQueue.update(q => q.slice(1));

//         console.log(`[Filler] Playing high-priority filler: "${fillerTask.content}"`);
//         await playFillerPhrase(fillerTask.content);
//         console.log('[Filler] Finished filler playback.');

//         // This will re-trigger the watcher, allowing it to continue with the producer/consumer logic.
//         ttsState.set('idle');
//         return;
//     }

//     // --- PRODUCER LOGIC ---
//     // If we are not busy playing and there's text to fetch, start fetching.
//     // We can fetch even while another clip is playing.
//     const shouldFetch = state !== 'fetching' && currentQueue.length > 0;

//     if (shouldFetch) {
//         ttsState.set('fetching');

//         const task = currentQueue[0];
//         ttsSentenceQueue.update(q => q.slice(1));

//         console.log(`[Fetcher] Fetching audio for: "${task.content}"`);
//         const reader = await synthesizeStreamingSpeech(task.content);
//         if (reader) {
//             readyToPlayQueue.update(q => [...q, { reader, content: task.content }]);
//         }

//         if (get(ttsState) === 'fetching') {
//             ttsState.set('idle');
//         }
//     }

//     // --- CONSUMER LOGIC ---
//     // If we are idle and have something ready to play, play it.
//     if (state === 'idle' && readyQueue.length > 0) {
//         ttsState.set('playing');

//         const audio = readyQueue[0];
//         readyToPlayQueue.update(q => q.slice(1));

//         console.log(`[Player] Playing: "${audio.content}"`);
//         await streamAudio(audio.reader);
//         console.log(`[Player] Finished: "${audio.content}"`);

//         // After playing, we are idle again. The watcher will re-run automatically on this state change.
//         ttsState.set('idle');
//     }
// }

// export async function processTTSQueue(currentState, currentQueue) {
// 	if (currentQueue.length > 0) {
// 		console.log(`[Watcher] Triggered. State: ${currentState}, Queue Length: ${currentQueue.length}, content: ${currentQueue[0].content}`);
// 	} else {
// 		console.log(`[Watcher] Triggered. State: ${currentState}, Queue Length: ${currentQueue.length}`);
// 	}


// 	////////////////////
// 	// scenario 1 play filler
// 	if(currentQueue[0].isFiller) {
// 		const task = currentQueue[0];
// 		ttsSentenceQueue.update(q => q.slice(1)); // Dequeue the task
// 		ttsState.set('playing_filler');
// 		await playFillerPhrase(task.content)
// 		ttsState.set('idle');
// 		return 
// 	} 

// 	// scenario 2 prefetch
// 	if ((currentState === 'playing_filler' && currentQueue.length > 0) || (currentState === 'playing_main' && currentQueue.length > 1)) {
// 		const taskToPrefetch = currentQueue[0];
// 		ttsSentenceQueue.update(q => q.slice(1));
// 		ttsState.set('prefetching');
// 		readyToPlayQueue.update(q => [...q, { reader: synthesizeStreamingSpeech(taskToPrefetch.content), content: taskToPrefetch.content }]);
// 	}

// 	// scenario 3 play from prefetched reader
// 	if (currentState.queue === 'idle') {
// 		const readyToPlayQueueTemp = get(readyToPlayQueue)
// 		ttsState.set('playing_main');
// 		console.log('[Watcher] playing main sentence');

// 		if (readyToPlayQueueTemp.length > 0) {
// 			const readerPromise = readyToPlayQueueTemp[0].reader
// 			readyToPlayQueue.update(q => q.slice(1));
// 			const reader = await readerPromise;
// 			if (reader) await streamAudio(reader);
// 		} else {
// 			const reader = await synthesizeStreamingSpeech(task.content);
// 			if (reader) await streamAudio(reader);
// 		}
// 		ttsState.set('idle');

// 	}

// 	///////////////////
// 	// // --- ACTION 1: The system is idle and work has appeared. ---
// 	// if (currentState === 'idle' && currentQueue.length > 0) {
// 	// 	const task = currentQueue[0];
// 	// 	ttsSentenceQueue.update(q => q.slice(1)); // Dequeue the task

// 	// 	if (task.isFiller) {
// 	// 		ttsState.set('playing_filler');

// 	// 		playFillerPhrase(task.content).then(async () => {
// 	// 			const finalState = get(ttsState);
// 	// 			const readerPromise = get(prefetchedReader);

// 	// 			// Case A: We successfully pre-fetched the next sentence.
// 	// 			if (finalState === 'prefetching' && readerPromise) {
// 	// 				console.log('[Watcher] Filler ended, pre-fetched audio is ready.');
// 	// 				ttsState.set('playing_main');
// 	// 				const reader = await readerPromise;
// 	// 				if (reader) await streamAudio(reader);
// 	// 				ttsState.set('idle'); // We are now idle
// 	// 				prefetchedReader.set(null); // Clean up
// 	// 			} 
// 	// 			// Case B: The filler finished and we did not pre-fetch anything.
// 	// 			else {
// 	// 				console.log('[Watcher] Filler ended, nothing was pre-fetched.');
// 	// 				ttsState.set('idle');
// 	// 			}
// 	// 		});

// 	// 	} else {
// 	// 		console.log('[Watcher] playing main sentence');
// 	// 		ttsState.set('playing_main');
// 	// 		const reader = await synthesizeStreamingSpeech(task.content);
// 	// 		if (reader) await streamAudio(reader);
// 	// 		ttsState.set('idle'); // We are now idle
// 	// 	}
// 	// }

// 	// // --- ACTION 2: We are playing a filler, and a main sentence just arrived. ---
// 	// if (currentState === 'playing_filler' && currentQueue.length > 0 && !currentQueue[0].isFiller) {
// 	// 	console.log('[Watcher] OPPORTUNITY! Pre-fetching main sentence while filler plays.');

// 	// 	const taskToPrefetch = currentQueue[0];
// 	// 	ttsSentenceQueue.update(q => q.slice(1)); // Dequeue the task we're pre-fetching

// 	// 	// Change state and start the fetch. DO NOT await.
// 	// 	// Store the promise so the `.then()` block above can access it.
// 	// 	ttsState.set('prefetching');
// 	// 	prefetchedReader.set(synthesizeStreamingSpeech(taskToPrefetch.content));
// 	// }
// }

// export async function processTTSQueue() {
//     const queue = get(ttsSentenceQueue);

//     // Guard Clause: If there's nothing to do, stop.
//     if (queue.length === 0) {
//         console.log('[Processor] Queue is empty. Going idle.');
//         ttsState.set('idle'); // Ensure we are idle
//         return;
//     }

//     // Dequeue the next task
//     const taskToProcess = queue[0];
//     ttsSentenceQueue.update(q => q.slice(1));

//     console.log(`[Processor] Dequeued: "${taskToProcess.content}"`);

//     try {
//         if (taskToProcess.isFiller) {
//             ttsState.set('playing_filler');
//             // Now, play the filler.
//             await playFillerPhrase(taskToProcess.content);
//             console.log('[Processor] Filler finished.');

//         } else { // The task is a main sentence
//             ttsState.set('playing_main');
//             const reader = await synthesizeStreamingSpeech(taskToProcess.content);
//             if (reader) await streamAudio(reader);
//         }
//     } catch (error) {
//         console.error(`[Processor] Error during processing:`, error);
//     }

//     // ---- CRITICAL FIX ----
//     // After ALL the work for this iteration is done,
//     // call the function again to process the next item.
//     // This is "asynchronous recursion" and is safe.
//     processTTSQueue();
// }

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
