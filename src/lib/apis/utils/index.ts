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
			error = err;
			return null;
		});

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

	const blob = await fetch(`${WEBUI_API_BASE_URL}/utils/pdf`, {
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
			return res.blob();
		})
		.catch((err) => {
			console.error(err);
			error = err;
			return null;
		});

	return blob;
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

export const downloadLiteLLMConfig = async (token: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/utils/litellm/config`, {
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
			a.download = 'config.yaml';
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

export const reindexData = async (
	token: string,
	options?: { process_from_disk: boolean; batch_size: number }
) => {
	let error = null;
	const body = JSON.stringify(options || {});
	console.log("Sending to backend:", body); // ← log the exact payload

	const res = await fetch(`${WEBUI_API_BASE_URL}/utils/reindex`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify(options || {})
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err.detail;
			console.log(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const listenToReindexProgress = (
	onProgress: (data: {
		memories: { progress: number; status: string };
		files: { progress: number; status: string };
		knowledge: { progress: number; status: string };
	}) => void,
	onComplete: (stopped: boolean) => void
) => {
	const eventSource = new EventSource(`${WEBUI_API_BASE_URL}/utils/reindex/stream`);

	eventSource.onmessage = (event) => {
		const data = JSON.parse(event.data);

		onProgress({
			memories: data.memories,
			files: data.files,
			knowledge: data.knowledge,
		});

		const statuses = Object.values(
			data as Record<string, { progress: number; status: string }>
		).map(task => task.status);

		// Determine if all tasks are finished or stopped
		const allFinished = statuses.every(status => status === "done" || status === "stopped");

		if (allFinished) {
			eventSource.close();
			// If any task is stopped, pass stopped=true
			const stopped = statuses.some(status => status === "stopped");
			onComplete(stopped);
		}
	};

	eventSource.onerror = (err) => {
		console.error("SSE error:", err);
		eventSource.close();
	};
};


export const checkIfReindexing = (): Promise<boolean> => {
	return new Promise((resolve) => {
		const eventSource = new EventSource(`${WEBUI_API_BASE_URL}/utils/reindex/stream`);

		const handleMessage = (event: MessageEvent) => {
			const data = JSON.parse(event.data);

			// Check if any task is currently running
			const inProgress = Object.values(
				data as Record<string, { progress: number; status: string }>
			)
				.some(task => task.status === "running");

			eventSource.close();
			resolve(inProgress);
		};

		const handleError = () => {
			eventSource.close();
			resolve(false);
		};

		eventSource.onmessage = handleMessage;
		eventSource.onerror = handleError;
	});
};

export const stopReindex = async (token: string) => {
    let error: any = null;

    const res = await fetch(`${WEBUI_API_BASE_URL}/utils/reindex/stop`, {
        method: 'POST',
        headers: {
            Accept: 'application/json',
            'Content-Type': 'application/json',
            authorization: `Bearer ${token}`,
        },
    })
        .then(async (res) => {
            if (!res.ok) {
                throw await res.json();
            }
            return res.json();
        })
        .catch((err) => {
            error = err.detail ?? err;
            console.error("Failed to stop reindex:", err);
            return null;
        });

    if (error) {
        throw error;
    }

    return res;
};
