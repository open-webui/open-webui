import { render } from 'svelte/server';
import { readable, writable } from 'svelte/store';
import { describe, expect, it } from 'vitest';
import type { CitationEntry } from '$lib/utils/citations';
import SourceToken from './SourceToken.svelte';

const entries: CitationEntry[] = [
	{
		id: 'mcp:call:c1',
		source: {
			name: 'Original article title',
			display_name: 'Publisher',
			url: 'https://publisher.example/article'
		},
		document: ['Quote'],
		metadata: [
			{
				source: 'mcp:call:c1',
				name: 'Original article title',
				display_name: 'Publisher',
				publisher: ['Publisher'],
				url: 'https://publisher.example/article'
			}
		],
		distances: [undefined]
	},
	{
		id: 'second',
		source: { name: 'Second source', url: 'https://second.example/article' },
		document: ['Second quote'],
		metadata: [{ source: 'second', name: 'Second source' }],
		distances: [undefined]
	}
];

const context = new Map([
	['citationEntries', readable(entries)],
	['i18n', writable({ t: (key: string) => key })]
]);

describe('SourceToken', () => {
	it('passes the first normalized citation to the multi-source chip icon resolver', () => {
		const { body } = render(SourceToken, {
			context,
			props: {
				token: { ids: [1, 2], citationIdentifiers: ['1', '2'] },
				sourceIds: ['Publisher', 'Second source']
			}
		});

		expect(body).toContain(
			'https://www.google.com/s2/favicons?domain_url=https%3A%2F%2Fpublisher.example&amp;sz=16'
		);
		expect(body).toContain('Publisher');
	});
});
