import { WEBUI_API_BASE_URL } from '$lib/constants';

export const getCharities = async (
	token: string,
	query?: string,
	orderBy?: string,
	direction?: string,
	page = 1
) => {
	let error = null;
	let res = null;

	let searchParams = new URLSearchParams();

	searchParams.set('page', `${page}`);

	if (query) {
		searchParams.set('query', query);
	}

	if (orderBy) {
		searchParams.set('order_by', orderBy);
	}

	if (direction) {
		searchParams.set('direction', direction);
	}

	res = await fetch(`${WEBUI_API_BASE_URL}/charities/?${searchParams.toString()}`, {
		method: 'GET',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			console.log('Fetch response:', res);
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			error = err.detail;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const createCharity = async (token: string, charity: object) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/charities/create`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			...charity
		})
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const deleteCharityById = async (token: string, id: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/charities/id/${id}/delete`, {
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
		.then((json) => {
			return json;
		})
		.catch((err) => {
			error = err.detail;

			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const updateCharityById = async (token: string, id: string, charity: object) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/charities/id/${id}/update`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			...charity
		})
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.then((json) => {
			return json;
		})
		.catch((err) => {
			error = err.detail;

			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};
