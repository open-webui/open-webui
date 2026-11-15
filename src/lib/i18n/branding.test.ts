import { describe, expect, it } from 'vitest';
import { brandTranslation } from './branding';

describe('GCAT translation branding', () => {
	it('normalizes upstream display names in translations and fallback keys', () => {
		expect(brandTranslation('Open WebUI / Open Web UI / OpenWebUI')).toBe('GCAT / GCAT / GCAT');
	});

	it('brands Persian translations without changing surrounding text', () => {
		expect(brandTranslation('به Open WebUI خوش آمدید')).toBe('به GCAT خوش آمدید');
	});

	it('preserves existing GCAT text and technical identifiers', () => {
		expect(brandTranslation('GCAT {{OPEN_WEBUI_VERSION}} open_webui')).toBe(
			'GCAT {{OPEN_WEBUI_VERSION}} open_webui'
		);
	});
});
