import { describe, expect, it } from 'vitest';

import { applyArtifactContentSecurityPolicy } from './artifacts';

describe('applyArtifactContentSecurityPolicy', () => {
	it('returns the original html when no policy is configured', () => {
		const html = '<html><head></head><body><h1>Hello</h1></body></html>';

		expect(applyArtifactContentSecurityPolicy(html, '')).toBe(html);
		expect(applyArtifactContentSecurityPolicy(html, '   ')).toBe(html);
	});

	it('injects the configured policy into the document head', () => {
		const html = '<!DOCTYPE html><html><head><title>Artifact</title></head><body>Body</body></html>';

		expect(applyArtifactContentSecurityPolicy(html, "default-src 'none'; img-src data:")).toBe(
			'<!DOCTYPE html><html><head><meta http-equiv="Content-Security-Policy" content="default-src \'none\'; img-src data:"><title>Artifact</title></head><body>Body</body></html>'
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
			'<html><head><meta http-equiv="Content-Security-Policy" content="default-src \'self\'; report-to &quot;artifact-endpoint&quot;"><meta charset="utf-8"></head><body>Body</body></html>'
		);
	});
});
