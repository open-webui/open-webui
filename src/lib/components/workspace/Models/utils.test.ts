import { describe, expect, it } from 'vitest';

import { normalizeModelKnowledge } from './utils';

describe('normalizeModelKnowledge', () => {
	it('marks singular collection_name entries as legacy', () => {
		expect(
			normalizeModelKnowledge([
				{
					collection_name: 'legacy-collection-id',
					name: 'Legacy knowledge'
				}
			])
		).toEqual([
			{
				id: 'legacy-collection-id',
				name: 'Legacy knowledge',
				legacy: true
			}
		]);
	});

	it('does not mark collection_names entries as legacy', () => {
		expect(
			normalizeModelKnowledge([
				{
					collection_names: ['collection-id'],
					name: 'Current knowledge'
				}
			])
		).toEqual([
			{
				name: 'Current knowledge',
				type: 'collection',
				collection_names: ['collection-id'],
				legacy: false
			}
		]);
	});

	it('leaves file knowledge entries unchanged', () => {
		const fileItem = {
			collection_name: 'file-id',
			name: 'Uploaded file',
			type: 'file'
		};

		expect(normalizeModelKnowledge([fileItem])).toEqual([fileItem]);
	});
});
