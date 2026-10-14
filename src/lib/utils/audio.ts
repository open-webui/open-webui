type AudioQueueEvent = 'stop' | 'empty-queue' | 'id-change' | 'error';

interface AudioQueueStopDetail {
	event: AudioQueueEvent;
	id: string | null;
}

const HOLD_IDLE_TIMEOUT_MS = 30_000;

const SILENT_WAV =
	'data:audio/wav;base64,UklGRsQAAABXQVZFZm10IBAAAAABAAEAQB8AAIA+AAACABAAZGF0YaAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA';

export type OnStoppedCallback = (detail: AudioQueueStopDetail) => void;

export class AudioQueue {
	private audio: HTMLAudioElement;
	private queue: string[] = [];
	private current: string | null = null;
	private holds = 0;
	private session = 0;
	private idleTimer: ReturnType<typeof setTimeout> | null = null;
	private readonly _onEnded = () => this.next();
	private readonly _onGesture = () => this.#unlock();

	id: string | null = null;
	onStopped: OnStoppedCallback | null = null;

	constructor(audioElement: HTMLAudioElement) {
		this.audio = audioElement;
		this.audio.addEventListener('ended', this._onEnded);
		document.addEventListener('pointerdown', this._onGesture, true);
		document.addEventListener('keydown', this._onGesture, true);
	}

	setId(newId: string) {
		if (this.id === newId) return;

		this.#resetHolds();
		this.#halt();
		this.id = newId;
		this.onStopped?.({ event: 'id-change', id: newId });
	}

	/**
	 * Signal that a producer is still working: while holds are active, an
	 * exhausted queue is treated as a gap between items rather than as
	 * end-of-playback. Returns a scoped release function.
	 *
	 * A watchdog force-releases after HOLD_IDLE_TIMEOUT_MS without a new
	 * enqueue so a stalled or hostile producer can never wedge playback.
	 */
	hold(): () => void {
		this.holds++;
		const session = this.session;
		this.#armIdleTimer();

		let released = false;
		return () => {
			if (released) return;
			released = true;
			if (session !== this.session) return;

			this.holds = Math.max(0, this.holds - 1);
			if (this.holds === 0) {
				this.#clearIdleTimer();
				this.#maybeDrain();
			}
		};
	}

	setPlaybackRate(rate: number) {
		this.audio.defaultPlaybackRate = rate;
		this.audio.playbackRate = rate;
	}

	enqueue(url: string) {
		this.queue.push(url);

		if (this.holds > 0) this.#armIdleTimer();

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

	/** Play silence inside the first user gesture so WebKit allows later programmatic playback. */
	#unlock() {
		if (this.current || !this.audio.paused) return;

		this.audio.src = SILENT_WAV;
		this.audio
			.play()
			.then(() => this.#removeGestureListeners())
			.catch(() => {})
			.finally(() => {
				if (this.current) return;

				this.audio.pause();
				if (this.queue.length) this.next();
			});
	}

	next() {
		this.current = this.queue.shift() ?? null;

		if (this.current) {
			const url = this.current;
			this.audio.src = url;
			this.audio.muted = false;
			this.audio.play().catch((error) => {
				if (this.current !== url) return;

				console.error(error);
				this.#resetHolds();
				this.#halt();
				this.onStopped?.({ event: 'error', id: this.id });
			});
		} else {
			this.#halt();

			// With an active hold an exhausted queue is a gap, not the end of playback.
			if (this.holds === 0) {
				this.onStopped?.({ event: 'empty-queue', id: this.id });
			}
		}
	}

	stop() {
		this.#resetHolds();
		this.#halt();
		this.onStopped?.({ event: 'stop', id: this.id });
	}

	destroy() {
		this.audio.removeEventListener('ended', this._onEnded);
		this.#removeGestureListeners();
		this.#resetHolds();
		this.#halt();
		this.onStopped = null;
	}

	#removeGestureListeners() {
		document.removeEventListener('pointerdown', this._onGesture, true);
		document.removeEventListener('keydown', this._onGesture, true);
	}

	/** Drop all outstanding holds and invalidate their release closures. */
	#resetHolds() {
		this.holds = 0;
		this.session++;
		this.#clearIdleTimer();
	}

	#armIdleTimer() {
		this.#clearIdleTimer();
		this.idleTimer = setTimeout(() => {
			this.idleTimer = null;
			if (this.holds === 0) return;

			// Playback is still progressing; keep waiting for the producer.
			if (this.current || !this.audio.paused || this.queue.length > 0) {
				this.#armIdleTimer();
				return;
			}

			this.#resetHolds();
			this.onStopped?.({ event: 'empty-queue', id: this.id });
		}, HOLD_IDLE_TIMEOUT_MS);
	}

	#clearIdleTimer() {
		if (this.idleTimer !== null) {
			clearTimeout(this.idleTimer);
			this.idleTimer = null;
		}
	}

	/** Fire end-of-playback once holds are gone and nothing is left to play. */
	#maybeDrain() {
		if (this.holds > 0) return;
		if (this.current || !this.audio.paused || this.queue.length > 0) return;

		this.#halt();
		this.onStopped?.({ event: 'empty-queue', id: this.id });
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
