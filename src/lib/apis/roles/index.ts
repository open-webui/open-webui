import { WEBUI_API_BASE_URL } from '$lib/constants';

export const getRoles = async (token: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/roles/`, {
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

export const addRole = async (token: string, roleName: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/roles/`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			role: roleName
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

export const updateRole = async (token: string, roleId: number, roleName: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/roles/${roleId}`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			role: roleName
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

export const deleteRole = async (token: string, roleName: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/roles/${roleName}`, {
		method: 'DELETE',
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

export const getRolePermissions = async (token: string, roleName: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/roles/${roleName}/permissions`, {
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

export const linkRoleToPermissions = async (
	token: string,
	roleName: string,
	categoryName: string,
	permissionName: string,
	value: boolean
) => {
	let error = null;
	const res = await fetch(`${WEBUI_API_BASE_URL}/roles/${roleName}/permission/link`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			permission_name: permissionName,
			category: categoryName,
			value: value
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

export const unlinkRoleFromPermissions = async (
	token: string,
	roleName: string,
	categoryName: string,
	permissionName: string
) => {
	let error = null;

	const res = await fetch(
		`${WEBUI_API_BASE_URL}/roles/${roleName}/permission/${categoryName}/${permissionName}`,
		{
			method: 'DELETE',
			headers: {
				'Content-Type': 'application/json',
				Authorization: `Bearer ${token}`
			}
		}
	)
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
