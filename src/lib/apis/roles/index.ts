import { WEBUI_API_BASE_URL } from '$lib/constants';
import { getUserPosition } from '$lib/utils';

export const getRoles = async (token: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/roles`, {
		method: 'GET',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		}
	})
    .then(async (res) => {
        if (!res.ok) throw await res.json();
        return res.json();
    })
    .catch((err) => {
        console.log(err);
        error = err.detail;
        return null;
    });

	if (error) {
		throw error;
	}

	return res;
};

export const addRole = async (token: string, role: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/roles`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			role: role
		})
	})
    .then(async (res) => {
        if (!res.ok) throw await res.json();
        return res.json();
    })
    .catch((err) => {
        console.log(err);
        error = err.detail;
        return null;
    });

	if (error) {
		throw error;
	}

	return res;
};

export const deleteRole = async (token: string, roleId: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/roles/${roleId}`, {
		method: 'DELETE',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
	})
    .then(async (res) => {
        if (!res.ok) throw await res.json();
        return res.json();
    })
    .catch((err) => {
        console.log(err);
        error = err.detail;
        return null;
    });

	if (error) {
		throw error;
	}

	return res;
};