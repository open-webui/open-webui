import { describe, expect, it } from 'vitest';

import { applyArtifactContentSecurityPolicy } from './artifacts';

describe('applyArtifactContentSecurityPolicy', () => {
	it('returns the original html when no policy is configured', () => {
		const html = '<html><head></head><body><h1>Hello</h1></body></html>';

		expect(applyArtifactContentSecurityPolicy(html, '')).toBe(html);
		expect(applyArtifactContentSecurityPolicy(html, '   ')).toBe(html);
		expect(applyArtifactContentSecurityPolicy(html, null)).toBe(html);
		expect(applyArtifactContentSecurityPolicy(html, undefined)).toBe(html);
	});

	it('injects the configured policy into the document head', () => {
		const html = '<!DOCTYPE html><html><head><title>Artifact</title></head><body>Body</body></html>';

		expect(applyArtifactContentSecurityPolicy(html, "default-src 'none'; img-src data:")).toBe(
			'<!DOCTYPE html><html><head><meta http-equiv="Content-Security-Policy" content="default-src &#39;none&#39;; img-src data:"><title>Artifact</title></head><body>Body</body></html>'
		);
	});

	it('replaces any existing content security policy meta tag before injecting the configured policy', () => {
		const html =
			'<html><head><meta http-equiv="Content-Security-Policy" content="default-src *"><meta charset="utf-8"></head><body>Body</body></html>';

		expect(
			applyArtifactContentSecurityPolicy(
				html,
				`default-src 'self'; report-to "artifact-endpoint"`
			)
		).toBe(
			'<html><head><meta http-equiv="Content-Security-Policy" content="default-src &#39;self&#39;; report-to &quot;artifact-endpoint&quot;"><meta charset="utf-8"></head><body>Body</body></html>'
		);
	});

	it('creates a head tag when the document has an html tag but no head tag', () => {
		expect(
			applyArtifactContentSecurityPolicy(
				'<html><body>Body</body></html>',
				"default-src 'none'"
			)
		).toBe(
			'<html><head><meta http-equiv="Content-Security-Policy" content="default-src &#39;none&#39;"></head><body>Body</body></html>'
		);
	});

	it('prepends the meta tag when there is no html wrapper and escapes special characters', () => {
		expect(
			applyArtifactContentSecurityPolicy(
				'<div>Body</div>',
				`default-src 'self' https://example.com?a=1&b=<2>`
			)
		).toBe(
			'<meta http-equiv="Content-Security-Policy" content="default-src &#39;self&#39; https://example.com?a=1&amp;b=&lt;2&gt;"><div>Body</div>'
		);
	});
});
