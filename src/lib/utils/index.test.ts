import { titleGenerationTemplate } from '$lib/utils/index';
import { expect, test } from 'vitest';

test('titleGenerationTemplate correctly replaces {{prompt}} placeholder', () => {
	const template = 'Hello {{prompt}}!';
	const prompt = 'world';
	const expected = 'Hello world!';
	const actual = titleGenerationTemplate(template, prompt);
	expect(actual).toBe(expected);
});

test('titleGenerationTemplate correctly replaces {{prompt:start:<length>}} placeholder', () => {
	const template = 'Hello {{prompt:start:3}}!';
	const prompt = 'world';
	const expected = 'Hello wor!';
	const actual = titleGenerationTemplate(template, prompt);
	expect(actual).toBe(expected);
});

test('titleGenerationTemplate correctly replaces {{prompt:end:<length>}} placeholder', () => {
	const template = 'Hello {{prompt:end:3}}!';
	const prompt = 'world';
	const expected = 'Hello rld!';
	const actual = titleGenerationTemplate(template, prompt);
	expect(actual).toBe(expected);
});

test('titleGenerationTemplate correctly replaces {{prompt:middletruncate:<length>}} placeholder when prompt length is greater than length', () => {
	const template = 'Hello {{prompt:middletruncate:4}}!';
	const prompt = 'world';
	const expected = 'Hello wo...ld!';
	const actual = titleGenerationTemplate(template, prompt);
	expect(actual).toBe(expected);
});

test('titleGenerationTemplate correctly replaces {{prompt:middletruncate:<length>}} placeholder when prompt length is less than or equal to length', () => {
	const template = 'Hello {{prompt:middletruncate:5}}!';
	const prompt = 'world';
	const expected = 'Hello world!';
	const actual = titleGenerationTemplate(template, prompt);
	expect(actual).toBe(expected);
});

test('titleGenerationTemplate returns original template when no placeholders are present', () => {
	const template = 'Hello world!';
	const prompt = 'world';
	const expected = 'Hello world!';
	const actual = titleGenerationTemplate(template, prompt);
	expect(actual).toBe(expected);
});

test('titleGenerationTemplate does not replace placeholders inside of replaced placeholders', () => {
	const template = 'Hello {{prompt}}!';
	const prompt = 'World, {{prompt}} injection';
	const expected = 'Hello World, {{prompt}} injection!';
	const actual = titleGenerationTemplate(template, prompt);
	expect(actual).toBe(expected);
});

test('titleGenerationTemplate correctly replaces multiple placeholders', () => {
	const template = 'Hello {{prompt}}! This is {{prompt:start:3}}!';
	const prompt = 'world';
	const expected = 'Hello world! This is wor!';
	const actual = titleGenerationTemplate(template, prompt);
	expect(actual).toBe(expected);
});
