import { WEBUI_API_BASE_URL } from '$lib/constants';
import { fetchApi } from '$lib/apis/utils';

export const getUserPermissions = async (token: string) =>
	await fetchApi(`${WEBUI_API_BASE_URL}/users/permissions/user`, {
		method: 'GET',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		}
	});

export const updateUserPermissions = async (token: string, permissions: object) =>
	await fetchApi(`${WEBUI_API_BASE_URL}/users/permissions/user`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			...permissions
		})
	});

export const updateUserRole = async (token: string, id: string, role: string) =>
	await fetchApi(`${WEBUI_API_BASE_URL}/users/update/role`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			id: id,
			role: role
		})
	});

export const getUsers = async (token: string) => {
	const res = await fetchApi(`${WEBUI_API_BASE_URL}/users/`, {
		method: 'GET',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		}
	});

	return res ? res : [];
};

export const deleteUserById = async (token: string, userId: string) =>
	await fetchApi(`${WEBUI_API_BASE_URL}/users/${userId}`, {
		method: 'DELETE',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		}
	});

type UserUpdateForm = {
	profile_image_url: string;
	email: string;
	name: string;
	password: string;
};

export const updateUserById = async (token: string, userId: string, user: UserUpdateForm) =>
	await fetchApi(`${WEBUI_API_BASE_URL}/users/${userId}/update`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			profile_image_url: user.profile_image_url,
			email: user.email,
			name: user.name,
			password: user.password !== '' ? user.password : undefined
		})
	});
