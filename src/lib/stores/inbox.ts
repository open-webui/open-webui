import { writable } from 'svelte/store';
import { inboxRequest } from '$lib/apis/notifications/inbox';

export const inboxCount = writable(0);
let revision = 0;

export function setInboxCount(count: number) {
	revision += 1;
	inboxCount.set(count);
}

export async function refreshInboxCount() {
	const request = ++revision;
	try {
		const result = await inboxRequest<{ count: number }>('/count');
		if (request === revision) inboxCount.set(result.count);
	} catch {
		/* Keep the last known count while disconnected. */
	}
}
