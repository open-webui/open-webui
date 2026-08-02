import { describe, it, expect } from 'vitest';
import { isToolResultError, parseToolResult } from './toolCallUtils';

describe('parseToolResult', () => {
	it('unwraps nested JSON-encoded strings', () => {
		expect(parseToolResult('{"error":"x"}')).toEqual({ error: 'x' });
		// Double-encoded payload: a JSON string containing a JSON string.
		expect(parseToolResult('"{\\"error\\":\\"x\\"}"')).toEqual({ error: 'x' });
	});

	it('returns scalars without looping forever', () => {
		expect(parseToolResult('5')).toBe(5);
		expect(parseToolResult('null')).toBe(null);
		expect(parseToolResult('true')).toBe(true);
		expect(parseToolResult(5)).toBe(5);
	});

	it('returns non-JSON strings as-is', () => {
		expect(parseToolResult('not json')).toBe('not json');
		expect(parseToolResult('')).toBe('');
	});
});

describe('isToolResultError', () => {
	it('detects a JSON-encoded object with a non-empty error string', () => {
		expect(isToolResultError('{"error":"403 Client Error: Forbidden for url: ..."}')).toBe(true);
		expect(isToolResultError({ error: 'boom' })).toBe(true);
	});

	it('ignores empty / null / non-string error fields', () => {
		expect(isToolResultError('{"error":""}')).toBe(false);
		expect(isToolResultError('{"error":null}')).toBe(false);
		expect(isToolResultError('{"error":0}')).toBe(false);
		expect(isToolResultError('{"error":false}')).toBe(false);
		expect(isToolResultError({ error: null })).toBe(false);
	});

	it('ignores non-error payloads', () => {
		expect(isToolResultError('{"results":[1,2,3]}')).toBe(false);
		expect(isToolResultError('{"query":"cats"}')).toBe(false);
		expect(isToolResultError('just text')).toBe(false);
		expect(isToolResultError('')).toBe(false);
		expect(isToolResultError(null)).toBe(false);
		expect(isToolResultError(undefined)).toBe(false);
		expect(isToolResultError([])).toBe(false);
	});
});
