import { AUDIO_API_BASE_URL } from '$lib/constants';

export type BridgeSubmission = {
	status: 'submitted' | 'deferred' | 'rejected';
	chatId?: string;
	userMessageId?: string;
	assistantMessageId?: string;
	taskIds?: string[];
};

type CallContext = {
	chatId?: string;
	modelId: string;
	voiceModel?: string;
	voice?: string;
	messages: { role: string; content: string }[];
};
type VoiceTurn = {
	callId: string;
	inputId: string;
	userId: string;
	assistantId?: string;
	taskIds?: string[];
	modelId: string;
	finished: boolean;
	approval: boolean;
};
type Options = {
	context: () => CallContext;
	addMessage: (role: string, text: string, voice: any, parentId?: string) => Promise<string>;
	submit: (text: string, options: any) => Promise<BridgeSubmission>;
	stop: (messageId: string) => Promise<void>;
	message: (messageId: string) => any;
	visibleText: (message: any) => string;
	saveVoice: (messageId: string, voice: any) => Promise<void>;
	change: () => void;
	error: (message: string) => void;
};

export function getBridgeTurnState(message: any) {
	if (!message) return 'working';
	if (message.error) return 'failed';
	if (message.bridgeCancelled) return 'cancelled';
	if (message.bridgeStopping) return 'working';
	const output = message.output ?? [];
	const results = new Set(
		output
			.filter((item: any) => item.type === 'function_call_output')
			.map((item: any) => item.call_id)
	);
	const pending = output.filter(
		(item: any) =>
			item.type === 'function_call' &&
			!results.has(item.call_id ?? item.id) &&
			!['rejected', 'cancelled', 'failed'].includes(item.status)
	);
	if (
		pending.some(
			(item: any) =>
				['pending', 'queued', 'requires_approval'].includes(item.status) || item.name === 'ask_user'
		)
	)
		return 'approval';
	if (pending.length || !message.done) return 'working';
	return 'completed';
}

/** One browser call, with no provider credentials and no alternate chat execution path. */
export class RealtimeCall {
	connected = false;
	connecting = false;
	muted = false;
	speaking = false;
	working = false;
	approval = false;
	model = '';
	voice = '';
	inputLevel = 0;
	outputLevel = 0;
	error = '';
	private ws?: WebSocket;
	private context?: AudioContext;
	private stream?: MediaStream;
	private source?: MediaStreamAudioSourceNode;
	private audio?: AudioWorkletNode;
	private timer?: ReturnType<typeof setInterval>;
	private session = 0;
	private callId = '';
	private token = '';
	private configuration = '';
	private cancelRequested = false;
	private receivingSpeech = false;
	private savingHistory = 0;
	private lastPong = 0;
	private activeResponse = '';
	private responseRequested = false;
	private speakingResponses = new Set<string>();
	private interrupted = new Set<string>();
	private responses = new Map<string, any>();
	private inputs = new Map<string, { text: string; userId: Promise<string>; modelId: string }>();
	private calls = new Map<string, VoiceTurn>();
	private pending?: VoiceTurn;
	private commands: any[] = [];
	private delegation = Promise.resolve();
	private recording = Promise.resolve();
	private metadata = Promise.resolve();
	private clearId = 0;
	private sentSamples = 0;
	private clears = new Map<number, Set<string>>();

	constructor(private options: Options) {}

	async connect(token: string) {
		if (this.connected || this.connecting) return;
		this.error = '';
		this.connecting = true;
		this.options.change();
		const session = ++this.session;
		this.callId = crypto.randomUUID();
		try {
			const context = this.options.context();
			this.token = token;
			this.configuration = JSON.stringify([context.modelId, context.voiceModel, context.voice]);
			if (!context.modelId) throw new Error('Select one server-configured chat model.');
			this.context = new AudioContext({ sampleRate: 24000 });
			if (this.context.sampleRate !== 24000 || !this.context.audioWorklet) {
				throw new Error(
					'This browser cannot use 24 kHz AudioWorklet audio. Use Standard call mode.'
				);
			}
			await this.context.resume();
			const stream = await navigator.mediaDevices.getUserMedia({
				audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true }
			});
			if (session !== this.session) {
				stream.getTracks().forEach((track) => track.stop());
				return;
			}
			this.stream = stream;
			await this.context.audioWorklet.addModule(new URL('./realtime-audio.js', import.meta.url));
			if (session !== this.session) return;
			this.audio = new AudioWorkletNode(this.context, 'realtime-audio', {
				outputChannelCount: [1]
			});
			this.source = this.context.createMediaStreamSource(stream);
			this.source.connect(this.audio);
			this.audio.connect(this.context.destination);
			this.audio.port.onmessage = ({ data }) => this.audioEvent(data);
			const url = new URL(`${AUDIO_API_BASE_URL}/realtime`, location.href);
			url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
			const ws = new WebSocket(url);
			this.ws = ws;
			const started = Date.now();
			this.lastPong = started;
			ws.onopen = () =>
				this.send({ type: 'auth', token, chat_id: context.chatId, model_id: context.modelId });
			ws.onmessage = ({ data }) => {
				if (session !== this.session) return;
				try {
					this.event(JSON.parse(data), context);
				} catch {
					this.fail('Invalid voice event. The call has ended.');
				}
			};
			ws.onerror = () => this.fail('Voice connection failed.');
			ws.onclose = () => {
				if (session === this.session) this.fail('Voice connection closed.');
			};
			this.timer = setInterval(() => {
				if (!this.connected && Date.now() - started > 45000)
					this.fail('Voice connection timed out.');
				else if (this.connected) {
					if (Date.now() - this.lastPong > 45000) this.fail('Voice connection stopped responding.');
					else this.send({ type: 'bridge.ping' });
				}
			}, 10000);
		} catch (error) {
			if (session === this.session)
				this.fail(error instanceof Error ? error.message : 'Could not start microphone.');
		}
	}

	private send(event: any) {
		if (this.ws?.readyState === WebSocket.OPEN) this.ws.send(JSON.stringify(event));
	}

	private audioEvent(data: any) {
		if (data.type === 'input' && this.connected && !this.muted) {
			// PCM expands by 4/3 in JSON base64; one second is 64 KB on the wire.
			if ((this.ws?.bufferedAmount ?? 0) > 64000) {
				this.fail('Microphone connection is more than one second behind.');
				return;
			}
			this.send({
				type: 'input_audio_buffer.append',
				audio: btoa(String.fromCharCode(...new Uint8Array(data.pcm)))
			});
		} else if (data.type === 'playback') {
			const inputLevel = this.muted ? 0 : (data.inputLevel ?? 0);
			const outputLevel = data.outputLevel ?? 0;
			const levelsChanged =
				Math.abs(inputLevel - this.inputLevel) > 0.002 ||
				Math.abs(outputLevel - this.outputLevel) > 0.002;
			const nextSpeaking = data.queued > 0 || this.sentSamples > data.received;
			const speakingChanged = this.speaking !== nextSpeaking;
			this.speaking = nextSpeaking;
			if (!this.speaking && !this.activeResponse && !this.responseRequested)
				this.speakingResponses.clear();
			if (levelsChanged || speakingChanged) {
				this.inputLevel = inputLevel;
				this.outputLevel = outputLevel;
				this.options.change();
			}
			this.flush();
		} else if (data.type === 'overflow') {
			this.stopSpeaking();
			this.fail('Voice playback exceeded the 120 second buffer.');
		} else if (data.type === 'cleared') {
			const responses = this.clears.get(data.id);
			this.clears.delete(data.id);
			const latency = (this.context?.baseLatency ?? 0) + (this.context?.outputLatency ?? 0);
			for (const item of data.rendered) {
				if (!responses?.has(item.response_id)) continue;
				this.send({
					type: 'conversation.item.truncate',
					item_id: item.item_id,
					content_index: item.content_index,
					audio_end_ms: Math.max(0, Math.floor(item.samples / 24 - latency * 1000))
				});
			}
			// An item may have been queued but never rendered.
			for (const responseId of responses ?? []) {
				for (const item of this.responses.get(responseId)?.audio?.values() ?? []) {
					if (
						!data.rendered.some(
							(entry: any) =>
								entry.item_id === item.item_id && entry.content_index === item.content_index
						)
					) {
						this.send({ type: 'conversation.item.truncate', ...item, audio_end_ms: 0 });
					}
				}
			}
			this.flush();
		}
	}

	private enqueue(command: any) {
		if (
			command.type === 'bridge.status' &&
			this.commands.some((item) => item.type === 'bridge.status' && item.status === command.status)
		)
			return;
		if (command.type === 'bridge.respond' && command.item_id) this.commands.unshift(command);
		else this.commands.push(command);
		this.flush();
	}

	private flush() {
		if (
			!this.connected ||
			this.receivingSpeech ||
			this.savingHistory ||
			this.activeResponse ||
			this.responseRequested ||
			this.speaking ||
			this.clears.size
		)
			return;
		this.syncModel();
		if (!this.connected) return;
		const command = this.commands.shift();
		if (command) {
			this.responseRequested = true;
			this.send(command);
		}
	}

	syncModel() {
		if (
			!this.connected ||
			this.receivingSpeech ||
			this.savingHistory ||
			this.working ||
			this.speaking ||
			this.activeResponse ||
			this.responseRequested ||
			this.commands.length
		)
			return;
		const context = this.options.context();
		if (
			this.configuration !== JSON.stringify([context.modelId, context.voiceModel, context.voice])
		) {
			const token = this.token;
			this.end();
			void this.connect(token);
		}
	}

	private event(event: any, initial: CallContext) {
		const type = event.type;
		if (type === 'bridge.error') {
			this.fail(event.message);
			return;
		}
		if (type === 'bridge.pong') {
			this.lastPong = Date.now();
			return;
		}
		if (type === 'bridge.ready') {
			if (event.sample_rate !== 24000) throw new Error('Wrong sample rate');
			this.model = event.model;
			this.voice = event.voice;
			this.connected = true;
			this.connecting = false;
			// A bounded visible-text history, without reasoning or raw tool output.
			let budget = 64000;
			const messages = initial.messages
				.slice(-100)
				.reverse()
				.flatMap((message) => {
					if (!['user', 'assistant'].includes(message.role) || budget <= 0) return [];
					const content = message.content.slice(0, Math.min(32000, budget));
					budget -= content.length;
					return content ? [{ role: message.role, content }] : [];
				})
				.reverse();
			this.send({ type: 'bridge.history', messages });
			this.audio?.port.postMessage({ type: 'capture', enabled: !this.muted });
		} else if (type === 'input_audio_buffer.speech_started') {
			this.receivingSpeech = true;
			this.stopSpeaking();
		} else if (type === 'conversation.item.input_audio_transcription.failed') {
			this.receivingSpeech = false;
			this.enqueue({ type: 'bridge.status', status: 'transcription_failed' });
		} else if (type === 'conversation.item.input_audio_transcription.completed') {
			this.receivingSpeech = false;
			if (this.inputs.has(event.item_id)) return;
			const text = event.transcript?.trim();
			if (!text) {
				this.enqueue({ type: 'bridge.status', status: 'transcription_failed' });
				return;
			}
			const session = this.session;
			const modelId = this.options.context().modelId;
			const userId = this.recording.then(() => {
				if (session !== this.session) return '';
				return this.options.addMessage('user', text, {
					call_id: this.callId,
					input_item_id: event.item_id,
					model: this.model
				});
			});
			this.recording = userId.then(() => undefined);
			this.inputs.set(event.item_id, { text, userId, modelId });
			userId
				.then(() => {
					if (session === this.session)
						this.enqueue({ type: 'bridge.respond', item_id: event.item_id });
				})
				.catch(() => this.fail('Could not save the spoken message.'));
		} else if (type === 'response.created') {
			this.responseRequested = false;
			this.activeResponse = event.response.id;
			if (this.cancelRequested) {
				this.cancelRequested = false;
				this.interrupted.add(event.response.id);
				this.send({ type: 'response.cancel', response_id: event.response.id });
			}
			this.responses.set(event.response.id, {
				...event.response,
				speech: new Map(),
				audio: new Map(),
				delegated: false
			});
		} else if (type === 'response.output_audio.delta') {
			if (this.interrupted.has(event.response_id)) return;
			const bytes = Uint8Array.from(atob(event.delta), (char) => char.charCodeAt(0));
			if (bytes.length % 2) throw new Error('Invalid PCM');
			const view = new DataView(bytes.buffer);
			const samples = new Float32Array(bytes.length / 2);
			for (let i = 0; i < samples.length; i++) samples[i] = view.getInt16(i * 2, true) / 32768;
			this.responses.get(event.response_id)?.audio.set(`${event.item_id}:${event.content_index}`, {
				item_id: event.item_id,
				content_index: event.content_index
			});
			this.sentSamples += samples.length;
			this.speakingResponses.add(event.response_id);
			this.speaking = true;
			this.audio?.port.postMessage(
				{
					type: 'audio',
					samples,
					response_id: event.response_id,
					item_id: event.item_id,
					content_index: event.content_index
				},
				[samples.buffer]
			);
		} else if (type === 'response.output_audio_transcript.delta') {
			const response = this.responses.get(event.response_id);
			if (response)
				response.speech.set(
					event.item_id,
					(response.speech.get(event.item_id) ?? '') + event.delta
				);
		} else if (type === 'response.output_audio_transcript.done') {
			this.responses.get(event.response_id)?.speech.set(event.item_id, event.transcript);
		} else if (
			type === 'response.output_item.done' &&
			event.item?.type === 'function_call' &&
			event.item.status === 'completed'
		) {
			const response = this.responses.get(event.response_id);
			if (
				!response ||
				event.item.name !== 'generate_chat_completion' ||
				this.calls.has(event.item.call_id)
			)
				return;
			const args = JSON.parse(event.item.arguments);
			if (typeof args.request !== 'string' || !args.request.trim())
				throw new Error('Invalid function arguments');
			const inputId = response.metadata?.input_item_id;
			const input = this.inputs.get(inputId);
			if (!input) throw new Error('Function has no transcribed input');
			response.delegated = true;
			if ([...this.calls.values()].some((call) => call.inputId === inputId)) {
				this.send({
					type: 'bridge.result',
					call_id: event.item.call_id,
					status: 'cancelled',
					answer: 'This input has already been delegated.'
				});
				return;
			}
			const turn: VoiceTurn = {
				callId: event.item.call_id,
				inputId,
				userId: '',
				modelId: input.modelId,
				finished: false,
				approval: false
			};
			this.calls.set(turn.callId, turn);
			// A replacement delegation suppresses any old result still waiting to be spoken.
			this.commands = this.commands.filter((command) => !command.call_id);
			const session = this.session;
			this.delegation = this.delegation
				.then(async () => {
					if (session !== this.session) return;
					if (this.pending && !this.pending.finished && this.pending.assistantId) {
						const previous = this.pending;
						previous.finished = true;
						await this.options.stop(previous.assistantId!);
						this.result(previous, 'cancelled', 'Superseded by a new request.', false);
						await this.options.saveVoice(previous.assistantId!, { superseded: true });
					}
					turn.userId = await input.userId;
					if (session !== this.session) return;
					this.pending = turn;
					this.working = true;
					this.options.change();
					const result = await this.options.submit(input.text, {
						_raw: true,
						bridge: { userMessageId: turn.userId, modelId: turn.modelId }
					});
					if (session !== this.session) return;
					if (result?.status !== 'submitted' || !result.assistantMessageId) {
						this.result(
							turn,
							result?.status === 'deferred' ? 'deferred' : 'failed',
							'Complete the required steps in chat and try again.'
						);
						return;
					}
					turn.assistantId = result.assistantMessageId;
					turn.taskIds = result.taskIds;
					this.saveSpeech(response);
					this.update();
				})
				.catch(() =>
					this.fail('Could not submit or stop the selected chat model. Review the request in chat.')
				);
		} else if (type === 'response.done') {
			if (this.activeResponse === event.response.id) this.activeResponse = '';
			this.responseRequested = false;
			this.audio?.port.postMessage({ type: 'done', response_id: event.response.id });
			const response = this.responses.get(event.response.id);
			if (response) {
				response.done = true;
				this.saveSpeech(response);
			}
			if (['failed', 'incomplete'].includes(event.response.status))
				this.options.error('The voice response did not complete.');
			this.flush();
		}
		this.options.change();
	}

	update() {
		const turn = this.pending;
		if (!turn?.assistantId || turn.finished || !this.connected) return;
		const message = this.options.message(turn.assistantId);
		const state = getBridgeTurnState(message);
		this.approval = state === 'approval';
		if (state === 'approval' && !turn.approval)
			this.enqueue({ type: 'bridge.status', status: 'approval' });
		turn.approval = this.approval;
		if (['completed', 'failed', 'cancelled'].includes(state)) {
			this.result(
				turn,
				state,
				state === 'completed'
					? this.options.visibleText(message)
					: 'The backend request did not complete successfully.'
			);
		}
		this.options.change();
	}

	private result(turn: VoiceTurn, status: string, answer: string, speak = true) {
		turn.finished = true;
		this.send({
			type: 'bridge.result',
			call_id: turn.callId,
			status,
			answer:
				answer.length <= 100000
					? answer
					: 'The complete answer is ready in chat. It is too long to read in this call.'
		});
		this.commands = this.commands.filter((command) => command.type !== 'bridge.status');
		if (speak) this.enqueue({ type: 'bridge.respond', call_id: turn.callId });
		if (this.pending === turn) {
			this.working = false;
			this.approval = false;
		}
		this.options.change();
	}

	private saveSpeech(response: any) {
		if (!response.speech.size) return;
		const inputId = response.metadata?.input_item_id;
		const turn = response.metadata?.status
			? this.pending
			: response.metadata?.call_id
				? this.calls.get(response.metadata.call_id)
				: [...this.calls.values()].find((call) => call.inputId === inputId);
		if (response.delegated && !turn?.assistantId) return;
		const input = this.inputs.get(inputId ?? turn?.inputId);
		const speech = [...response.speech.entries()].map(([item_id, transcript]) => ({
			item_id,
			transcript,
			response_id: response.id,
			model: this.model,
			interrupted: this.interrupted.has(response.id)
		}));
		const metadata = {
			call_id: this.callId,
			input_item_id: inputId ?? turn?.inputId,
			function_call_id: turn?.callId,
			task_ids: turn?.taskIds,
			model: this.model,
			speech
		};
		const savedChatId = this.options.context().chatId;
		const savesHistory = !turn?.assistantId;
		if (savesHistory) this.savingHistory++;
		this.metadata = this.metadata
			.then(async () => {
				if (savedChatId !== this.options.context().chatId) return;
				if (turn?.assistantId) await this.options.saveVoice(turn.assistantId, metadata);
				else if (!response.messageId) {
					response.messageId = await this.options.addMessage(
						'assistant',
						speech.map((item) => item.transcript).join('\n'),
						metadata,
						input ? await input.userId : undefined
					);
				} else await this.options.saveVoice(response.messageId, metadata);
			})
			.catch(() => this.options.error('Could not save the voice transcript.'))
			.finally(() => {
				if (savesHistory) this.savingHistory--;
				this.flush();
			});
	}

	stopSpeaking() {
		if (this.responseRequested) this.cancelRequested = true;
		const responses = new Set(
			[...this.speakingResponses].filter((id) => !this.interrupted.has(id))
		);
		if (this.activeResponse && !this.interrupted.has(this.activeResponse)) {
			responses.add(this.activeResponse);
			this.send({ type: 'response.cancel', response_id: this.activeResponse });
		}
		for (const id of responses) {
			this.interrupted.add(id);
			const response = this.responses.get(id);
			if (response?.done) this.saveSpeech(response);
		}
		this.speakingResponses.clear();
		this.speaking = false;
		this.outputLevel = 0;
		const id = ++this.clearId;
		this.clears.set(id, responses);
		this.audio?.port.postMessage({ type: 'clear', id });
		this.commands = this.commands.filter((command) => command.type !== 'bridge.status');
		this.options.change();
	}

	async stopBackend() {
		const turn = this.pending;
		if (!turn?.assistantId || turn.finished) return;
		turn.finished = true;
		try {
			await this.options.stop(turn.assistantId);
			if (this.connected)
				this.result(
					turn,
					'cancelled',
					'The backend request was cancelled. Completed actions have not been undone.'
				);
		} catch {
			this.fail('Backend cancellation was not confirmed. Review the request in chat.');
		}
	}

	mute() {
		this.muted = !this.muted;
		if (this.muted) this.inputLevel = 0;
		this.stream?.getAudioTracks().forEach((track) => {
			track.enabled = !this.muted;
		});
		this.audio?.port.postMessage({ type: 'capture', enabled: this.connected && !this.muted });
		if (this.muted) this.send({ type: 'input_audio_buffer.clear' });
		this.options.change();
	}

	private fail(message: string) {
		this.error = message;
		this.options.error(message);
		this.end();
	}

	end() {
		if (this.connected) {
			this.stopSpeaking();
			for (const response of this.responses.values()) {
				if (!response.done) this.saveSpeech(response);
			}
		}
		++this.session;
		clearInterval(this.timer);
		if (this.ws) {
			this.ws.onclose = null;
			this.ws.onerror = null;
			this.ws.onmessage = null;
			this.ws.close();
		}
		this.ws = undefined;
		this.stream?.getTracks().forEach((track) => track.stop());
		this.source?.disconnect();
		if (this.audio) {
			this.audio.port.onmessage = null;
			this.audio.disconnect();
			this.audio.port.close();
		}
		void this.context?.close();
		this.context = undefined;
		this.audio = undefined;
		this.connected = this.connecting = this.speaking = this.working = this.approval = false;
		this.inputLevel = this.outputLevel = 0;
		this.responseRequested = false;
		this.cancelRequested = false;
		this.receivingSpeech = false;
		this.activeResponse = '';
		this.pending = undefined;
		this.sentSamples = 0;
		this.commands = [];
		this.speakingResponses.clear();
		this.interrupted.clear();
		this.responses.clear();
		this.inputs.clear();
		this.calls.clear();
		this.clears.clear();
		this.options.change();
	}
}
