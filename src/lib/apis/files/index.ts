import { WEBUI_API_BASE_URL } from '$lib/constants';

export type UploadFileOptions = {
	onProgress?: (progress: number) => void;
	signal?: AbortSignal;
};

const tryParseJson = (text: string) => {
	try {
		return JSON.parse(text);
	} catch {
		return null;
	}
};

const coerceToString = (value: any) => {
	if (typeof value === 'string') return value;
	if (typeof value === 'number' || typeof value === 'boolean') return String(value);
	if (value instanceof Error) return value.message || String(value);
	if (value === null || value === undefined) return '';
	try {
		return JSON.stringify(value);
	} catch {
		return String(value);
	}
};

const uploadFileWithProgress = async (
	token: string,
	url: string,
	formData: FormData,
	onProgress: (progress: number) => void,
	signal?: AbortSignal
) => {
	let error: any = null;

	const res = await new Promise<any | null>((resolve) => {
		const xhr = new XMLHttpRequest();
		const abortHandler = () => {
			try {
				xhr.abort();
			} catch (err) {
				// Ignore abort errors
			}
		};

		xhr.open('POST', url, true);
		// Note: Do NOT set xhr.responseType = 'json' as it causes issues on iOS Safari
		// where accessing xhr.responseText throws InvalidStateError.
		// Instead, we parse the response text manually.
		xhr.setRequestHeader('Accept', 'application/json');
		xhr.setRequestHeader('authorization', `Bearer ${token}`);

		if (signal) {
			if (signal.aborted) {
				error = new DOMException('Upload aborted', 'AbortError');
				resolve(null);
				return;
			}
			signal.addEventListener('abort', abortHandler);
		}

		if (xhr.upload) {
			xhr.upload.onprogress = (event) => {
				if (!event.lengthComputable) return;
				const progress = Math.round((event.loaded / event.total) * 100);
				onProgress(Math.max(0, Math.min(100, progress)));
			};
		}

		xhr.onload = () => {
			if (signal) signal.removeEventListener('abort', abortHandler);
			const status = xhr.status;

			// Parse response - use responseText since we're not setting responseType
			let response: any = null;
			try {
				const responseText = xhr.responseText || '';
				if (responseText) {
					response = tryParseJson(responseText);
				}
			} catch (e) {
				// On some browsers/environments, accessing responseText might fail
				// In that case, try xhr.response as fallback
				try {
					response = xhr.response;
					if (typeof response === 'string') {
						response = tryParseJson(response);
					}
				} catch {
					// Ignore fallback errors
				}
			}

			if (status >= 200 && status < 300) {
				if (response && typeof response === 'object') {
					resolve(response);
					return;
				}

				error = 'Upload succeeded but the server returned an invalid response';
				resolve(null);
				return;
			}

			let message: any = null;
			if (typeof response === 'string' && response) {
				message = response;
			} else if (response?.detail) {
				message = response.detail;
			} else if (response?.message) {
				message = response.message;
			} else if (xhr.statusText) {
				message = xhr.statusText;
			} else {
				message = `Upload failed with status ${status}`;
			}

			const messageText = coerceToString(message) || `Upload failed with status ${status}`;
			error = status ? `HTTP ${status}: ${messageText}` : messageText;
			resolve(null);
		};

		xhr.onerror = () => {
			if (signal) signal.removeEventListener('abort', abortHandler);
			error = 'Network error while uploading file';
			resolve(null);
		};

		xhr.onabort = () => {
			if (signal) signal.removeEventListener('abort', abortHandler);
			error = new DOMException('Upload aborted', 'AbortError');
			resolve(null);
		};

		xhr.send(formData);
	});

	if (error) {
		throw error;
	}

	return res;
};

export const uploadFile = async (
	token: string,
	file: File,
	metadata?: object | null,
	options: UploadFileOptions = {}
) => {
	const data = new FormData();
	data.append('file', file);
	if (metadata) {
		data.append('metadata', JSON.stringify(metadata));
	}

	let error = null;

	const uploadUrl = `${WEBUI_API_BASE_URL}/files/`;

	const res = options.onProgress
		? await uploadFileWithProgress(
				token,
				uploadUrl,
				data,
				options.onProgress,
				options.signal
			).catch((err) => {
				error = err;
				console.error(err);
				return null;
			})
		: await fetch(uploadUrl, {
				method: 'POST',
				headers: {
					Accept: 'application/json',
					authorization: `Bearer ${token}`
				},
				signal: options.signal,
				body: data
			})
				.then(async (res) => {
					if (!res.ok) throw await res.json();
					return res.json();
				})
				.catch((err) => {
					error = err?.detail ?? err?.message ?? err;
					console.error(err);
					return null;
				});

	if (error) {
		throw error;
	}

	return res;
};

export const uploadDir = async (token: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/files/upload/dir`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err.detail;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getFiles = async (token: string = '') => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/files/`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.then((json) => {
			return json;
		})
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getFileById = async (token: string, id: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/files/${id}`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.then((json) => {
			return json;
		})
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const updateFileDataContentById = async (token: string, id: string, content: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/files/${id}/data/content/update`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			content: content
		})
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.then((json) => {
			return json;
		})
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const updateFileProcessingMode = async (
	token: string,
	id: string,
	mode: 'text' | 'pdf'
) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/files/${id}/process-mode`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify({ mode })
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err?.detail ?? err;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getFileContentById = async (id: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/files/${id}/content`, {
		method: 'GET',
		headers: {
			Accept: 'application/json'
		},
		credentials: 'include'
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return await res.blob();
		})
		.catch((err) => {
			error = err.detail;
			console.error(err);

			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const deleteFileById = async (token: string, id: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/files/${id}`, {
		method: 'DELETE',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.then((json) => {
			return json;
		})
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const deleteAllFiles = async (token: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/files/all`, {
		method: 'DELETE',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.then((json) => {
			return json;
		})
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};
