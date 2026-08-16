type WebKitWindow = Window &
	typeof globalThis & {
		webkitAudioContext?: typeof AudioContext;
	};

let audioContext: AudioContext | null = null;
let activeSource: AudioBufferSourceNode | null = null;
let activeGain: GainNode | null = null;
let activeResolve: (() => void) | null = null;

const isIOS = () => {
	if (typeof navigator === 'undefined') {
		return false;
	}

	return (
		/iPad|iPhone|iPod/.test(navigator.userAgent) ||
		(navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1)
	);
};

const getAudioContextConstructor = () => {
	if (typeof window === 'undefined') {
		return null;
	}

	return (
		window.AudioContext ??
		(window as WebKitWindow).webkitAudioContext ??
		null
	);
};

/**
 * Unlock a persistent AudioContext while the browser is still handling
 * the user's Voice Mode gesture.
 *
 * This must be called synchronously from the click/touch handler, before
 * getUserMedia(), network requests, or any other awaited operation.
 */
export const unlockIOSCallAudio = () => {
	if (!isIOS()) {
		return;
	}

	const AudioContextConstructor = getAudioContextConstructor();

	if (!AudioContextConstructor) {
		return;
	}

	if (!audioContext || audioContext.state === 'closed') {
		audioContext = new AudioContextConstructor();

		// Start a silent buffer while user activation is still available.
		const buffer = audioContext.createBuffer(1, 1, audioContext.sampleRate);
		const source = audioContext.createBufferSource();

		source.buffer = buffer;
		source.connect(audioContext.destination);
		source.start();
	}

	if (audioContext.state === 'suspended') {
		void audioContext.resume().catch((error) => {
			console.debug('Unable to resume iOS call AudioContext:', error);
		});
	}
};

export const canUseIOSCallAudio = () =>
	isIOS() && audioContext !== null && audioContext.state !== 'closed';

export const stopIOSCallAudio = () => {
	const resolve = activeResolve;
	activeResolve = null;

	if (activeSource) {
		activeSource.onended = null;

		try {
			activeSource.stop();
		} catch {
			// Source may already have ended.
		}

		try {
			activeSource.disconnect();
		} catch {
			// Already disconnected.
		}

		activeSource = null;
	}

	if (activeGain) {
		try {
			activeGain.disconnect();
		} catch {
			// Already disconnected.
		}

		activeGain = null;
	}

	// Allow callers waiting for playback to continue after interruption.
	resolve?.();
};

export const playIOSCallAudio = async (
	url: string,
	playbackRate = 1,
	volume = 1
) => {
	if (!audioContext || audioContext.state === 'closed') {
		throw new Error('iOS call AudioContext has not been unlocked');
	}

	if (audioContext.state === 'suspended') {
		await audioContext.resume();
	}

	const response = await fetch(url);

	if (!response.ok) {
		throw new Error(`Unable to load call audio: HTTP ${response.status}`);
	}

	const encodedAudio = await response.arrayBuffer();
	const decodedAudio = await audioContext.decodeAudioData(encodedAudio.slice(0));

	stopIOSCallAudio();

	return await new Promise<void>((resolve, reject) => {
		if (!audioContext) {
			reject(new Error('iOS call AudioContext became unavailable'));
			return;
		}

		const source = audioContext.createBufferSource();
		const gain = audioContext.createGain();

		source.buffer = decodedAudio;
		source.playbackRate.value = playbackRate;
		gain.gain.value = volume;

		source.connect(gain);
		gain.connect(audioContext.destination);

		activeSource = source;
		activeGain = gain;
		activeResolve = resolve;

		source.onended = () => {
			if (activeSource === source) {
				activeSource = null;
			}

			if (activeGain === gain) {
				activeGain = null;
			}

			activeResolve = null;

			try {
				source.disconnect();
			} catch {
				// Already disconnected.
			}

			try {
				gain.disconnect();
			} catch {
				// Already disconnected.
			}

			resolve();
		};

		try {
			source.start();
		} catch (error) {
			activeSource = null;
			activeGain = null;
			activeResolve = null;

			reject(error);
		}
	});
};
