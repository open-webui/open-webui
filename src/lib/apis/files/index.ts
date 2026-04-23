import { WEBUI_API_BASE_URL } from '$lib/constants';
import { isIOSLike, splitStream } from '$lib/utils';

// iOS/iPadOS WebKit rejects very large single multipart POSTs ("Load failed").
// On those platforms only, files above CHUNKED_UPLOAD_THRESHOLD are streamed
// to the backend in CHUNK_SIZE-sized pieces via /files/chunked/* endpoints.
// Other platforms keep the existing single-POST path unchanged.
const CHUNKED_UPLOAD_THRESHOLD = 500 * 1024; // 500 KiB
const CHUNK_SIZE = 500 * 1024; // 500 KiB per chunk

const uploadFileChunked = async (
	token: string,
	file: File,
	metadata: object | null | undefined,
	process: boolean | null | undefined
): Promise<any> => {
	const startRes = await fetch(`${WEBUI_API_BASE_URL}/files/chunked/start`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			filename: file.name,
			size: file.size,
			content_type: file.type || null
		})
	});

	if (!startRes.ok) {
		throw await startRes.json().catch(() => ({ detail: 'Failed to start chunked upload' }));
	}
	const { upload_id: uploadId } = await startRes.json();

	const abortSession = async () => {
		try {
			await fetch(`${WEBUI_API_BASE_URL}/files/chunked/${uploadId}`, {
				method: 'DELETE',
				headers: { authorization: `Bearer ${token}` }
			});
		} catch (_) {}
	};

	let offset = 0;
	while (offset < file.size) {
		const end = Math.min(offset + CHUNK_SIZE, file.size);
		const blob = file.slice(offset, end);
		const chunkRes = await fetch(
			`${WEBUI_API_BASE_URL}/files/chunked/${uploadId}?offset=${offset}`,
			{
				method: 'POST',
				headers: {
					'Content-Type': 'application/octet-stream',
					authorization: `Bearer ${token}`
				},
				body: blob
			}
		).catch(async (err) => {
			await abortSession();
			throw { detail: `network error at offset ${offset}: ${err?.message || err}` };
		});

		if (!chunkRes.ok) {
			const body = await chunkRes
				.json()
				.catch(() => ({ detail: `Chunk upload failed at offset ${offset}` }));
			await abortSession();
			throw body;
		}
		offset = end;
	}

	const completeParams = new URLSearchParams();
	if (process !== undefined && process !== null) {
		completeParams.append('process', String(process));
	}

	const completeBody = new FormData();
	if (metadata) {
		completeBody.append('metadata', JSON.stringify(metadata));
	}

	const completeRes = await fetch(
		`${WEBUI_API_BASE_URL}/files/chunked/${uploadId}/complete?${completeParams.toString()}`,
		{
			method: 'POST',
			headers: {
				Accept: 'application/json',
				authorization: `Bearer ${token}`
			},
			body: completeBody
		}
	);

	if (!completeRes.ok) {
		throw await completeRes
			.json()
			.catch(() => ({ detail: 'Failed to finalize chunked upload' }));
	}
	return completeRes.json();
};

export const uploadFile = async (
	token: string,
	file: File,
	metadata?: object | null,
	process?: boolean | null
) => {
	let error = null;
	let res: any = null;

	if (isIOSLike() && file.size > CHUNKED_UPLOAD_THRESHOLD) {
		try {
			res = await uploadFileChunked(token, file, metadata, process);
		} catch (err: any) {
			error = err?.detail || err?.message || err;
			console.error(err);
			res = null;
		}

		if (error) {
			throw error;
		}
		if (res) {
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
									if (res?.data) {
										res.data = data;
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
		return res;
	}

	const data = new FormData();
	data.append('file', file);
	if (metadata) {
		data.append('metadata', JSON.stringify(metadata));
	}

	const searchParams = new URLSearchParams();
	if (process !== undefined && process !== null) {
		searchParams.append('process', String(process));
	}

	res = await fetch(`${WEBUI_API_BASE_URL}/files/?${searchParams.toString()}`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			authorization: `Bearer ${token}`
		},
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

	if (res) {
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

								if (res?.data) {
									res.data = data;
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

export const searchFiles = async (
	token: string,
	filename: string = '*',
	skip: number = 0,
	limit: number = 50
) => {
	let error = null;

	const searchParams = new URLSearchParams();
	searchParams.append('filename', filename);
	searchParams.append('skip', String(skip));
	searchParams.append('limit', String(limit));

	const res = await fetch(`${WEBUI_API_BASE_URL}/files/search?${searchParams.toString()}`, {
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
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return [];
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
			return await res.arrayBuffer();
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
