import { render } from 'svelte/server';
import { writable } from 'svelte/store';
import { describe, expect, it } from 'vitest';
import CitationPreview from './CitationPreview.svelte';

const context = new Map([
	[
		'i18n',
		writable({
			t: (key: string) => key,
			resolvedLanguage: 'en-US',
			language: 'en-US'
		})
	]
]);

describe('CitationPreview', () => {
	it('renders the citation name as its title, not the publisher chip label', () => {
		const { body } = render(CitationPreview, {
			context,
			props: {
				identifier: 1,
				entry: {
					id: 'mcp:call:c1',
					source: {
						name: 'Original article title',
						display_name: 'OpenAI',
						url: 'https://openai.com/article'
					},
					document: ['Supporting quote'],
					metadata: [
						{
							source: 'mcp:call:c1',
							name: 'Original article title',
							display_name: 'OpenAI',
							publisher: ['OpenAI'],
							url: 'https://openai.com/article'
						}
					],
					distances: [undefined]
				}
			}
		});

		expect(body).toContain('Original article title');
		expect(body).toContain('OpenAI');
		expect(body.indexOf('Original article title')).toBeLessThan(body.indexOf('OpenAI'));
		expect(body).toContain('href="https://openai.com/article#:~:text=Supporting%2Cquote"');
		expect(body).toContain('target="_blank"');
		expect(body).toContain('noopener noreferrer');
		expect(body).not.toContain('View source');
		expect(body).not.toContain('Previous citation');
		expect(body).not.toContain('Next citation');
	});

	it('renders bounded navigation only for grouped citations', () => {
		const { body } = render(CitationPreview, {
			context,
			props: {
				identifier: 1,
				position: 0,
				count: 3,
				entry: {
					id: 'grouped',
					source: { name: 'Grouped source', url: 'https://example.com/grouped' },
					document: ['Quote'],
					metadata: [{ name: 'Grouped source', url: 'https://example.com/grouped' }],
					distances: [undefined]
				}
			}
		});

		expect(body).toContain('Previous citation');
		expect(body).toContain('Next citation');
		expect(body).toContain('1 / 3');
		expect(body).toMatch(/aria-label="Previous citation"[^>]*disabled/);
	});

	it('renders the title as text when the citation URL is unsafe', () => {
		const { body } = render(CitationPreview, {
			context,
			props: {
				identifier: 1,
				entry: {
					id: 'unsafe',
					source: { name: 'Unsafe source', url: 'javascript:alert(1)' },
					document: ['Quote'],
					metadata: [{ name: 'Unsafe source', url: 'javascript:alert(1)' }],
					distances: [undefined]
				}
			}
		});

		expect(body).toContain('Unsafe source');
		expect(body).not.toContain('<a ');
		expect(body).not.toContain('javascript:');
	});
});
