import { describe, expect, it } from 'vitest';

import {
	BASE_MODEL_PICKER_LAYER_B_DECISION,
	buildBaseModelPickerItems,
	fromBaseModelSelectorValue,
	isEligibleBaseModel,
	normalizeSavedBaseModelId,
	toBaseModelSelectorValue
} from './baseModelPicker';

const baseModel = (overrides: Record<string, unknown> = {}) =>
	({
		id: 'gpt-4o',
		name: 'GPT-4o',
		owned_by: 'openai',
		...overrides
	}) as Parameters<typeof isEligibleBaseModel>[0];

describe('baseModelPicker eligibility', () => {
	it('includes a standard external model', () => {
		expect(isEligibleBaseModel(baseModel())).toBe(true);
	});

	it('excludes the workspace model currently being edited', () => {
		expect(
			isEligibleBaseModel(baseModel({ id: 'my-preset' }), { editingModelId: 'my-preset' })
		).toBe(false);
	});

	it('excludes preset, arena, and direct models', () => {
		expect(isEligibleBaseModel(baseModel({ preset: true }))).toBe(false);
		expect(isEligibleBaseModel(baseModel({ arena: true }))).toBe(false);
		expect(isEligibleBaseModel(baseModel({ owned_by: 'arena' }))).toBe(false);
		expect(isEligibleBaseModel(baseModel({ direct: true }))).toBe(false);
	});
});

describe('baseModelPicker value bridge', () => {
	it('maps nullish ids to an empty selector value', () => {
		expect(toBaseModelSelectorValue(null)).toBe('');
		expect(toBaseModelSelectorValue(undefined)).toBe('');
		expect(toBaseModelSelectorValue('openrouter/owl-alpha')).toBe('openrouter/owl-alpha');
	});

	it('maps empty selector values back to null', () => {
		expect(fromBaseModelSelectorValue('')).toBe(null);
		expect(fromBaseModelSelectorValue('openrouter/owl-alpha')).toBe('openrouter/owl-alpha');
	});
});

describe('baseModelPicker normalization', () => {
	const catalog = [
		baseModel({ id: 'llama3', name: 'Llama 3' }),
		baseModel({ id: 'llama3:latest', name: 'Llama 3 Latest' }),
		baseModel({ id: 'my-preset', name: 'My Preset', preset: true })
	];

	it('resolves :latest aliases against eligible models', () => {
		expect(normalizeSavedBaseModelId('llama3', catalog)).toBe('llama3');
		expect(normalizeSavedBaseModelId('llama3:latest', catalog)).toBe('llama3:latest');
	});

	it('clears saved ids that are no longer eligible', () => {
		expect(normalizeSavedBaseModelId('my-preset', catalog)).toBe(null);
		expect(normalizeSavedBaseModelId('missing-model', catalog)).toBe(null);
	});
});

describe('baseModelPicker items', () => {
	it('builds selector items from eligible models only', () => {
		const items = buildBaseModelPickerItems(
			[
				baseModel({ id: 'a', name: 'Alpha' }),
				baseModel({ id: 'b', name: 'Beta', direct: true }),
				baseModel({ id: 'c', name: 'Current' })
			],
			{ editingModelId: 'c' }
		);

		expect(items).toEqual([
			{
				value: 'a',
				label: 'Alpha',
				model: expect.objectContaining({ id: 'a' })
			}
		]);
	});
});

describe('baseModelPicker layer B gate', () => {
	it('records a no-go decision until connection identity exists in model payloads', () => {
		expect(BASE_MODEL_PICKER_LAYER_B_DECISION).toBe('no-go');
	});
});
