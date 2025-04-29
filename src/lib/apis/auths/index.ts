import { WEBUI_API_BASE_URL } from '$lib/constants';

export const getAdminDetails = async (token: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/auths/admin/details`, {
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

export const getAdminConfig = async (token: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/auths/admin/config`, {
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

export const updateAdminConfig = async (token: string, body: object) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/auths/admin/config`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify(body)
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

export const getSessionUser = async (token: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/auths/`, {
		method: 'GET',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		credentials: 'include'
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

export const ldapUserSignIn = async (user: string, password: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/auths/ldap`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json'
		},
		credentials: 'include',
		body: JSON.stringify({
			user: user,
			password: password
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

export const getLdapConfig = async (token: string = '') => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/auths/admin/config/ldap`, {
		method: 'GET',
		headers: {
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
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

export const updateLdapConfig = async (token: string = '', enable_ldap: boolean) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/auths/admin/config/ldap`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		},
		body: JSON.stringify({
			enable_ldap: enable_ldap
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

export const getLdapServer = async (token: string = '') => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/auths/admin/config/ldap/server`, {
		method: 'GET',
		headers: {
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
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

export const updateLdapServer = async (token: string = '', body: object) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/auths/admin/config/ldap/server`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		},
		body: JSON.stringify(body)
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

export const userSignIn = async (email: string, password: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/auths/signin`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json'
		},
		credentials: 'include',
		body: JSON.stringify({
			email: email,
			password: password
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

export const userSignUp = async (
	name: string,
	email: string,
	password: string,
	profile_image_url: string
) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/auths/signup`, {
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

export const completeInvite = async (
	firstName: string,
	lastName: string,
	password: string,
	inviteToken: string,
	profileImageUrl: string
) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/auths/complete_invite`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json'
		},
		credentials: 'include',
		body: JSON.stringify({
			first_name: firstName,
			last_name: lastName,
			password: password,
			invite_token: inviteToken,
			profile_image_url: profileImageUrl.length ? profileImageUrl : null
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
}

export const userSignOut = async () => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/auths/signout`, {
		method: 'GET',
		headers: {
			'Content-Type': 'application/json'
		},
		credentials: 'include'
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res;
		})
		.catch((err) => {
			console.log(err);
			error = err.detail;
			return null;
		});

	if (error) {
		throw error;
	}
};

export const addUser = async (
	token: string,
	first_name: string,
	last_name: string,
	email: string,
	role: string = 'pending'
) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/auths/add`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		},
		body: JSON.stringify({
			first_name: first_name,
			last_name: last_name,
			email: email,
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

export const inviteUser = async (
	token: string,
	email: string,
	role: string = 'pending'
) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/users/invite`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		},
		body: JSON.stringify({
			email: email,
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

export const updateUserProfile = async (token: string, firstName: string, profileImageUrl: string, lastName: string, email: string, password: string | null) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/auths/update/profile`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		},
		body: JSON.stringify({
			first_name: firstName,
			profile_image_url: profileImageUrl,
			last_name: lastName,
			email: email,
			password: password,
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

export const deleteUserProfile = async (token: string, userId: string) => {
	let error = null;
	const res = await fetch(`${WEBUI_API_BASE_URL}/auths/delete/profile`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		},
		body: JSON.stringify({
			user_id: userId
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

}

export const updateUserPassword = async (token: string, password: string, newPassword: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/auths/update/password`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		},
		body: JSON.stringify({
			password: password,
			new_password: newPassword
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

export const getSignUpEnabledStatus = async (token: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/auths/signup/enabled`, {
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

export const getDefaultUserRole = async (token: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/auths/signup/user/role`, {
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

export const updateDefaultUserRole = async (token: string, role: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/auths/signup/user/role`, {
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

export const toggleSignUpEnabledStatus = async (token: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/auths/signup/enabled/toggle`, {
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

export const getJWTExpiresDuration = async (token: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/auths/token/expires`, {
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

export const updateJWTExpiresDuration = async (token: string, duration: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/auths/token/expires/update`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			duration: duration
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

export const createAPIKey = async (token: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/auths/api-key`, {
		method: 'POST',
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
	return res.api_key;
};

export const getAPIKey = async (token: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/auths/api-key`, {
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
	return res.api_key;
};

export const deleteAPIKey = async (token: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/auths/api-key`, {
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

export const requestPasswordReset = async (email: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/auths/reset-password/request`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json'
		},
		body: JSON.stringify({
			email: email
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

export const confirmPasswordReset = async (resetToken: string, newPassword: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/auths/reset-password/confirm`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json'
		},
		body: JSON.stringify({
			reset_token: resetToken,
			new_password: newPassword
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
