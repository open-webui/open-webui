<script lang="ts">
	import { config, models, settings, showCallOverlay, TTSWorker } from '$lib/stores';
	import { onMount, tick, getContext, onDestroy, createEventDispatcher } from 'svelte';

	const dispatch = createEventDispatcher();

	import { blobToFile } from '$lib/utils';
	import { generateEmoji } from '$lib/apis';
	import { synthesizeOpenAISpeech, transcribeAudio, synthesizeFallbackSpeech } from '$lib/apis/audio';

	import { toast } from 'svelte-sonner';

	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import VideoInputMenu from './CallOverlay/VideoInputMenu.svelte';
	import ModelSelector from '../ModelSelector.svelte';
	import Voice from '$lib/components/icons/Voice.svelte';

	const i18n = getContext('i18n');

	export let eventTarget: EventTarget;
	export let submitPrompt: Function;
	export let stopResponse: Function;
	export let files;
	export let chatId;
	export let modelId;
	export let selectedModels = [''];

	let wakeLock: any = null;
	let model: any = null;

	// Stage states: 'idle' | 'listening' | 'transcribing' | 'asking' | 'speaking' | 'review'
	let currentStage: 'idle' | 'listening' | 'transcribing' | 'asking' | 'speaking' | 'review' = 'idle';

	let loading = false;
	let transcribing = false;
	let confirmed = false;
	let interrupted = false;
	let assistantSpeaking = false;
	let muted = false;

	// Speech Input & Playback Review
	let autoSendMode = false; // default to manual review (Start -> Stop -> Listen -> Send)
	let isRecording = false;
	let recordedAudioBlob: Blob | null = null;
	let recordedAudioUrl: string | null = null;
	let userAudioPlayer: HTMLAudioElement | null = null;
	let ttsAudioElement: HTMLAudioElement | null = null;
	let isPlayingUserAudio = false;

	let pendingText = '';
	let lastPromptText = '';
	let streamingAssistantResponse = '';

	let emoji: string | null = null;
	let camera = false;
	let cameraStream: MediaStream | null = null;

	let chatStreaming = false;
	let rmsLevel = 0;
	let hasStartedSpeaking = false;
	let mediaRecorder: any = null;
	let audioStream: MediaStream | null = null;
	let audioChunks: Blob[] = [];

	let videoInputDevices: any[] = [];
	let selectedVideoInputDeviceId: string | null = null;

	// Selected STT Language
	let currentLanguage = 'en-US';
	$: if ($i18n?.language) {
		currentLanguage = localStorage.getItem('locale') || $i18n.language || 'en-US';
	}

	const setLanguage = (lang: string) => {
		currentLanguage = lang;
		localStorage.setItem('locale', lang);
		let langName = 'English';
		if (lang === 'hi-IN') langName = 'Hindi';
		if (lang === 'gu-IN') langName = 'Gujarati';

		const currentSettings = JSON.parse(localStorage.getItem('settings') || '{}');
		currentSettings.system = `Please reply in ${langName}.`;
		localStorage.setItem('settings', JSON.stringify(currentSettings));
	};

	const getVideoInputDevices = async () => {
		try {
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

			if (selectedVideoInputDeviceId === null && videoInputDevices.length > 0) {
				const savedDeviceId = localStorage.getItem('selectedVideoInputDeviceId');
				if (savedDeviceId && videoInputDevices.some((d) => d.deviceId === savedDeviceId)) {
					selectedVideoInputDeviceId = savedDeviceId;
				} else {
					selectedVideoInputDeviceId = videoInputDevices[0].deviceId;
				}
			}
		} catch (err) {
			console.error('Error getting video devices:', err);
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
		const video = document.getElementById('camera-feed') as HTMLVideoElement;
		if (video) {
			if (selectedVideoInputDeviceId === 'screen') {
				cameraStream = await navigator.mediaDevices.getDisplayMedia({
					video: { cursor: 'always' },
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
		const video = document.getElementById('camera-feed') as HTMLVideoElement;
		const canvas = document.getElementById('camera-canvas') as HTMLCanvasElement;
		if (!canvas || !video) return null;

		const context = canvas.getContext('2d');
		if (!context) return null;
		canvas.width = video.videoWidth;
		canvas.height = video.videoHeight;
		context.drawImage(video, 0, 0, video.videoWidth, video.videoHeight);
		return canvas.toDataURL('image/png');
	};

	const stopCamera = async () => {
		await stopVideoStream();
		camera = false;
	};

	const MIN_DECIBELS = -55;

	// User audio playback (Listen what you said)
	const togglePlayUserAudio = () => {
		if (!recordedAudioUrl) return;

		if (isPlayingUserAudio && userAudioPlayer) {
			userAudioPlayer.pause();
			isPlayingUserAudio = false;
		} else {
			if (userAudioPlayer) {
				userAudioPlayer.pause();
			}
			userAudioPlayer = new Audio(recordedAudioUrl);
			isPlayingUserAudio = true;
			userAudioPlayer.onended = () => {
				isPlayingUserAudio = false;
			};
			userAudioPlayer.onerror = () => {
				isPlayingUserAudio = false;
			};
			userAudioPlayer.play().catch((err) => {
				console.error('Audio play error:', err);
				isPlayingUserAudio = false;
			});
		}
	};

	// STT Handler
	const transcribeHandler = async (audioBlob: Blob) => {
		if (!audioBlob || audioBlob.size < 100) {
			console.log('Audio blob too small or empty, skipping transcription');
			currentStage = 'idle';
			return;
		}

		currentStage = 'transcribing';
		transcribing = true;

		await tick();
		const file = blobToFile(audioBlob, 'recording.wav');

		const savedLocale = localStorage.getItem('locale') || currentLanguage || 'en-US';
		const currentLangCode = savedLocale.split('-')[0];
		const sttLanguage = savedLocale === 'gu-IN' ? 'gu-IN' : currentLangCode;

		const res = await transcribeAudio(localStorage.token, file, sttLanguage).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		transcribing = false;

		if (res && res.text) {
			pendingText = res.text.trim();
			lastPromptText = pendingText;

			if (autoSendMode) {
				// Hands-free mode: immediately send to model
				await handleSendPrompt();
			} else {
				// Review mode: user can listen to what they said, edit text, and press send
				currentStage = 'review';
			}
		} else {
			currentStage = 'idle';
		}
	};

	// Send prompt to Agent / Current Model
	const handleSendPrompt = async () => {
		if (!pendingText.trim()) return;

		const textToSend = pendingText.trim();
		lastPromptText = textToSend;
		pendingText = '';
		streamingAssistantResponse = '';

		// Stop any user audio preview
		if (isPlayingUserAudio && userAudioPlayer) {
			userAudioPlayer.pause();
			isPlayingUserAudio = false;
		}

		currentStage = 'asking';
		loading = true;

		try {
			await submitPrompt(textToSend, { _raw: true });
		} catch (err) {
			console.error('Submit error:', err);
			toast.error('Failed to get answer from model');
		} finally {
			loading = false;
		}
	};

	const stopRecordingCallback = async (_continue = true) => {
		if ($showCallOverlay) {
			const _audioChunks = audioChunks.slice(0);
			audioChunks = [];

			if (isRecording) {
				isRecording = false;
			}

			if (confirmed || _audioChunks.length > 0) {
				if (cameraStream) {
					const imageUrl = takeScreenshot();
					if (imageUrl) {
						files = [{ type: 'image', url: imageUrl }];
					}
				}

				const type = _audioChunks[0]?.type || mediaRecorder?.mimeType || 'audio/webm';
				recordedAudioBlob = new Blob(_audioChunks, { type });
				if (recordedAudioUrl) {
					URL.revokeObjectURL(recordedAudioUrl);
				}
				recordedAudioUrl = URL.createObjectURL(recordedAudioBlob);

				await transcribeHandler(recordedAudioBlob);
				confirmed = false;
			}

			if (_continue && autoSendMode) {
				startRecording();
			}
		} else {
			audioChunks = [];
			mediaRecorder = null;
			if (audioStream) {
				const tracks = audioStream.getTracks();
				tracks.forEach((track) => track.stop());
			}
			audioStream = null;
		}
	};

	const startRecording = async () => {
		if (!$showCallOverlay) return;

		try {
			if (!audioStream) {
				audioStream = await navigator.mediaDevices.getUserMedia({
					audio: {
						echoCancellation: true,
						noiseSuppression: true,
						autoGainControl: true
					}
				});
			}

			if (audioStream) {
				mediaRecorder = new MediaRecorder(audioStream);
				audioChunks = [];

				mediaRecorder.onstart = () => {
					isRecording = true;
					currentStage = 'listening';
					audioChunks = [];
				};

				mediaRecorder.ondataavailable = (event: any) => {
					if (event.data && event.data.size > 0) {
						audioChunks.push(event.data);
					}
				};

				mediaRecorder.onstop = () => {
					isRecording = false;
					stopRecordingCallback(autoSendMode);
				};

				analyseAudio(audioStream);
			}
		} catch (err) {
			console.error('Error starting audio recorder:', err);
			toast.error('Microphone access denied or unavailable');
		}
	};

	// Manual Start Speech Action
	const startSpeechManual = async () => {
		if (assistantSpeaking) {
			stopAllAudio();
		}
		if (isPlayingUserAudio && userAudioPlayer) {
			userAudioPlayer.pause();
			isPlayingUserAudio = false;
		}

		pendingText = '';
		confirmed = false;
		hasStartedSpeaking = true;
		currentStage = 'listening';

		if (!audioStream) {
			await startRecording();
		}

		if (mediaRecorder && mediaRecorder.state !== 'recording') {
			try {
				mediaRecorder.start();
				isRecording = true;
			} catch (e) {
				console.error('Error starting recorder:', e);
			}
		}
	};

	// Manual Stop Speech Action
	const stopSpeechManual = () => {
		confirmed = true;
		hasStartedSpeaking = false;
		if (mediaRecorder && mediaRecorder.state === 'recording') {
			mediaRecorder.stop();
		} else {
			stopRecordingCallback(false);
		}
	};

	const stopAudioStream = async () => {
		try {
			if (mediaRecorder && mediaRecorder.state === 'recording') {
				mediaRecorder.stop();
			}
		} catch (error) {
			console.log('Error stopping audio stream:', error);
		}

		if (!audioStream) return;
		audioStream.getAudioTracks().forEach((track) => track.stop());
		audioStream = null;
	};

	// Function to calculate the RMS level from time domain data
	const calculateRMS = (data: Uint8Array) => {
		let sumSquares = 0;
		for (let i = 0; i < data.length; i++) {
			const normalizedValue = (data[i] - 128) / 128;
			sumSquares += normalizedValue * normalizedValue;
		}
		return Math.sqrt(sumSquares / data.length);
	};

	const analyseAudio = (stream: MediaStream) => {
		try {
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
					if (!mediaRecorder || !$showCallOverlay) return;

					if (muted || (assistantSpeaking && !($settings?.voiceInterruption ?? false))) {
						analyser.maxDecibels = 0;
						analyser.minDecibels = -1;
					} else {
						analyser.minDecibels = MIN_DECIBELS;
						analyser.maxDecibels = -30;
					}

					analyser.getByteTimeDomainData(timeDomainData);
					analyser.getByteFrequencyData(domainData);

					rmsLevel = calculateRMS(timeDomainData);

					if (muted || (assistantSpeaking && !($settings?.voiceInterruption ?? false))) {
						rmsLevel = 0;
					}

					const hasSound = domainData.some((value) => value > 0);
					if (hasSound) {
						// Only auto-start recording in Auto Mode when actively in the listening stage
						if (autoSendMode && currentStage === 'listening' && mediaRecorder && mediaRecorder.state !== 'recording') {
							try {
								mediaRecorder.start();
								isRecording = true;
							} catch (e) {}
						}

						// Only auto-interrupt the assistant if Auto Mode is active and voice interruption setting is enabled
						if (autoSendMode && assistantSpeaking && ($settings?.voiceInterruption ?? false)) {
							if (!hasStartedSpeaking) {
								hasStartedSpeaking = true;
								stopAllAudio();
							}
						}
						lastSoundTime = Date.now();
					}

					// Silence auto-detection only in autoSendMode
					if (autoSendMode && hasStartedSpeaking) {
						if (Date.now() - lastSoundTime > 2000) {
							confirmed = true;
							if (mediaRecorder && mediaRecorder.state === 'recording') {
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
		} catch (e) {
			console.error('Error analysing audio:', e);
		}
	};

	let currentMessageId: string | null = null;

	const getVoiceId = () => {
		return model?.info?.meta?.tts?.voice ?? $settings?.audio?.tts?.voice ?? $config?.audio?.tts?.voice;
	};

	let currentUtterance: SpeechSynthesisUtterance | null = null;
	let audioAbortController = new AbortController();
	let audioQueue: string[] = [];
	let isPlayingAudioQueue = false;
	const audioCache = new Map();
	const emojiCache = new Map();

	const speakSpeechSynthesisHandler = (content: string) => {
		if ($showCallOverlay && typeof window !== 'undefined' && 'speechSynthesis' in window) {
			return new Promise((resolve) => {
				const savedLocale = localStorage.getItem('locale') || currentLanguage || 'en-US';
				const langPrefix = savedLocale.split('-')[0];
				const utterance = new SpeechSynthesisUtterance(content);
				utterance.rate = $settings.audio?.tts?.playbackRate ?? 1;
				utterance.lang = savedLocale;

				const voices = speechSynthesis.getVoices();
				const voiceId = getVoiceId();
				const voice = voices?.find((v) => v.voiceURI === voiceId || v.lang.startsWith(langPrefix));
				if (voice) {
					utterance.voice = voice;
				} else if (langPrefix !== 'en') {
					console.warn(`No native speech synthesis voice found for language ${langPrefix}`);
					resolve(true);
					return;
				}

				currentUtterance = utterance;
				let resolved = false;

				const done = () => {
					if (!resolved) {
						resolved = true;
						resolve(true);
					}
				};

				utterance.onend = done;
				utterance.onerror = done;

				// Safety timeout in case browser TTS does not fire onend
				setTimeout(done, 12000);

				speechSynthesis.speak(utterance);
			});
		} else {
			return Promise.resolve(true);
		}
	};

	const playAudio = (audio: HTMLAudioElement) => {
		if (!$showCallOverlay) return Promise.resolve(true);

		return new Promise((resolve) => {
			// Use the bound in-DOM audio element; fall back to the passed object only if
			// the component hasn't mounted yet (should not happen in practice).
			const audioElement: HTMLAudioElement = ttsAudioElement ?? audio;

			audioElement.src = audio.src;
			audioElement.muted = false;
			audioElement.playbackRate = $settings.audio?.tts?.playbackRate ?? 1;

			let isResolved = false;
			const onFinish = () => {
				if (!isResolved) {
					isResolved = true;
					resolve(true);
				}
			};

			audioElement.onended = onFinish;
			audioElement.onerror = onFinish;

			audioElement
				.play()
				.then(() => {
					audioElement.muted = false;
				})
				.catch((error) => {
					console.error('Audio play error:', error);
					onFinish();
				});

			// Safety timeout
			setTimeout(onFinish, 20000);
		});
	};

	const stopAllAudio = async () => {
		assistantSpeaking = false;
		interrupted = true;
		audioQueue = [];
		isPlayingAudioQueue = false;

		if (chatStreaming) {
			stopResponse();
		}

		if (currentUtterance) {
			speechSynthesis.cancel();
			currentUtterance = null;
		}

		if (ttsAudioElement) {
			ttsAudioElement.muted = true;
			ttsAudioElement.pause();
			ttsAudioElement.currentTime = 0;
		}
	};

	const fetchAudio = async (content: string) => {
		content = content.replace(/!\[.*?\]\(.*?\)/g, ''); // Strip markdown images
		console.log('[TTS-DEBUG] fetchAudio called, content:', content?.substring(0, 60));
		if (!content || !content.trim()) return null;

		if (!audioCache.has(content)) {
			console.log('[TTS-DEBUG] cache MISS, fetching fresh audio');
			try {
				if ($settings?.showEmojiInCall ?? false) {
					const emojiRes = await generateEmoji(localStorage.token, modelId, content, chatId);
					if (emojiRes) {
						emojiCache.set(content, emojiRes);
					}
				}

				const savedLocale = localStorage.getItem('locale') || currentLanguage || 'en-US';
				const langPrefix = savedLocale.split('-')[0];

				const sarvamVoices = [
					'aditya', 'shubh', 'manan', 'rahul', 'rohan', 'amit',
					'shreya', 'ishita', 'ritu', 'pooja', 'roopa', 'suhani', 'neha', 'mani'
				];
				const isSarvamVoice = sarvamVoices.includes(getVoiceId());

				// Prioritize native Google TTS for Gujarati ('gu'), Hindi ('hi'), and English ('en') if no backend engine is configured.
				if (!isSarvamVoice && $config.audio.tts.engine === '' && (langPrefix === 'gu' || langPrefix === 'hi' || langPrefix === 'en')) {
					console.log(`[TTS-DEBUG] Using Google fallback TTS for lang=${langPrefix}`);
					try {
						const res = await synthesizeFallbackSpeech(localStorage.token, content, langPrefix);
						console.log(`[TTS-DEBUG] fallback-tts response: ok=${res?.ok}, status=${res?.status}`);
						if (res && res.ok) {
							const blob = await res.blob();
							console.log(`[TTS-DEBUG] Got audio blob: size=${blob.size}, type=${blob.type}`);
							const blobUrl = URL.createObjectURL(blob);
							audioCache.set(content, new Audio(blobUrl));
							return audioCache.get(content);
						} else {
							console.error(`[TTS-DEBUG] fallback-tts FAILED: status=${res?.status}`);
						}
					} catch (e) {
						console.error('[TTS-DEBUG] Google native TTS exception:', e);
					}
					return null;
				}

				if ($settings.audio?.tts?.engine === 'browser-kokoro') {
					// For non-English with kokoro, try fallback-tts first
					if (langPrefix !== 'en') {
						try {
							const res = await synthesizeFallbackSpeech(localStorage.token, content, langPrefix);
							if (res && res.ok) {
								const blob = await res.blob();
								const blobUrl = URL.createObjectURL(blob);
								audioCache.set(content, new Audio(blobUrl));
								return audioCache.get(content);
							}
						} catch (e) {
							console.error('Google native TTS failed, falling back to kokoro:', e);
						}
					}
					const url = await $TTSWorker
						.generate({
							text: content,
							voice: getVoiceId()
						})
						.catch((error) => {
							console.error(error);
							toast.error(`${error}`);
						});

					if (url) {
						audioCache.set(content, new Audio(url));
					}
				} else if ($config.audio.tts.engine !== '' || isSarvamVoice) {
					const res = await synthesizeOpenAISpeech(localStorage.token, getVoiceId(), content).catch(
						(error) => {
							console.error(error);
							return null;
						}
					);

					if (res) {
						const blob = await res.blob();
						const blobUrl = URL.createObjectURL(blob);
						audioCache.set(content, new Audio(blobUrl));
					}
				} else {
					// Fallback to backend google TTS endpoint
					try {
						const res = await synthesizeFallbackSpeech(localStorage.token, content, langPrefix);
						if (res && res.ok) {
							const blob = await res.blob();
							const blobUrl = URL.createObjectURL(blob);
							audioCache.set(content, new Audio(blobUrl));
						} else {
							audioCache.set(content, true);
						}
					} catch (e) {
						console.error('Fallback TTS fetch failed:', e);
						audioCache.set(content, true);
					}
				}
			} catch (error) {
				console.error('Error synthesizing speech:', error);
				audioCache.set(content, true);
			}
		}

		return audioCache.get(content);
	};

	const enqueueAndPlayAudio = async (textChunk: string) => {
		if (!textChunk || !textChunk.trim()) return;
		audioQueue.push(textChunk);
		processAudioQueue();
	};

	const processAudioQueue = async () => {
		if (isPlayingAudioQueue) return;
		isPlayingAudioQueue = true;

		while (audioQueue.length > 0 && !audioAbortController.signal.aborted) {
			const text = audioQueue.shift();
			if (!text) continue;

			currentStage = 'speaking';
			assistantSpeaking = true;

			try {
				const audioObjOrBool = await fetchAudio(text);
				console.log('[TTS-DEBUG] fetchAudio returned:', typeof audioObjOrBool, audioObjOrBool?.src ? 'has src' : 'no src');
				if (audioAbortController.signal.aborted) break;

				if (audioObjOrBool && typeof audioObjOrBool === 'object' && audioObjOrBool.src) {
					console.log('[TTS-DEBUG] Playing audio blob via playAudio()');
					await playAudio(audioObjOrBool);
				} else {
					console.log('[TTS-DEBUG] Falling back to browser speechSynthesis');
					await speakSpeechSynthesisHandler(text);
				}
				await new Promise((r) => setTimeout(r, 150));
			} catch (err) {
				console.error('TTS audio processing error:', err);
			}
		}

		isPlayingAudioQueue = false;
		if (!chatStreaming) {
			assistantSpeaking = false;
			currentStage = autoSendMode ? 'listening' : 'idle';
		}
	};

	const chatStartHandler = async (e: any) => {
		const { id } = e.detail;
		chatStreaming = true;
		streamingAssistantResponse = '';
		currentStage = 'asking';

		if (currentMessageId !== id) {
			currentMessageId = id;
			if (audioAbortController) {
				audioAbortController.abort();
			}
			audioAbortController = new AbortController();
			audioQueue = [];
			isPlayingAudioQueue = false;
		}
	};

	const chatEventHandler = async (e: any) => {
		const { id, content } = e.detail;
		if (currentMessageId === id && content) {
			streamingAssistantResponse = (streamingAssistantResponse + ' ' + content).trim();
			enqueueAndPlayAudio(content);
		}
	};

	const chatFinishHandler = async (e: any) => {
		chatStreaming = false;
		if (!isPlayingAudioQueue && audioQueue.length === 0) {
			assistantSpeaking = false;
			currentStage = autoSendMode ? 'listening' : 'idle';
		}
	};

	const toggleMute = () => {
		muted = !muted;
		if (muted && isRecording) {
			stopSpeechManual();
		}
	};

	let wasAssistantSpeaking = false;
	$: {
		if (assistantSpeaking && !wasAssistantSpeaking) {
			wasAssistantSpeaking = true;
		} else if (!assistantSpeaking && wasAssistantSpeaking) {
			wasAssistantSpeaking = false;
			if (muted) {
				muted = false;
			}
		}
	}

	const handleKeydown = (e: KeyboardEvent) => {
		if (e.key === 'm' || e.key === 'M') {
			const target = e.target as HTMLElement;
			if (target.tagName !== 'INPUT' && target.tagName !== 'TEXTAREA' && !target.isContentEditable) {
				e.preventDefault();
				toggleMute();
			}
		}
	};

	onMount(async () => {
		const setWakeLock = async () => {
			try {
				wakeLock = await (navigator as any).wakeLock?.request('screen');
			} catch (err) {
				console.log(err);
			}
		};

		if ('wakeLock' in navigator) {
			await setWakeLock();
			document.addEventListener('visibilitychange', async () => {
				if (wakeLock !== null && document.visibilityState === 'visible') {
					await setWakeLock();
				}
			});
		}

		model = $models.find((m) => m.id === modelId);

		eventTarget.addEventListener('chat:start', chatStartHandler);
		eventTarget.addEventListener('chat', chatEventHandler);
		eventTarget.addEventListener('chat:finish', chatFinishHandler);
		document.addEventListener('keydown', handleKeydown);

		return async () => {
			await stopAllAudio();
			stopAudioStream();
			eventTarget.removeEventListener('chat:start', chatStartHandler);
			eventTarget.removeEventListener('chat', chatEventHandler);
			eventTarget.removeEventListener('chat:finish', chatFinishHandler);
			document.removeEventListener('keydown', handleKeydown);
			audioAbortController.abort();
			await tick();
			await stopRecordingCallback(false);
			await stopCamera();
			if (recordedAudioUrl) {
				URL.revokeObjectURL(recordedAudioUrl);
			}
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
		document.removeEventListener('keydown', handleKeydown);
		audioAbortController.abort();
		if (recordedAudioUrl) {
			URL.revokeObjectURL(recordedAudioUrl);
		}
	});
</script>

{#if $showCallOverlay}
	<!-- Hidden TTS audio element — must live in the DOM so the browser's autoplay
	     policy treats it as connected to a user gesture. Bound via ttsAudioElement. -->
	<!-- svelte-ignore a11y-media-has-caption -->
	<audio bind:this={ttsAudioElement} id="audioElement" style="display:none;"></audio>

	<div
		class="relative w-full h-full max-h-[100dvh] flex flex-col justify-between p-3 md:p-5 bg-gradient-to-b from-slate-950 via-[#071d2b] to-[#040f17] text-white select-none overflow-hidden rounded-2xl shadow-2xl border border-sky-900/30"
	>
		<!-- Background ambient glowing orbs -->
		<div class="pointer-events-none absolute -top-24 -left-24 w-80 h-80 rounded-full bg-cyan-500/10 blur-3xl animate-pulse"></div>
		<div class="pointer-events-none absolute -bottom-24 -right-24 w-80 h-80 rounded-full bg-teal-500/10 blur-3xl"></div>

		<!-- Top Header Controls -->
		<div class="relative z-20 flex items-center justify-between gap-2 pb-2 border-b border-white/10 shrink-0">
			<!-- Language & Model Selectors -->
			<div class="flex items-center gap-2 shrink-0">
				<!-- Model Selector -->
				<div class="bg-white/10 hover:bg-white/15 backdrop-blur-md rounded-full px-2 py-0.5 text-xs border border-white/10 shrink-0">
					<ModelSelector
						bind:selectedModels
						showSetDefault={false}
						placement="bottom-start"
						align="left"
						triggerClassName="items-center gap-1 text-xs font-medium text-cyan-200 hover:text-white"
					/>
				</div>
			</div>

			<!-- Mode toggle & Close -->
			<div class="flex items-center gap-1.5 shrink-0">
				<!-- Mode Pill: Auto vs Review -->
				<button
					type="button"
					class="px-2.5 py-1 rounded-full text-[11px] font-medium transition border flex items-center gap-1 shrink-0 whitespace-nowrap {autoSendMode
						? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40'
						: 'bg-indigo-500/20 text-indigo-300 border-indigo-500/40'}"
					on:click={() => {
						autoSendMode = !autoSendMode;
					}}
					title={autoSendMode ? 'Hands-Free Auto-Send Mode Active' : 'Manual Review Mode Active'}
				>
					<span class="size-1.5 rounded-full {autoSendMode ? 'bg-emerald-400 animate-ping' : 'bg-indigo-400'}"></span>
					{autoSendMode ? 'Auto Mode' : 'Review Mode'}
				</button>

				<!-- Close Button -->
				<button
					aria-label="Close"
					class="p-1.5 rounded-full bg-white/10 hover:bg-white/20 text-gray-300 hover:text-white transition shrink-0"
					on:click={async () => {
						await stopAudioStream();
						await stopVideoStream();
						showCallOverlay.set(false);
						dispatch('close');
					}}
				>
					<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="size-4">
						<path d="M6.28 5.22a.75.75 0 0 0-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 1 0 1.06 1.06L10 11.06l3.72 3.72a.75.75 0 1 0 1.06-1.06L11.06 10l3.72-3.72a.75.75 0 0 0-1.06-1.06L10 8.94 6.28 5.22Z"/>
					</svg>
				</button>
			</div>
		</div>

		<!-- Stage Progression Breadcrumb Bar -->
		<div class="relative z-10 grid grid-cols-4 gap-1.5 py-2 px-1 text-center text-[11px] font-medium">
			<!-- Stage 1: Listen -->
			<div
				class="flex items-center justify-center gap-1 py-1 rounded-lg transition-all duration-300 {currentStage === 'listening' || isRecording
					? 'bg-cyan-500/30 text-cyan-200 border border-cyan-400/50 shadow-sm shadow-cyan-500/20 font-semibold'
					: 'bg-white/5 text-gray-400'}"
			>
				<span>1. Listen</span>
				{#if currentStage === 'listening' || isRecording}
					<span class="size-1.5 rounded-full bg-cyan-400 animate-pulse"></span>
				{/if}
			</div>

			<!-- Stage 2: Convert to Text -->
			<div
				class="flex items-center justify-center gap-1 py-1 rounded-lg transition-all duration-300 {currentStage === 'transcribing' || (currentStage === 'review' && pendingText)
					? 'bg-sky-500/30 text-sky-200 border border-sky-400/50 shadow-sm shadow-sky-500/20 font-semibold'
					: 'bg-white/5 text-gray-400'}"
			>
				<span>2. STT Text</span>
				{#if currentStage === 'transcribing'}
					<span class="size-1.5 rounded-full bg-sky-400 animate-spin"></span>
				{/if}
			</div>

			<!-- Stage 3: Asking Agent / Crunching -->
			<div
				class="flex items-center justify-center gap-1 py-1 rounded-lg transition-all duration-300 {currentStage === 'asking' || loading
					? 'bg-amber-500/30 text-amber-200 border border-amber-400/50 shadow-sm shadow-amber-500/20 font-semibold'
					: 'bg-white/5 text-gray-400'}"
			>
				<span>3. Agent Model</span>
				{#if currentStage === 'asking' || loading}
					<span class="size-1.5 rounded-full bg-amber-400 animate-ping"></span>
				{/if}
			</div>

			<!-- Stage 4: Giving Answer (TTS) -->
			<div
				class="flex items-center justify-center gap-1 py-1 rounded-lg transition-all duration-300 {currentStage === 'speaking' || assistantSpeaking
					? 'bg-emerald-500/30 text-emerald-200 border border-emerald-400/50 shadow-sm shadow-emerald-500/20 font-semibold'
					: 'bg-white/5 text-gray-400'}"
			>
				<span>4. TTS Answer</span>
				{#if currentStage === 'speaking' || assistantSpeaking}
					<span class="size-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
				{/if}
			</div>
		</div>

		<!-- Central Visual Display / Orb / Live Waveform -->
		<div class="relative z-10 flex-1 flex flex-col justify-center items-center px-4 min-h-0">
			<!-- Glowing Orb and Animated Waves Container -->
			<button
				type="button"
				class="relative flex flex-col items-center justify-center p-6 cursor-pointer group focus:outline-none"
				on:click={() => {
					if (assistantSpeaking) {
						stopAllAudio();
					}
				}}
			>
					{#if emoji}
						<div
							class="transition-all transform duration-200"
							style="font-size: {Math.max(4, Math.min(8, 5 + rmsLevel * 20))}rem;"
						>
							{emoji}
						</div>
					{:else}
						<!-- Glowing Aura Rings -->
						<div
							class="absolute rounded-full transition-all duration-300 pointer-events-none {isRecording || currentStage === 'listening'
								? 'bg-cyan-500/20 border-2 border-cyan-400/40 animate-ping'
								: assistantSpeaking
									? 'bg-emerald-500/20 border-2 border-emerald-400/40 animate-pulse'
									: loading
										? 'bg-amber-500/20 border-2 border-amber-400/40 animate-spin'
										: 'bg-sky-500/10'}"
							style="width: {120 + rmsLevel * 220}px; height: {120 + rmsLevel * 220}px;"
						></div>

						<!-- Core Orb -->
						<div
							class="relative flex items-center justify-center rounded-full transition-all duration-300 shadow-2xl {isRecording || currentStage === 'listening'
								? 'size-32 bg-gradient-to-tr from-cyan-600 via-sky-500 to-teal-400 ring-4 ring-cyan-400/50 shadow-cyan-500/50'
								: assistantSpeaking
									? 'size-32 bg-gradient-to-tr from-emerald-600 via-teal-500 to-cyan-400 ring-4 ring-emerald-400/50 shadow-emerald-500/50'
									: loading
										? 'size-32 bg-gradient-to-tr from-amber-600 via-yellow-500 to-orange-400 ring-4 ring-amber-400/50 shadow-amber-500/50 animate-pulse'
										: 'size-28 bg-gradient-to-tr from-sky-800 via-indigo-700 to-blue-900 ring-2 ring-white/20'}"
						>
							{#if loading || transcribing}
								<!-- Shimmering Spinner -->
								<svg class="size-12 text-white animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor">
									<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
									<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path>
								</svg>
							{:else if assistantSpeaking}
								<!-- Audio Wave Icon -->
								<Voice className="size-12 text-white animate-bounce" strokeWidth="2" />
							{:else if isRecording || currentStage === 'listening'}
								<!-- Mic Pulse Wave -->
								<svg xmlns="http://www.w3.org/2000/svg" class="size-12 text-white animate-pulse" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
									<path stroke-linecap="round" stroke-linejoin="round" d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m-4 0h8m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z"/>
								</svg>
							{:else}
								<!-- Idle Icon -->
								<Voice className="size-10 text-cyan-200" strokeWidth="1.5" />
							{/if}
						</div>
					{/if}

					<!-- Dynamic Audio Equalizer Bars -->
					<div class="flex items-center justify-center gap-1.5 mt-4 h-6">
						{#each [0.6, 1.2, 1.8, 2.4, 1.9, 1.3, 0.7] as factor}
							<div
								class="w-1.5 rounded-full transition-all duration-100 {isRecording || currentStage === 'listening'
									? 'bg-cyan-400'
									: assistantSpeaking
										? 'bg-emerald-400'
										: loading
											? 'bg-amber-400'
											: 'bg-white/20'}"
								style="height: {Math.max(4, Math.min(24, (rmsLevel * 100 * factor) + 4))}px;"
							></div>
						{/each}
					</div>
				</button>

			<!-- Current Stage Status Details & Descriptions -->
			<div class="mt-2 text-center max-w-sm px-2">
				<div class="text-sm font-semibold tracking-wide text-white/90">
					{#if currentStage === 'listening' || isRecording}
						<span class="text-cyan-300">🎤 Listening to your voice...</span>
					{:else if currentStage === 'transcribing'}
						<span class="text-sky-300">🔄 Converting speech to text (STT)...</span>
					{:else if currentStage === 'asking' || loading}
						<span class="text-amber-300">⚡ Asking agent & crunching numbers...</span>
					{:else if currentStage === 'speaking' || assistantSpeaking}
						<span class="text-emerald-300">🔊 Giving answer (Tap orb to interrupt)...</span>
					{:else if currentStage === 'review'}
						<span class="text-indigo-300">✨ Speech converted! Ready to send</span>
					{:else}
						<span class="text-gray-300">Tap "Start Speech" to begin</span>
					{/if}
				</div>

				{#if lastPromptText && (currentStage === 'asking' || currentStage === 'speaking' || loading)}
					<div class="mt-1 text-xs text-cyan-200/80 italic line-clamp-1 bg-black/30 rounded-lg px-2 py-0.5 border border-white/5">
						Asking: "{lastPromptText}"
					</div>
				{/if}

				{#if streamingAssistantResponse && (currentStage === 'speaking' || assistantSpeaking)}
					<div class="mt-1.5 text-xs text-white/80 max-h-16 overflow-y-auto line-clamp-3 bg-black/40 rounded-xl p-2 text-left border border-emerald-500/20">
						{streamingAssistantResponse}
					</div>
				{/if}
			</div>
		</div>

		<!-- Speech Input Review & Action Area -->
		<div class="relative z-20 flex flex-col gap-2 pt-2 pb-1 border-t border-white/10">
			<!-- Transcribed Text Box & Send Controls -->
			<div class="flex items-center gap-2 px-3 py-1.5 rounded-2xl bg-white/10 backdrop-blur-md border border-white/15 shadow-inner">
				{#if pendingText}
					<input
						type="text"
						bind:value={pendingText}
						placeholder="Transcribed text here..."
						class="flex-1 bg-transparent text-sm text-white placeholder-white/40 outline-none min-w-0"
						on:keydown={(e) => {
							if (e.key === 'Enter') {
								handleSendPrompt();
							}
						}}
					/>
				{:else}
					<span class="flex-1 text-xs text-white/40 italic truncate">
						{isRecording ? 'Listening in real-time...' : 'Click Start Speech or speak to transcribe...'}
					</span>
				{/if}

				<!-- "Listen what you said" Audio Playback Button -->
				{#if recordedAudioUrl}
					<Tooltip content={isPlayingUserAudio ? 'Pause what you said' : 'Listen what you said'}>
						<button
							type="button"
							class="p-1.5 rounded-full transition {isPlayingUserAudio
								? 'bg-amber-500 text-white animate-pulse'
								: 'bg-white/20 hover:bg-white/30 text-cyan-300'}"
							on:click={togglePlayUserAudio}
							aria-label="Listen what you said"
						>
							{#if isPlayingUserAudio}
								<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="size-4">
									<path d="M5.75 3a.75.75 0 0 0-.75.75v12.5c0 .414.336.75.75.75h1.5a.75.75 0 0 0 .75-.75V3.75A.75.75 0 0 0 7.25 3h-1.5ZM12.75 3a.75.75 0 0 0-.75.75v12.5c0 .414.336.75.75.75h1.5a.75.75 0 0 0 .75-.75V3.75a.75.75 0 0 0-.75-.75h-1.5Z" />
								</svg>
							{:else}
								<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="size-4">
									<path d="M6.3 2.84A1.5 1.5 0 0 0 4 4.11v11.78a1.5 1.5 0 0 0 2.3 1.27l9.344-5.891a1.5 1.5 0 0 0 0-2.538L6.3 2.841Z" />
								</svg>
							{/if}
						</button>
					</Tooltip>
				{/if}

				<!-- Clear / Discard Button -->
				{#if pendingText}
					<button
						type="button"
						aria-label="Clear Text"
						class="p-1.5 rounded-full bg-white/10 hover:bg-white/20 text-gray-300 hover:text-white transition"
						on:click={() => {
							pendingText = '';
							recordedAudioBlob = null;
							if (recordedAudioUrl) {
								URL.revokeObjectURL(recordedAudioUrl);
								recordedAudioUrl = null;
							}
						}}
					>
						<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="size-3.5">
							<path d="M6.28 5.22a.75.75 0 0 0-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 1 0 1.06 1.06L10 11.06l3.72 3.72a.75.75 0 1 0 1.06-1.06L11.06 10l3.72-3.72a.75.75 0 0 0-1.06-1.06L10 8.94 6.28 5.22Z" />
						</svg>
					</button>
				{/if}

				<!-- Send Button -->
				<Tooltip content="Send question to model">
					<button
						type="button"
						aria-label="Send"
						disabled={!pendingText.trim() || loading}
						class="p-1.5 px-3 rounded-xl font-medium text-xs text-white transition flex items-center gap-1.5 {pendingText.trim() && !loading
							? 'bg-gradient-to-r from-teal-500 to-emerald-500 hover:from-teal-400 hover:to-emerald-400 shadow-md shadow-emerald-500/20'
							: 'bg-white/10 text-white/40 cursor-not-allowed'}"
						on:click={handleSendPrompt}
					>
						<span>Send</span>
						<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="size-3.5">
							<path d="M3.105 2.288a.75.75 0 0 0-.826.95l1.414 4.926A1.5 1.5 0 0 0 5.135 9.25h6.115a.75.75 0 0 1 0 1.5H5.135a1.5 1.5 0 0 0-1.442 1.086l-1.414 4.926a.75.75 0 0 0 .826.95 28.897 28.897 0 0 0 15.293-7.155.75.75 0 0 0 0-1.114A28.897 28.897 0 0 0 3.105 2.288Z" />
						</svg>
					</button>
				</Tooltip>
			</div>

			<!-- Main Floating Bottom Control Bar -->
			<div class="flex items-center justify-center gap-4 pt-1">


				<!-- Speech Recording Button: Start Speech / Stop Speech -->
				{#if isRecording || currentStage === 'listening'}
					<!-- Stop Speech Button -->
					<Tooltip content="Stop Recording Speech">
						<button
							class="px-5 py-3 rounded-full bg-red-600 hover:bg-red-500 text-white font-semibold flex items-center gap-2 shadow-lg shadow-red-600/40 animate-pulse transition transform hover:scale-105"
							type="button"
							aria-label="Stop Speech"
							on:click={stopSpeechManual}
						>
							<div class="size-3.5 rounded-sm bg-white"></div>
							<span class="text-xs">Stop Speech</span>
						</button>
					</Tooltip>
				{:else}
					<!-- Start Speech Button -->
					<Tooltip content="Start Speaking (Record Audio)">
						<button
							class="px-5 py-3 rounded-full bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white font-semibold flex items-center gap-2 shadow-lg shadow-cyan-500/30 transition transform hover:scale-105"
							type="button"
							aria-label="Start Speech"
							on:click={startSpeechManual}
						>
							<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="size-4">
								<path stroke-linecap="round" stroke-linejoin="round" d="M12 18.75a6 6 0 0 0 6-6v-1.5m-6 7.5a6 6 0 0 1-6-6v-1.5m6 7.5v3.75m-3.75 0h7.5M12 15.75a3 3 0 0 1-3-3V4.5a3 3 0 1 1 6 0v8.25a3 3 0 0 1-3 3Z" />
							</svg>
							<span class="text-xs">Start Speech</span>
						</button>
					</Tooltip>
				{/if}

				<!-- Mute / Unmute Toggle -->
				<Tooltip content={muted ? 'Unmute (M)' : 'Mute (M)'}>
					<button
						class="p-3 rounded-full transition-colors duration-200 {muted
							? 'bg-rose-500 text-white'
							: 'bg-white/10 hover:bg-white/20 text-white'}"
						type="button"
						aria-label={muted ? 'Unmute' : 'Mute'}
						on:click={toggleMute}
					>
						{#if muted}
							<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="size-5">
								<path stroke-linecap="round" stroke-linejoin="round" d="M12 18.75a6 6 0 0 0 6-6v-1.5m-6 7.5a6 6 0 0 1-6-6v-1.5m6 7.5v3.75m-3.75 0h7.5M12 15.75a3 3 0 0 1-3-3V4.5a3 3 0 1 1 6 0v8.25a3 3 0 0 1-3 3Z" />
								<line x1="3" y1="3" x2="21" y2="21" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" />
							</svg>
						{:else}
							<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="size-5">
								<path stroke-linecap="round" stroke-linejoin="round" d="M12 18.75a6 6 0 0 0 6-6v-1.5m-6 7.5a6 6 0 0 1-6-6v-1.5m6 7.5v3.75m-3.75 0h7.5M12 15.75a3 3 0 0 1-3-3V4.5a3 3 0 1 1 6 0v8.25a3 3 0 0 1-3 3Z" />
							</svg>
						{/if}
					</button>
				</Tooltip>

				<!-- End / Close Button -->
				<Tooltip content="End Conversational Session">
					<button
						aria-label="End Call"
						class="p-3 rounded-full bg-white/10 hover:bg-red-500 text-white backdrop-blur transition"
						on:click={async () => {
							await stopAudioStream();
							await stopVideoStream();
							showCallOverlay.set(false);
							dispatch('close');
						}}
						type="button"
					>
						<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="size-5">
							<path d="M6.28 5.22a.75.75 0 0 0-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 1 0 1.06 1.06L10 11.06l3.72 3.72a.75.75 0 1 0 1.06-1.06L11.06 10l3.72-3.72a.75.75 0 0 0-1.06-1.06L10 8.94 6.28 5.22Z" />
						</svg>
					</button>
				</Tooltip>
			</div>
		</div>
	</div>
{/if}
