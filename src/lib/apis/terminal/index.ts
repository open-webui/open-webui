export type FileEntry = {
	name: string;
	type: 'file' | 'directory';
	size?: number;
	modified?: number;
};

export const getCwd = async (baseUrl: string, apiKey: string): Promise<string | null> => {
	const url = `${baseUrl.replace(/\/$/, '')}/files/cwd`;
	const res = await fetch(url, {
		headers: { Authorization: `Bearer ${apiKey}` }
	}).catch(() => null);
	if (!res || !res.ok) return null;
	const json = await res.json().catch(() => null);
	return json?.cwd ?? null;
};

export const listFiles = async (
	baseUrl: string,
	apiKey: string,
	path: string = '/'
): Promise<FileEntry[] | null> => {
	// The endpoint uses `directory` as the query param name
	const url = `${baseUrl.replace(/\/$/, '')}/files/list?directory=${encodeURIComponent(path)}`;
	const res = await fetch(url, {
		headers: { Authorization: `Bearer ${apiKey}` }
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error('open-terminal listFiles error:', err);
			return null;
		});
	return res?.entries ?? null;
};

export const readFile = async (
	baseUrl: string,
	apiKey: string,
	path: string
): Promise<string | null> => {
	const url = `${baseUrl.replace(/\/$/, '')}/files/read?path=${encodeURIComponent(path)}`;
	const res = await fetch(url, {
		headers: { Authorization: `Bearer ${apiKey}` }
	}).catch((err) => {
		console.error('open-terminal readFile error:', err);
		return null;
	});

	if (!res || !res.ok) return null;

	const contentType = res.headers.get('content-type') ?? '';
	if (contentType.startsWith('image/') || contentType.startsWith('application/octet')) {
		// Binary — return a placeholder
		return `[Binary file: ${contentType}]`;
	}

	// Text files: endpoint returns JSON { path, total_lines, content }
	// Binary image files: endpoint returns raw bytes (handled above)
	const json = await res.json().catch(() => null);
	return json?.content ?? null;
};

export const downloadFileBlob = async (
	baseUrl: string,
	apiKey: string,
	path: string
): Promise<{ blob: Blob; filename: string } | null> => {
	const url = `${baseUrl.replace(/\/$/, '')}/files/view?path=${encodeURIComponent(path)}`;
	const res = await fetch(url, {
		headers: { Authorization: `Bearer ${apiKey}` }
	}).catch(() => null);

	if (!res || !res.ok) return null;

	const filename = path.split('/').pop() ?? 'file';
	const blob = await res.blob();
	return { blob, filename };
};

export const uploadToTerminal = async (
	baseUrl: string,
	apiKey: string,
	directory: string,
	file: File
): Promise<{ path: string; size: number } | null> => {
	const url = `${baseUrl.replace(/\/$/, '')}/files/upload?directory=${encodeURIComponent(directory)}`;
	const body = new FormData();
	body.append('file', file);
	const res = await fetch(url, {
		method: 'POST',
		headers: { Authorization: `Bearer ${apiKey}` },
		body
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error('open-terminal uploadToTerminal error:', err);
			return null;
		});
	return res;
};

export const createDirectory = async (
	baseUrl: string,
	apiKey: string,
	path: string
): Promise<{ path: string } | null> => {
	const url = `${baseUrl.replace(/\/$/, '')}/files/mkdir`;
	const res = await fetch(url, {
		method: 'POST',
		headers: {
			Authorization: `Bearer ${apiKey}`,
			'Content-Type': 'application/json'
		},
		body: JSON.stringify({ path })
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error('open-terminal createDirectory error:', err);
			return null;
		});
	return res;
};

export const deleteEntry = async (
	baseUrl: string,
	apiKey: string,
	path: string
): Promise<{ path: string; type: string } | null> => {
	const url = `${baseUrl.replace(/\/$/, '')}/files/delete?path=${encodeURIComponent(path)}`;
	const res = await fetch(url, {
		method: 'DELETE',
		headers: { Authorization: `Bearer ${apiKey}` }
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error('open-terminal deleteEntry error:', err);
			return null;
		});
	return res;
};

export const setCwd = async (
	baseUrl: string,
	apiKey: string,
	path: string
): Promise<{ cwd: string } | null> => {
	const url = `${baseUrl.replace(/\/$/, '')}/files/cwd`;
	const res = await fetch(url, {
		method: 'POST',
		headers: {
			Authorization: `Bearer ${apiKey}`,
			'Content-Type': 'application/json'
		},
		body: JSON.stringify({ path })
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error('open-terminal setCwd error:', err);
			return null;
		});
	return res;
};
