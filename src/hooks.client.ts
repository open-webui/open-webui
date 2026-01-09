import { get } from 'svelte/store';
import { getI18nStore } from './lib/i18n';

export function customHeadersFetch() {
	const originalFetch = window.fetch;
	const i18nStore = getI18nStore();

	window.fetch = async (input: RequestInfo | URL, init: RequestInit = {}) => {
		// get current values
		const i18n = get(i18nStore);

		// normalize headers to a plain object
		const existingHeaders =
			init.headers instanceof Headers
				? Object.fromEntries(init.headers.entries())
				: Array.isArray(init.headers)
				? Object.fromEntries(init.headers)
				: { ...(init.headers || {}) };

		const newHeaders: Record<string, string> = { ...existingHeaders };


		if (i18n?.language) {
			newHeaders['X-Language'] = i18n.language;
		}

		return originalFetch(input, {
			...init,
			headers: newHeaders,
		});
	};
}
