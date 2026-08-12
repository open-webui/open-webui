import { describe, expect, it } from 'vitest';

import { resolveImageUrl } from './imageUrl';

describe('resolveImageUrl', () => {
	it('prefixes root-relative paths with the backend base URL', () => {
		expect(resolveImageUrl('/api/v1/files/image/content', 'http://localhost:8080')).toBe(
			'http://localhost:8080/api/v1/files/image/content'
		);
	});

	it('keeps root-relative paths unchanged for same-origin production builds', () => {
		expect(resolveImageUrl('/api/v1/files/image/content', '')).toBe('/api/v1/files/image/content');
	});

	it('does not rewrite absolute URLs', () => {
		expect(resolveImageUrl('https://cdn.example.com/image.png', 'http://localhost:8080')).toBe(
			'https://cdn.example.com/image.png'
		);
	});

	it('does not rewrite data URLs', () => {
		const dataUrl = 'data:image/png;base64,AAAA';

		expect(resolveImageUrl(dataUrl, 'http://localhost:8080')).toBe(dataUrl);
	});
});
