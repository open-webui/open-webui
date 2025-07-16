import { WEBUI_API_BASE_URL } from '$lib/constants';

export const uploadFile = async (token: string, file: File, metadata?: object | null) => {
	const data = new FormData();
	data.append('file', file);
	if (metadata) {
		data.append('metadata', JSON.stringify(metadata));
	}

	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/files/`, {
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

export const reindexFiles = async (token: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/files/reindex`, {
		method: 'POST',
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
			console.log(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const countFiles = async (token: string) => {
	let error = null;
	
	const res = await fetch(`${WEBUI_API_BASE_URL}/files/?content=false`, {
	  method: 'GET',
	  headers: {
		Accept: 'application/json',
		'Content-Type': 'application/json',
		authorization: `Bearer ${token}`,
	  }
	})
	  .then(async (res) => {
		if (!res.ok) throw await res.json();
		const files = await res.json();
		return files.length;
	  })
	  .catch((err) => {
		error = err.detail;
		console.log(err);
		return 0;
	  });
  
	if (error) {
	  throw error;
	}
  
	return res;
  };

export const reindexMemories = async (token: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/memories/reindex`, {
		method: 'POST',
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
			console.log(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const reindexKnowledge = async (token: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/knowledge/reindex`, {
		method: 'POST',
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
			console.log(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const countKnowledges = async (token: string) => {
	let error = null;
	
	const res = await fetch(`${WEBUI_API_BASE_URL}/knowledge/?content=false`, {
	  method: 'GET',
	  headers: {
		Accept: 'application/json',
		'Content-Type': 'application/json',
		authorization: `Bearer ${token}`,
	  }
	})
	  .then(async (res) => {
		if (!res.ok) throw await res.json();
		const knowledges = await res.json();
		return knowledges.length;
	  })
	  .catch((err) => {
		error = err.detail;
		console.log(err);
		return 0;
	  });
  
	if (error) {
	  throw error;
	}
  
	return res;
  };

export const listenToReindexProgress = (onProgress: (data: { source: string | null; progress: number }) => void) => {
	
	const eventSource = new EventSource(`${WEBUI_API_BASE_URL}/utils/reindex/stream`);

	eventSource.onmessage = (event) => {
		const data = JSON.parse(event.data);
		const source = data.source;
		const progress = data.progress;

		onProgress({ source, progress });
		if (source === null) {
			eventSource?.close();
		}
	};

	eventSource.onerror = (err) => {
		console.error('SSE error:', err);
		eventSource?.close();
	};
};

export const checkIfReindexing = (): Promise<boolean> => {
	return new Promise((resolve) => {
		const eventSource = new EventSource(`${WEBUI_API_BASE_URL}/utils/reindex/stream`);

		const handleMessage = (event: MessageEvent) => {
			const data = JSON.parse(event.data);
        	const progress = data.progress;

			eventSource.close();
			resolve(progress > 0 && progress < 100); // treat as "in progress"
		};

		const handleError = () => {
			eventSource.close();
			resolve(false);
		};

		eventSource.onmessage = handleMessage;
		eventSource.onerror = handleError;
	});
};