type ConnectionState = 'idle' | 'connecting' | 'connected' | 'error' | 'closed';

type SocketRuntimeOptions = {
	socket: any;
	getEffectiveChatId: () => string;
	getConnectionState: () => ConnectionState;
	getIsMicMuted: () => boolean;
	getCurrentCallId: () => string;
	getIsPTTMode: () => boolean;
	getIsToolCalling: () => boolean;
	getIsReconnecting: () => boolean;
	getAssistantAudioActive: () => boolean;
	getAssistantOutputObserved: () => boolean;
	getAutoUnmuteWhenReady: () => boolean;
	connect: () => void;
	cleanup: (options?: {
		preserveSocketRuntime?: boolean;
		nextState?: ConnectionState;
	}) => Promise<void>;
	closeOverlay: () => void;
	setPTTMode: (value: boolean) => void;
	setPTTHeld: (value: boolean) => void;
	setAssistantSpeaking: (value: boolean) => void;
	setUserSpeaking: (value: boolean) => void;
	setToolCalling: (value: boolean) => void;
	setContextPreparing: (value: boolean) => void;
	setContextPreparingMessage: (value: string) => void;
	setMicMuted: (value: boolean) => void;
	setReconnecting: (value: boolean) => void;
	setOverlayErrorMessage: (value: string) => void;
	setConnectionState: (value: ConnectionState) => void;
	invalidateQuietWindow: (resetAssistantOutput?: boolean) => void;
	scheduleQuietWindowOpen: (delayMs?: number) => void;
	stopToolPing: () => void;
	startToolPing: () => void;
	showErrorToast: (message: string) => void;
};

export function setupRealtimeSocketRuntime(options: SocketRuntimeOptions) {
	function getEventCallId(data: any): string {
		return (
			data?.callId ||
			data?.data?.callId ||
			data?.data?.notification?.callId ||
			data?.notification?.callId ||
			''
		);
	}

	function matchesCurrentCall(data: any): boolean {
		const currentCallId = options.getCurrentCallId();
		const eventCallId = getEventCallId(data);
		return Boolean(currentCallId && eventCallId && currentCallId === eventCallId);
	}

	function handleRealtimeEvents(event: any) {
		if (event?.chat_id !== options.getEffectiveChatId()) return;
		const data = event?.data;
		if (!data) return;

		const type = data.type || '';
		if (type === 'status' || type === 'chat:completion') {
			if (!matchesCurrentCall(data)) {
				// During bootstrap (no callId yet, still connecting), allow status
				// events through so the overlay can display progress messages.
				const isBootstrapStatus =
					type === 'status' &&
					!options.getCurrentCallId() &&
					options.getConnectionState() === 'connecting';
				if (!isBootstrapStatus) {
					return;
				}
			}
		}

		if (type === 'status') {
			const desc = (data.data?.description || '').toLowerCase();
			const activity = (data.data?.activity || '').toLowerCase();
			const isToolActivity =
				activity === 'tool' ||
				desc.includes('tool') ||
				desc.startsWith('calling ') ||
				desc.endsWith(' completed') ||
				desc.endsWith(' failed');

			if (isToolActivity) {
				if (!data.data?.done) {
					options.invalidateQuietWindow();
					options.setToolCalling(true);
					options.startToolPing();
				}
			} else {
				const assistantStartedOutput = desc.includes('speaking') || desc.includes('responding');
				if (assistantStartedOutput) {
					options.setAssistantSpeaking(true);
					options.invalidateQuietWindow();
					options.setToolCalling(false);
					options.stopToolPing();
				}
			}

			const isContextActivity = desc.includes('preparing') || desc.includes('context') || desc.includes('loading') || desc.includes('summariz') || desc.includes('injecting');
			options.setContextPreparing(isContextActivity);
			if (isContextActivity) {
				options.setContextPreparingMessage(data.data?.description || '');
			}
			if (data.data?.done) {
				if (!isToolActivity && !options.getAssistantAudioActive()) {
					options.setAssistantSpeaking(false);
				}
				options.setContextPreparing(false);
				options.setContextPreparingMessage('');
				if (!isToolActivity && !options.getAssistantOutputObserved()) {
					options.scheduleQuietWindowOpen();
				}
			}
		} else if (type === 'chat:completion') {
			const output = data.data?.output ?? [];
			const lastAssistantMessage = Array.isArray(output)
				? [...output]
						.reverse()
						.find((item) => item?.type === 'message' && item?.role === 'assistant')
				: null;
			const assistantMessageText =
				lastAssistantMessage?.content
					?.filter((item) => item?.type === 'output_text')
					?.map((item) => item?.text || '')
					?.join('') || '';
			const hasPendingToolCall =
				Array.isArray(output) &&
				output.some((item) => item?.type === 'function_call' && item?.status === 'in_progress');

			if (hasPendingToolCall) {
				options.invalidateQuietWindow();
				options.setToolCalling(true);
				options.startToolPing();
			} else if (data.data?.done) {
				if (!options.getAssistantAudioActive()) {
					options.setAssistantSpeaking(false);
				}
				options.setToolCalling(false);
				options.stopToolPing();
				if (!options.getAssistantOutputObserved()) {
					options.scheduleQuietWindowOpen();
				}
			} else if (assistantMessageText.trim()) {
				options.setAssistantSpeaking(true);
				options.invalidateQuietWindow();
				options.setToolCalling(false);
				options.stopToolPing();
			}
		}
	}

	function onRealtimeReady(data: { auto_unmute?: boolean; callId?: string }) {
		if (!matchesCurrentCall(data)) {
			return;
		}
		const autoUnmute = data?.auto_unmute !== false && options.getAutoUnmuteWhenReady();
		options.setContextPreparing(false);
		options.setOverlayErrorMessage('');
		options.setToolCalling(false);
		options.stopToolPing();
		if (!options.getIsPTTMode() && autoUnmute) {
			options.setMicMuted(false);
		}
		options.invalidateQuietWindow(true);
		options.scheduleQuietWindowOpen();
	}

	function onSidebandLost(data: { callId?: string }) {
		if (!matchesCurrentCall(data)) {
			return;
		}
		options.setReconnecting(true);
		options.invalidateQuietWindow();
	}

	function onRealtimeSession(data: any) {
		if (data?.autoStart && !data?.callId) {
			if (options.getConnectionState() === 'idle') {
				options.connect();
			}
			return;
		}
		if (!matchesCurrentCall(data)) {
			return;
		}
		options.setPTTMode(
			data?.sessionConfig?.vadType === 'push_to_talk' || data?.sessionConfig?.vadType === null
		);
		options.setPTTHeld(false);
		options.setAssistantSpeaking(false);
		options.setUserSpeaking(false);
		options.setToolCalling(false);
		options.invalidateQuietWindow(true);
		options.stopToolPing();
		if (options.getIsReconnecting()) {
			options.setReconnecting(false);
			options.connect();
		}
	}

	async function onRealtimeEnded(data: { reason: string; message?: string; callId?: string }) {
		if (!matchesCurrentCall(data)) {
			return;
		}
		const reason = data?.reason || 'unknown';
		const shouldAutoClose = reason === 'idle';
		options.setToolCalling(false);
		options.stopToolPing();
		options.invalidateQuietWindow();

		if (reason === 'voice_change') {
			options.setReconnecting(true);
			options.setMicMuted(true);
			options.setOverlayErrorMessage('');
			await options.cleanup({
				preserveSocketRuntime: true,
				nextState: 'idle'
			});
			options.setReconnecting(false);
			options.connect();
			return;
		}

		if (reason === 'idle') {
			options.setOverlayErrorMessage('');
		} else if (reason === 'sideband_error') {
			options.setOverlayErrorMessage(data?.message || '');
			options.setConnectionState('error');
		} else if (reason === 'sideband_closed') {
			options.setOverlayErrorMessage('');
		} else if (reason === 'auth_error') {
			options.setOverlayErrorMessage(data?.message || '');
			options.setConnectionState('error');
		} else if (reason === 'config_error' || reason === 'error') {
			options.setOverlayErrorMessage(data?.message || '');
			options.setConnectionState('error');
		} else {
			options.setOverlayErrorMessage('');
		}

		if (
			data?.message &&
			['sideband_error', 'auth_error', 'config_error', 'error'].includes(reason)
		) {
			options.showErrorToast(data.message);
		}

		await options.cleanup();
		if (shouldAutoClose) {
			options.closeOverlay();
		}
	}

	options.socket.on('events', handleRealtimeEvents);
	options.socket.on('realtime:ready', onRealtimeReady);
	options.socket.on('realtime:sideband_lost', onSidebandLost);
	options.socket.on('realtime:session', onRealtimeSession);
	options.socket.on('realtime:ended', onRealtimeEnded);

	return () => {
		options.socket.off('events', handleRealtimeEvents);
		options.socket.off('realtime:ready', onRealtimeReady);
		options.socket.off('realtime:sideband_lost', onSidebandLost);
		options.socket.off('realtime:session', onRealtimeSession);
		options.socket.off('realtime:ended', onRealtimeEnded);
	};
}
