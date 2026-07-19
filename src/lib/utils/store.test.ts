import { describe, expect, it, vi } from 'vitest';
import { writable } from 'svelte/store';

import { waitForStore } from './store';

describe('waitForStore', () => {
	it('resolves immediately when the current value matches', async () => {
		const ready = writable(true);

		await expect(waitForStore(ready, Boolean)).resolves.toBe(true);
	});

	it('waits until a later value matches and then unsubscribes', async () => {
		const ready = writable(false);
		const predicate = vi.fn(Boolean);
		const pending = waitForStore(ready, predicate);

		ready.set(true);
		await expect(pending).resolves.toBe(true);

		ready.set(false);
		expect(predicate).toHaveBeenCalledTimes(2);
	});
});
