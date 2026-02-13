import { describe, expect, it } from 'vitest';

import { buildOpenRouterMetadata } from './openrouter';

describe('buildOpenRouterMetadata', () => {
	it('A) changes preset metadata from UI', () => {
		const metadata = buildOpenRouterMetadata({ preset: 'smart' });
		expect(metadata?.openrouter?.preset).toBe('smart');
	});

	it('B) supports streaming toggle + non-stream fallback', () => {
		const metadata = buildOpenRouterMetadata({
			streaming: false,
			non_stream_fallback: true
		});

		expect(metadata?.openrouter?.non_stream).toBe(true);
		expect(metadata?.openrouter?.non_stream_fallback).toBe(true);
	});

	it('C) enables structured output schema metadata', () => {
		const metadata = buildOpenRouterMetadata({
			json_output: true,
			json_schema: '{"type":"object","properties":{"answer":{"type":"string"}},"required":["answer"]}'
		});

		expect(metadata?.openrouter?.json_output).toBe(true);
		expect(metadata?.openrouter?.json_schema).toBeDefined();
	});

	it('D) enables response healing when JSON mode is on', () => {
		const metadata = buildOpenRouterMetadata({
			json_output: true,
			response_healing: true
		});

		expect(metadata?.openrouter?.enable_response_healing).toBe(true);
	});

	it('E) sets sensitive flag for ZDR path', () => {
		const metadata = buildOpenRouterMetadata({
			zdr_sensitive: true
		});

		expect(metadata?.openrouter?.sensitive).toBe(true);
	});

	it('F) maps guardrails fields from UI', () => {
		const metadata = buildOpenRouterMetadata({
			guardrail_allowed_models: 'google/gemini-3-flash-preview, anthropic/claude-sonnet-4.5',
			guardrail_allowed_providers: 'google, openai',
			guardrail_max_tokens: '256',
			guardrail_hard_fail: true
		});

		expect(metadata?.openrouter?.guardrail_allowed_models).toEqual([
			'google/gemini-3-flash-preview',
			'anthropic/claude-sonnet-4.5'
		]);
		expect(metadata?.openrouter?.guardrail_allowed_providers).toEqual(['google', 'openai']);
		expect(metadata?.openrouter?.guardrail_max_tokens).toBe(256);
		expect(metadata?.openrouter?.guardrail_hard_fail).toBe(true);
	});
});
