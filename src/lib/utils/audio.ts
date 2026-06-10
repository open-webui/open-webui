type AudioQueueEvent = 'stop' | 'empty-queue' | 'id-change';

export interface UndispatchedAudioContentPart {
	index: number;
	content: string;
}

/**
 * Returns the TTS content parts that have not been emitted yet.
 * While streaming, the trailing part is left pending because it may still be incomplete.
 */
export const getUndispatchedAudioContentParts = (
	contentParts: string[],
	lastDispatchedIndex = -1,
	includeLastPart = false
): UndispatchedAudioContentPart[] => {
	const normalizedLastDispatchedIndex = Number.isInteger(lastDispatchedIndex)
		? lastDispatchedIndex
		: -1;
	const dispatchableContentParts = includeLastPart ? contentParts : contentParts.slice(0, -1);

	return dispatchableContentParts
		.map((content, index) => ({ index, content }))
		.slice(Math.max(0, normalizedLastDispatchedIndex + 1))
		.filter(({ content }) => content);
};

interface AudioQueueStopDetail {
	event: AudioQueueEvent;
	id: string | null;
}

export type OnStoppedCallback = (detail: AudioQueueStopDetail) => void;

export class AudioQueue {
	private audio: HTMLAudioElement;
	private queue: string[] = [];
	private current: string | null = null;
	private readonly _onEnded = () => this.next();

	id: string | null = null;
	onStopped: OnStoppedCallback | null = null;

	constructor(audioElement: HTMLAudioElement) {
		this.audio = audioElement;
		this.audio.addEventListener('ended', this._onEnded);
	}

	setId(newId: string) {
		if (this.id === newId) return;

		this.#halt();
		this.id = newId;
		this.onStopped?.({ event: 'id-change', id: newId });
	}

	setPlaybackRate(rate: number) {
		this.audio.playbackRate = rate;
	}

	enqueue(url: string) {
		this.queue.push(url);

		// Auto-play if nothing is currently playing or loaded
		if (this.audio.paused && !this.current) {
			this.next();
		}
	}

	play() {
		if (!this.current && this.queue.length > 0) {
			this.next();
		} else {
			this.audio.play();
		}
	}

	next() {
		this.current = this.queue.shift() ?? null;

		if (this.current) {
			this.audio.src = this.current;
			this.audio.play();
		} else {
			this.#halt();
			this.onStopped?.({ event: 'empty-queue', id: this.id });
		}
	}

	stop() {
		this.#halt();
		this.onStopped?.({ event: 'stop', id: this.id });
	}

	destroy() {
		this.audio.removeEventListener('ended', this._onEnded);
		this.#halt();
		this.onStopped = null;
	}

	/**
	 * Pause audio and clear queue without firing onStopped.
	 * Callers that need the callback should invoke it themselves.
	 */
	#halt() {
		this.audio.pause();
		this.audio.currentTime = 0;
		this.audio.removeAttribute('src');
		this.audio.load();
		this.queue = [];
		this.current = null;
	}
}
