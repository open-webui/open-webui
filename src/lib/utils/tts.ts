import { synthesizeOpenAISpeech } from '$lib/apis/audio';
import { config, settings, TTSWorker } from '$lib/stores';
import { toast } from 'svelte-sonner';

import { getMessageContentParts } from '$lib/utils';
import { KokoroWorker } from '$lib/workers/KokoroWorker';
import { get } from 'svelte/store';
import { v4 as uuidv4 } from 'uuid';

const _internal = Symbol('TTSManagerInternal');

export class TTSElement {
	private readonly id: string;
	public readonly content: string;
	private abortController;

	private engine: 'webAPI' | 'browser-kokoro' | 'external' = 'webAPI';
	private webApiSpeak: undefined | SpeechSynthesisUtterance;
	private messageContentParts: string[] = [];
	private playingAudio: undefined | HTMLAudioElement;

	[_internal] = {
		getId: () => this.id,

		load: async () => {
			if (this.abortController.signal.aborted) return;

			return new Promise<void>(async (resolve, reject) => {
				// Handle cancellation
				this.abortController.signal.addEventListener('abort', () => {
					reject({ canceled: true });
				});

				const currentConfig = get(config);
				const currentSettings = get(settings);

				const audioEngine = currentConfig?.audio.tts.engine;
				if (audioEngine === '') {
					// WebAPI
					this.engine = 'webAPI';

					const voices = speechSynthesis.getVoices();

					const voice =
						voices
							?.filter(
								(v) =>
									v.voiceURI ===
									(currentSettings?.audio?.tts?.voice ?? currentConfig?.audio?.tts?.voice)
							)
							?.at(0) ?? undefined;

					console.log(voice);

					this.webApiSpeak = new SpeechSynthesisUtterance(this.content);
					this.webApiSpeak.rate = currentSettings.audio?.tts?.playbackRate ?? 1;

					if (voice) {
						this.webApiSpeak.voice = voice;
					}

					console.log(this.webApiSpeak);

					resolve();
				} else {
					this.messageContentParts = getMessageContentParts(
						this.content,
						currentConfig?.audio?.tts?.split_on ?? 'punctuation'
					);

					if (!this.messageContentParts.length) {
						console.log('No content to speak');
						toast.info('No content to speak');

						reject();
					}

					console.debug('Prepared message content for TTS', this.messageContentParts);

					if (audioEngine === 'browser-kokoro') {
						// Kokoro
						this.engine = 'browser-kokoro';

						const currentTTSWorker = get(TTSWorker);
						if (currentTTSWorker) {
							await TTSWorker.set(
								new KokoroWorker({
									dtype: currentSettings?.audio?.tts?.engineConfig?.dtype ?? 'fp32'
								})
							);

							await get(TTSWorker)?.init?.();
						}
					} else {
						// External (OpenAI, Azure, etc - call backend)

						this.engine = 'external';
					}

					resolve();
				}
			});
		},

		play: async () => {
			if (this.abortController.signal.aborted) return;

			return new Promise<void>(async (resolve, reject) => {
				// Handle cancellation
				this.abortController.signal.addEventListener('abort', () => {
					if (this.engine === 'webAPI') {
						speechSynthesis.cancel();
					} else if (this.engine === 'browser-kokoro' || this.engine === 'external') {
						this.playingAudio!.pause();
						this.playingAudio!.currentTime = 0;
					}

					reject({ canceled: true });
				});

				if (this.engine === 'webAPI') {
					this.webApiSpeak!.onend = () => {
						resolve();
					};

					speechSynthesis.speak(this.webApiSpeak!);
				} else if (this.engine === 'browser-kokoro' || this.engine === 'external') {
					const audioParts: Record<number, HTMLAudioElement | null> =
						this.messageContentParts.reduce(
							(acc, _sentence, idx) => {
								acc[idx] = null;
								return acc;
							},
							{} as typeof audioParts
						);

					let playing = false;
					let playingIdx = 0;

					const playPart = async (followOn?: boolean) => {
						console.log(playing, followOn, this.messageContentParts, audioParts, playingIdx);

						if (!playing || followOn) {
							this.playingAudio = audioParts[playingIdx] ?? undefined;

							if (!this.playingAudio) {
								playing = false;
								return;
							}

							playing = true;
							this.playingAudio.onended = () => {
								playingIdx++;

								if (playingIdx >= Object.keys(audioParts).length) {
									resolve();
									return;
								}

								playPart(true);
							};

							this.playingAudio.play();
						}
					};

					const currentConfig = get(config);
					const currentSettings = get(settings);

					for (const [idx, sentence] of this.messageContentParts.entries()) {
						let blob;

						if (this.engine === 'browser-kokoro') {
							blob = await get(TTSWorker)
								.generate({
									text: sentence,
									voice: get(settings)?.audio?.tts?.voice ?? currentConfig?.audio?.tts?.voice
								})
								.catch((error) => {
									console.error(error);
									toast.error(`${error}`);

									reject();
								});
						} else {
							const res = await synthesizeOpenAISpeech(
								localStorage.token,
								currentSettings?.audio?.tts?.defaultVoice === currentConfig?.audio.tts.voice
									? (currentSettings?.audio?.tts?.voice ?? currentConfig?.audio?.tts?.voice)
									: currentConfig?.audio?.tts?.voice,
								sentence,
								undefined
							).catch((error) => {
								console.error(error);
								toast.error(`${error}`);

								reject();
							});

							blob = await res?.blob();
						}

						if (blob) {
							const blobUrl = URL.createObjectURL(blob);
							const audio = new Audio(blobUrl);
							audio.playbackRate = get(settings)?.audio?.tts?.playbackRate ?? 1;

							audioParts[idx] = audio;
							playPart();
						}
					}
				}
			});
		},

		cancel: () => {
			this.abortController.abort();
			this.onCancel?.();
		}
	};

	get canceled() {
		return this.abortController.signal.aborted;
	}

	// Callbacks
	onLoading?: () => void;
	onSpeaking?: () => void;
	onFinish?: () => void;
	onCancel?: () => void;

	constructor(content: string) {
		this.id = uuidv4();
		this.content = content;
		this.abortController = new AbortController();
	}
}

export class TTSManager {
	private static ttsQueue: TTSElement[] = [];

	static queue(element: TTSElement) {
		this.ttsQueue.push(element);

		// If this is the only element then play in now
		if (this.ttsQueue.length === 1) {
			this.play();
		}
	}

	static cancel(element: TTSElement) {
		const idx = this.ttsQueue.findIndex((e) => e[_internal].getId() === element[_internal].getId());

		if (idx !== -1) {
			this.ttsQueue[idx][_internal].cancel();
			this.ttsQueue.splice(idx, 1);
		}
	}

	private static async play() {
		if (this.ttsQueue.length >= 1) {
			const e = this.ttsQueue[0];

			try {
				e.onLoading?.();
				await e[_internal].load();

				e.onSpeaking?.();
				await e[_internal].play();

				e.onFinish?.();

				// Remove once playback completed
				this.ttsQueue.splice(0, 1);
			} catch (err: any) {
				if (err && err.canceled) {
					// Audio playback was cancelled - this would have already removed it
				} else {
					// Error in loading/playback
					this.ttsQueue.splice(0, 1);
					e.onCancel?.();
				}
			} finally {
				// Play the next in the queue
				this.play();
			}
		}
	}

	static cancelAll() {
		while (this.ttsQueue.length > 0) {
			const element = this.ttsQueue.pop()!;
			element[_internal].cancel();
		}
	}
}
