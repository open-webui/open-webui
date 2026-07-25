import { describe, it, expect } from 'vitest';
import { withStatsOutdated } from './knowledge';

describe('withStatsOutdated', () => {
	it('is a no-op (same reference) when there are no stats yet', () => {
		const noMeta = { id: '1' };
		expect(withStatsOutdated(noMeta)).toBe(noMeta);

		const emptyMeta = { id: '1', meta: {} };
		expect(withStatsOutdated(emptyMeta)).toBe(emptyMeta);

		const nullMeta = { id: '1', meta: null };
		expect(withStatsOutdated(nullMeta)).toBe(nullMeta);
	});

	it('flags stats outdated when stats exist, preserving the stats', () => {
		const kb = {
			id: '1',
			meta: { stats: { file_count: 3, directory_count: 1, total_size: 100 }, statistics_outdated: false }
		};

		const out = withStatsOutdated(kb);

		expect(out).not.toBe(kb); // new object → reactivity fires
		expect(out.meta.statistics_outdated).toBe(true);
		expect(out.meta.stats).toEqual({ file_count: 3, directory_count: 1, total_size: 100 });
	});

	it('does not mutate the original knowledge object', () => {
		const kb = { id: '1', meta: { stats: { file_count: 3 }, statistics_outdated: false } };
		withStatsOutdated(kb);
		expect(kb.meta.statistics_outdated).toBe(false);
	});
});
