<script lang="ts">
	import { settings, showCallOverlay } from '$lib/stores';
	import { onMount, tick, getContext } from 'svelte';

	import { blobToFile, calculateSHA256, extractSentences, findWordIndices } from '$lib/utils';
	import { synthesizeOpenAISpeech, transcribeAudio } from '$lib/apis/audio';
	import { toast } from 'svelte-sonner';
	import Tooltip from '$lib/components/common/Tooltip.svelte';

	const i18n = getContext('i18n');

	export let submitPrompt: Function;

	let loading = false;
	let confirmed = false;

	let assistantSpeaking = false;
	let assistantAudio = {};
	let assistantAudioIdx = null;

	let rmsLevel = 0;
	let hasStartedSpeaking = false;

	let audioContext;
	let analyser;
	let dataArray;
	let audioElement;
	let animationFrameId;

	let speechRecognition;
	let currentUtterance = null;

	let mediaRecorder;
	let audioChunks = [];

	const MIN_DECIBELS = -45;
	const VISUALIZER_BUFFER_LENGTH = 300;

	let visualizerData = Array(VISUALIZER_BUFFER_LENGTH).fill(0);

	const startAudio = () => {
		audioContext = new (window.AudioContext || window.webkitAudioContext)();
		analyser = audioContext.createAnalyser();
		const source = audioContext.createMediaElementSource(audioElement);
		source.connect(analyser);
		analyser.connect(audioContext.destination);
		analyser.fftSize = 32; // Adjust the fftSize
		dataArray = new Uint8Array(analyser.frequencyBinCount);
		visualize();
	};

	const visualize = () => {
		analyser.getByteFrequencyData(dataArray);
		div1Height = dataArray[1] / 2;
		div2Height = dataArray[3] / 2;
		div3Height = dataArray[5] / 2;
		div4Height = dataArray[7] / 2;
		animationFrameId = requestAnimationFrame(visualize);
	};

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

	const analyseAudio = (stream) => {
		const audioContext = new AudioContext();
		const audioStreamSource = audioContext.createMediaStreamSource(stream);

		const analyser = audioContext.createAnalyser();
		analyser.minDecibels = MIN_DECIBELS;
		audioStreamSource.connect(analyser);

		const bufferLength = analyser.frequencyBinCount;

		const domainData = new Uint8Array(bufferLength);
		const timeDomainData = new Uint8Array(analyser.fftSize);

		let lastSoundTime = Date.now();
		hasStartedSpeaking = false;

		const detectSound = () => {
			const processFrame = () => {
				if (!mediaRecorder || !$showCallOverlay) {
					if (mediaRecorder) {
						mediaRecorder.stop();
					}

					return;
				}
				analyser.getByteTimeDomainData(timeDomainData);
				analyser.getByteFrequencyData(domainData);

				// Calculate RMS level from time domain data
				rmsLevel = calculateRMS(timeDomainData);

				// Check if initial speech/noise has started
				const hasSound = domainData.some((value) => value > 0);
				if (hasSound) {
					stopAllAudio();
					hasStartedSpeaking = true;
					lastSoundTime = Date.now();
				}

				// Start silence detection only after initial speech/noise has been detected
				if (hasStartedSpeaking) {
					if (Date.now() - lastSoundTime > 2000) {
						confirmed = true;

						if (mediaRecorder) {
							mediaRecorder.stop();
						}
					}
				}

				window.requestAnimationFrame(processFrame);
			};

			window.requestAnimationFrame(processFrame);
		};

		detectSound();
	};

	const stopAllAudio = () => {
		if (currentUtterance) {
			speechSynthesis.cancel();
			currentUtterance = null;
		}
		if (assistantAudio[assistantAudioIdx]) {
			assistantAudio[assistantAudioIdx].pause();
			assistantAudio[assistantAudioIdx].currentTime = 0;
		}
		assistantSpeaking = false;
	};

	const playAudio = (idx) => {
		return new Promise((res) => {
			assistantAudioIdx = idx;
			const audio = assistantAudio[idx];
			audio.play();
			audio.onended = async (e) => {
				await new Promise((r) => setTimeout(r, 300));

				if (Object.keys(assistantAudio).length - 1 === idx) {
					assistantSpeaking = false;
				}

				res(e);
			};
		});
	};

	const getOpenAISpeech = async (text) => {
		const res = await synthesizeOpenAISpeech(
			localStorage.token,
			$settings?.audio?.speaker ?? 'alloy',
			text,
			$settings?.audio?.model ?? 'tts-1'
		).catch((error) => {
			toast.error(error);
			assistantSpeaking = false;
			return null;
		});

		if (res) {
			const blob = await res.blob();
			const blobUrl = URL.createObjectURL(blob);
			const audio = new Audio(blobUrl);
			assistantAudio = audio;
		}
	};

	const transcribeHandler = async (audioBlob) => {
		// Create a blob from the audio chunks

		await tick();
		const file = blobToFile(audioBlob, 'recording.wav');

		const res = await transcribeAudio(localStorage.token, file).catch((error) => {
			toast.error(error);
			return null;
		});

		if (res) {
			console.log(res.text);

			const _responses = await submitPrompt(res.text);
			console.log(_responses);

			if (_responses.at(0)) {
				const content = _responses[0];
				if (content) {
					assistantSpeakingHandler(content);
				}
			}
		}
	};

	const assistantSpeakingHandler = async (content) => {
		assistantSpeaking = true;

		if (($settings?.audio?.TTSEngine ?? '') == '') {
			currentUtterance = new SpeechSynthesisUtterance(content);
			speechSynthesis.speak(currentUtterance);
		} else if ($settings?.audio?.TTSEngine === 'openai') {
			console.log('openai');

			const sentences = extractSentences(content).reduce((mergedTexts, currentText) => {
				const lastIndex = mergedTexts.length - 1;
				if (lastIndex >= 0) {
					const previousText = mergedTexts[lastIndex];
					const wordCount = previousText.split(/\s+/).length;
					if (wordCount < 2) {
						mergedTexts[lastIndex] = previousText + ' ' + currentText;
					} else {
						mergedTexts.push(currentText);
					}
				} else {
					mergedTexts.push(currentText);
				}
				return mergedTexts;
			}, []);

			console.log(sentences);

			let lastPlayedAudioPromise = Promise.resolve(); // Initialize a promise that resolves immediately

			for (const [idx, sentence] of sentences.entries()) {
				const res = await synthesizeOpenAISpeech(
					localStorage.token,
					$settings?.audio?.speaker,
					sentence,
					$settings?.audio?.model
				).catch((error) => {
					toast.error(error);

					assistantSpeaking = false;
					return null;
				});

				if (res) {
					const blob = await res.blob();
					const blobUrl = URL.createObjectURL(blob);
					const audio = new Audio(blobUrl);
					assistantAudio[idx] = audio;
					lastPlayedAudioPromise = lastPlayedAudioPromise.then(() => playAudio(idx));
				}
			}
		}
	};

	const stopRecordingCallback = async () => {
		if ($showCallOverlay) {
			if (confirmed) {
				loading = true;

				const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
				await transcribeHandler(audioBlob);

				confirmed = false;
				loading = false;
			}
			audioChunks = [];
			mediaRecorder = false;

			startRecording();
		} else {
			audioChunks = [];
			mediaRecorder = false;
		}
	};

	const startRecording = async () => {
		const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
		mediaRecorder = new MediaRecorder(stream);
		mediaRecorder.onstart = () => {
			console.log('Recording started');
			audioChunks = [];
			analyseAudio(stream);
		};
		mediaRecorder.ondataavailable = (event) => {
			if (hasStartedSpeaking) {
				audioChunks.push(event.data);
			}
		};
		mediaRecorder.onstop = async () => {
			console.log('Recording stopped');

			await stopRecordingCallback();
		};
		mediaRecorder.start();
	};

	$: if ($showCallOverlay) {
		startRecording();
	}
</script>

{#if $showCallOverlay}
	<div class=" absolute w-full h-full flex z-[999]">
		<div
			class="absolute w-full h-full bg-white text-gray-700 dark:bg-black dark:text-gray-300 flex justify-center"
		>
			<div class="max-w-lg w-full h-screen flex flex-col justify-between p-6">
				<div>
					<!-- navbar -->
				</div>

				<div class="flex justify-center items-center w-ull">
					{#if loading}
						<svg
							class="size-44 text-gray-900 dark:text-gray-400"
							viewBox="0 0 24 24"
							fill="currentColor"
							xmlns="http://www.w3.org/2000/svg"
							><style>
								.spinner_qM83 {
									animation: spinner_8HQG 1.05s infinite;
								}
								.spinner_oXPr {
									animation-delay: 0.1s;
								}
								.spinner_ZTLf {
									animation-delay: 0.2s;
								}
								@keyframes spinner_8HQG {
									0%,
									57.14% {
										animation-timing-function: cubic-bezier(0.33, 0.66, 0.66, 1);
										transform: translate(0);
									}
									28.57% {
										animation-timing-function: cubic-bezier(0.33, 0, 0.66, 0.33);
										transform: translateY(-6px);
									}
									100% {
										transform: translate(0);
									}
								}
							</style><circle class="spinner_qM83" cx="4" cy="12" r="3" /><circle
								class="spinner_qM83 spinner_oXPr"
								cx="12"
								cy="12"
								r="3"
							/><circle class="spinner_qM83 spinner_ZTLf" cx="20" cy="12" r="3" /></svg
						>
					{:else}
						<div
							class=" {rmsLevel * 100 > 4
								? ' size-52'
								: rmsLevel * 100 > 2
								? 'size-48'
								: rmsLevel * 100 > 1
								? 'size-[11.5rem]'
								: 'size-44'}  transition-all bg-black dark:bg-white rounded-full"
						/>
					{/if}
				</div>

				<div class="flex justify-between items-center pb-2 w-full">
					<div>
						<Tooltip content="WIP 🚧">
							<button class=" p-3 rounded-full bg-gray-50 dark:bg-gray-900">
								<svg
									xmlns="http://www.w3.org/2000/svg"
									fill="none"
									viewBox="0 0 24 24"
									stroke-width="1.5"
									stroke="currentColor"
									class="size-5"
								>
									<path
										stroke-linecap="round"
										stroke-linejoin="round"
										d="M6.827 6.175A2.31 2.31 0 0 1 5.186 7.23c-.38.054-.757.112-1.134.175C2.999 7.58 2.25 8.507 2.25 9.574V18a2.25 2.25 0 0 0 2.25 2.25h15A2.25 2.25 0 0 0 21.75 18V9.574c0-1.067-.75-1.994-1.802-2.169a47.865 47.865 0 0 0-1.134-.175 2.31 2.31 0 0 1-1.64-1.055l-.822-1.316a2.192 2.192 0 0 0-1.736-1.039 48.774 48.774 0 0 0-5.232 0 2.192 2.192 0 0 0-1.736 1.039l-.821 1.316Z"
									/>
									<path
										stroke-linecap="round"
										stroke-linejoin="round"
										d="M16.5 12.75a4.5 4.5 0 1 1-9 0 4.5 4.5 0 0 1 9 0ZM18.75 10.5h.008v.008h-.008V10.5Z"
									/>
								</svg>
							</button>
						</Tooltip>
					</div>

					<div>
						<button type="button">
							<div class=" line-clamp-1 text-sm font-medium">
								{#if loading}
									Thinking...
								{:else}
									Listening...
								{/if}
							</div>
						</button>
					</div>

					<div>
						<button
							class=" p-3 rounded-full bg-gray-50 dark:bg-gray-900"
							on:click={async () => {
								showCallOverlay.set(false);
							}}
							type="button"
						>
							<svg
								xmlns="http://www.w3.org/2000/svg"
								viewBox="0 0 20 20"
								fill="currentColor"
								class="size-5"
							>
								<path
									d="M6.28 5.22a.75.75 0 0 0-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 1 0 1.06 1.06L10 11.06l3.72 3.72a.75.75 0 1 0 1.06-1.06L11.06 10l3.72-3.72a.75.75 0 0 0-1.06-1.06L10 8.94 6.28 5.22Z"
								/>
							</svg>
						</button>
					</div>
				</div>
			</div>
		</div>
	</div>
{/if}
