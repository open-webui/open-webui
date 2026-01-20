import canchatAPI from '$lib/apis/canchatAPI';
import { WEBUI_API_BASE_PATH } from '$lib/constants';

export const createNewFunction = async (token: string, func: object) => {
	let error = null;

	const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/functions/create`, {
		method: 'POST',
		data: {
			...func
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

export const getFunctions = async (token: string = '') => {
	let error = null;

	const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/functions/`, {
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

export const exportFunctions = async (token: string = '') => {
	let error = null;

	const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/functions/export`, {
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

export const getFunctionById = async (token: string, id: string) => {
	let error = null;

	const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/functions/id/${id}`, {
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

export const updateFunctionById = async (token: string, id: string, func: object) => {
	let error = null;

	const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/functions/id/${id}/update`, {
		method: 'POST',
		data: {
			...func
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

export const deleteFunctionById = async (token: string, id: string) => {
	let error = null;

	const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/functions/id/${id}/delete`, {
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

export const toggleFunctionById = async (token: string, id: string) => {
	let error = null;

	const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/functions/id/${id}/toggle`, {
		method: 'POST'
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

export const toggleGlobalById = async (token: string, id: string) => {
	let error = null;

	const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/functions/id/${id}/toggle/global`, {
		method: 'POST'
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

export const getFunctionValvesById = async (token: string, id: string) => {
	let error = null;

	const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/functions/id/${id}/valves`, {
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

export const getFunctionValvesSpecById = async (token: string, id: string) => {
	let error = null;

	const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/functions/id/${id}/valves/spec`, {
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

export const updateFunctionValvesById = async (token: string, id: string, valves: object) => {
	let error = null;

	const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/functions/id/${id}/valves/update`, {
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

	const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/functions/id/${id}/valves/user`, {
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

	const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/functions/id/${id}/valves/user/spec`, {
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

	const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/functions/id/${id}/valves/user/update`, {
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
