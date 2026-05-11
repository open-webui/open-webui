import { WEBUI_API_BASE_URL } from '$lib/constants';

export const getGravatarUrl = async (token: string, email: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/utils/gravatar?email=${email}`, {
		method: 'GET',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			error = err.detail ?? err;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const executeCode = async (token: string, code: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/utils/code/execute`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			code: code
		})
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);

			error = err;
			if (err.detail) {
				error = err.detail;
			}
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const formatPythonCode = async (token: string, code: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/utils/code/format`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			code: code
		})
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);

			error = err;
			if (err.detail) {
				error = err.detail;
			}
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const downloadChatAsPDF = async (token: string, title: string, messages: object[]) => {
	let error = null;

	const result = await fetch(`${WEBUI_API_BASE_URL}/utils/pdf`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			title: title,
			messages: messages
		})
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			
			// Extract filename from Content-Disposition header (includes timestamp)
			const contentDisposition = res.headers.get('Content-Disposition');
			let filename = `${title}.pdf`; // Default fallback
			
			if (contentDisposition) {
				const matches = contentDisposition.match(/filename="?([^"]+)"?/);
				if (matches && matches[1]) {
					filename = matches[1];
				}
			}
			
			const blob = await res.blob();
			return { blob, filename };
		})
		.catch((err) => {
			console.error(err);
			error = err;
			return null;
		});

	return result;
};

export const downloadChatAsWord = async (token: string, title: string, messages: object[]) => {
	let error = null;

	const result = await fetch(`${WEBUI_API_BASE_URL}/utils/word`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			title: title,
			messages: messages
		})
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			
			// Extract filename from Content-Disposition header (includes timestamp)
			const contentDisposition = res.headers.get('Content-Disposition');
			let filename = `${title}.docx`; // Default fallback
			
			if (contentDisposition) {
				const matches = contentDisposition.match(/filename="?([^"]+)"?/);
				if (matches && matches[1]) {
					filename = matches[1];
				}
			}
			
			const blob = await res.blob();
			return { blob, filename };
		})
		.catch((err) => {
			console.error(err);
			error = err;
			return null;
		});

	return result;
};

export const exportArtifactToExcel = async (
	token: string,
	artifactType: string,
	content: string,
	filename: string = 'data.xlsx'
) => {
	let error = null;

	const result = await fetch(`${WEBUI_API_BASE_URL}/utils/artifacts/export-excel`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			artifact_type: artifactType,
			content: content,
			filename: filename
		})
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();

			// Extract filename from Content-Disposition header
			const contentDisposition = res.headers.get('Content-Disposition');
			let finalFilename = filename;

			if (contentDisposition) {
				const matches = contentDisposition.match(/filename="?([^"]+)"?/);
				if (matches && matches[1]) {
					finalFilename = matches[1];
				}
			}

			const blob = await res.blob();
			return { blob, filename: finalFilename };
		})
		.catch((err) => {
			console.error(err);
			error = err;
			return null;
		});

	return result;
};

export const getHTMLFromMarkdown = async (token: string, md: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/utils/markdown`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
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
			console.error(err);
			error = err;
			return null;
		});

	return res.html;
};

export const downloadDatabase = async (token: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/utils/db/download`, {
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
			console.error(err);
			error = err.detail;
			return null;
		});

	if (error) {
		throw error;
	}
};
