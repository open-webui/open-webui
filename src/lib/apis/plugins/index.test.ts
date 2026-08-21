import { describe, expect, it } from 'vitest';
import { pluginAssetUrl, type PluginApp } from './index';

const app: PluginApp = {
	id: 'example_plugin',
	title: 'Example Plugin',
	version: '1.0.0',
	default_page: 'home',
	pages: [],
	revision: '42'
};

describe('pluginAssetUrl', () => {
	it('keeps assets under the Open WebUI-owned, versioned namespace', () => {
		expect(pluginAssetUrl(app, 'chunks/app.js')).toBe(
			'/api/v1/functions/apps/example_plugin/assets/42/chunks/app.js'
		);
	});

	it('encodes every dynamic path segment', () => {
		expect(pluginAssetUrl({ ...app, id: 'my plugin' }, 'images/logo mark.svg')).toBe(
			'/api/v1/functions/apps/my%20plugin/assets/42/images/logo%20mark.svg'
		);
	});
});
