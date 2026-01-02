import { WEBUI_API_BASE_URL } from '$lib/constants';

// Types for Gemini RAG API
export interface GeminiRagStore {
	name: string;
	display_name: string;
	create_time?: string;
	corpora_count?: number;
}

export interface GeminiRagCorpus {
	name: string;
	displayName: string;
	createTime?: string;
	updateTime?: string;
}

export interface GeminiRagDocument {
	name: string;
	displayName: string;
	mimeType?: string;
	sizeBytes?: string;
	createTime?: string;
	updateTime?: string;
}

// Create a new store (folder)
export const createStore = async (token: string, displayName: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/gemini-rag/stores`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			display_name: displayName
		})
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err.detail || err.message || 'Failed to create store';
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

// Get all stores (folders)
export const getStores = async (token: string = '') => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/gemini-rag/stores`, {
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
			error = err.detail || err.message || 'Failed to get stores';
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	// Return stores array from response object
	return res?.stores || [];
};

// Delete a store (folder)
export const deleteStore = async (token: string, storeName: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/gemini-rag/stores/${encodeURIComponent(storeName)}`, {
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
		.catch((err) => {
			error = err.detail || err.message || 'Failed to delete store';
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

// Upload a file to a store
export const uploadFileToStore = async (token: string, storeName: string, file: File, displayName?: string) => {
	let error = null;

	const formData = new FormData();
	// include the filename explicitly as the third arg so multipart has the original name
	formData.append('file', file, displayName ?? file.name);
	// also send display_name as metadata in case the server expects it
	formData.append('display_name', displayName ?? file.name);

	const res = await fetch(`${WEBUI_API_BASE_URL}/gemini-rag/stores/${encodeURIComponent(storeName)}/upload`, {
		method: 'POST',
		headers: {
			authorization: `Bearer ${token}`
		},
		body: formData
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err.detail || err.message || 'Failed to upload file';
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

// Get files in a store
export const getStoreFiles = async (token: string, storeName: string) => {
	let error = null;
	console.log('Fetching files for store:', storeName);
	const res = await fetch(`${WEBUI_API_BASE_URL}/gemini-rag/stores/${encodeURIComponent(storeName)}/files`, {
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
			error = err.detail || err.message || 'Failed to get files';
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

// Delete a corpus (document) from a store
export const deleteCorpus = async (token: string, corpusName: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/gemini-rag/corpora/${encodeURIComponent(corpusName)}`, {
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
		.catch((err) => {
			error = err.detail || err.message || 'Failed to delete corpus';
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};
