import { describe, expect, it } from 'vitest';

import { getAvailableFeatureToggleState } from './features';

describe('getAvailableFeatureToggleState', () => {
	it('turns off enabled feature state when the feature control is unavailable', () => {
		expect(getAvailableFeatureToggleState(true, false)).toBe(false);
	});

	it('preserves feature state when the feature control is available', () => {
		expect(getAvailableFeatureToggleState(true, true)).toBe(true);
		expect(getAvailableFeatureToggleState(false, true)).toBe(false);
	});
});
