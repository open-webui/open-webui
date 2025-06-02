import { MCP_API_BASE_URL } from '$lib/constants';

export const verifyMCPConnection = async (
	token: string = '',
	url: string = '',
	key: string = ''
) => {
	let error = null;

	const res = await fetch(`${MCP_API_BASE_URL}/verify`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			Authorization: `Bearer ${token}`,
			'Content-Type': 'application/json'
		},
		body: JSON.stringify({
			url,
			key
		})
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = `MCP: ${err?.detail ?? err?.error?.message ?? err?.message ?? 'Network Problem'}`;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getMCPConfig = async (token: string = '') => {
	let error = null;

	const res = await fetch(`${MCP_API_BASE_URL}/config`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = `MCP: ${err?.detail ?? err?.error?.message ?? err?.message ?? 'Network Problem'}`;
			return [];
		});

	if (error) {
		throw error;
	}

	return res;
};

export const updateMCPConfig = async (token: string = '', config: object) => {
	let error = null;

	const res = await fetch(`${MCP_API_BASE_URL}/config/update`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			Authorization: `Bearer ${token}`,
			'Content-Type': 'application/json'
		},
		body: JSON.stringify(config)
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = `MCP: ${err?.detail ?? err?.error?.message ?? err?.message ?? 'Network Problem'}`;
			return [];
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getMCPURLs = async (token: string = '') => {
	let error = null;

	const res = await fetch(`${MCP_API_BASE_URL}/urls`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = `MCP: ${err?.detail ?? err?.error?.message ?? err?.message ?? 'Network Problem'}`;
			return [];
		});

	if (error) {
		throw error;
	}

	return res;
};

export const updateMCPURLs = async (token: string = '', urls: string[]) => {
	let error = null;

	const res = await fetch(`${MCP_API_BASE_URL}/urls/update`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			Authorization: `Bearer ${token}`,
			'Content-Type': 'application/json'
		},
		body: JSON.stringify({
			urls
		})
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = `MCP: ${err?.detail ?? err?.error?.message ?? err?.message ?? 'Network Problem'}`;
			return [];
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getMCPTools = async (token: string = '') => {
	let error = null;

	const res = await fetch(`${MCP_API_BASE_URL}/tools`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = `MCP: ${err?.detail ?? err?.error?.message ?? err?.message ?? 'Network Problem'}`;
			return [];
		});

	if (error) {
		throw error;
	}

	return res?.tools || res || [];
};

export const callMCPTool = async (
	token: string = '',
	tool_name: string,
	parameters: object = {}
) => {
	let error = null;

	const res = await fetch(`${MCP_API_BASE_URL}/tools/call`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			Authorization: `Bearer ${token}`,
			'Content-Type': 'application/json'
		},
		body: JSON.stringify({
			tool_name,
			parameters
		})
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = `MCP: ${err?.detail ?? err?.error?.message ?? err?.message ?? 'Network Problem'}`;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};