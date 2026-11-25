<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { tick, getContext, onMount, onDestroy } from 'svelte';
	import { config, settings } from '$lib/stores';
	import { blobToFile, calculateSHA256, extractCurlyBraceWords } from '$lib/utils';

	import { transcribeAudio } from '$lib/apis/audio';
	import XMark from '$lib/components/icons/XMark.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';

	import dayjs from 'dayjs';

	const i18n = getContext<typeof import('$lib/i18n').default>('i18n');

	export let recording = false;
	export let transcribe = true;
	export let displayMedia = false;

	export let echoCancellation = true;
	export let noiseSuppression = true;
	export let autoGainControl = true;

	export let className = 'w-full max-w-full';

	export let confirmButtonId = 'confirm-recording-button';
	export let onCancel = () => {};
	export let onConfirm = (data) => {};

	let loading = false;
	let confirmed = false;

	let durationSeconds = 0;
	let durationCounter = null;

	let transcription = '';

	const startDurationCounter = () => {
		durationCounter = setInterval(() => {
			durationSeconds++;
		}, 1000);
	};

	const stopDurationCounter = () => {
		clearInterval(durationCounter);
		durationSeconds = 0;
	};

	$: if (recording) {
		startRecording();
	} else {
		stopRecording();
	}

	const formatSeconds = (seconds) => {
		const minutes = Math.floor(seconds / 60);
		const remainingSeconds = seconds % 60;
		const formattedSeconds = remainingSeconds < 10 ? `0${remainingSeconds}` : remainingSeconds;
		return `${minutes}:${formattedSeconds}`;
	};

	let wakeLock = null;

	const requestWakeLock = async () => {
		if ('wakeLock' in navigator) {
			try {
				wakeLock = await navigator.wakeLock.request('screen');
				console.log('Wake Lock acquired');

				wakeLock.addEventListener('release', () => {
					console.log('Wake Lock released');
				});
			} catch (err) {
				console.log('Wake Lock request failed:', err);
			}
		}
	};

	const releaseWakeLock = async () => {
		if (wakeLock) {
			try {
				await wakeLock.release();
			} catch (err) {
				console.log('Wake Lock release failed:', err);
			}
			wakeLock = null;
		}
	};

	let stream;
	let audioContext: AudioContext | null = null;
	let speechRecognition;

	let mediaRecorder;
	let audioChunks = [];

	const MIN_DECIBELS = -45;
	let VISUALIZER_BUFFER_LENGTH = 300;

	let visualizerData = Array(VISUALIZER_BUFFER_LENGTH).fill(0);

	// Function to calculate the RMS level from time domain data
	const calculateRMS = (data: Uint8Array) => {
		let sumSquares = 0;
		for (let i = 0; i < data.length; i++) {
			const normalizedValue = (data[i] - 128) / 128; // Normalize the data
			sumSquares += normalizedValue * normalizedValue;
		}
		return Math.sqrt(sumSquares / data.length);
	};

	const normalizeRMS = (rms) => {
		rms = rms * 10;
		const exp = 1.5; // Adjust exponent value; values greater than 1 expand larger numbers more and compress smaller numbers more
		const scaledRMS = Math.pow(rms, exp);

		// Scale between 0.01 (1%) and 1.0 (100%)
		return Math.min(1.0, Math.max(0.01, scaledRMS));
	};

	// Chrome on Android caps open audio outputs at 10.
	const closeAudioContext = () => {
		void audioContext?.close();
		audioContext = null;
	};

	const analyseAudio = (stream) => {
		audioContext = new AudioContext();
		const audioStreamSource = audioContext.createMediaStreamSource(stream);

		const analyser = audioContext.createAnalyser();
		analyser.minDecibels = MIN_DECIBELS;
		audioStreamSource.connect(analyser);

		const bufferLength = analyser.frequencyBinCount;

		const domainData = new Uint8Array(bufferLength);
		const timeDomainData = new Uint8Array(analyser.fftSize);

		let lastSoundTime = Date.now();
		// One bar per interval (the loudest frame in it) keeps the waveform scrolling calmly.
		const VISUALIZER_SAMPLE_MS = 40;
		let lastSampleTime = 0;
		let peakLevel = 0;

		const detectSound = () => {
			const processFrame = () => {
				if (!recording || loading) return;

				if (recording && !loading) {
					analyser.getByteTimeDomainData(timeDomainData);
					analyser.getByteFrequencyData(domainData);

					// Calculate RMS level from time domain data
					const rmsLevel = calculateRMS(timeDomainData);
					peakLevel = Math.max(peakLevel, normalizeRMS(rmsLevel));

					const now = performance.now();
					if (now - lastSampleTime >= VISUALIZER_SAMPLE_MS) {
						lastSampleTime = now;
						visualizerData.push(peakLevel);
						peakLevel = 0;

						// Ensure visualizerData array stays within the buffer length
						if (visualizerData.length >= VISUALIZER_BUFFER_LENGTH) {
							visualizerData.shift();
						}

						visualizerData = visualizerData;
					}

					// if (domainData.some((value) => value > 0)) {
					// 	lastSoundTime = Date.now();
					// }
				}

				window.requestAnimationFrame(processFrame);
			};

			window.requestAnimationFrame(processFrame);
		};

		detectSound();
	};

	const onStopHandler = async (audioBlob, ext: string = 'wav') => {
		// Create a blob from the audio chunks

		await tick();
		const file = blobToFile(audioBlob, `Recording-${dayjs().format('YYYY-MM-DD HH-mm-ss')}.${ext}`);

		if (transcribe) {
			if ($config.audio.stt.engine === 'web' || ($settings?.audio?.stt?.engine ?? '') === 'web') {
				// with web stt, we don't need to send the file to the server
				return;
			}

			const res = await transcribeAudio(
				localStorage.token,
				file,
				$settings?.audio?.stt?.language
			).catch((error) => {
				toast.error(`${error}`);
				return null;
			});

			if (res) {
				console.log(res);
				onConfirm(res);
			}
		} else {
			onConfirm({
				file: file,
				blob: audioBlob
			});
		}
	};

	const startRecording = async () => {
		loading = true;

		try {
			if (displayMedia) {
				const mediaStream = await navigator.mediaDevices.getDisplayMedia({
					audio: true
				});

				stream = new MediaStream();
				for (const track of mediaStream.getAudioTracks()) {
					stream.addTrack(track);
				}

				for (const track of mediaStream.getVideoTracks()) {
					track.stop();
				}
			} else {
				stream = await navigator.mediaDevices.getUserMedia({
					audio: {
						echoCancellation: echoCancellation,
						noiseSuppression: noiseSuppression,
						autoGainControl: autoGainControl
					}
				});
			}
		} catch (err) {
			console.error('Error accessing media devices.', err);
			toast.error($i18n.t('Error accessing media devices.'));
			loading = false;
			recording = false;
			return;
		}

		const mineTypes = [
			'audio/webm; codecs=opus',
			'audio/webm',
			'audio/ogg; codecs=opus',
			'audio/mp4',
			'audio/wav'
		];

		mediaRecorder = new MediaRecorder(stream, {
			mimeType: mineTypes.find((type) => MediaRecorder.isTypeSupported(type))
		});

		mediaRecorder.onstart = async () => {
			console.log('Recording started');
			loading = false;
			startDurationCounter();

			if (document.activeElement === document.body || !document.activeElement?.checkVisibility()) {
				await tick();
				document.getElementById(confirmButtonId)?.focus({ preventScroll: true });
			}

			await requestWakeLock();

			audioChunks = [];
			analyseAudio(stream);
		};
		mediaRecorder.ondataavailable = (event) => audioChunks.push(event.data);
		mediaRecorder.onstop = async () => {
			console.log('Recording stopped');

			if (confirmed) {
				// Use the actual type provided by MediaRecorder
				let type = audioChunks[0]?.type || mediaRecorder.mimeType || 'audio/webm';

				// split `/` and `;` to get the extension
				let ext = type.split('/')[1].split(';')[0] || 'webm';

				// If not audio, default to audio/webm
				if (!type.startsWith('audio/')) {
					ext = 'webm';
				}

				const audioBlob = new Blob(audioChunks, { type: type });
				await onStopHandler(audioBlob, ext);

				confirmed = false;
				loading = false;
			}

			audioChunks = [];
			recording = false;
		};

		try {
			mediaRecorder.start();
		} catch (error) {
			console.error('Error starting recording:', error);
			toast.error($i18n.t('Error starting recording.'));
			loading = false;
			recording = false;
			return;
		}

		if (transcribe) {
			if ($config.audio.stt.engine === 'web' || ($settings?.audio?.stt?.engine ?? '') === 'web') {
				if ('SpeechRecognition' in window || 'webkitSpeechRecognition' in window) {
					// reset accumulated transcription from previous sessions
					transcription = '';

					// Create a SpeechRecognition object
					speechRecognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();

					// Set continuous to true for continuous recognition
					speechRecognition.continuous = true;
					// Interim results keep the inactivity timeout from firing mid-sentence
					speechRecognition.interimResults = true;

					// Set the timeout for turning off the recognition after inactivity (in milliseconds)
					const inactivityTimeout = 2000; // 3 seconds

					let timeoutId;
					// Start recognition
					speechRecognition.start();

					// Event triggered when speech is recognized
					speechRecognition.onresult = async (event) => {
						// Clear the inactivity timeout
						clearTimeout(timeoutId);

						// Handle recognized speech
						console.log(event);
						for (const result of Array.from(event.results).slice(event.resultIndex)) {
							if (result.isFinal) {
								transcription = `${transcription}${result[0].transcript}`;
							}
						}

						await tick();
						document.getElementById('chat-input')?.focus({ preventScroll: true });

						// Restart the inactivity timeout
						timeoutId = setTimeout(() => {
							console.log('Speech recognition turned off due to inactivity.');
							speechRecognition.stop();
						}, inactivityTimeout);
					};

					// Event triggered when recognition is ended
					speechRecognition.onend = function () {
						// Restart recognition after it ends
						console.log('recognition ended');

						confirmRecording();
						onConfirm({
							text: transcription
						});
						confirmed = false;
						loading = false;
					};

					// Event triggered when an error occurs
					speechRecognition.onerror = function (event) {
						console.log(event);
						toast.error($i18n.t(`Speech recognition error: {{error}}`, { error: event.error }));
						onCancel();

						cancelRecording();
					};
				}
			}
		}
	};

	const cancelRecording = async () => {
		if (speechRecognition) {
			// detach onend so cancelling does not confirm the transcription
			speechRecognition.onend = null;
		}
		await stopRecording();
	};

	const stopRecording = async () => {
		if (recording && mediaRecorder) {
			await mediaRecorder.stop();
		}

		if (speechRecognition) {
			speechRecognition.stop();
		}

		await releaseWakeLock();

		stopDurationCounter();
		audioChunks = [];
		visualizerData = Array(VISUALIZER_BUFFER_LENGTH).fill(0);

		if (stream) {
			const tracks = stream.getTracks();
			tracks.forEach((track) => track.stop());
		}

		stream = null;
		closeAudioContext();
	};

	const confirmRecording = async () => {
		loading = true;
		confirmed = true;

		if (recording && mediaRecorder) {
			await mediaRecorder.stop();
		}
		clearInterval(durationCounter);

		await releaseWakeLock();

		if (stream) {
			const tracks = stream.getTracks();
			tracks.forEach((track) => track.stop());
		}

		stream = null;
		closeAudioContext();
	};

	let resizeObserver;
	let containerWidth;

	let maxVisibleItems = 300;
	$: maxVisibleItems = Math.floor(containerWidth / 5); // 2px width + 0.5px gap

	let containerElement: HTMLDivElement;
	const handleKeyDown = (e) => {
		if (recording && e.key === 'Escape' && containerElement?.getClientRects().length) {
			e.preventDefault();
			cancelRecording();
			onCancel();
		}
	};

	const handleVisibilityChange = async () => {
		if (recording && document.visibilityState === 'visible') {
			await requestWakeLock();
		}
	};

	onMount(() => {
		window.addEventListener('keydown', handleKeyDown);
		document.addEventListener('visibilitychange', handleVisibilityChange);

		// listen to width changes
		resizeObserver = new ResizeObserver(() => {
			VISUALIZER_BUFFER_LENGTH = Math.floor(window.innerWidth / 4);
			if (visualizerData.length > VISUALIZER_BUFFER_LENGTH) {
				visualizerData = visualizerData.slice(visualizerData.length - VISUALIZER_BUFFER_LENGTH);
			} else {
				visualizerData = Array(VISUALIZER_BUFFER_LENGTH - visualizerData.length)
					.fill(0)
					.concat(visualizerData);
			}
		});

		resizeObserver.observe(document.body);
	});

	onDestroy(() => {
		window.removeEventListener('keydown', handleKeyDown);
		document.removeEventListener('visibilitychange', handleVisibilityChange);
		stopRecording();
		releaseWakeLock();
		closeAudioContext();
		// remove resize observer
		resizeObserver.disconnect();
	});
</script>

<!-- Single-row card styled like the chat composer. -->
<div
	bind:this={containerElement}
	bind:clientWidth={containerWidth}
	class="flex items-center gap-3 overflow-hidden rounded-3xl border border-base-200/60 bg-base-0/80 px-2 py-2 shadow-[0_6px_24px_-4px_rgba(0,0,0,0.1)] backdrop-blur-md dark:border-base-800/40 dark:bg-[color-mix(in_oklab,var(--color-base-850)_55%,var(--color-base-900))]/90 {className}"
>
	<button
		type="button"
		class="flex size-[1.875rem] shrink-0 items-center justify-center rounded-full text-base-700 transition hover:bg-base-100/40 dark:text-base-0 dark:hover:bg-base-800/40"
		aria-label={$i18n.t('Cancel')}
		on:click={async () => {
			cancelRecording();
			onCancel();
		}}
	>
		<XMark className="size-4" />
	</button>

	<div class="flex shrink-0 items-center gap-1.5">
		<span
			aria-hidden="true"
			class="size-1.5 rounded-full {loading
				? 'bg-base-300 dark:bg-base-600'
				: 'animate-pulse bg-red-500'}"
		></span>
		<span class="text-[0.8125rem] tabular-nums text-base-600 dark:text-base-300">
			{loading ? $i18n.t('Processing...') : formatSeconds(durationSeconds)}
		</span>
	</div>

	<div class="flex h-6 min-w-0 flex-1 items-center overflow-hidden" dir="rtl">
		<div
			class="flex h-6 w-full max-w-full flex-wrap items-center gap-[3px] overflow-hidden transition-opacity {loading
				? 'opacity-30'
				: ''}"
		>
			{#each visualizerData.slice().reverse() as rms}
				<div class="flex h-full items-center">
					<div
						class="inline-block h-full w-0.5 shrink-0 rounded-full bg-base-800 dark:bg-base-200"
						style="height: {Math.min(100, Math.max(14, rms * 100))}%;"
					/>
				</div>
			{/each}
		</div>
	</div>

	{#if loading}
		<div class="flex size-[1.875rem] shrink-0 items-center justify-center text-base-500">
			<Spinner className="size-4" />
		</div>
	{:else}
		<button
			id={confirmButtonId}
			type="button"
			aria-label={$i18n.t('Confirm recording')}
			class="shrink-0 rounded-full bg-base-1000 p-[0.3125rem] text-base-0 transition hover:bg-base-900 dark:bg-base-0 dark:text-base-1000 dark:hover:bg-base-100"
			on:click={async () => {
				await confirmRecording();
			}}
		>
			<svg
				xmlns="http://www.w3.org/2000/svg"
				fill="none"
				viewBox="0 0 24 24"
				stroke-width="2.5"
				stroke="currentColor"
				class="size-5"
			>
				<path stroke-linecap="round" stroke-linejoin="round" d="m4.5 12.75 6 6 9-13.5" />
			</svg>
		</button>
	{/if}
</div>
