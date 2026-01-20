import canchatAPI from '$lib/apis/canchatAPI';
import { WEBUI_API_BASE_PATH } from '$lib/constants';

export const createDomain = async (
	token: string,
	domain: { domain: string; description?: string }
) => {
	let error = null;

	const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/domains/create`, {
		method: 'POST',
		data: domain
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

export const getDomains = async (token: string = '') => {
	let error = null;

	const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/domains/`, {
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

export const getAvailableDomains = async (token: string = '') => {
	let error = null;

	const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/domains/available`, {
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

export const updateDomainById = async (
	token: string,
	domainId: string,
	domain: { domain: string; description?: string }
) => {
	let error = null;

	const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/domains/id/${domainId}/update`, {
		method: 'POST',
		data: domain
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

export const deleteDomainById = async (token: string, domainId: string) => {
	let error = null;

	const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/domains/id/${domainId}/delete`, {
		method: 'DELETE'
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
