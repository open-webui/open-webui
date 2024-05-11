import { WEBUI_API_BASE_URL } from '$lib/constants';

export const getGravatarUrl = async (email: string) => {
	const res = await fetch(`${WEBUI_API_BASE_URL}/utils/gravatar?email=${email}`, {
		method: 'GET',
		headers: {
			'Content-Type': 'application/json'
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error('Failed to get gravatar url', err);
			return null;
		});

	return res;
};

export const downloadChatAsPDF = async (chat: { title: string; messages: never[] }) => {
	return await fetch(`${WEBUI_API_BASE_URL}/utils/pdf`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json'
		},
		body: JSON.stringify({
			title: chat.title,
			messages: chat.messages
		})
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.blob();
		})
		.catch((err) => {
			console.error('Failed to download chat as pdf', err);
			return null;
		});
};

export const getHTMLFromMarkdown = async (md: string) => {
	const res = await fetch(`${WEBUI_API_BASE_URL}/utils/markdown`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json'
		},
		body: JSON.stringify({
			md: md
		})
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error('Failed to get HTML from markdown', err);
			return null;
		});

	return res.html;
};

export const downloadDatabase = async (token: string) => {
	let error = null;

	await fetch(`${WEBUI_API_BASE_URL}/utils/db/download`, {
		method: 'GET',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		}
	})
		.then(async (response) => {
			if (!response.ok) {
				throw await response.json();
			}
			return response.blob();
		})
		.then((blob) => {
			const url = window.URL.createObjectURL(blob);
			const a = document.createElement('a');
			a.href = url;
			a.download = 'webui.db';
			document.body.appendChild(a);
			a.click();
			window.URL.revokeObjectURL(url);
		})
		.catch((err) => {
			console.log(err);
			error = err.detail;
			return null;
		});

	if (error) {
		throw error;
	}
};
