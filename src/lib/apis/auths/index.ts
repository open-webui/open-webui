import { WEBUI_API_BASE_URL } from '$lib/constants';

async function apiRequest<T>(url: string, options: RequestInit): Promise<T> {
	try {
		const response = await fetch(url, options);
		if (!response.ok) {
			const errorData = await response.json();
			throw new Error(errorData?.detail ?? 'An error occurred');
		}
		return await response.json();
	} catch (error) {
		console.error('Request failed:', error);
		throw error;
	}
}

export const getAdminDetails = async (token: string) => {
	return await apiRequest(`${WEBUI_API_BASE_URL}/auths/admin/details`, {
		method: 'GET',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		}
	});
};

export const getAdminConfig = async (token: string) => {
	return await apiRequest(`${WEBUI_API_BASE_URL}/auths/admin/config`, {
		method: 'GET',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		}
	});
};

export const updateAdminConfig = async (token: string, body: object) => {
	return await apiRequest(`${WEBUI_API_BASE_URL}/auths/admin/config`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify(body)
	});
};

export const getSessionUser = async (token: string) => {
	return await apiRequest(`${WEBUI_API_BASE_URL}/auths/`, {
		method: 'GET',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		credentials: 'include'
	});
};

export const ldapUserSignIn = async (user: string, password: string) => {
	return await apiRequest(`${WEBUI_API_BASE_URL}/auths/ldap`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json'
		},
		credentials: 'include',
		body: JSON.stringify({
			user: user,
			password: password
		})
	});
};

export const getLdapConfig = async (token: string = '') => {
	return await apiRequest(`${WEBUI_API_BASE_URL}/auths/admin/config/ldap`, {
		method: 'GET',
		headers: {
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		}
	});
};

export const updateLdapConfig = async (token: string = '', enable_ldap: boolean) => {
	return await apiRequest(`${WEBUI_API_BASE_URL}/auths/admin/config/ldap`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		},
		body: JSON.stringify({
			enable_ldap: enable_ldap
		})
	});
};

export const getLdapServer = async (token: string = '') => {
	return await apiRequest(`${WEBUI_API_BASE_URL}/auths/admin/config/ldap/server`, {
		method: 'GET',
		headers: {
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		}
	});
};

export const updateLdapServer = async (token: string = '', body: object) => {
	return await fetch(`${WEBUI_API_BASE_URL}/auths/admin/config/ldap/server`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		},
		body: JSON.stringify(body)
	});
};

export const userSignIn = async (email: string, password: string) => {
	return await apiRequest(`${WEBUI_API_BASE_URL}/auths/signin`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json'
		},
		credentials: 'include',
		body: JSON.stringify({
			email: email,
			password: password
		})
	});
};

export const userSignUp = async (
	name: string,
	email: string,
	password: string,
	profile_image_url: string
) => {
	return await apiRequest(`${WEBUI_API_BASE_URL}/auths/signup`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json'
		},
		credentials: 'include',
		body: JSON.stringify({
			name: name,
			email: email,
			password: password,
			profile_image_url: profile_image_url
		})
	});
};

export const userSignOut = async () => {
	return await apiRequest(`${WEBUI_API_BASE_URL}/auths/signout`, {
		method: 'GET',
		headers: {
			'Content-Type': 'application/json'
		},
		credentials: 'include'
	});
};

export const addUser = async (
	token: string,
	name: string,
	email: string,
	password: string,
	role: string = 'pending'
) => {
	return await apiRequest(`${WEBUI_API_BASE_URL}/auths/add`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		},
		body: JSON.stringify({
			name: name,
			email: email,
			password: password,
			role: role
		})
	});
};

export const updateUserProfile = async (token: string, name: string, profileImageUrl: string) => {
	return await apiRequest(`${WEBUI_API_BASE_URL}/auths/update/profile`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		},
		body: JSON.stringify({
			name: name,
			profile_image_url: profileImageUrl
		})
	});
};

export const updateUserPassword = async (token: string, password: string, newPassword: string) => {
	return await apiRequest(`${WEBUI_API_BASE_URL}/auths/update/password`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		},
		body: JSON.stringify({
			password: password,
			new_password: newPassword
		})
	});
};

export const getSignUpEnabledStatus = async (token: string) => {
	return await apiRequest(`${WEBUI_API_BASE_URL}/auths/signup/enabled`, {
		method: 'GET',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		}
	});
};

export const getDefaultUserRole = async (token: string) => {
	return await apiRequest(`${WEBUI_API_BASE_URL}/auths/signup/user/role`, {
		method: 'GET',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		}
	});
};

export const updateDefaultUserRole = async (token: string, role: string) => {
	return await apiRequest(`${WEBUI_API_BASE_URL}/auths/signup/user/role`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			role: role
		})
	});
};

export const toggleSignUpEnabledStatus = async (token: string) => {
	return await apiRequest(`${WEBUI_API_BASE_URL}/auths/signup/enabled/toggle`, {
		method: 'GET',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		}
	});
};

export const getJWTExpiresDuration = async (token: string) => {
	return await apiRequest(`${WEBUI_API_BASE_URL}/auths/token/expires`, {
		method: 'GET',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		}
	});
};

export const updateJWTExpiresDuration = async (token: string, duration: string) => {
	return await apiRequest(`${WEBUI_API_BASE_URL}/auths/token/expires/update`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			duration: duration
		})
	});
};

export const createAPIKey = async (token: string) => {
	return await apiRequest(`${WEBUI_API_BASE_URL}/auths/api_key`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		}
	});
};

export const getAPIKey = async (token: string) => {
	return await apiRequest(`${WEBUI_API_BASE_URL}/auths/api_key`, {
		method: 'GET',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		}
	});
};

export const deleteAPIKey = async (token: string) => {
	return await apiRequest(`${WEBUI_API_BASE_URL}/auths/api_key`, {
		method: 'DELETE',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		}
	});
};
