<script lang="ts">
	import { WEBUI_API_BASE_URL } from '$lib/constants';
	import { models, settings, showCallOverlay, socket } from '$lib/stores';
	import { onMount, getContext, onDestroy, createEventDispatcher } from 'svelte';
	import { createRealtimeAudioRuntime } from './realtime/audio-runtime';
	import { setupRealtimeSocketRuntime } from './realtime/socket-runtime';

	const dispatch = createEventDispatcher();

	import { negotiateRealtimeSdp } from '$lib/apis/audio';
	import { toast } from 'svelte-sonner';
	import MicSolid from '$lib/components/icons/MicSolid.svelte';

	const i18n = getContext('i18n');

	export let modelId;
	export let chatId;

	export let selectedToolIds: string[] = [];
	export let toolServers = [];
	export let features = {};
	export let terminalId: string | null = null;
	export let sessionId: string | null = null;
	export let systemPrompt: string = '';

	let model = null;
	type ConnectionState = 'idle' | 'connecting' | 'connected' | 'error' | 'closed';

	// Connection state
	let connectionState: ConnectionState = 'idle';
	let pc: RTCPeerConnection | null = null;
	let dc: RTCDataChannel | null = null;
	let mediaStream: MediaStream | null = null;
	let audioElement: HTMLAudioElement | null = null;

	// UI state — driven by data channel (latency-critical) and Socket.IO (status)
	let isPTTMode = false; // true when VAD is disabled (turn_detection: null)
	let isPTTHeld = false;
	let isAssistantSpeaking = false;
	let isUserSpeaking = false;
	let isToolCalling = false;
	let isContextPreparing = false;
	let contextPreparingMessage = '';
	let isMicMuted = true; // Starts muted until readiness barrier
	let isReconnecting = false;
	let overlayErrorMessage = '';
	let rmsLevel = 0;
	let wakeLock = null;
	let disconnectTimeout: ReturnType<typeof setTimeout> | null = null;
	let connectGeneration = 0;
	let cleanupSocketRuntime = () => {};

	$: model = $models.find((m) => m.id === modelId) ?? null;

	const audioRuntime = createRealtimeAudioRuntime({
		getQuietState: () => ({
			connectionState,
			overlayErrorMessage,
			isReconnecting,
			isContextPreparing,
			isToolCalling,
			isUserSpeaking,
			isAssistantSpeaking
		}),
		onLocalRmsLevel: (level) => {
			rmsLevel = level;
		},
		onAssistantAudioStarted: () => {
			isAssistantSpeaking = true;
		},
		onAssistantAudioQuiet: () => {
			isAssistantSpeaking = false;
		},
		// Timer management is fully backend-driven via sideband events.
	});

	$: {
		connectionState;
		overlayErrorMessage;
		isReconnecting;
		isContextPreparing;
		isToolCalling;
		isUserSpeaking;
		isAssistantSpeaking;
		audioRuntime.syncToolPingLoop();
	}

	function setMicrophoneMuted(muted: boolean) {
		isMicMuted = muted;
		if (mediaStream) {
			mediaStream.getAudioTracks().forEach((track) => {
				track.enabled = !muted;
			});
		}
	}

	let callId = '';

	function handleDataChannelMessage(event: MessageEvent) {
		try {
			const data = JSON.parse(event.data);
			const type = data.type || '';
			if (type === 'input_audio_buffer.speech_started') {
				isUserSpeaking = true;
				isToolCalling = false;
				audioRuntime.invalidateQuietWindow(true);
				audioRuntime.stopToolPing();
			} else if (type === 'input_audio_buffer.speech_stopped') {
				isUserSpeaking = false;
			}
		} catch {
			// Ignore parse errors
		}
	}

	function getRealtimeErrorMessage(error: any): string {
		if (!error) return '';
		if (typeof error === 'string') return error;
		if (typeof error?.detail === 'string') return error.detail;
		if (typeof error?.error?.message === 'string') return error.error.message;
		if (typeof error?.message === 'string') return error.message;
		return '';
	}

	function setRealtimeError(error: any, fallback = 'Connection failed') {
		const message = getRealtimeErrorMessage(error);
		isToolCalling = false;
		audioRuntime.stopToolPing();
		overlayErrorMessage = message;
		connectionState = 'error';
		toast.error(message || $i18n.t(fallback));
	}

	async function releaseConnectionResources() {
		connectGeneration += 1;
		isToolCalling = false;
		audioRuntime.stopToolPing();

		if (dc) {
			dc.onmessage = null;
			dc.close();
			dc = null;
		}

		if (pc) {
			pc.ontrack = null;
			pc.onconnectionstatechange = null;
			pc.close();
			pc = null;
		}

		if (mediaStream) {
			mediaStream.getTracks().forEach((track) => track.stop());
			mediaStream = null;
		}

		if (disconnectTimeout !== null) {
			clearTimeout(disconnectTimeout);
			disconnectTimeout = null;
		}
		await audioRuntime.release(audioElement);

		if (wakeLock) {
			try {
				await wakeLock.release();
			} catch {
				// Ignore
			}
			wakeLock = null;
		}
	}

	async function connect() {
		if (connectionState === 'connecting' || connectionState === 'connected') {
			return;
		}

		connectionState = 'connecting';
		overlayErrorMessage = '';
		const currentSessionId = sessionId || $socket?.id;
		const generation = connectGeneration + 1;
		connectGeneration = generation;

		try {
			if (!currentSessionId) {
				throw new Error('Realtime socket is not connected');
			}

			// Set up WebRTC
			const nextPc = new RTCPeerConnection({
				iceServers: [{ urls: 'stun:stun.l.google.com:19302' }]
			});
			pc = nextPc;
			let startedRealtime = false;
			let connectCallId = '';

			const startRealtimeSession = () => {
				if (startedRealtime || !connectCallId) {
					return;
				}

				startedRealtime = true;
				if (disconnectTimeout !== null) {
					clearTimeout(disconnectTimeout);
					disconnectTimeout = null;
				}
				connectionState = 'connected';
				$socket?.emit('realtime:start', {
					modelId,
					chatId: chatId || `local:${currentSessionId}`,
					callId: connectCallId,
					toolIds: selectedToolIds,
					toolServers,
					features,
					terminalId
				});
			};

			nextPc.onconnectionstatechange = () => {
				if (nextPc.connectionState === 'connected') {
					startRealtimeSession();
				} else if (nextPc.connectionState === 'failed') {
					if (disconnectTimeout !== null) {
						clearTimeout(disconnectTimeout);
						disconnectTimeout = null;
					}
					overlayErrorMessage = '';
					connectionState = 'error';
					if (connectCallId) {
						$socket?.emit('realtime:stop', { callId: connectCallId });
					}
				} else if (nextPc.connectionState === 'disconnected') {
					// Transient state — allow 8 seconds for self-healing before treating as error
					if (disconnectTimeout === null) {
						disconnectTimeout = setTimeout(() => {
							disconnectTimeout = null;
							if (nextPc.connectionState === 'disconnected') {
								overlayErrorMessage = '';
								connectionState = 'error';
								if (connectCallId) {
									$socket?.emit('realtime:stop', { callId: connectCallId });
								}
							}
						}, 8000);
					}
				}
			};

			// Audio output
			nextPc.ontrack = (e) => {
				if (audioElement) {
					audioElement.srcObject = e.streams[0];
				}
				audioRuntime.startRemoteAudioMonitoring(e.streams[0]);
				const audioTrack = e.streams[0]?.getAudioTracks?.()[0];
				if (audioTrack) {
					audioTrack.onunmute = () => audioRuntime.markAssistantAudioStarted();
				}
			};

			// Microphone input
			const nextMediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
			if (connectGeneration !== generation || pc !== nextPc) {
				nextMediaStream.getTracks().forEach((track) => track.stop());
				nextPc.close();
				return;
			}

			mediaStream = nextMediaStream;
			nextMediaStream.getAudioTracks().forEach((track) => {
				track.enabled = false; // Start muted until readiness barrier
				nextPc.addTrack(track, nextMediaStream);
			});

			audioRuntime.startLocalRmsMonitoring(nextMediaStream);

			// Data channel (read-only — only for latency-critical speech indicators)
			const nextDc = nextPc.createDataChannel('oai-events');
			dc = nextDc;
			nextDc.onmessage = handleDataChannelMessage;
			// SDP exchange — backend proxies everything, ephemeral key never leaves server
			const offer = await nextPc.createOffer();
			await nextPc.setLocalDescription(offer);

			const result = await negotiateRealtimeSdp(localStorage.token, modelId, offer.sdp, {
				tool_ids: selectedToolIds,
				tool_servers: toolServers,
				features,
				terminal_id: terminalId,
				chat_id: chatId || `local:${currentSessionId}`,
				session_id: currentSessionId,
				system_prompt: systemPrompt,
				language: localStorage.getItem('locale') || navigator.language || ''
			});
			if (!result || !result.sdp_answer) {
				throw new Error('Failed to negotiate realtime session');
			}

			if (connectGeneration !== generation || pc !== nextPc) {
				nextMediaStream.getTracks().forEach((track) => track.stop());
				nextPc.close();
				return;
			}

			connectCallId = result.call_id || '';
			callId = connectCallId;
			await nextPc.setRemoteDescription({ type: 'answer', sdp: result.sdp_answer });
			if (nextPc.connectionState === 'connected') {
				startRealtimeSession();
			}

			// Request wake lock
			try {
				wakeLock = await navigator.wakeLock.request('screen');
			} catch {
				// Wake lock not supported
			}
		} catch (e) {
			await releaseConnectionResources();
			setRealtimeError(e);
		}
	}

	function pttStart() {
		if (!isPTTMode || isPTTHeld) return;
		isPTTHeld = true;
		isToolCalling = false;
		audioRuntime.invalidateQuietWindow(true);
		audioRuntime.stopToolPing();
		if (callId) {
			$socket?.emit('realtime:clear_audio', { callId });
		}
		setMicrophoneMuted(false);
	}

	function pttEnd() {
		if (!isPTTMode || !isPTTHeld) return;
		isPTTHeld = false;
		setMicrophoneMuted(true);
		if (callId) {
			$socket?.emit('realtime:commit_audio', { callId });
		}
	}

	async function cleanup({
		preserveSocketRuntime = false,
		nextState = 'closed'
	}: { preserveSocketRuntime?: boolean; nextState?: ConnectionState } = {}) {
		const cleanupCallId = callId;
		callId = '';
		audioRuntime.invalidateQuietWindow(true);
		await releaseConnectionResources();

		if (!preserveSocketRuntime) {
			cleanupSocketRuntime();
			cleanupSocketRuntime = () => {};
		}
		if (connectionState !== 'error') {
			connectionState = nextState;
		}
	}

	onMount(async () => {
		if ($socket) {
			cleanupSocketRuntime = setupRealtimeSocketRuntime({
				socket: $socket,
				getEffectiveChatId: () => chatId || `local:${sessionId || $socket?.id}`,
				getConnectionState: () => connectionState,
				getIsMicMuted: () => isMicMuted,
				getCurrentCallId: () => callId,
				getIsPTTMode: () => isPTTMode,
				getIsToolCalling: () => isToolCalling,
				getIsReconnecting: () => isReconnecting,
				getAssistantAudioActive: () => audioRuntime.isAssistantAudioActive(),
				getAssistantOutputObserved: () => audioRuntime.hasAssistantOutputObserved(),
				getAutoUnmuteWhenReady: () => $settings?.audio?.realtime?.autoUnmuteWhenReady ?? false,
				connect,
				cleanup,
				closeOverlay: () => {
					showCallOverlay.set(false);
					dispatch('close');
				},
				setPTTMode: (value) => {
					isPTTMode = value;
				},
				setPTTHeld: (value) => {
					isPTTHeld = value;
				},
				setAssistantSpeaking: (value) => {
					isAssistantSpeaking = value;
				},
				setUserSpeaking: (value) => {
					isUserSpeaking = value;
				},
				setToolCalling: (value) => {
					isToolCalling = value;
				},
				setContextPreparing: (value) => {
					isContextPreparing = value;
				},
				setContextPreparingMessage: (value) => {
					contextPreparingMessage = value;
				},
				setMicMuted: setMicrophoneMuted,
				setReconnecting: (value) => {
					isReconnecting = value;
				},
				setOverlayErrorMessage: (value) => {
					overlayErrorMessage = value;
				},
				setConnectionState: (value) => {
					connectionState = value;
				},
				invalidateQuietWindow: audioRuntime.invalidateQuietWindow,
				scheduleQuietWindowOpen: audioRuntime.scheduleQuietWindowOpen,
				stopToolPing: audioRuntime.stopToolPing,
				startToolPing: () => {
					audioRuntime.startToolPingLoop();
				},
				showErrorToast: (message) => {
					toast.error(message);
				}
			});
		}
		await connect();
	});

	onDestroy(() => {
		if (connectionState === 'closed') return;
		if (callId) {
			$socket?.emit('realtime:stop', { callId });
		}
		// Fire-and-forget — Svelte doesn't await onDestroy promises
		cleanup().catch(() => {});
	});
</script>

{#if $showCallOverlay}
	<div class="max-w-lg w-full h-full max-h-[100dvh] flex flex-col justify-between p-3 md:p-6">
		<div class="flex justify-center items-center flex-1 h-full w-full max-h-full">
			<button
				type="button"
				on:click={() => {
					if (isAssistantSpeaking) {
						if (callId) {
							$socket?.emit('realtime:cancel', { callId });
						}
						isAssistantSpeaking = false;
					}
				}}
			>
				{#if isAssistantSpeaking || isToolCalling || isContextPreparing || connectionState === 'connecting'}
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
				{:else if connectionState === 'error'}
					<div class="size-40 flex items-center justify-center">
						<svg
							xmlns="http://www.w3.org/2000/svg"
							fill="none"
							viewBox="0 0 24 24"
							stroke-width="1.5"
							stroke="currentColor"
							class="size-20 text-red-500"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z"
							/>
						</svg>
					</div>
				{:else}
					<div
						class="{rmsLevel * 100 > 4
							? 'size-52'
							: rmsLevel * 100 > 2
								? 'size-48'
								: rmsLevel * 100 > 1
									? 'size-44'
									: 'size-40'} transition-all rounded-full bg-cover bg-center bg-no-repeat"
						style={`background-image: url('${WEBUI_API_BASE_URL}/models/model/profile/image?id=${model?.id}&lang=${$i18n.language}&voice=true');`}
					/>
				{/if}
			</button>
		</div>

		<!-- svelte-ignore a11y-media-has-caption -->
		<audio
			bind:this={audioElement}
			autoplay
			on:playing={() => {
				audioRuntime.markAssistantAudioStarted();
			}}
		/>

		{#if isReconnecting}
			<div class="absolute inset-0 bg-black/50 flex items-center justify-center z-10">
				<div class="text-white text-sm font-medium">{$i18n.t('Reconnecting...')}</div>
			</div>
		{/if}

		<div class="flex justify-between items-center pb-2 w-full">
			<div>
				{#if isPTTMode}
					<!-- Hold-to-talk button for PTT mode -->
					<button
						class="p-3 rounded-full relative flex items-center justify-center {isPTTHeld
							? 'bg-red-500 text-white'
							: 'bg-gray-50 dark:bg-gray-900'}"
						type="button"
						aria-label={$i18n.t('Hold to talk')}
						on:mousedown={pttStart}
						on:mouseup={pttEnd}
						on:mouseleave={pttEnd}
						on:touchstart|preventDefault={pttStart}
						on:touchend|preventDefault={pttEnd}
					>
						<MicSolid className="size-5" />
					</button>
				{:else}
					<!-- Mic mute toggle for VAD mode -->
					<button
						class="p-3 rounded-full relative flex items-center justify-center {isContextPreparing || connectionState === 'connecting' ? 'bg-gray-200 dark:bg-gray-800 opacity-50 cursor-not-allowed' : 'bg-gray-50 dark:bg-gray-900'}"
						type="button"
						disabled={isContextPreparing || connectionState === 'connecting'}
						aria-label={isContextPreparing || connectionState === 'connecting' ? $i18n.t('Preparing...') : isMicMuted ? $i18n.t('Unmute microphone') : $i18n.t('Mute microphone')}
						on:click={() => {
							if (!isContextPreparing && connectionState !== 'connecting') {
								setMicrophoneMuted(!isMicMuted);
							}
						}}
					>
						<MicSolid className="size-5" />
						{#if isMicMuted}
							<svg
								xmlns="http://www.w3.org/2000/svg"
								viewBox="0 0 20 20"
								fill="none"
								class="absolute size-5"
							>
								<path
									d="M4 4L16 16"
									stroke="currentColor"
									stroke-width="1.75"
									stroke-linecap="round"
								/>
							</svg>
						{/if}
					</button>
				{/if}
			</div>

			<div>
				<div class="text-center">
					{#if isAssistantSpeaking}
						<div class="line-clamp-1 text-sm font-medium">
							{$i18n.t('Tap to interrupt')}
						</div>
					{:else if connectionState === 'error'}
						<div class="line-clamp-1 text-sm font-medium">
							{$i18n.t('Connection failed')}
						</div>
					{:else if connectionState === 'connecting' || isContextPreparing || isToolCalling}
						<div class="line-clamp-1 text-sm font-medium">
							{#if isContextPreparing && contextPreparingMessage}
								{$i18n.t(contextPreparingMessage)}
							{:else}
								{$i18n.t('Thinking...')}
							{/if}
						</div>
					{:else if isPTTMode && isPTTHeld}
						<div class="line-clamp-1 text-sm font-medium">
							{$i18n.t('Recording...')}
						</div>
					{:else if isPTTMode}
						<div class="line-clamp-1 text-sm font-medium">
							{$i18n.t('Hold to talk')}
						</div>
					{:else if isMicMuted}
						<div class="line-clamp-1 text-sm font-medium">
							{$i18n.t('Microphone muted')}
						</div>
					{:else}
						<div class="line-clamp-1 text-sm font-medium">
							{$i18n.t('Listening...')}
						</div>
					{/if}
					{#if connectionState === 'error' && overlayErrorMessage}
						<div class="mt-1 max-w-xs text-center text-xs text-red-500 break-words">
							{overlayErrorMessage}
						</div>
					{/if}
				</div>
			</div>

			<div class="flex gap-2">
				<button
					class="p-3 rounded-full bg-gray-50 dark:bg-gray-900"
					on:click={async () => {
						if (callId) {
							$socket?.emit('realtime:stop', { callId });
						}
						await cleanup();
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
