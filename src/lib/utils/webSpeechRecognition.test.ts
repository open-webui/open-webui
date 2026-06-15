import { describe, expect, test, vi } from 'vitest';

import { createWebSpeechInactivityController } from './webSpeechRecognition';

describe('createWebSpeechInactivityController', () => {
	test('stops recognition after speech has ended and the inactivity timeout elapses', () => {
		vi.useFakeTimers();
		const stop = vi.fn();
		const controller = createWebSpeechInactivityController({ stop, timeoutMs: 5000 });

		controller.handleSpeechEnd();
		vi.advanceTimersByTime(4999);
		expect(stop).not.toHaveBeenCalled();

		vi.advanceTimersByTime(1);
		expect(stop).toHaveBeenCalledTimes(1);

		vi.useRealTimers();
	});

	test('does not let stale speech-end timers stop active speech', () => {
		vi.useFakeTimers();
		const stop = vi.fn();
		const controller = createWebSpeechInactivityController({ stop, timeoutMs: 5000 });

		controller.handleSpeechEnd();
		vi.advanceTimersByTime(2000);
		controller.handleSpeechStart();
		vi.advanceTimersByTime(3000);

		expect(stop).not.toHaveBeenCalled();

		vi.useRealTimers();
	});
});
