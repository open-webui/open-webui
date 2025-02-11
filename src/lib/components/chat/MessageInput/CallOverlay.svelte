<script lang="ts">
	import { config, models, settings, showCallOverlay, TTSWorker } from '$lib/stores';
	import { onMount, tick, getContext, onDestroy, createEventDispatcher } from 'svelte';

	const dispatch = createEventDispatcher();

	import { blobToFile } from '$lib/utils';
	import { generateEmoji } from '$lib/apis';
	import { synthesizeOpenAISpeech, transcribeAudio } from '$lib/apis/audio';

	import { toast } from 'svelte-sonner';

	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import VideoInputMenu from './CallOverlay/VideoInputMenu.svelte';
	import { KokoroWorker } from '$lib/workers/KokoroWorker';

	const i18n = getContext('i18n');

	export let eventTarget: EventTarget;
	export let submitPrompt: Function;
	export let stopResponse: Function;
	export let files;
	export let chatId;
	export let modelId;

	let wakeLock = null;

	let model = null;

	let loading = false;
	let confirmed = false;
	let interrupted = false;
	let assistantSpeaking = false;

	let emoji = null;
	let camera = false;
	let cameraStream = null;

	let chatStreaming = false;
	let rmsLevel = 0;
	let hasStartedSpeaking = false;
	let mediaRecorder;
	let audioStream = null;
	let audioChunks = [];

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

	const MIN_DECIBELS = -55;
	const VISUALIZER_BUFFER_LENGTH = 300;

	const transcribeHandler = async (audioBlob) => {
		// Create a blob from the audio chunks

		await tick();
		const file = blobToFile(audioBlob, 'recording.wav');

		const res = await transcribeAudio(localStorage.token, file).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			console.log(res.text);

			if (res.text !== '') {
				const _responses = await submitPrompt(res.text, { _raw: true });
				console.log(_responses);
			}
		}
	};

	const stopRecordingCallback = async (_continue = true) => {
		if ($showCallOverlay) {
			console.log('%c%s', 'color: red; font-size: 20px;', '🚨 stopRecordingCallback 🚨');

			// deep copy the audioChunks array
			const _audioChunks = audioChunks.slice(0);

			audioChunks = [];
			mediaRecorder = false;

			if (_continue) {
				startRecording();
			}

			if (confirmed) {
				loading = true;
				emoji = null;

				if (cameraStream) {
					const imageUrl = takeScreenshot();

					files = [
						{
							type: 'image',
							url: imageUrl
						}
					];
				}

				const audioBlob = new Blob(_audioChunks, { type: 'audio/wav' });
				await transcribeHandler(audioBlob);

				confirmed = false;
				loading = false;
			}
		} else {
			audioChunks = [];
			mediaRecorder = false;

			if (audioStream) {
				const tracks = audioStream.getTracks();
				tracks.forEach((track) => track.stop());
			}
			audioStream = null;
		}
	};

	const startRecording = async () => {
		if ($showCallOverlay) {
			if (!audioStream) {
				audioStream = await navigator.mediaDevices.getUserMedia({
					audio: {
						echoCancellation: true,
						noiseSuppression: true,
						autoGainControl: true
					}
				});
			}
			mediaRecorder = new MediaRecorder(audioStream);

			mediaRecorder.onstart = () => {
				console.log('Recording started');
				audioChunks = [];
			};

			mediaRecorder.ondataavailable = (event) => {
				if (hasStartedSpeaking) {
					audioChunks.push(event.data);
				}
			};

			mediaRecorder.onstop = (e) => {
				console.log('Recording stopped', audioStream, e);
				stopRecordingCallback();
			};

			analyseAudio(audioStream);
		}
	};

	const stopAudioStream = async () => {
		try {
			if (mediaRecorder) {
				mediaRecorder.stop();
			}
		} catch (error) {
			console.log('Error stopping audio stream:', error);
		}

		if (!audioStream) return;

		audioStream.getAudioTracks().forEach(function (track) {
			track.stop();
		});

		audioStream = null;
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

		console.log('🔊 Sound detection started', lastSoundTime, hasStartedSpeaking);

		const detectSound = () => {
			const processFrame = () => {
				if (!mediaRecorder || !$showCallOverlay) {
					return;
				}

				if (assistantSpeaking && !($settings?.voiceInterruption ?? false)) {
					// Mute the audio if the assistant is speaking
					analyser.maxDecibels = 0;
					analyser.minDecibels = -1;
				} else {
					analyser.minDecibels = MIN_DECIBELS;
					analyser.maxDecibels = -30;
				}

				analyser.getByteTimeDomainData(timeDomainData);
				analyser.getByteFrequencyData(domainData);

				// Calculate RMS level from time domain data
				rmsLevel = calculateRMS(timeDomainData);

				// Check if initial speech/noise has started
				const hasSound = domainData.some((value) => value > 0);
				if (hasSound) {
					// BIG RED TEXT
					console.log('%c%s', 'color: red; font-size: 20px;', '🔊 Sound detected');
					if (mediaRecorder && mediaRecorder.state !== 'recording') {
						mediaRecorder.start();
					}

					if (!hasStartedSpeaking) {
						hasStartedSpeaking = true;
						stopAllAudio();
					}

					lastSoundTime = Date.now();
				}

				// Start silence detection only after initial speech/noise has been detected
				if (hasStartedSpeaking) {
					if (Date.now() - lastSoundTime > 2000) {
						confirmed = true;

						if (mediaRecorder) {
							console.log('%c%s', 'color: red; font-size: 20px;', '🔇 Silence detected');
							mediaRecorder.stop();
							return;
						}
					}
				}

				window.requestAnimationFrame(processFrame);
			};

			window.requestAnimationFrame(processFrame);
		};

		detectSound();
	};

	let finishedMessages = {};
	let currentMessageId = null;
	let currentUtterance = null;

	const speakSpeechSynthesisHandler = (content) => {
		if ($showCallOverlay) {
			return new Promise((resolve) => {
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
						currentUtterance.rate = $settings.audio?.tts?.playbackRate ?? 1;

						if (voice) {
							currentUtterance.voice = voice;
						}

						speechSynthesis.speak(currentUtterance);
						currentUtterance.onend = async (e) => {
							await new Promise((r) => setTimeout(r, 200));
							resolve(e);
						};
					}
				}, 100);
			});
		} else {
			return Promise.resolve();
		}
	};

	const playAudio = (audio) => {
		if ($showCallOverlay) {
			return new Promise((resolve) => {
				const audioElement = document.getElementById('audioElement') as HTMLAudioElement;

				if (audioElement) {
					audioElement.src = audio.src;
					audioElement.muted = true;
					audioElement.playbackRate = $settings.audio?.tts?.playbackRate ?? 1;

					audioElement
						.play()
						.then(() => {
							audioElement.muted = false;
						})
						.catch((error) => {
							console.error(error);
						});

					audioElement.onended = async (e) => {
						await new Promise((r) => setTimeout(r, 100));
						resolve(e);
					};
				}
			});
		} else {
			return Promise.resolve();
		}
	};

	const stopAllAudio = async () => {
		assistantSpeaking = false;
		interrupted = true;

		if (chatStreaming) {
			stopResponse();
		}

		if (currentUtterance) {
			speechSynthesis.cancel();
			currentUtterance = null;
		}

		const audioElement = document.getElementById('audioElement');
		if (audioElement) {
			audioElement.muted = true;
			audioElement.pause();
			audioElement.currentTime = 0;
		}
	};

	let audioAbortController = new AbortController();

	// Audio cache map where key is the content and value is the Audio object.
	const audioCache = new Map();
	const emojiCache = new Map();

	const fetchAudio = async (content) => {
		if (!audioCache.has(content)) {
			try {
				// Set the emoji for the content if needed
				if ($settings?.showEmojiInCall ?? false) {
					const emoji = await generateEmoji(localStorage.token, modelId, content, chatId);
					if (emoji) {
						emojiCache.set(content, emoji);
					}
				}

				if ($settings.audio?.tts?.engine === 'browser-kokoro') {
					const blob = await $TTSWorker
						.generate({
							text: content,
							voice: $settings?.audio?.tts?.voice ?? $config?.audio?.tts?.voice
						})
						.catch((error) => {
							console.error(error);
							toast.error(`${error}`);
						});

					if (blob) {
						audioCache.set(content, new Audio(blob));
					}
				} else if ($config.audio.tts.engine !== '') {
					const res = await synthesizeOpenAISpeech(
						localStorage.token,
						$settings?.audio?.tts?.defaultVoice === $config.audio.tts.voice
							? ($settings?.audio?.tts?.voice ?? $config?.audio?.tts?.voice)
							: $config?.audio?.tts?.voice,
						content
					).catch((error) => {
						console.error(error);
						return null;
					});

					if (res) {
						const blob = await res.blob();
						const blobUrl = URL.createObjectURL(blob);
						audioCache.set(content, new Audio(blobUrl));
					}
				} else {
					audioCache.set(content, true);
				}
			} catch (error) {
				console.error('Error synthesizing speech:', error);
			}
		}

		return audioCache.get(content);
	};

	let messages = {};

	const monitorAndPlayAudio = async (id, signal) => {
		while (!signal.aborted) {
			if (messages[id] && messages[id].length > 0) {
				// Retrieve the next content string from the queue
				const content = messages[id].shift(); // Dequeues the content for playing

				if (audioCache.has(content)) {
					// If content is available in the cache, play it

					// Set the emoji for the content if available
					if (($settings?.showEmojiInCall ?? false) && emojiCache.has(content)) {
						emoji = emojiCache.get(content);
					} else {
						emoji = null;
					}

					if ($config.audio.tts.engine !== '') {
						try {
							console.log(
								'%c%s',
								'color: red; font-size: 20px;',
								`Playing audio for content: ${content}`
							);

							const audio = audioCache.get(content);
							await playAudio(audio); // Here ensure that playAudio is indeed correct method to execute
							console.log(`Played audio for content: ${content}`);
							await new Promise((resolve) => setTimeout(resolve, 200)); // Wait before retrying to reduce tight loop
						} catch (error) {
							console.error('Error playing audio:', error);
						}
					} else {
						await speakSpeechSynthesisHandler(content);
					}
				} else {
					// If not available in the cache, push it back to the queue and delay
					messages[id].unshift(content); // Re-queue the content at the start
					console.log(`Audio for "${content}" not yet available in the cache, re-queued...`);
					await new Promise((resolve) => setTimeout(resolve, 200)); // Wait before retrying to reduce tight loop
				}
			} else if (finishedMessages[id] && messages[id] && messages[id].length === 0) {
				// If the message is finished and there are no more messages to process, break the loop
				assistantSpeaking = false;
				break;
			} else {
				// No messages to process, sleep for a bit
				await new Promise((resolve) => setTimeout(resolve, 200));
			}
		}
		console.log(`Audio monitoring and playing stopped for message ID ${id}`);
	};

	const chatStartHandler = async (e) => {
		const { id } = e.detail;

		chatStreaming = true;

		if (currentMessageId !== id) {
			console.log(`Received chat start event for message ID ${id}`);

			currentMessageId = id;
			if (audioAbortController) {
				audioAbortController.abort();
			}
			audioAbortController = new AbortController();

			assistantSpeaking = true;
			// Start monitoring and playing audio for the message ID
			monitorAndPlayAudio(id, audioAbortController.signal);
		}
	};

	const chatEventHandler = async (e) => {
		const { id, content } = e.detail;
		// "id" here is message id
		// if "id" is not the same as "currentMessageId" then do not process
		// "content" here is a sentence from the assistant,
		// there will be many sentences for the same "id"

		if (currentMessageId === id) {
			console.log(`Received chat event for message ID ${id}: ${content}`);

			try {
				if (messages[id] === undefined) {
					messages[id] = [content];
				} else {
					messages[id].push(content);
				}

				console.log(content);

				fetchAudio(content);
			} catch (error) {
				console.error('Failed to fetch or play audio:', error);
			}
		}
	};

	const chatFinishHandler = async (e) => {
		const { id, content } = e.detail;
		// "content" here is the entire message from the assistant
		finishedMessages[id] = true;

		chatStreaming = false;
	};

	onMount(async () => {
		const setWakeLock = async () => {
			try {
				wakeLock = await navigator.wakeLock.request('screen');
			} catch (err) {
				// The Wake Lock request has failed - usually system related, such as battery.
				console.log(err);
			}

			if (wakeLock) {
				// Add a listener to release the wake lock when the page is unloaded
				wakeLock.addEventListener('release', () => {
					// the wake lock has been released
					console.log('Wake Lock released');
				});
			}
		};

		if ('wakeLock' in navigator) {
			await setWakeLock();

			document.addEventListener('visibilitychange', async () => {
				// Re-request the wake lock if the document becomes visible
				if (wakeLock !== null && document.visibilityState === 'visible') {
					await setWakeLock();
				}
			});
		}

		model = $models.find((m) => m.id === modelId);

		startRecording();

		eventTarget.addEventListener('chat:start', chatStartHandler);
		eventTarget.addEventListener('chat', chatEventHandler);
		eventTarget.addEventListener('chat:finish', chatFinishHandler);

		return async () => {
			await stopAllAudio();

			stopAudioStream();

			eventTarget.removeEventListener('chat:start', chatStartHandler);
			eventTarget.removeEventListener('chat', chatEventHandler);
			eventTarget.removeEventListener('chat:finish', chatFinishHandler);

			audioAbortController.abort();
			await tick();

			await stopAllAudio();

			await stopRecordingCallback(false);
			await stopCamera();
		};
	});

	onDestroy(async () => {
		await stopAllAudio();
		await stopRecordingCallback(false);
		await stopCamera();

		await stopAudioStream();
		eventTarget.removeEventListener('chat:start', chatStartHandler);
		eventTarget.removeEventListener('chat', chatEventHandler);
		eventTarget.removeEventListener('chat:finish', chatFinishHandler);
		audioAbortController.abort();

		await tick();

		await stopAllAudio();
	});
</script>

{#if $showCallOverlay}
	<div class="max-w-lg w-full h-full max-h-[100dvh] flex flex-col justify-between p-3 md:p-6">
		{#if camera}
			<button
				type="button"
				class="flex justify-center items-center w-full h-20 min-h-20"
				on:click={() => {
					if (assistantSpeaking) {
						stopAllAudio();
					}
				}}
			>
				{#if emoji}
					<div
						class="  transition-all rounded-full"
						style="font-size:{rmsLevel * 100 > 4
							? '4.5'
							: rmsLevel * 100 > 2
								? '4.25'
								: rmsLevel * 100 > 1
									? '3.75'
									: '3.5'}rem;width: 100%; text-align:center;"
					>
						{emoji}
					</div>
				{:else if loading || assistantSpeaking}
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
									: 'size-12'}  transition-all rounded-full {(model?.info?.meta
							?.profile_image_url ?? '/static/favicon.png') !== '/static/favicon.png'
							? ' bg-cover bg-center bg-no-repeat'
							: 'bg-black dark:bg-white'}  bg-black dark:bg-white"
						style={(model?.info?.meta?.profile_image_url ?? '/static/favicon.png') !==
						'/static/favicon.png'
							? `background-image: url('${model?.info?.meta?.profile_image_url}');`
							: ''}
					/>
				{/if}
				<!-- navbar -->
			</button>
		{/if}

		<div class="flex justify-center items-center flex-1 h-full w-full max-h-full">
			{#if !camera}
				<button
					type="button"
					on:click={() => {
						if (assistantSpeaking) {
							stopAllAudio();
						}
					}}
				>
					{#if emoji}
						<div
							class="  transition-all rounded-full"
							style="font-size:{rmsLevel * 100 > 4
								? '13'
								: rmsLevel * 100 > 2
									? '12'
									: rmsLevel * 100 > 1
										? '11.5'
										: '11'}rem;width:100%;text-align:center;"
						>
							{emoji}
						</div>
					{:else if loading || assistantSpeaking}
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
										? 'size-44'
										: 'size-40'}  transition-all rounded-full {(model?.info?.meta
								?.profile_image_url ?? '/static/favicon.png') !== '/static/favicon.png'
								? ' bg-cover bg-center bg-no-repeat'
								: 'bg-black dark:bg-white'} "
							style={(model?.info?.meta?.profile_image_url ?? '/static/favicon.png') !==
							'/static/favicon.png'
								? `background-image: url('${model?.info?.meta?.profile_image_url}');`
								: ''}
						/>
					{/if}
				</button>
			{:else}
				<div class="relative flex video-container w-full max-h-full pt-2 pb-4 md:py-6 px-2 h-full">
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
				<button
					type="button"
					on:click={() => {
						if (assistantSpeaking) {
							stopAllAudio();
						}
					}}
				>
					<div class=" line-clamp-1 text-sm font-medium">
						{#if loading}
							{$i18n.t('Thinking...')}
						{:else if assistantSpeaking}
							{$i18n.t('Tap to interrupt')}
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
						await stopAudioStream();
						await stopVideoStream();

						console.log(audioStream);
						console.log(cameraStream);

						showCallOverlay.set(false);
						dispatch('close');
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
{/if}
