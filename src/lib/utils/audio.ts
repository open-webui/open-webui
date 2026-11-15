type AudioQueueEvent = 'stop' | 'empty-queue' | 'id-change' | 'error';

interface AudioQueueStopDetail {
	event: AudioQueueEvent;
	id: string | null;
}

const SILENT_WAV =
	'data:audio/wav;base64,UklGRsQAAABXQVZFZm10IBAAAAABAAEAQB8AAIA+AAACABAAZGF0YaAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA';

export type OnStoppedCallback = (detail: AudioQueueStopDetail) => void;

export class AudioQueue {
	private audio: HTMLAudioElement;
	private queue: string[] = [];
	private current: string | null = null;
	private readonly _onEnded = () => this.next();
	private readonly _onGesture = () => this.#unlock();

	id: string | null = null;
	onStopped: OnStoppedCallback | null = null;

	constructor(
		audioElement: HTMLAudioElement,
		private isAutoPlaybackEnabled: () => boolean
	) {
		this.audio = audioElement;
		this.audio.addEventListener('ended', this._onEnded);
		document.addEventListener('pointerdown', this._onGesture, true);
		document.addEventListener('keydown', this._onGesture, true);
	}

	setId(newId: string) {
		if (this.id === newId) return;

		this.#halt();
		this.id = newId;
		this.onStopped?.({ event: 'id-change', id: newId });
	}

	setPlaybackRate(rate: number) {
		this.audio.defaultPlaybackRate = rate;
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

	/** Play silence inside the first user gesture so WebKit allows later programmatic playback. */
	#unlock() {
		if (this.current || !this.audio.paused || !this.isAutoPlaybackEnabled()) return;

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
				this.#halt();
				this.onStopped?.({ event: 'error', id: this.id });
			});
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
		this.#removeGestureListeners();
		this.#halt();
		this.onStopped = null;
	}

	#removeGestureListeners() {
		document.removeEventListener('pointerdown', this._onGesture, true);
		document.removeEventListener('keydown', this._onGesture, true);
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

export const notificationSoundStyles = ['chime', 'soft', 'bell', 'tap'] as const;
export type NotificationSoundStyle = (typeof notificationSoundStyles)[number];

type NotificationTone = {
	frequency: number;
	duration: number;
	volume: number;
	delay?: number;
	endFrequency?: number;
};

const notificationTones: Record<NotificationSoundStyle, NotificationTone[]> = {
	chime: [
		{ frequency: 659.25, duration: 0.36, volume: 0.08 },
		{ frequency: 880, duration: 0.48, volume: 0.06, delay: 0.09 }
	],
	soft: [
		{ frequency: 440, duration: 0.3, volume: 0.07 },
		{ frequency: 660, duration: 0.24, volume: 0.025 }
	],
	bell: [
		{ frequency: 1046.5, duration: 0.6, volume: 0.06 },
		{ frequency: 2093, duration: 0.24, volume: 0.025 },
		{ frequency: 2900, duration: 0.13, volume: 0.012 }
	],
	tap: [{ frequency: 200, endFrequency: 90, duration: 0.07, volume: 0.16 }]
};

let notificationContext: AudioContext | null = null;
let notificationSoundEnabled = true;
const notificationVoices = new Set<{ oscillator: OscillatorNode; gain: GainNode }>();

function stopNotificationVoices() {
	if (!notificationContext) return;
	const now = notificationContext.currentTime;
	for (const { oscillator, gain } of notificationVoices) {
		gain.gain.cancelScheduledValues(now);
		gain.gain.setValueAtTime(gain.gain.value, now);
		gain.gain.linearRampToValueAtTime(0, now + 0.02);
		oscillator.stop(now + 0.02);
	}
	notificationVoices.clear();
}

export function setNotificationSoundEnabled(enabled: boolean) {
	notificationSoundEnabled = enabled;
	if (!enabled) stopNotificationVoices();
}

// Unlock inside a user gesture so later background completions can make sound.
export async function unlockNotificationAudio(): Promise<boolean> {
	if (
		!notificationSoundEnabled ||
		typeof window === 'undefined' ||
		navigator.userActivation?.hasBeenActive === false ||
		!window.AudioContext
	)
		return false;
	try {
		notificationContext ??= new AudioContext();
		if (notificationContext.state === 'suspended') await notificationContext.resume();
		return notificationContext.state === 'running';
	} catch {
		return false;
	}
}

export async function playNotificationSound(
	style: NotificationSoundStyle = 'chime'
): Promise<boolean> {
	if (!(await unlockNotificationAudio()) || !notificationSoundEnabled || !notificationContext)
		return false;
	stopNotificationVoices();
	const selected = notificationSoundStyles.includes(style) ? style : 'chime';
	for (const tone of notificationTones[selected]) {
		const oscillator = notificationContext.createOscillator();
		const gain = notificationContext.createGain();
		const start = notificationContext.currentTime + (tone.delay ?? 0);
		oscillator.frequency.setValueAtTime(tone.frequency, start);
		if (tone.endFrequency) {
			oscillator.frequency.exponentialRampToValueAtTime(tone.endFrequency, start + tone.duration);
		}
		gain.gain.setValueAtTime(0, start);
		gain.gain.linearRampToValueAtTime(tone.volume, start + (selected === 'soft' ? 0.03 : 0.005));
		gain.gain.exponentialRampToValueAtTime(0.0001, start + tone.duration);
		oscillator.connect(gain).connect(notificationContext.destination);
		const voice = { oscillator, gain };
		notificationVoices.add(voice);
		oscillator.onended = () => {
			oscillator.disconnect();
			gain.disconnect();
			notificationVoices.delete(voice);
		};
		oscillator.start(start);
		oscillator.stop(start + tone.duration + 0.02);
	}
	return true;
}
