import canchatAPI from '$lib/apis/canchatAPI';
import { MCP_API_BASE_PATH } from '$lib/constants';

export const verifyMCPConnection = async (
	token: string = '',
	url: string = '',
	key: string = ''
) => {
	let error = null;

	const res = await canchatAPI(`${MCP_API_BASE_PATH}/verify`, {
		method: 'POST',
		data: {
			url,
			key
		}
	})
		.then(async (res) => {
			return res.data;
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

	const res = await canchatAPI(`${MCP_API_BASE_PATH}/config`, {
		method: 'GET'
	})
		.then(async (res) => {
			return res.data;
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

	const res = await canchatAPI(`${MCP_API_BASE_PATH}/config/update`, {
		method: 'POST',
		data: config
	})
		.then(async (res) => {
			return res.data;
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

	const res = await canchatAPI(`${MCP_API_BASE_PATH}/urls`, {
		method: 'GET'
	})
		.then(async (res) => {
			return res.data;
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

	const res = await canchatAPI(`${MCP_API_BASE_PATH}/urls/update`, {
		method: 'POST',
		data: {
			urls
		}
	})
		.then(async (res) => {
			return res.data;
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

	const res = await canchatAPI(`${MCP_API_BASE_PATH}/tools`, {
		method: 'GET'
	})
		.then(async (res) => {
			return res.data;
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

	const res = await canchatAPI(`${MCP_API_BASE_PATH}/tools/call`, {
		method: 'POST',
		data: {
			tool_name,
			parameters
		}
	})
		.then(async (res) => {
			return res.data;
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

export const getBuiltinServers = async (token: string = '') => {
	let error = null;

	const res = await canchatAPI(`${MCP_API_BASE_PATH}/servers/builtin`, {
		method: 'GET'
	})
		.then(async (res) => {
			return res.data;
		})
		.catch((err) => {
			error = `MCP: ${err?.detail ?? err?.error?.message ?? err?.message ?? 'Network Problem'}`;
			return { servers: [] };
		});

	if (error) {
		throw error;
	}

	return res;
};

export const restartBuiltinServer = async (token: string = '', serverName: string = '') => {
	let error = null;

	const res = await canchatAPI(`${MCP_API_BASE_PATH}/servers/builtin/${serverName}/restart`, {
		method: 'POST'
	})
		.then(async (res) => {
			return res.data;
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

// External Server Management API Functions

export const getExternalServers = async (token: string = '') => {
	let error = null;

	const res = await canchatAPI(`${MCP_API_BASE_PATH}/servers/external`, {
		method: 'GET'
	})
		.then(async (res) => {
			return res.data;
		})
		.catch((err) => {
			error = `MCP: ${err?.detail ?? err?.error?.message ?? err?.message ?? 'Network Problem'}`;
			return { servers: [] };
		});

	if (error) {
		throw error;
	}

	return res;
};

export const createExternalServer = async (token: string = '', serverData: object) => {
	let error = null;

	const res = await canchatAPI(`${MCP_API_BASE_PATH}/servers/external`, {
		method: 'POST',
		data: serverData
	})
		.then(async (res) => {
			return res.data;
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

export const getExternalServer = async (token: string = '', serverId: string = '') => {
	let error = null;

	const res = await canchatAPI(`${MCP_API_BASE_PATH}/servers/external/${serverId}`, {
		method: 'GET'
	})
		.then(async (res) => {
			return res.data;
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

export const updateExternalServer = async (
	token: string = '',
	serverId: string = '',
	serverData: object
) => {
	let error = null;

	const res = await canchatAPI(`${MCP_API_BASE_PATH}/servers/external/${serverId}`, {
		method: 'PUT',
		data: serverData
	})
		.then(async (res) => {
			return res.data;
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

export const deleteExternalServer = async (token: string = '', serverId: string = '') => {
	let error = null;

	const res = await canchatAPI(`${MCP_API_BASE_PATH}/servers/external/${serverId}`, {
		method: 'DELETE'
	})
		.then(async (res) => {
			return res.data;
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

export const startExternalServer = async (token: string = '', serverId: string = '') => {
	let error = null;

	const res = await canchatAPI(`${MCP_API_BASE_PATH}/servers/external/${serverId}/start`, {
		method: 'POST'
	})
		.then(async (res) => {
			return res.data;
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

export const stopExternalServer = async (token: string = '', serverId: string = '') => {
	let error = null;

	const res = await canchatAPI(`${MCP_API_BASE_PATH}/servers/external/${serverId}/stop`, {
		method: 'POST'
	})
		.then(async (res) => {
			return res.data;
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

export const restartExternalServer = async (token: string = '', serverId: string = '') => {
	let error = null;

	const res = await canchatAPI(`${MCP_API_BASE_PATH}/servers/external/${serverId}/restart`, {
		method: 'POST'
	})
		.then(async (res) => {
			return res.data;
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
