import { describe, expect, it } from 'vitest';
import { parseReasoningEffortOptions } from './reasoning-effort';

describe('parseReasoningEffortOptions', () => {
	it('parses a comma-separated list', () => {
		expect(parseReasoningEffortOptions('low,medium,high')).toEqual(['low', 'medium', 'high']);
	});

	it('trims whitespace around options', () => {
		expect(parseReasoningEffortOptions(' low , medium ,high ')).toEqual(['low', 'medium', 'high']);
	});

	it('drops empty entries', () => {
		expect(parseReasoningEffortOptions('low,,high,')).toEqual(['low', 'high']);
	});

	it('deduplicates exact matches', () => {
		expect(parseReasoningEffortOptions('low,low,high')).toEqual(['low', 'high']);
	});

	it('returns [] for non-string input', () => {
		expect(parseReasoningEffortOptions(null)).toEqual([]);
		expect(parseReasoningEffortOptions(undefined)).toEqual([]);
		expect(parseReasoningEffortOptions(42)).toEqual([]);
	});

	it('returns [] for whitespace and commas only', () => {
		expect(parseReasoningEffortOptions(' , ,, ')).toEqual([]);
	});
});
