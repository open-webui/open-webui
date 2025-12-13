type RealtimeSttEvent =
	| { type: 'error'; code: string; message: string }
	| { message_type: 'session_started'; session_id?: string }
	| { message_type: 'partial_transcript'; text: string }
	| { message_type: 'committed_transcript'; text: string }
	| { message_type: 'committed_transcript_with_timestamps'; text: string }
	| { message_type: 'error' | 'auth_error'; error: string }
	| { message_type: string; [key: string]: unknown }
	| { [key: string]: unknown };

export type RealtimeSttCallbacks = {
	onPartial?: (text: string) => void;
	onCommitted?: (text: string) => void;
	onError?: (error: string) => void;
	onEvent?: (event: RealtimeSttEvent) => void;
};

const clamp = (value: number, min: number, max: number) => Math.min(max, Math.max(min, value));

const resampleLinear = (
	input: Float32Array,
	inputSampleRate: number,
	outputSampleRate: number
): Float32Array => {
	if (inputSampleRate === outputSampleRate) {
		return input;
	}

	const ratio = inputSampleRate / outputSampleRate;
	const newLength = Math.max(1, Math.round(input.length / ratio));
	const output = new Float32Array(newLength);

	for (let i = 0; i < newLength; i++) {
		const position = i * ratio;
		const leftIndex = Math.floor(position);
		const rightIndex = Math.min(leftIndex + 1, input.length - 1);
		const fraction = position - leftIndex;
		output[i] = input[leftIndex] * (1 - fraction) + input[rightIndex] * fraction;
	}

	return output;
};

const floatToPcm16 = (input: Float32Array): Int16Array => {
	const output = new Int16Array(input.length);
	for (let i = 0; i < input.length; i++) {
		const s = clamp(input[i], -1, 1);
		output[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
	}
	return output;
};

export class RealtimeSttStream {
	private readonly wsUrl: string;
	private readonly callbacks: RealtimeSttCallbacks;
	private readonly targetSampleRate: number;
	private shouldSendAudio: () => boolean;
	private shouldReconnect: () => boolean | Promise<boolean>;
	private readonly maxReconnectRetries: number = 3;

	private ws: WebSocket | null = null;
	private audioContext: AudioContext | null = null;
	private source: MediaStreamAudioSourceNode | null = null;
	private processor: ScriptProcessorNode | null = null;
	private gain: GainNode | null = null;
	private stopped = false;
	private reconnecting = false;
	private reconnectDisabled = false;
	private reconnectAttempt = 0;
	private stream: MediaStream | null = null;

	constructor({
		wsUrl,
		callbacks,
		targetSampleRate = 16000,
		shouldSendAudio = () => true,
		shouldReconnect = () => true
	}: {
		wsUrl: string;
		callbacks?: RealtimeSttCallbacks;
		targetSampleRate?: number;
		shouldSendAudio?: () => boolean;
		shouldReconnect?: () => boolean | Promise<boolean>;
	}) {
		this.wsUrl = wsUrl;
		this.callbacks = callbacks ?? {};
		this.targetSampleRate = targetSampleRate;
		this.shouldSendAudio = shouldSendAudio;
		this.shouldReconnect = shouldReconnect;
	}

	setShouldSendAudio(fn: () => boolean) {
		this.shouldSendAudio = fn;
	}

	setShouldReconnect(fn: () => boolean | Promise<boolean>) {
		this.shouldReconnect = fn;
	}

	private async sleep(ms: number) {
		await new Promise<void>((resolve) => setTimeout(resolve, ms));
	}

	private disableReconnect() {
		this.reconnectDisabled = true;
	}

	private async connectWs() {
		if (this.stopped) {
			throw new Error('Stopped');
		}

		const ws = new WebSocket(this.wsUrl);
		ws.binaryType = 'arraybuffer';
		this.ws = ws;

		ws.onmessage = (event) => {
			if (typeof event.data !== 'string') {
				return;
			}

			let parsed: RealtimeSttEvent | null = null;
			try {
				parsed = JSON.parse(event.data) as RealtimeSttEvent;
			} catch {
				return;
			}

			this.callbacks.onEvent?.(parsed);

			if (parsed && typeof parsed === 'object' && (parsed as any).type === 'error') {
				const code = (parsed as any).code;
				const message = (parsed as any).message;
				if (typeof message === 'string') {
					this.callbacks.onError?.(message);
				}

				if (
					code === 'AUTH_REQUIRED' ||
					code === 'LIMIT_EXHAUSTED' ||
					code === 'POLICY' ||
					code === 'CREDITS_UNAVAILABLE' ||
					code === 'STT_DISABLED' ||
					code === 'STT_NOT_CONFIGURED' ||
					code === 'SESSION_ACTIVE'
				) {
					this.disableReconnect();
				}
				return;
			}

			if (
				parsed &&
				typeof parsed === 'object' &&
				(parsed as any).message_type === 'partial_transcript' &&
				typeof (parsed as any).text === 'string'
			) {
				this.callbacks.onPartial?.((parsed as any).text);
			}

			if (
				parsed &&
				typeof parsed === 'object' &&
				(((parsed as any).message_type === 'committed_transcript' ||
					(parsed as any).message_type === 'committed_transcript_with_timestamps') &&
					typeof (parsed as any).text === 'string')
			) {
				this.callbacks.onCommitted?.((parsed as any).text);
			}

			if (
				parsed &&
				typeof parsed === 'object' &&
				(((parsed as any).message_type === 'error' || (parsed as any).message_type === 'auth_error') &&
					typeof (parsed as any).error === 'string')
			) {
				const errorText = (parsed as any).error as string;
				this.callbacks.onError?.(errorText);
				if ((parsed as any).message_type === 'auth_error') {
					this.disableReconnect();
				}
			}
		};

		await new Promise<void>((resolve, reject) => {
			let settled = false;

			ws.onopen = () => {
				if (settled) return;
				settled = true;
				resolve();
			};

			ws.onerror = () => {
				if (settled) return;
				settled = true;
				reject(new Error('WebSocket connection failed'));
			};

			ws.onclose = (event) => {
				if (this.ws === ws) {
					this.ws = null;
				}
				void this.handleClose(event);

				if (settled) return;
				settled = true;
				reject(new Error(`WebSocket closed (${event.code})`));
			};
		});
	}

	private async handleClose(event: CloseEvent) {
		if (this.stopped || this.reconnecting || this.reconnectDisabled) {
			return;
		}

		if (event.code === 1000) {
			return;
		}

		if (event.code === 1008) {
			return;
		}

		try {
			const shouldReconnect = await this.shouldReconnect();
			if (!shouldReconnect) {
				return;
			}
		} catch {
			// If the reconnect policy check fails, be permissive and let the WS connect path decide.
		}

		// Browser reports abnormal closes as 1006 and does not allow reconnect reasons.
		this.reconnecting = true;
		try {
			while (!this.stopped && !this.reconnectDisabled && this.reconnectAttempt < this.maxReconnectRetries) {
				const delayMs = 1000 * Math.pow(2, this.reconnectAttempt); // 1s, 2s, 4s
				this.reconnectAttempt += 1;
				await this.sleep(delayMs);

				if (this.stopped || this.reconnectDisabled) {
					return;
				}

				try {
					const shouldReconnect = await this.shouldReconnect();
					if (!shouldReconnect) {
						return;
					}
				} catch {
					// ignore policy check failures
				}

				try {
					await this.connectWs();
					this.reconnectAttempt = 0;
					return;
				} catch {
					// try again
				}
			}

			if (!this.stopped && !this.reconnectDisabled) {
				this.callbacks.onError?.('WebSocket connection lost. Please try again.');
			}
		} finally {
			this.reconnecting = false;
		}
	}

	async start(stream: MediaStream) {
		this.stop();
		this.stopped = false;
		this.reconnectDisabled = false;
		this.reconnectAttempt = 0;
		this.stream = stream;

		await this.connectWs();

		let audioContext: AudioContext;
		try {
			audioContext = new AudioContext({ sampleRate: this.targetSampleRate });
		} catch {
			audioContext = new AudioContext();
		}
		this.audioContext = audioContext;

		const source = audioContext.createMediaStreamSource(stream);
		this.source = source;

		const processor = audioContext.createScriptProcessor(2048, 1, 1);
		this.processor = processor;

		const gain = audioContext.createGain();
		gain.gain.value = 0;
		this.gain = gain;

		processor.onaudioprocess = (e) => {
			if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
				return;
			}
			if (!this.shouldSendAudio()) {
				return;
			}

			const input = e.inputBuffer.getChannelData(0);
			const resampled = resampleLinear(input, audioContext.sampleRate, this.targetSampleRate);
			const pcm16 = floatToPcm16(resampled);
			this.ws.send(pcm16.buffer);
		};

		source.connect(processor);
		processor.connect(gain);
		gain.connect(audioContext.destination);
	}

	stop() {
		this.stopped = true;
		try {
			this.processor?.disconnect();
		} catch {
			// ignore
		}
		try {
			this.source?.disconnect();
		} catch {
			// ignore
		}
		try {
			this.gain?.disconnect();
		} catch {
			// ignore
		}

		this.processor = null;
		this.source = null;
		this.gain = null;

		if (this.audioContext) {
			this.audioContext.close().catch(() => {});
			this.audioContext = null;
		}

		if (this.ws) {
			try {
				this.ws.close();
			} catch {
				// ignore
			}
			this.ws = null;
		}

		this.reconnecting = false;
		this.reconnectDisabled = false;
		this.reconnectAttempt = 0;
		this.stream = null;
	}
}
