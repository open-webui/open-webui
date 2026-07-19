import type { Readable } from 'svelte/store';

export const waitForStore = <T>(store: Readable<T>, predicate: (value: T) => boolean) =>
	new Promise<T>((resolve) => {
		const unsubscribe = store.subscribe((value) => {
			if (predicate(value)) {
				resolve(value);
				queueMicrotask(unsubscribe);
			}
		});
	});
