import { describe, expect, it } from 'vitest';
import {
	buildCitableCitationEntries,
	buildCitationEntries,
	buildTextFragmentUrl,
	findCitationEntryForLink,
	formatCitationDate,
	getCitationDisplayName,
	getCitationDocumentName,
	getCitationFaviconUrl,
	getCitationIconInfo,
	getCitationListLabel,
	getCitationThumbnailUrl,
	getCitationTitle,
	getSafeCitationUrl,
	isSafeCitationUrl
} from './citations';

describe('getCitationDocumentName', () => {
	it('prefers a document source name over a webpage URL', () => {
		expect(
			getCitationDocumentName(
				{ name: 'Report.pdf', url: 'https://example.com/reports/view?id=42' },
				{ name: 'Report.pdf', url: 'https://example.com/reports/view?id=42' }
			)
		).toBe('Report.pdf');
	});

	it('reads normalized filename and title metadata', () => {
		expect(getCitationDocumentName({}, { filename: 'forecast.xlsx' })).toBe('forecast.xlsx');
		expect(getCitationDocumentName({}, { file_name: 'minutes.doc' })).toBe('minutes.doc');
		expect(getCitationDocumentName({}, { title: 'slides.ppt' })).toBe('slides.ppt');
	});

	it('recognizes URL path extensions while ignoring query strings and fragments', () => {
		expect(
			getCitationDocumentName(
				{ url: 'https://example.com/files/data.csv?download=1#section' },
				undefined
			)
		).toBe('data.csv');
		expect(
			getCitationDocumentName({}, { url: 'https://example.com/archive.tar.gz?signature=abc' })
		).toBe('archive.tar.gz');
	});

	it('does not classify ordinary dotted prose as a document', () => {
		expect(
			getCitationDocumentName(
				{ name: 'Dr. Smith explains v2.0', url: 'https://example.com/articles/overview' },
				{ title: 'Quarterly results are up 3.2 percent' }
			)
		).toBeNull();
	});
});

describe('buildCitationEntries', () => {
	it('uses source identity rather than title for citation numbering', () => {
		const entries = buildCitationEntries([
			{
				source: { name: 'search' },
				document: ['First result', 'Second result'],
				metadata: [
					{ source: 'https://one.example', name: 'Same title', url: 'https://one.example' },
					{ source: 'https://two.example', name: 'Same title', url: 'https://two.example' }
				]
			}
		]);

		expect(entries).toHaveLength(2);
		expect(entries.map((entry) => entry.id)).toEqual([
			'https://one.example',
			'https://two.example'
		]);
	});

	it('merges chunks that share the same source identity', () => {
		const entries = buildCitationEntries([
			{
				source: { name: 'Report' },
				document: ['First chunk', 'Second chunk'],
				metadata: [
					{ source: 'report.pdf', name: 'Report' },
					{ source: 'report.pdf', name: 'Report' }
				]
			}
		]);

		expect(entries).toHaveLength(1);
		expect(entries[0].document).toEqual(['First chunk', 'Second chunk']);
	});

	it('keeps display-only search results out of numeric citation entries', () => {
		const sources = [
			{
				source: {
					id: 'https://search.example/result',
					name: 'Search result',
					url: 'https://search.example/result',
					citable: false
				},
				document: ['Unfetched search snippet'],
				metadata: [
					{
						source: 'https://search.example/result',
						url: 'https://search.example/result',
						citable: false,
						fetched: false
					}
				]
			},
			{
				source: { id: 'fetched', name: 'Fetched page', url: 'https://fetched.example/page' },
				document: ['Fetched page quote'],
				metadata: [{ source: 'fetched', url: 'https://fetched.example/page' }]
			}
		];

		expect(buildCitationEntries(sources)).toHaveLength(2);
		expect(buildCitableCitationEntries(sources).map((entry) => entry.id)).toEqual(['fetched']);
	});
});

describe('citation labels', () => {
	it('uses the normalized publisher label for chips while keeping the citation name as title', () => {
		const source = {
			name: 'Original article title',
			display_name: 'OpenAI',
			url: 'https://openai.com/article'
		};
		const metadata = {
			name: 'Original article title',
			display_name: 'OpenAI',
			publisher: ['OpenAI']
		};

		expect(getCitationDisplayName(source, metadata)).toBe('OpenAI');
		expect(getCitationTitle(source, metadata)).toBe('Original article title');
	});

	it('falls back to citation name for absent or empty normalized publisher labels', () => {
		expect(getCitationDisplayName({ name: 'Name only' }, { name: 'Name only' })).toBe('Name only');
		expect(
			getCitationDisplayName(
				{ name: 'Name only', display_name: '  ' },
				{ name: 'Name only', display_name: '' }
			)
		).toBe('Name only');
	});

	it('preserves display and title fields when building frontend entries', () => {
		const [entry] = buildCitationEntries([
			{
				source: { name: 'Original title', display_name: 'Publisher' },
				document: ['Quote'],
				metadata: [
					{
						source: 'mcp:call:c1',
						name: 'Original title',
						display_name: 'Publisher',
						publisher: ['Publisher']
					}
				]
			}
		]);

		expect(getCitationDisplayName(entry.source, entry.metadata[0])).toBe('Publisher');
		expect(getCitationTitle(entry.source, entry.metadata[0])).toBe('Original title');
	});

	it('composes publisher and page title without empty or duplicate separators', () => {
		expect(
			getCitationListLabel(
				{ name: 'Original article title', display_name: 'OpenAI' },
				{ name: 'Original article title', publisher: ['OpenAI'] }
			)
		).toBe('OpenAI | Original article title');
		expect(getCitationListLabel({ name: 'Title only' }, { name: 'Title only' })).toBe('Title only');
		expect(
			getCitationListLabel(
				{ name: 'Publisher', display_name: 'Publisher' },
				{ name: 'Publisher', publisher: ['Publisher'] }
			)
		).toBe('Publisher');
		expect(
			getCitationListLabel({ name: 'publisher', display_name: 'Publisher' }, { name: 'publisher' })
		).toBe('publisher');
	});
});

describe('formatCitationDate', () => {
	it('formats dates using the requested locale', () => {
		expect(formatCitationDate('2026-10-13', 'en-US')).toBe('Oct 13, 2026');
		expect(formatCitationDate('2026-10-13', 'de-DE')).toBe('13. Okt. 2026');
	});

	it('keeps date-only values stable across time zones', () => {
		const previousTimeZone = process.env.TZ;
		try {
			process.env.TZ = 'America/Los_Angeles';
			expect(formatCitationDate('2026-01-01', 'en-US')).toBe('Jan 1, 2026');
		} finally {
			if (previousTimeZone === undefined) delete process.env.TZ;
			else process.env.TZ = previousTimeZone;
		}
	});

	it('handles partial and invalid dates without throwing', () => {
		expect(formatCitationDate('2026-10', 'en-US')).toBe('October 2026');
		expect(formatCitationDate('2026', 'en-US')).toBe('2026');
		expect(formatCitationDate('not-a-date', 'en-US')).toBe('not-a-date');
		expect(formatCitationDate('')).toBeNull();
	});
});

describe('citation URLs', () => {
	it('rejects unsafe automatic preview targets', () => {
		expect(isSafeCitationUrl('file:///etc/passwd')).toBe(false);
		expect(isSafeCitationUrl('http://169.254.169.254/latest/meta-data')).toBe(false);
		expect(isSafeCitationUrl('https://127.0.0.1/private')).toBe(false);
		expect(isSafeCitationUrl('https://user:password@example.com/private')).toBe(false);
		expect(isSafeCitationUrl('javascript:alert(1)')).toBe(false);
		expect(isSafeCitationUrl('http://example.com/article')).toBe(true);
		expect(isSafeCitationUrl('https://example.com/article')).toBe(true);
	});

	it('normalizes safe external targets', () => {
		expect(getSafeCitationUrl(' https://example.com/article ')).toBe('https://example.com/article');
		expect(getSafeCitationUrl('//example.com/article')).toBeNull();
	});

	it('keeps preview images ahead of the separate favicon fallback', () => {
		expect(getCitationFaviconUrl('https://example.com/news/story')).toBe(
			'https://www.google.com/s2/favicons?domain_url=https%3A%2F%2Fexample.com&sz=32'
		);
		expect(
			getCitationThumbnailUrl({
				thumbnail_url: 'https://images.example/structured.png',
				image_url: 'https://images.example/image.png',
				og_image_url: 'https://images.example/og.png'
			})
		).toBe('https://images.example/structured.png');
		expect(
			getCitationThumbnailUrl({
				thumbnail_url: 'http://localhost/private.png',
				og_image_url: 'https://images.example/og.png'
			})
		).toBe('https://images.example/og.png');
		expect(getCitationThumbnailUrl({})).toBeNull();
		expect(getCitationFaviconUrl('http://127.0.0.1/private')).toBeNull();
	});

	it('builds only an encoded Google favicon URL', () => {
		expect(getCitationFaviconUrl('https://docs.example:8443/guide?q=private', null, 16)).toBe(
			'https://www.google.com/s2/favicons?domain_url=https%3A%2F%2Fdocs.example%3A8443&sz=16'
		);
	});

	it('never sends same-origin, private, localhost, file, or proxy URLs to Google', () => {
		expect(
			getCitationFaviconUrl(
				'https://webui.example/api/v1/files/file-1/content',
				'https://webui.example'
			)
		).toBeNull();
		expect(getCitationFaviconUrl('https://proxy.example/api/v1/files/file-1/content')).toBeNull();
		expect(getCitationFaviconUrl('http://localhost:8080/private')).toBeNull();
		expect(getCitationFaviconUrl('http://10.0.0.4/private')).toBeNull();
		expect(getCitationFaviconUrl('file:///etc/passwd')).toBeNull();
		expect(
			getCitationIconInfo(
				{ url: 'https://webui.example/api/v1/files/file-1/content' },
				{},
				'https://webui.example'
			)
		).toEqual({ documentName: null, faviconUrl: null });
	});

	it('never derives a favicon from the app origin or an internal file proxy', () => {
		expect(
			getCitationFaviconUrl(
				'https://webui.example/api/v1/files/file-1/content',
				'https://webui.example'
			)
		).toBeNull();
		expect(
			getCitationFaviconUrl('https://webui.example/citation-proxy', 'https://webui.example')
		).toBeNull();
		expect(getCitationFaviconUrl('https://other.example/api/v1/files/file-1/content')).toBeNull();
	});

	it('resolves document, Google favicon, then generic icon inputs without direct origin requests', () => {
		expect(
			getCitationIconInfo(
				{ name: 'Report.pdf', url: 'https://webui.example/api/v1/files/1/content' },
				undefined,
				'https://webui.example'
			)
		).toEqual({ documentName: 'Report.pdf', faviconUrl: null });
		expect(
			getCitationIconInfo(
				{ url: 'https://webui.example/api/v1/files/1/content' },
				undefined,
				'https://webui.example'
			)
		).toEqual({ documentName: null, faviconUrl: null });
		expect(getCitationIconInfo({ url: 'https://docs.example/article' })).toEqual({
			documentName: null,
			faviconUrl: 'https://www.google.com/s2/favicons?domain_url=https%3A%2F%2Fdocs.example&sz=32'
		});
		expect(
			JSON.stringify(getCitationIconInfo({ url: 'https://docs.example/article' }))
		).not.toContain('https://docs.example/favicon.ico');
	});

	it('uses the actual external source origin when metadata points at an internal proxy', () => {
		const [entry] = buildCitationEntries([
			{
				source: { url: 'https://publisher.example/report' },
				document: ['Quote'],
				metadata: [
					{
						source: 'report',
						url: 'https://webui.example/api/v1/files/file-1/content'
					}
				]
			}
		]);

		expect(getCitationIconInfo(entry.source, entry.metadata[0], 'https://webui.example')).toEqual({
			documentName: null,
			faviconUrl:
				'https://www.google.com/s2/favicons?domain_url=https%3A%2F%2Fpublisher.example&sz=32'
		});
	});

	it('preserves server-provided granular fragments', () => {
		expect(
			buildTextFragmentUrl({
				source: { url: 'https://example.com/report.pdf#page=12' },
				document: 'A quote from the report'
			})
		).toBe('https://example.com/report.pdf#page=12');
	});

	it('does not create text fragments for unfetched display-only search snippets', () => {
		expect(
			buildTextFragmentUrl({
				source: {
					url: 'https://example.com/search-result',
					citable: false,
					fetched: false
				},
				metadata: { citable: false, fetched: false },
				document: 'Search-engine snippet only'
			})
		).toBe('https://example.com/search-result');
	});
});

describe('findCitationEntryForLink', () => {
	it('matches synthesized markdown links to the shared citation entry', () => {
		const entries = buildCitationEntries([
			{
				source: { name: 'Marbury', url: 'https://example.com/marbury' },
				document: ['Quote'],
				metadata: [
					{
						source: 'mcp:call_1:c1',
						citation_id: 'c1',
						name: 'Marbury v. Madison',
						url: 'https://example.com/marbury'
					}
				]
			}
		]);

		expect(
			findCitationEntryForLink(entries, 'https://example.com/marbury', 'Marbury v. Madison')
		).toEqual({ entry: entries[0], identifier: 1 });
	});

	it('matches a raw URL markdown link so it can render as a citation chip', () => {
		const entries = buildCitationEntries([
			{
				source: { name: 'External reference', url: 'https://example.com/reference' },
				document: ['Quote'],
				metadata: [
					{
						source: 'mcp:call_2:c1',
						name: 'External reference',
						url: 'https://example.com/reference'
					}
				]
			}
		]);

		expect(
			findCitationEntryForLink(
				entries,
				'https://example.com/reference',
				'https://example.com/reference'
			)
		).toEqual({ entry: entries[0], identifier: 1 });
	});

	it('matches a citation whose markdown label is the raw source URL', () => {
		const entries = buildCitationEntries([
			{
				source: { name: 'External source', url: 'https://example.com/report' },
				document: ['Quote'],
				metadata: [{ source: 'citation-1', url: 'https://example.com/report' }]
			}
		]);

		expect(
			findCitationEntryForLink(entries, 'https://example.com/report', 'https://example.com/report')
		).toEqual({ entry: entries[0], identifier: 1 });
	});

	it('matches markdown links to display-only search sources by URL', () => {
		const entries = buildCitationEntries([
			{
				source: {
					name: 'Search result',
					url: 'https://example.com/search-result',
					citable: false
				},
				document: ['Search snippet'],
				metadata: [
					{
						source: 'https://example.com/search-result',
						name: 'Search result',
						url: 'https://example.com/search-result',
						citable: false
					}
				]
			}
		]);

		expect(
			findCitationEntryForLink(entries, 'https://example.com/search-result', 'Search result')
		).toEqual({ entry: entries[0], identifier: 1 });
	});
});
