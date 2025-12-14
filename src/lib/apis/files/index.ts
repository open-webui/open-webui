import { WEBUI_API_BASE_URL } from '$lib/constants';
import { splitStream } from '$lib/utils';

export type UploadFileOptions = {
	process?: boolean;
	processInBackground?: boolean;
	waitForProcessing?: boolean;
	onProgress?: (progress: number) => void;
	signal?: AbortSignal;
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
		xhr.responseType = 'json';
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
			if (xhr.status >= 200 && xhr.status < 300) {
				resolve(xhr.response ?? null);
				return;
			}

			const response = xhr.response;
			if (response?.detail) {
				error = response.detail;
			} else if (response?.message) {
				error = response.message;
			} else if (typeof response === 'string' && response) {
				error = response;
			} else if (xhr.statusText) {
				error = xhr.statusText;
			} else {
				error = `Upload failed with status ${xhr.status}`;
			}

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
	const process = options.process ?? true;
	const processInBackground = options.processInBackground ?? true;
	const waitForProcessing = options.waitForProcessing ?? true;

	const queryParams = new URLSearchParams();
	queryParams.set('process', String(process));
	queryParams.set('process_in_background', String(processInBackground));

	const data = new FormData();
	data.append('file', file);
	if (metadata) {
		data.append('metadata', JSON.stringify(metadata));
	}

	let error = null;

	const uploadUrl = `${WEBUI_API_BASE_URL}/files/?${queryParams.toString()}`;

	const res = options.onProgress
		? await uploadFileWithProgress(token, uploadUrl, data, options.onProgress, options.signal).catch((err) => {
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
					error = err.detail || err.message;
					console.error(err);
					return null;
				});

	if (error) {
		throw error;
	}

	if (res && process && waitForProcessing) {
		const status = await getFileProcessStatus(token, res.id);

		if (status && status.ok) {
			const reader = status.body
				.pipeThrough(new TextDecoderStream())
				.pipeThrough(splitStream('\n'))
				.getReader();

			while (true) {
				const { value, done } = await reader.read();
				if (done) {
					break;
				}

				try {
					let lines = value.split('\n');

					for (const line of lines) {
						if (line !== '') {
							console.log(line);
							if (line === 'data: [DONE]') {
								console.log(line);
							} else {
								let data = JSON.parse(line.replace(/^data: /, ''));
								console.log(data);

								if (data?.error) {
									console.error(data.error);
									res.error = data.error;
								}
							}
						}
					}
				} catch (error) {
					console.log(error);
				}
			}
		}
	}

	if (error) {
		throw error;
	}

	return res;
};

export const getFileProcessStatus = async (token: string, id: string) => {
	const queryParams = new URLSearchParams();
	queryParams.append('stream', 'true');

	let error = null;
	const res = await fetch(`${WEBUI_API_BASE_URL}/files/${id}/process/status?${queryParams}`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			authorization: `Bearer ${token}`
		}
	}).catch((err) => {
		error = err.detail;
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
