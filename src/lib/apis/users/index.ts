import canchatAPI from '$lib/apis/canchatAPI';
import { WEBUI_API_BASE_PATH } from '$lib/constants';
import { getUserPosition } from '$lib/utils';

export const getUserGroups = async (token: string) => {
	let error = null;

	const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/users/groups`, {
		method: 'GET'
	})
		.then(async (res) => {
			return res.data;
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

export const getUserDefaultPermissions = async (token: string) => {
	let error = null;

	const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/users/default/permissions`, {
		method: 'GET'
	})
		.then(async (res) => {
			return res.data;
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

export const updateUserDefaultPermissions = async (token: string, permissions: object) => {
	let error = null;

	const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/users/default/permissions`, {
		method: 'POST',
		data: {
			...permissions
		}
	})
		.then(async (res) => {
			return res.data;
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

export const updateUserRole = async (token: string, id: string, role: string) => {
	let error = null;

	const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/users/update/role`, {
		method: 'POST',
		data: {
			id: id,
			role: role
		}
	})
		.then(async (res) => {
			return res.data;
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

export const getUsers = async (token: string) => {
	let error = null;

	const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/users/`, {
		method: 'GET'
	})
		.then(async (res) => {
			return res.data;
		})
		.catch((err) => {
			console.log(err);
			error = err.detail;
			return null;
		});

	if (error) {
		throw error;
	}

	return res ? res : [];
};

export const getUserSettings = async (token: string) => {
	let error = null;
	const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/users/user/settings`, {
		method: 'GET'
	})
		.then(async (res) => {
			return res.data;
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

export const updateUserSettings = async (token: string, settings: object) => {
	let error = null;

	const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/users/user/settings/update`, {
		method: 'POST',
		data: {
			...settings
		}
	})
		.then(async (res) => {
			return res.data;
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

// Timezone-specific helper functions
export const getUserTimezoneFromSettings = async (token: string): Promise<string | null> => {
	try {
		const settings = await getUserSettings(token);
		return settings?.timezone || null;
	} catch (error) {
		console.error('Failed to get user timezone from settings:', error);
		return null;
	}
};

export const updateUserTimezone = async (token: string, timezone: string) => {
	try {
		const currentSettings = await getUserSettings(token);
		const updatedSettings = {
			...currentSettings,
			timezone: timezone
		};
		return await updateUserSettings(token, updatedSettings);
	} catch (error) {
		console.error('Failed to update user timezone:', error);
		throw error;
	}
};

export const detectAndUpdateUserTimezone = async (token: string) => {
	try {
		// Get current user's timezone from browser
		const detectedTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone;

		// Get stored timezone preference
		const storedTimezone = await getUserTimezoneFromSettings(token);

		// Update only if timezone has changed or is not set
		if (!storedTimezone || storedTimezone !== detectedTimezone) {
			await updateUserTimezone(token, detectedTimezone);
			console.log(`Updated user timezone to: ${detectedTimezone}`);
		}

		return detectedTimezone;
	} catch (error) {
		console.error('Failed to detect and update user timezone:', error);
		// Return Toronto timezone as default for Canadian users
		return 'America/Toronto';
	}
};

export const getUserById = async (token: string, userId: string) => {
	let error = null;

	const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/users/${userId}`, {
		method: 'GET'
	})
		.then(async (res) => {
			return res.data;
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

export const getUserInfo = async (token: string) => {
	let error = null;
	const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/users/user/info`, {
		method: 'GET'
	})
		.then(async (res) => {
			return res.data;
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

export const getUserRole = async (token: string) => {
	let error = null;
	const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/users/user/role`, {
		method: 'GET'
	})
		.then(async (res) => {
			return res.data;
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

export const updateUserInfo = async (token: string, info: object) => {
	let error = null;

	const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/users/user/info/update`, {
		method: 'POST',
		data: {
			...info
		}
	})
		.then(async (res) => {
			return res.data;
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

export const getAndUpdateUserLocation = async (token: string) => {
	const location = await getUserPosition().catch((err) => {
		throw err;
	});

	if (location) {
		await updateUserInfo(token, { location: location });
		return location;
	} else {
		throw new Error('Failed to get user location');
	}
};

export const deleteUserById = async (token: string, userId: string) => {
	let error = null;

	const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/users/${userId}`, {
		method: 'DELETE'
	})
		.then(async (res) => {
			return res.data;
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

type UserUpdateForm = {
	profile_image_url: string;
	email: string;
	name: string;
	password: string;
};

export const updateUserById = async (token: string, userId: string, user: UserUpdateForm) => {
	let error = null;

	const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/users/${userId}/update`, {
		method: 'POST',
		data: {
			profile_image_url: user.profile_image_url,
			email: user.email,
			name: user.name,
			password: user.password !== '' ? user.password : undefined
		}
	})
		.then(async (res) => {
			return res.data;
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
