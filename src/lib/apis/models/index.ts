import canchatAPI from '$lib/apis/canchatAPI';
import { WEBUI_API_BASE_PATH } from '$lib/constants';

export const getModels = async (token: string = '') => {
	let error = null;

	const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/models/`, {
		method: 'GET'
	})
		.then(async (res) => {
			return res.data;
		})
		.catch((err) => {
			error = err;
			console.log(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getBaseModels = async (token: string = '') => {
	let error = null;

	const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/models/base`, {
		method: 'GET'
	})
		.then(async (res) => {
			return res.data;
		})
		.catch((err) => {
			error = err;
			console.log(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const createNewModel = async (token: string, model: object) => {
	let error = null;

	const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/models/create`, {
		method: 'POST',
		data: model
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

export const getModelById = async (token: string, id: string) => {
	let error = null;

	const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/models/model`, {
		method: 'GET',
		params: {
			id: id
		}
	})
		.then(async (res) => {
			return res.data;
		})
		.catch((err) => {
			error = err;

			console.log(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const toggleModelById = async (token: string, id: string) => {
	let error = null;

	const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/models/model/toggle`, {
		method: 'POST',
		params: {
			id: id
		}
	})
		.then(async (res) => {
			return res.data;
		})
		.catch((err) => {
			error = err;

			console.log(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const updateModelById = async (token: string, id: string, model: object) => {
	let error = null;

	const searchParams = new URLSearchParams();
	searchParams.append('id', id);

	const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/models/model/update`, {
		method: 'POST',
		data: model,
		params: {
			id: id
		}
	})
		.then(async (res) => {
			return res.data;
		})
		.catch((err) => {
			error = err;

			console.log(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const deleteModelById = async (token: string, id: string) => {
	let error = null;
	const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/models/model/delete`, {
		method: 'DELETE',
		params: {
			id: id
		}
	})
		.then(async (res) => {
			return res.data;
		})
		.catch((err) => {
			error = err;

			console.log(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const deleteAllModels = async (token: string) => {
	let error = null;

	const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/models/delete/all`, {
		method: 'DELETE'
	})
		.then(async (res) => {
			return res.data;
		})
		.catch((err) => {
			error = err;

			console.log(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};
