import { describe, it, expect } from 'vitest';
import {
	getWebSearchReadiness,
	parseModelParameterSize,
	parseParameterSizeString
} from '$lib/utils/models';

describe('parseParameterSizeString', () => {
	it('parses plain billion sizes', () => {
		expect(parseParameterSizeString('7B')).toBe(7);
		expect(parseParameterSizeString('70b')).toBe(70);
		expect(parseParameterSizeString('7.6B')).toBe(7.6);
	});

	it('parses million sizes into billions', () => {
		expect(parseParameterSizeString('350M')).toBe(0.35);
	});

	it('parses mixture-of-experts notation as total parameters', () => {
		expect(parseParameterSizeString('8x7B')).toBe(56);
	});

	it('tolerates surrounding whitespace', () => {
		expect(parseParameterSizeString(' 13 B ')).toBe(13);
	});

	it('returns null for missing or unparseable values', () => {
		expect(parseParameterSizeString('')).toBeNull();
		expect(parseParameterSizeString(undefined)).toBeNull();
		expect(parseParameterSizeString(null)).toBeNull();
		expect(parseParameterSizeString('abc')).toBeNull();
		expect(parseParameterSizeString('7')).toBeNull(); // no unit -> ambiguous
	});
});

describe('parseModelParameterSize', () => {
	it('prefers nested ollama metadata', () => {
		expect(parseModelParameterSize({ ollama: { details: { parameter_size: '32B' } } })).toBe(32);
	});

	it('falls back to top-level details metadata', () => {
		expect(parseModelParameterSize({ details: { parameter_size: '13B' } })).toBe(13);
	});

	it('falls back to a size token in the model id', () => {
		expect(parseModelParameterSize({ id: 'llama3.1:8b' })).toBe(8);
		expect(parseModelParameterSize({ id: 'mixtral:8x7b' })).toBe(56);
	});

	it('does not mistake a version number for a size', () => {
		expect(parseModelParameterSize({ id: 'llama3.2' })).toBeNull();
	});

	it('returns null when nothing is available', () => {
		expect(parseModelParameterSize(null)).toBeNull();
		expect(parseModelParameterSize({ id: 'gpt-4o' })).toBeNull();
	});
});

describe('getWebSearchReadiness', () => {
	const local = (parameterSizeB: number | null, contextLength: number | null = null) =>
		getWebSearchReadiness({
			isLocal: true,
			parameterSizeB,
			contextLength,
			capabilityEnabled: true
		});

	it('reports disabled when the capability is off', () => {
		const result = getWebSearchReadiness({
			isLocal: true,
			parameterSizeB: 70,
			contextLength: 16384,
			capabilityEnabled: false
		});
		expect(result.state).toBe('disabled');
		expect(result.reasons).toContain('capability_disabled');
	});

	it('treats non-local (API) models as ready without warnings', () => {
		const result = getWebSearchReadiness({
			isLocal: false,
			parameterSizeB: null,
			contextLength: null,
			capabilityEnabled: true
		});
		expect(result.state).toBe('ready');
		expect(result.reasons).toEqual([]);
	});

	it('flags small local models as limited', () => {
		expect(local(3).state).toBe('limited');
		expect(local(3).reasons).toContain('size_low');
		expect(local(8).state).toBe('limited');
		expect(local(8).reasons).toContain('size_experimental');
	});

	it('treats mid/large local models as ready', () => {
		expect(local(24).state).toBe('ready');
		expect(local(24).reasons).toContain('size_usable');
		expect(local(70).state).toBe('ready');
		expect(local(70).reasons).toContain('size_recommended');
	});

	it('returns unknown when neither size nor context is known', () => {
		expect(local(null, null).state).toBe('unknown');
		expect(local(null, null).reasons).toEqual(['size_unknown', 'context_unknown']);
	});

	it('warns on low context even for a large model', () => {
		expect(local(32, 2048).state).toBe('limited');
		expect(local(32, 2048).reasons).toContain('context_low');
		expect(local(32, 4096).state).toBe('limited');
		expect(local(32, 4096).reasons).toContain('context_limited');
		expect(local(32, 16384).state).toBe('ready');
	});

	it('keeps a small model limited regardless of generous context', () => {
		expect(local(8, 16384).state).toBe('limited');
	});

	it('does not warn on unknown size when context is generous', () => {
		expect(local(null, 16384).state).toBe('ready');
	});
});
