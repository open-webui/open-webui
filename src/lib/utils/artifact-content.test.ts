import { describe, expect, it } from 'vitest';

import { getCodeBlockContents, hasRenderableArtifactContent } from './index';

describe('artifact content detection', () => {
	it('detects html artifacts from fenced code blocks', () => {
		expect(hasRenderableArtifactContent('```html\n<div>Hello</div>\n```')).toBe(true);
	});

	it('detects svg artifacts from xml code blocks', () => {
		expect(hasRenderableArtifactContent('```xml\n<svg></svg>\n```')).toBe(true);
	});

	it('ignores non-artifact code blocks', () => {
		expect(hasRenderableArtifactContent('```markdown\n# title\n```')).toBe(false);
	});

	it('builds grouped html artifacts from outlet-transformed content', () => {
		const result = getCodeBlockContents('```html\n<div>Hello</div>\n```') as {
			htmlGroups: Array<{ html: string; css: string; js: string }>;
		};

		expect(result.htmlGroups).toHaveLength(1);
		expect(result.htmlGroups[0]).toMatchObject({ html: '<div>Hello</div>', css: '', js: '' });
	});
});
