import canchatAPI from '$lib/apis/canchatAPI';
import { WEBUI_API_BASE_PATH } from '$lib/constants';

export const getMemories = async (token: string) => {
	let error = null;

	const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/memories/`, {
		method: 'GET'
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

export const addNewMemory = async (token: string, content: string) => {
	let error = null;

	const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/memories/add`, {
		method: 'POST',
		data: {
			content: content
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

export const updateMemoryById = async (token: string, id: string, content: string) => {
	let error = null;

	const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/memories/${id}/update`, {
		method: 'POST',
		data: {
			content: content
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

export const queryMemory = async (token: string, content: string) => {
	let error = null;

	const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/memories/query`, {
		method: 'POST',
		data: {
			content: content
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

export const deleteMemoryById = async (token: string, id: string) => {
	let error = null;

	const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/memories/${id}`, {
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

export const deleteMemoriesByUserId = async (token: string) => {
	let error = null;

	const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/memories/delete/user`, {
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
