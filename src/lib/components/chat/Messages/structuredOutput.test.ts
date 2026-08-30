import { describe, expect, it } from 'vitest';
import {
	buildOutputDisplayItems,
	getGeneratedText,
	getOutputText,
	type OutputItem
} from './structuredOutput';

const reasoning = (text: string): OutputItem => ({
	type: 'reasoning',
	content: [{ type: 'reasoning_text', text }]
});

const message = (text: string): OutputItem => ({
	type: 'message',
	content: [{ type: 'output_text', text }]
});

describe('getGeneratedText', () => {
	it('includes reasoning text that getOutputText leaves out', () => {
		const output = [reasoning('thinking hard'), message('Hello!')];

		// The visible answer only
		// what belongs in message.content
		expect(getOutputText(output)).toBe('Hello!');
		// Everything the model produced
		// what generation stats must measure
		expect(getGeneratedText(output)).toBe('thinking hard\nHello!');
	});

	it('measures a response that is still mid-reasoning', () => {
		// The case that reported 0 tokens:
		// reasoning has started, no answer yet
		const output = [reasoning('still working on it')];

		expect(getOutputText(output)).toBe('');
		expect(getGeneratedText(output)).toBe('still working on it');
	});

	it('prefers a reasoning summary when the provider sends one', () => {
		const output: OutputItem[] = [
			{
				type: 'reasoning',
				summary: [{ type: 'summary_text', text: 'summarised' }],
				content: [{ type: 'reasoning_text', text: 'raw' }]
			}
		];
		expect(getGeneratedText(output)).toBe('summarised');
	});

	it('ignores non-generated items such as tool calls', () => {
		const output: OutputItem[] = [
			{ type: 'function_call', name: 'search', arguments: '{"q":"x"}' },
			message('done')
		];
		expect(getGeneratedText(output)).toBe('done');
	});

	it('handles empty and missing output', () => {
		expect(getGeneratedText([])).toBe('');
		expect(getGeneratedText(null)).toBe('');
		expect(getGeneratedText(undefined)).toBe('');
	});
});

describe('buildOutputDisplayItems', () => {
	// A reasoning item with no status and no duration
	// sitting last in the array
	const inProgressReasoning: OutputItem[] = [
		{ type: 'reasoning', content: [{ type: 'reasoning_text', text: 'hmm' }] }
	];

	const summaryOf = (items: OutputItem[], done: boolean) => {
		const built = buildOutputDisplayItems(items, done);
		const first = built[0] as { token?: { summary?: string } };
		return first?.token?.summary;
	};

	it('shows the in-progress label while the message is still streaming', () => {
		expect(summaryOf(inProgressReasoning, false)).toBe('Thinking...');
	});

	it('never shows the in-progress label once the message is done', () => {
		expect(summaryOf(inProgressReasoning, true)).not.toBe('Thinking...');
	});

	it('defaults to streaming behaviour when no done flag is passed', () => {
		expect(summaryOf(inProgressReasoning, undefined as unknown as boolean)).toBe('Thinking...');
	});

	it('keeps reasoning ahead of the answer it preceded', () => {
		const items: OutputItem[] = [
			{ type: 'reasoning', status: 'completed', content: [{ type: 'reasoning_text', text: 'r' }] },
			{ type: 'message', status: 'completed', content: [{ type: 'output_text', text: 'answer' }] }
		];
		expect(buildOutputDisplayItems(items, true).map((i) => i.type)).toEqual([
			'detail_single',
			'message'
		]);
	});
});
