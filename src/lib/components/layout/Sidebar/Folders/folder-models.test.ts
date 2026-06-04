import { describe, expect, it } from 'vitest';

import { normalizeFolderModelIds } from './folder-models';

describe('normalizeFolderModelIds', () => {
	it('returns undefined when no concrete model is selected', () => {
		expect(normalizeFolderModelIds([''])).toBeUndefined();
		expect(normalizeFolderModelIds([])).toBeUndefined();
	});

	it('preserves selected model ids and strips empty placeholders', () => {
		expect(normalizeFolderModelIds(['model-a'])).toEqual(['model-a']);
		expect(normalizeFolderModelIds(['model-a', '', 'model-b'])).toEqual(['model-a', 'model-b']);
	});
});
