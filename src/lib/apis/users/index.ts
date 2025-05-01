import { getUserPosition } from '$lib/utils';
import { webuiApiClient } from '../clients';

type UserUpdateForm = {
	profile_image_url: string;
	email: string;
	name: string;
	password: string;
};

export const getUserGroups = async (token: string) =>
	webuiApiClient.get('/users/groups', { token });

export const getUserDefaultPermissions = async (token: string) =>
	webuiApiClient.get('/users/default/permissions', { token });

export const updateUserDefaultPermissions = async (token: string, permissions: object) =>
	webuiApiClient.post('/users/default/permissions', permissions, { token });

export const updateUserRole = async (token: string, id: string, role: string) =>
	webuiApiClient.post('/users/update/role', { id, role }, { token });

export const getUsers = async (token: string) =>
	webuiApiClient.get('/users/', { token }).then((response) => response || []);

export const getUserSettings = async (token: string) =>
	webuiApiClient.get('/users/user/settings', { token });

export const updateUserSettings = async (token: string, settings: object) =>
	webuiApiClient.post('/users/user/settings/update', settings, { token });

export const getUserById = async (token: string, userId: string) =>
	webuiApiClient.get(`/users/${userId}`, { token });

export const getUserInfo = async (token: string) =>
	webuiApiClient.get('/users/user/info', { token });

export const updateUserInfo = async (token: string, info: object) =>
	webuiApiClient.post('/users/user/info/update', info, { token });

export const getAndUpdateUserLocation = async (token: string) => {
	try {
		const location = await getUserPosition();
		if (location) {
			await updateUserInfo(token, { location });
			return location;
		}
		console.log('Failed to get user location');
		return null;
	} catch (error) {
		console.error('Failed to get/update user location:', error);
		return null;
	}
};

export const deleteUserById = async (token: string, userId: string) =>
	webuiApiClient.del(`/users/${userId}`, null, { token });

export const updateUserById = async (token: string, userId: string, user: UserUpdateForm) =>
	webuiApiClient.post(
		`/users/${userId}/update`,
		{
			profile_image_url: user.profile_image_url,
			email: user.email,
			name: user.name,
			...(user.password !== '' && { password: user.password })
		},
		{ token }
	);
