import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { AudioQueue } from './audio';

const HOLD_IDLE_TIMEOUT_MS = 30_000;

class FakeAudioElement {
	paused = true;
	currentTime = 0;
	src = '';
	muted = false;
	playbackRate = 1;
	defaultPlaybackRate = 1;

	private listeners: Record<string, (() => void)[]> = {};

	addEventListener(type: string, fn: () => void) {
		(this.listeners[type] ??= []).push(fn);
	}

	removeEventListener(type: string, fn: () => void) {
		this.listeners[type] = (this.listeners[type] ?? []).filter((f) => f !== fn);
	}

	play() {
		this.paused = false;
		return Promise.resolve();
	}

	pause() {
		this.paused = true;
	}

	removeAttribute(name: string) {
		if (name === 'src') this.src = '';
	}

	load() {}

	/** Simulate the element finishing the current clip. */
	simulateEnded() {
		this.paused = true;
		for (const fn of this.listeners['ended'] ?? []) fn();
	}
}

const createQueue = () => {
	const audio = new FakeAudioElement();
	const queue = new AudioQueue(audio as unknown as HTMLAudioElement);

	const events: string[] = [];
	queue.onStopped = ({ event }) => events.push(event);

	return { audio, queue, events };
};

describe('AudioQueue', () => {
	beforeEach(() => {
		vi.useFakeTimers();
		vi.stubGlobal('document', {
			addEventListener: () => {},
			removeEventListener: () => {}
		});
	});

	afterEach(() => {
		vi.runOnlyPendingTimers();
		vi.useRealTimers();
		vi.unstubAllGlobals();
	});

	it('fires empty-queue when an exhausted queue has no active hold', () => {
		const { audio, queue, events } = createQueue();

		queue.enqueue('a');
		audio.simulateEnded();

		expect(events).toEqual(['empty-queue']);
	});

	it('treats an exhausted queue as a gap while held and resumes on next enqueue', () => {
		const { audio, queue, events } = createQueue();

		const release = queue.hold();

		queue.enqueue('a');
		audio.simulateEnded(); // queue drains mid-production

		expect(events).toEqual([]);

		queue.enqueue('b'); // producer catches up

		expect(events).toEqual([]);
		expect(audio.paused).toBe(false); // playback resumed

		audio.simulateEnded(); // last item finished, queue empty, still held

		expect(events).toEqual([]);

		release(); // producer done

		expect(events).toEqual(['empty-queue']);
	});

	it('fires empty-queue exactly once when the producer releases with nothing left', () => {
		const { queue, events } = createQueue();

		const release = queue.hold();
		release();
		release(); // idempotent

		expect(events).toEqual(['empty-queue']);
	});

	it('watchdog force-terminates a hold when the producer goes silent', () => {
		const { queue, events } = createQueue();

		queue.hold(); // producer never enqueues anything

		vi.advanceTimersByTime(HOLD_IDLE_TIMEOUT_MS - 1);
		expect(events).toEqual([]);

		vi.advanceTimersByTime(1);
		expect(events).toEqual(['empty-queue']);
	});

	it('enqueue during a hold resets the watchdog', () => {
		const { audio, queue, events } = createQueue();

		queue.hold();

		vi.advanceTimersByTime(20_000);
		queue.enqueue('a'); // re-arms the watchdog

		vi.advanceTimersByTime(5_000);
		audio.simulateEnded(); // gap begins, timer still armed from the enqueue

		vi.advanceTimersByTime(24_000); // 29s since last enqueue
		expect(events).toEqual([]);

		vi.advanceTimersByTime(1_000); // 30s of silence
		expect(events).toEqual(['empty-queue']);
	});

	it('watchdog keeps waiting while audio is still playing', () => {
		const { queue, events } = createQueue();

		queue.hold();
		queue.enqueue('a'); // long clip, still playing when the timer fires

		vi.advanceTimersByTime(HOLD_IDLE_TIMEOUT_MS * 3);
		expect(events).toEqual([]);
	});

	it('stop clears holds and stale releases become no-ops', () => {
		const { audio, queue, events } = createQueue();

		const release = queue.hold();
		queue.enqueue('a');

		queue.stop();
		expect(events).toEqual(['stop']);

		release(); // stale release must not fire anything

		expect(events).toEqual(['stop']);

		queue.enqueue('b');
		audio.simulateEnded();

		expect(events).toEqual(['stop', 'empty-queue']);
	});

	it('setId clears holds from a previous speak session', () => {
		const { queue, events } = createQueue();

		const release = queue.hold();
		queue.setId('message-1');

		expect(events).toEqual(['id-change']);

		release(); // stale release must not fire empty-queue

		expect(events).toEqual(['id-change']);
	});
});
