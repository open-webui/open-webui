/// <reference types="@sveltejs/kit" />
import { openDB } from 'idb';

async function formDataToIndexDB(formData) {
	const data = {};

	const processValue = async (value) => {
		if (Array.isArray(value)) {
			return await Promise.all(value.map((item) => processValue(item)));
		} else if (value instanceof File) {
			const reader = new FileReader();
			return new Promise((resolve) => {
				reader.onload = () => {
					resolve({
						name: value.name,
						type: value.type,
						size: value.size,
						data: reader.result
					});
				};
				reader.readAsDataURL(value);
			});
		} else if (value instanceof FormData) {
			return await formDataToIndexDB(value);
		} else {
			return value;
		}
	};

	for (const [key, value] of formData.entries()) {
		data[key] = await processValue(value);
	}

	return data;
}

self.addEventListener('fetch', (event) => {
	const url = new URL(event.request.url);
	if (event.request.method === 'POST' && url.pathname === '/share') {
		event.respondWith(
			(async () => {
				const formData = await event.request.formData();

				const data = await formDataToIndexDB(formData);

				const db = await openDB('share', 1, {
					upgrade(db) {
						db.createObjectStore('share');
					}
				});

				await db.put('share', data, 'share');

				// Redirect to the origin
				return Response.redirect(url.origin, 303);
			})()
		);
	}
});
