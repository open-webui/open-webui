import { describe, expect, it, vi } from 'vitest';
import { hasLiveAudioTrack, singleFlight, watchAudioTrackEnd } from './audio-stream';

class FakeAudioTrack extends EventTarget {
	readyState: MediaStreamTrackState;

	constructor(readyState: MediaStreamTrackState) {
		super();
		this.readyState = readyState;
	}

	end() {
		this.readyState = 'ended';
		this.dispatchEvent(new Event('ended'));
	}
}

const stream = (...tracks: FakeAudioTrack[]) => ({
	getAudioTracks: () => tracks
});

describe('call audio stream lifecycle', () => {
	it('requires at least one live audio track', () => {
		expect(hasLiveAudioTrack(null)).toBe(false);
		expect(hasLiveAudioTrack(stream(new FakeAudioTrack('ended')))).toBe(false);
		expect(hasLiveAudioTrack(stream(new FakeAudioTrack('ended'), new FakeAudioTrack('live')))).toBe(
			true
		);
	});

	it('reports a disconnected stream only once', () => {
		const first = new FakeAudioTrack('live');
		const second = new FakeAudioTrack('live');
		const onEnded = vi.fn();

		watchAudioTrackEnd(stream(first, second), onEnded);
		first.end();
		second.end();

		expect(onEnded).toHaveBeenCalledOnce();
	});

	it('does not report intentional shutdown after cleanup', () => {
		const track = new FakeAudioTrack('live');
		const onEnded = vi.fn();
		const cleanup = watchAudioTrackEnd(stream(track), onEnded);

		cleanup();
		track.end();

		expect(onEnded).not.toHaveBeenCalled();
	});

	it('coalesces simultaneous recovery signals and permits a later retry', async () => {
		let finishRecovery: (() => void) | undefined;
		const recover = vi.fn(
			() =>
				new Promise<void>((resolve) => {
					finishRecovery = resolve;
				})
		);
		const runRecovery = singleFlight(recover);

		const trackEndedRecovery = runRecovery();
		const deviceChangeRecovery = runRecovery();

		expect(recover).toHaveBeenCalledOnce();
		expect(deviceChangeRecovery).toBe(trackEndedRecovery);

		finishRecovery?.();
		await trackEndedRecovery;

		const laterRecovery = runRecovery();
		expect(recover).toHaveBeenCalledTimes(2);
		finishRecovery?.();
		await laterRecovery;
	});
});
