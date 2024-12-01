/// <reference types="@sveltejs/kit" />
import { openDB } from 'idb';

function formDataToIndexDB(formData) {
	return new Promise((resolve) => {
		const data = {};

		const entries = formData.entries();
		// Iterate over the form data
		for (const entry of entries) {
			const [key, value] = entry;
			// If the value is a file
			if (value instanceof File) {
				// Convert the file to base64
				const reader = new FileReader();
				reader.onload = () => {
					data[key] = {
						name: value.name,
						type: value.type,
						size: value.size,
						data: reader.result
					};
				};
				reader.readAsDataURL(value);
			} else {
				data[key] = value;
			}
		}

		resolve(data);
	});
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
