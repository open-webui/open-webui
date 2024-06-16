<script lang="ts">
	import { config, settings, showCallOverlay } from '$lib/stores';
	import { onMount, tick, getContext } from 'svelte';

	import { blobToFile, calculateSHA256, extractSentences, findWordIndices } from '$lib/utils';
	import { synthesizeOpenAISpeech, transcribeAudio } from '$lib/apis/audio';
	import { toast } from 'svelte-sonner';

	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import VideoInputMenu from './CallOverlay/VideoInputMenu.svelte';
	import { get } from 'svelte/store';

	const i18n = getContext('i18n');

	export let submitPrompt: Function;
	export let files;

	let loading = false;
	let confirmed = false;

	let camera = false;
	let cameraStream = null;

	let assistantSpeaking = false;
	let assistantAudio = {};
	let assistantAudioIdx = null;

	let rmsLevel = 0;
	let hasStartedSpeaking = false;

	let currentUtterance = null;

	let mediaRecorder;
	let audioChunks = [];

	const MIN_DECIBELS = -45;
	const VISUALIZER_BUFFER_LENGTH = 300;

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

		const audioElement = document.getElementById('audioElement');
		audioElement.pause();
		audioElement.currentTime = 0;

		assistantSpeaking = false;
	};

	const playAudio = (idx) => {
		if ($showCallOverlay) {
			return new Promise((res) => {
				assistantAudioIdx = idx;
				const audioElement = document.getElementById('audioElement');
				const audio = assistantAudio[idx];

				audioElement.src = audio.src; // Assume `assistantAudio` has objects with a `src` property

				audioElement.muted = true;

				audioElement
					.play()
					.then(() => {
						audioElement.muted = false;
					})
					.catch((error) => {
						toast.error(error);
					});

				audioElement.onended = async (e) => {
					await new Promise((r) => setTimeout(r, 300));

					if (Object.keys(assistantAudio).length - 1 === idx) {
						assistantSpeaking = false;
					}

					res(e);
				};
			});
		} else {
			return Promise.resolve();
		}
	};

	const getOpenAISpeech = async (text) => {
		const res = await synthesizeOpenAISpeech(
			localStorage.token,
			$settings?.audio?.tts?.voice ?? $config?.audio?.tts?.voice,
			text
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

			if (res.text !== '') {
				const _responses = await submitPrompt(res.text);
				console.log(_responses);

				if (_responses.at(0)) {
					const content = _responses[0];
					if ((content ?? '').trim() !== '') {
						assistantSpeakingHandler(content);
					}
				}
			}
		}
	};

	const assistantSpeakingHandler = async (content) => {
		assistantSpeaking = true;

		if (($config.audio.tts.engine ?? '') == '') {
			let voices = [];
			const getVoicesLoop = setInterval(async () => {
				voices = await speechSynthesis.getVoices();
				if (voices.length > 0) {
					clearInterval(getVoicesLoop);

					const voice =
						voices
							?.filter(
								(v) => v.voiceURI === ($settings?.audio?.tts?.voice ?? $config?.audio?.tts?.voice)
							)
							?.at(0) ?? undefined;

					currentUtterance = new SpeechSynthesisUtterance(content);

					if (voice) {
						currentUtterance.voice = voice;
					}

					speechSynthesis.speak(currentUtterance);
				}
			}, 100);
		} else if ($config.audio.tts.engine === 'openai') {
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
					$settings?.audio?.tts?.voice ?? $config?.audio?.tts?.voice,
					sentence
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

				if (cameraStream) {
					const imageUrl = takeScreenshot();

					files = [
						{
							type: 'image',
							url: imageUrl
						}
					];
				}

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

	let videoInputDevices = [];
	let selectedVideoInputDeviceId = null;

	const getVideoInputDevices = async () => {
		const devices = await navigator.mediaDevices.enumerateDevices();
		videoInputDevices = devices.filter((device) => device.kind === 'videoinput');

		if (!!navigator.mediaDevices.getDisplayMedia) {
			videoInputDevices = [
				...videoInputDevices,
				{
					deviceId: 'screen',
					label: 'Screen Share'
				}
			];
		}

		console.log(videoInputDevices);
		if (selectedVideoInputDeviceId === null && videoInputDevices.length > 0) {
			selectedVideoInputDeviceId = videoInputDevices[0].deviceId;
		}
	};

	const startCamera = async () => {
		await getVideoInputDevices();

		if (cameraStream === null) {
			camera = true;
			await tick();
			try {
				await startVideoStream();
			} catch (err) {
				console.error('Error accessing webcam: ', err);
			}
		}
	};

	const startVideoStream = async () => {
		const video = document.getElementById('camera-feed');
		if (video) {
			if (selectedVideoInputDeviceId === 'screen') {
				cameraStream = await navigator.mediaDevices.getDisplayMedia({
					video: {
						cursor: 'always'
					},
					audio: false
				});
			} else {
				cameraStream = await navigator.mediaDevices.getUserMedia({
					video: {
						deviceId: selectedVideoInputDeviceId ? { exact: selectedVideoInputDeviceId } : undefined
					}
				});
			}

			if (cameraStream) {
				await getVideoInputDevices();
				video.srcObject = cameraStream;
				await video.play();
			}
		}
	};

	const stopVideoStream = async () => {
		if (cameraStream) {
			const tracks = cameraStream.getTracks();
			tracks.forEach((track) => track.stop());
		}

		cameraStream = null;
	};

	const takeScreenshot = () => {
		const video = document.getElementById('camera-feed');
		const canvas = document.getElementById('camera-canvas');

		if (!canvas) {
			return;
		}

		const context = canvas.getContext('2d');

		// Make the canvas match the video dimensions
		canvas.width = video.videoWidth;
		canvas.height = video.videoHeight;

		// Draw the image from the video onto the canvas
		context.drawImage(video, 0, 0, video.videoWidth, video.videoHeight);

		// Convert the canvas to a data base64 URL and console log it
		const dataURL = canvas.toDataURL('image/png');
		console.log(dataURL);

		return dataURL;
	};

	const stopCamera = async () => {
		await stopVideoStream();
		camera = false;
	};

	$: if ($showCallOverlay) {
		startRecording();
	} else {
		stopCamera();
	}
</script>

{#if $showCallOverlay}
	<audio id="audioElement" src="" style="display: none;" />
	<div class=" absolute w-full h-screen max-h-[100dvh] flex z-[999] overflow-hidden">
		<div
			class="absolute w-full h-screen max-h-[100dvh] bg-white text-gray-700 dark:bg-black dark:text-gray-300 flex justify-center"
		>
			<div class="max-w-lg w-full h-screen max-h-[100dvh] flex flex-col justify-between p-3 md:p-6">
				{#if camera}
					<div class="flex justify-center items-center w-full min-h-20">
						{#if loading}
							<svg
								class="size-12 text-gray-900 dark:text-gray-400"
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
									? ' size-[4.5rem]'
									: rmsLevel * 100 > 2
									? ' size-16'
									: rmsLevel * 100 > 1
									? 'size-14'
									: 'size-12'}  transition-all bg-black dark:bg-white rounded-full"
							/>
						{/if}
						<!-- navbar -->
					</div>
				{/if}

				<div class="flex justify-center items-center flex-1 h-full w-full max-h-full">
					{#if !camera}
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
					{:else}
						<div
							class="relative flex video-container w-full max-h-full pt-2 pb-4 md:py-6 px-2 h-full"
						>
							<video
								id="camera-feed"
								autoplay
								class="rounded-2xl h-full min-w-full object-cover object-center"
								playsinline
							/>

							<canvas id="camera-canvas" style="display:none;" />

							<div class=" absolute top-4 md:top-8 left-4">
								<button
									type="button"
									class="p-1.5 text-white cursor-pointer backdrop-blur-xl bg-black/10 rounded-full"
									on:click={() => {
										stopCamera();
									}}
								>
									<svg
										xmlns="http://www.w3.org/2000/svg"
										viewBox="0 0 16 16"
										fill="currentColor"
										class="size-6"
									>
										<path
											d="M5.28 4.22a.75.75 0 0 0-1.06 1.06L6.94 8l-2.72 2.72a.75.75 0 1 0 1.06 1.06L8 9.06l2.72 2.72a.75.75 0 1 0 1.06-1.06L9.06 8l2.72-2.72a.75.75 0 0 0-1.06-1.06L8 6.94 5.28 4.22Z"
										/>
									</svg>
								</button>
							</div>
						</div>
					{/if}
				</div>

				<div class="flex justify-between items-center pb-2 w-full">
					<div>
						{#if camera}
							<VideoInputMenu
								devices={videoInputDevices}
								on:change={async (e) => {
									console.log(e.detail);
									selectedVideoInputDeviceId = e.detail;
									await stopVideoStream();
									await startVideoStream();
								}}
							>
								<button class=" p-3 rounded-full bg-gray-50 dark:bg-gray-900" type="button">
									<svg
										xmlns="http://www.w3.org/2000/svg"
										viewBox="0 0 20 20"
										fill="currentColor"
										class="size-5"
									>
										<path
											fill-rule="evenodd"
											d="M15.312 11.424a5.5 5.5 0 0 1-9.201 2.466l-.312-.311h2.433a.75.75 0 0 0 0-1.5H3.989a.75.75 0 0 0-.75.75v4.242a.75.75 0 0 0 1.5 0v-2.43l.31.31a7 7 0 0 0 11.712-3.138.75.75 0 0 0-1.449-.39Zm1.23-3.723a.75.75 0 0 0 .219-.53V2.929a.75.75 0 0 0-1.5 0V5.36l-.31-.31A7 7 0 0 0 3.239 8.188a.75.75 0 1 0 1.448.389A5.5 5.5 0 0 1 13.89 6.11l.311.31h-2.432a.75.75 0 0 0 0 1.5h4.243a.75.75 0 0 0 .53-.219Z"
											clip-rule="evenodd"
										/>
									</svg>
								</button>
							</VideoInputMenu>
						{:else}
							<Tooltip content={$i18n.t('Camera')}>
								<button
									class=" p-3 rounded-full bg-gray-50 dark:bg-gray-900"
									type="button"
									on:click={async () => {
										await navigator.mediaDevices.getUserMedia({ video: true });
										startCamera();
									}}
								>
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
						{/if}
					</div>

					<div>
						<button type="button">
							<div class=" line-clamp-1 text-sm font-medium">
								{#if loading}
									{$i18n.t('Thinking...')}
								{:else}
									{$i18n.t('Listening...')}
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
