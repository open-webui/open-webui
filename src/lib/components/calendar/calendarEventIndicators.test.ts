import { describe, expect, it } from 'vitest';
import {
	miniCalendarEventIndicators,
	miniCalendarVisibleRange
} from './calendarEventIndicators';

const NS = 1_000_000;

function atLocalNoon(year: number, monthIndex: number, day: number): number {
	return new Date(year, monthIndex, day, 12, 0, 0, 0).getTime() * NS;
}

describe('miniCalendarEventIndicators', () => {
	it('returns one visible color dot per calendar color by local calendar day', () => {
		const indicators = miniCalendarEventIndicators(
			[
				{
					calendar_id: 'personal',
					start_at: atLocalNoon(2026, 5, 22),
					end_at: null,
					color: null
				},
				{
					calendar_id: 'personal',
					start_at: atLocalNoon(2026, 5, 22),
					end_at: null,
					color: null
				},
				{
					calendar_id: 'care',
					start_at: atLocalNoon(2026, 5, 22),
					end_at: null,
					color: '#ef4444'
				},
				{
					calendar_id: 'hidden',
					start_at: atLocalNoon(2026, 5, 23),
					end_at: null,
					color: null
				}
			],
			new Set(['personal', 'care']),
			new Map([
				['personal', '#3b82f6'],
				['care', '#22c55e'],
				['hidden', '#f59e0b']
			])
		);

		expect(indicators.get(new Date(2026, 5, 22).getTime().toString())).toEqual([
			'#3b82f6',
			'#ef4444'
		]);
		expect(indicators.has(new Date(2026, 5, 23).getTime().toString())).toBe(false);
	});
});

describe('miniCalendarVisibleRange', () => {
	it('returns the six-week mini calendar grid range for the selected month', () => {
		const range = miniCalendarVisibleRange(new Date(2026, 5, 22));

		expect(range.start.getFullYear()).toBe(2026);
		expect(range.start.getMonth()).toBe(4);
		expect(range.start.getDate()).toBe(31);
		expect(range.end.getFullYear()).toBe(2026);
		expect(range.end.getMonth()).toBe(6);
		expect(range.end.getDate()).toBe(12);
	});
});
