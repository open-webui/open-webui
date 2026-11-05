import { desktopEvent, type DesktopEvent, type SpotlightQuery } from '$lib/stores';
import { get } from 'svelte/store';

// Acknowledge when the composer owns the draft, not when model generation finishes.
export async function receiveSpotlightQuery(
	data: SpotlightQuery,
	navigate: () => Promise<void>,
	getUserId: () => string | undefined
): Promise<void> {
	const userId = getUserId();
	if (!userId) throw new Error('Sign in to WebUI, then send again. Your Spotlight draft is kept.');
	let active = true;
	let timer: ReturnType<typeof setTimeout>;
	let event: DesktopEvent;
	const received = new Promise<void>((resolve, reject) => {
		event = {
			type: 'query',
			data,
			handoff: {
				isCurrent: () => active && getUserId() === userId,
				complete: (error?: string) => {
					if (error) reject(new Error(error));
					else resolve();
				}
			}
		};
		timer = setTimeout(
			() => reject(new Error('The WebUI composer is not ready. Your Spotlight draft is kept.')),
			15_000
		);
	});
	desktopEvent.set(event!);
	try {
		await Promise.all([navigate(), received]);
	} finally {
		active = false;
		clearTimeout(timer!);
		if (get(desktopEvent) === event!) desktopEvent.set(null);
	}
}
