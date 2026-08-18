import { describe, expect, it } from 'vitest';
import { selectCallOverlayAudioParts } from './index';

describe('selectCallOverlayAudioParts', () => {
	it('dispatches every newly completed part when a chunk finishes multiple sentences', () => {
		const parts = [
			'This is the first complete sentence prepared for speech playback now.',
			'This is the second complete sentence prepared for speech playback now.',
			'This is the third complete sentence prepared for speech playback now.'
		];

		const first = selectCallOverlayAudioParts(parts, 0, false);
		expect(first.parts).toEqual(parts);
		expect(first.nextSent).toBe(3);

		const second = selectCallOverlayAudioParts(parts, first.nextSent, false);
		expect(second.parts).toEqual([]);
		expect(second.nextSent).toBe(3);
	});

	it('holds a still-short trailing part until it is long enough or final', () => {
		const streaming = [
			'This is a long enough first sentence prepared for speech playback.',
			'Hi there'
		];
		const held = selectCallOverlayAudioParts(streaming, 0, false);
		expect(held.parts).toEqual([streaming[0]]);
		expect(held.nextSent).toBe(1);

		const finalized = selectCallOverlayAudioParts(streaming, held.nextSent, true);
		expect(finalized.parts).toEqual([streaming[1]]);
		expect(finalized.nextSent).toBe(2);
	});
});
