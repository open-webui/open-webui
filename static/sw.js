self.addEventListener('install', () => {
	self.skipWaiting();
});

self.addEventListener('activate', (event) => {
	event.waitUntil(self.clients.claim());
});

self.addEventListener('push', (event) => {
	let payload = {};
	try {
		payload = event.data ? event.data.json() : {};
	} catch {
		payload = {};
	}

	event.waitUntil(
		self.registration.showNotification(payload.title || 'Open WebUI', {
			body: payload.body || '',
			icon: '/static/favicon.png',
			badge: '/static/favicon.png',
			// Coalesce notifications for the same chat or channel
			...(payload.url ? { tag: payload.url, renotify: true } : {}),
			data: { url: payload.url || '' }
		})
	);
});

self.addEventListener('notificationclick', (event) => {
	event.notification.close();
	const url = event.notification.data?.url || '';

	event.waitUntil(
		self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then(async (windows) => {
			const win = windows.find((w) => 'focus' in w);
			if (win) {
				await win.focus();
				// Only navigate for deep links; never yank an open window to '/'
				if (url) {
					try {
						if (win.url !== new URL(url, self.location.origin).href) {
							await win.navigate(url);
						}
					} catch {
						// Uncontrolled clients cannot be navigated; open the link in a new window
						await self.clients.openWindow(url).catch(() => {});
					}
				}
				return;
			}
			return self.clients.openWindow(url || '/');
		})
	);
});

self.addEventListener('pushsubscriptionchange', (event) => {
	if (!event.oldSubscription?.options?.applicationServerKey) {
		return;
	}
	event.waitUntil(
		self.registration.pushManager
			.subscribe(event.oldSubscription.options)
			.then((subscription) =>
				fetch('/api/v1/notifications/webpush/subscriptions', {
					method: 'POST',
					credentials: 'include',
					headers: { 'Content-Type': 'application/json' },
					body: JSON.stringify(subscription.toJSON())
				})
			)
			.catch(() => {
				// Without a valid session cookie the subscription is re-established on next app open
			})
	);
});
