import canchatAPI from '$lib/apis/canchatAPI';
import { WEBUI_API_BASE_PATH } from '$lib/constants';

export const createNewTool = async (token: string, tool: object) => {
	let error = null;

	const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/tools/create`, {
		method: 'POST',
		data: {
			...tool
		}
	})
		.then(async (res) => {
			return res.data;
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

export const getTools = async (token: string = '') => {
	let error = null;

	const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/tools/`, {
		method: 'GET'
	})
		.then(async (res) => {
			return res.data;
		})
		.then((json) => {
			return json;
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

export const getToolList = async (token: string = '') => {
	let error = null;

	const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/tools/list`, {
		method: 'GET'
	})
		.then(async (res) => {
			return res.data;
		})
		.then((json) => {
			return json;
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

export const exportTools = async (token: string = '') => {
	let error = null;

	const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/tools/export`, {
		method: 'GET'
	})
		.then(async (res) => {
			return res.data;
		})
		.then((json) => {
			return json;
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

export const getToolById = async (token: string, id: string) => {
	let error = null;

	const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/tools/id/${id}`, {
		method: 'GET'
	})
		.then(async (res) => {
			return res.data;
		})
		.then((json) => {
			return json;
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

export const updateToolById = async (token: string, id: string, tool: object) => {
	let error = null;

	const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/tools/id/${id}/update`, {
		method: 'POST',
		data: {
			...tool
		}
	})
		.then(async (res) => {
			return res.data;
		})
		.then((json) => {
			return json;
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

export const deleteToolById = async (token: string, id: string) => {
	let error = null;

	const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/tools/id/${id}/delete`, {
		method: 'DELETE'
	})
		.then(async (res) => {
			return res.data;
		})
		.then((json) => {
			return json;
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

export const getToolValvesById = async (token: string, id: string) => {
	let error = null;

	const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/tools/id/${id}/valves`, {
		method: 'GET'
	})
		.then(async (res) => {
			return res.data;
		})
		.then((json) => {
			return json;
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

export const getToolValvesSpecById = async (token: string, id: string) => {
	let error = null;

	const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/tools/id/${id}/valves/spec`, {
		method: 'GET'
	})
		.then(async (res) => {
			return res.data;
		})
		.then((json) => {
			return json;
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

export const updateToolValvesById = async (token: string, id: string, valves: object) => {
	let error = null;

	const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/tools/id/${id}/valves/update`, {
		method: 'POST',
		data: {
			...valves
		}
	})
		.then(async (res) => {
			return res.data;
		})
		.then((json) => {
			return json;
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

export const getUserValvesById = async (token: string, id: string) => {
	let error = null;

	const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/tools/id/${id}/valves/user`, {
		method: 'GET'
	})
		.then(async (res) => {
			return res.data;
		})
		.then((json) => {
			return json;
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

export const getUserValvesSpecById = async (token: string, id: string) => {
	let error = null;

	const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/tools/id/${id}/valves/user/spec`, {
		method: 'GET'
	})
		.then(async (res) => {
			return res.data;
		})
		.then((json) => {
			return json;
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

export const updateUserValvesById = async (token: string, id: string, valves: object) => {
	let error = null;

	const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/tools/id/${id}/valves/user/update`, {
		method: 'POST',
		data: {
			...valves
		}
	})
		.then(async (res) => {
			return res.data;
		})
		.then((json) => {
			return json;
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
