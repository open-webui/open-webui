import { describe, expect, it } from 'vitest';
import { get } from 'svelte/store';
import {
	activeCitationHovercard,
	clampCitationIndex,
	closeCitationHovercard,
	openCitationHovercard,
	stepCitationIndex
} from './citationHovercard';

describe('citation hovercard ownership', () => {
	it('replaces the prior owner and ignores its stale close', () => {
		const first = {};
		const second = {};

		openCitationHovercard(first);
		openCitationHovercard(second);
		closeCitationHovercard(first);

		expect(get(activeCitationHovercard)).toBe(second);
		closeCitationHovercard(second);
		expect(get(activeCitationHovercard)).toBeNull();
	});
});

describe('citation hovercard selection', () => {
	it('clamps invalid and out-of-range indexes', () => {
		expect(clampCitationIndex(-2, 3)).toBe(0);
		expect(clampCitationIndex(8, 3)).toBe(2);
		expect(clampCitationIndex(Number.NaN, 3)).toBe(0);
		expect(clampCitationIndex(1, 0)).toBe(0);
	});

	it('uses disabled boundary navigation instead of wrapping', () => {
		expect(stepCitationIndex(0, 3, -1)).toBe(0);
		expect(stepCitationIndex(0, 3, 1)).toBe(1);
		expect(stepCitationIndex(2, 3, 1)).toBe(2);
	});
});
