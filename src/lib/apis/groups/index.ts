import canchatAPI from '$lib/apis/canchatAPI';
import { WEBUI_API_BASE_PATH } from '$lib/constants';

export const createNewGroup = async (token: string, group: object) => {
	let error = null;

	const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/groups/create`, {
		method: 'POST',
		data: {
			...group
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

export const getGroups = async (token: string = '') => {
	let error = null;

	const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/groups/`, {
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

export const getGroupById = async (token: string, id: string) => {
	let error = null;

	const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/groups/id/${id}`, {
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

export const updateGroupById = async (token: string, id: string, group: object) => {
	let error = null;

	const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/groups/id/${id}/update`, {
		method: 'POST',
		data: {
			...group
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

export const deleteGroupById = async (token: string, id: string) => {
	let error = null;

	const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/groups/id/${id}/delete`, {
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
