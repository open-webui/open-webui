type QuietState = {
	connectionState: 'idle' | 'connecting' | 'connected' | 'error' | 'closed';
	overlayErrorMessage: string;
	isReconnecting: boolean;
	isContextPreparing: boolean;
	isToolCalling: boolean;
	isUserSpeaking: boolean;
	isAssistantSpeaking: boolean;
};

type AudioRuntimeOptions = {
	getQuietState: () => QuietState;
	onLocalRmsLevel: (level: number) => void;
	onAssistantAudioStarted: () => void;
	onAssistantAudioQuiet: () => void;
};

const REMOTE_AUDIO_ACTIVE_RMS = 0.008;
const REMOTE_AUDIO_SILENCE_DELAY_MS = 550;

export function createRealtimeAudioRuntime(options: AudioRuntimeOptions) {
	let audioContext: AudioContext | null = null;
	let analyserNode: AnalyserNode | null = null;
	let localAudioSourceNode: MediaStreamAudioSourceNode | null = null;
	let remoteAnalyserNode: AnalyserNode | null = null;
	let remoteAudioSourceNode: MediaStreamAudioSourceNode | null = null;
	let remoteStream: MediaStream | null = null;
	let rmsAnimationFrame: number | null = null;
	let remoteRmsAnimationFrame: number | null = null;
	let toolPingTimeout: ReturnType<typeof setTimeout> | null = null;
	let remoteQuietTimeout: ReturnType<typeof setTimeout> | null = null;
	let quietWindowOpenTimeout: ReturnType<typeof setTimeout> | null = null;
	let assistantAudioActive = false;
	let assistantOutputObserved = false;
	let quietWindowLatched = false;

	function stopRemoteQuietTimeout() {
		if (remoteQuietTimeout !== null) {
			clearTimeout(remoteQuietTimeout);
			remoteQuietTimeout = null;
		}
	}

	function stopQuietWindowOpenTimeout() {
		if (quietWindowOpenTimeout !== null) {
			clearTimeout(quietWindowOpenTimeout);
			quietWindowOpenTimeout = null;
		}
	}

	function invalidateQuietWindow(resetAssistantOutput = false) {
		quietWindowLatched = false;
		stopRemoteQuietTimeout();
		stopQuietWindowOpenTimeout();
		if (resetAssistantOutput) {
			assistantOutputObserved = false;
			assistantAudioActive = false;
		}
	}

	function isQuietWindowOpenable() {
		const state = options.getQuietState();
		return (
			state.connectionState === 'connected' &&
			!state.overlayErrorMessage &&
			!state.isReconnecting &&
			!state.isContextPreparing &&
			!state.isToolCalling &&
			!state.isUserSpeaking &&
			!assistantAudioActive &&
			!state.isAssistantSpeaking
		);
	}

	function emitQuietWindowOpen() {
		if (quietWindowLatched || !isQuietWindowOpenable()) {
			return;
		}

		quietWindowLatched = true;
		assistantOutputObserved = false;
	}

	function scheduleQuietWindowOpen(delayMs = 0) {
		stopQuietWindowOpenTimeout();
		if (quietWindowLatched) {
			return;
		}

		quietWindowOpenTimeout = setTimeout(() => {
			quietWindowOpenTimeout = null;
			emitQuietWindowOpen();
		}, delayMs);
	}

	function markAssistantAudioStarted() {
		assistantOutputObserved = true;
		assistantAudioActive = true;
		invalidateQuietWindow();
		options.onAssistantAudioStarted();
	}

	function handleAssistantAudioQuiet() {
		assistantAudioActive = false;
		stopRemoteQuietTimeout();
		options.onAssistantAudioQuiet();
		scheduleQuietWindowOpen();
	}

	function startLocalRmsMonitoring(stream: MediaStream) {
		audioContext = new AudioContext();
		localAudioSourceNode = audioContext.createMediaStreamSource(stream);
		analyserNode = audioContext.createAnalyser();
		analyserNode.fftSize = 256;
		localAudioSourceNode.connect(analyserNode);

		const dataArray = new Float32Array(analyserNode.fftSize);
		const tick = () => {
			if (!analyserNode) return;
			analyserNode.getFloatTimeDomainData(dataArray);
			let sum = 0;
			for (const value of dataArray) sum += value * value;
			options.onLocalRmsLevel(Math.sqrt(sum / dataArray.length));
			rmsAnimationFrame = requestAnimationFrame(tick);
		};
		tick();
	}

	function startRemoteAudioMonitoring(stream: MediaStream) {
		stopRemoteAudioMonitoring();
		remoteStream = stream;
		if (!audioContext) {
			audioContext = new AudioContext();
		}

		try {
			if (audioContext.state === 'suspended') {
				void audioContext.resume().catch(() => {});
			}
		} catch {
			// Ignore resume failures; monitor still has onplaying fallback.
		}

		remoteAudioSourceNode = audioContext.createMediaStreamSource(stream);
		remoteAnalyserNode = audioContext.createAnalyser();
		remoteAnalyserNode.fftSize = 256;
		remoteAudioSourceNode.connect(remoteAnalyserNode);

		const dataArray = new Float32Array(remoteAnalyserNode.fftSize);
		const tick = () => {
			if (!remoteAnalyserNode) return;
			remoteAnalyserNode.getFloatTimeDomainData(dataArray);
			let sum = 0;
			for (const value of dataArray) sum += value * value;
			const rms = Math.sqrt(sum / dataArray.length);

			if (rms >= REMOTE_AUDIO_ACTIVE_RMS) {
				stopRemoteQuietTimeout();
				if (!assistantAudioActive) {
					markAssistantAudioStarted();
				}
			} else if (assistantAudioActive && remoteQuietTimeout === null) {
				remoteQuietTimeout = setTimeout(() => {
					remoteQuietTimeout = null;
					if (
						assistantAudioActive &&
						!options.getQuietState().isToolCalling &&
						!options.getQuietState().isUserSpeaking
					) {
						handleAssistantAudioQuiet();
					}
				}, REMOTE_AUDIO_SILENCE_DELAY_MS);
			}

			remoteRmsAnimationFrame = requestAnimationFrame(tick);
		};
		tick();
	}

	function stopRemoteAudioMonitoring() {
		stopRemoteQuietTimeout();
		if (remoteRmsAnimationFrame !== null) {
			cancelAnimationFrame(remoteRmsAnimationFrame);
			remoteRmsAnimationFrame = null;
		}

		if (remoteAudioSourceNode) {
			try {
				remoteAudioSourceNode.disconnect();
			} catch {
				// Ignore cleanup failures
			}
			remoteAudioSourceNode = null;
		}

		if (remoteAnalyserNode) {
			try {
				remoteAnalyserNode.disconnect();
			} catch {
				// Ignore cleanup failures
			}
			remoteAnalyserNode = null;
		}

		if (remoteStream) {
			remoteStream.getAudioTracks().forEach((track) => {
				track.onmute = null;
				track.onunmute = null;
			});
			remoteStream = null;
		}

		assistantAudioActive = false;
	}

	function stopToolPingLoop() {
		if (toolPingTimeout !== null) {
			clearTimeout(toolPingTimeout);
			toolPingTimeout = null;
		}
	}

	async function playToolPing() {
		if (!audioContext) return;

		try {
			if (audioContext.state === 'suspended') {
				await audioContext.resume();
			}

			const startTime = audioContext.currentTime + 0.02;
			const gainNode = audioContext.createGain();
			gainNode.connect(audioContext.destination);
			gainNode.gain.setValueAtTime(0, startTime);
			gainNode.gain.linearRampToValueAtTime(0.045, startTime + 0.01);
			gainNode.gain.exponentialRampToValueAtTime(0.0001, startTime + 0.32);

			const firstOsc = audioContext.createOscillator();
			firstOsc.type = 'sine';
			firstOsc.frequency.setValueAtTime(960, startTime);
			firstOsc.frequency.exponentialRampToValueAtTime(520, startTime + 0.2);
			firstOsc.connect(gainNode);
			firstOsc.start(startTime);
			firstOsc.stop(startTime + 0.22);

			const secondOsc = audioContext.createOscillator();
			secondOsc.type = 'sine';
			secondOsc.frequency.setValueAtTime(1320, startTime + 0.24);
			secondOsc.frequency.exponentialRampToValueAtTime(820, startTime + 0.44);
			secondOsc.connect(gainNode);
			secondOsc.start(startTime + 0.24);
			secondOsc.stop(startTime + 0.46);

			secondOsc.onended = () => {
				try {
					firstOsc.disconnect();
					secondOsc.disconnect();
					gainNode.disconnect();
				} catch {
					// Ignore cleanup failures
				}
			};
		} catch {
			// Ignore ping playback failures
		}
	}

	function startToolPingLoop() {
		if (toolPingTimeout !== null) {
			return;
		}

		void playToolPing();
		const loop = () => {
			toolPingTimeout = setTimeout(() => {
				const state = options.getQuietState();
				if (
					state.connectionState !== 'connected' ||
					!state.isToolCalling ||
					state.isAssistantSpeaking ||
					state.isUserSpeaking
				) {
					stopToolPingLoop();
					return;
				}

				void playToolPing();
				loop();
			}, 1400);
		};
		loop();
	}

	function stopToolPing() {
		stopToolPingLoop();
	}

	function syncToolPingLoop() {
		const state = options.getQuietState();
		const shouldPlayPing =
			state.connectionState === 'connected' &&
			state.isToolCalling &&
			!state.isAssistantSpeaking &&
			!state.isUserSpeaking;

		if (!shouldPlayPing) {
			stopToolPingLoop();
			return;
		}

		startToolPingLoop();
	}

	async function release(audioElement: HTMLAudioElement | null) {
		stopToolPingLoop();

		if (rmsAnimationFrame !== null) {
			cancelAnimationFrame(rmsAnimationFrame);
			rmsAnimationFrame = null;
		}
		if (remoteRmsAnimationFrame !== null) {
			cancelAnimationFrame(remoteRmsAnimationFrame);
			remoteRmsAnimationFrame = null;
		}
		stopRemoteQuietTimeout();
		stopQuietWindowOpenTimeout();

		if (localAudioSourceNode) {
			try {
				localAudioSourceNode.disconnect();
			} catch {
				// Ignore cleanup failures
			}
			localAudioSourceNode = null;
		}
		stopRemoteAudioMonitoring();

		if (audioContext) {
			await audioContext.close().catch(() => {});
			audioContext = null;
			analyserNode = null;
		}

		if (audioElement) {
			audioElement.srcObject = null;
		}
	}

	return {
		startLocalRmsMonitoring,
		startRemoteAudioMonitoring,
		stopRemoteAudioMonitoring,
		invalidateQuietWindow,
		scheduleQuietWindowOpen,
		markAssistantAudioStarted,
		stopToolPing,
		startToolPingLoop,
		syncToolPingLoop,
		release,
		isAssistantAudioActive: () => assistantAudioActive,
		hasAssistantOutputObserved: () => assistantOutputObserved
	};
}
