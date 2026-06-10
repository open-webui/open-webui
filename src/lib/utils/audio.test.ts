import { describe, expect, it } from 'vitest';

import { getUndispatchedAudioContentParts } from './audio';

describe('getUndispatchedAudioContentParts', () => {
	it('returns every completed content part that has not been dispatched yet', () => {
		expect(
			getUndispatchedAudioContentParts(
				['Sentence one.', 'Sentence two.', 'Sentence three.', 'partial'],
				0
			)
		).toEqual([
			{ index: 1, content: 'Sentence two.' },
			{ index: 2, content: 'Sentence three.' }
		]);
	});

	it('tracks by index so repeated sentences are still dispatched once each', () => {
		expect(
			getUndispatchedAudioContentParts(['Hello.', 'Goodbye.', 'Hello.', 'partial'], -1)
		).toEqual([
			{ index: 0, content: 'Hello.' },
			{ index: 1, content: 'Goodbye.' },
			{ index: 2, content: 'Hello.' }
		]);
	});

	it('includes the final content part when the stream is complete', () => {
		expect(
			getUndispatchedAudioContentParts(
				['Sentence one.', 'Sentence two.', 'Final sentence.'],
				1,
				true
			)
		).toEqual([{ index: 2, content: 'Final sentence.' }]);
	});
});
