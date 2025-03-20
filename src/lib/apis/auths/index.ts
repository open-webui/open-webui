import { WEBUI_API_BASE_URL } from "$lib/constants";

export const getAdminDetails = async (token: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/auths/admin/details`, {
		method: "GET",
		headers: {
			"Content-Type": "application/json",
			Authorization: `Bearer ${token}`,
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

export const getAdminConfig = async (token: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/auths/admin/config`, {
		method: "GET",
		headers: {
			"Content-Type": "application/json",
			Authorization: `Bearer ${token}`,
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

export const updateAdminConfig = async (token: string, body: object) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/auths/admin/config`, {
		method: "POST",
		headers: {
			"Content-Type": "application/json",
			Authorization: `Bearer ${token}`,
		},
		body: JSON.stringify(body),
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

export const getSessionUser = async () => {
	console.log("[DEBUG] getSessionUser: Starting session user retrieval");
	const token = localStorage.getItem("token");
	if (!token) {
		console.error("[DEBUG] getSessionUser: No token found in localStorage");
		throw new Error("No token found");
	}

	console.log("[DEBUG] getSessionUser: Token exists, length:", token.length);
	console.log(
		"[DEBUG] getSessionUser: Making request to:",
		`${WEBUI_API_BASE_URL}/auths/userinfo`,
	);

	try {
		const response = await fetch(`${WEBUI_API_BASE_URL}/auths/userinfo`, {
			method: "GET",
			headers: {
				"Content-Type": "application/json",
				Authorization: `Bearer ${token}`,
			},
		});

		console.log("[DEBUG] getSessionUser: Response status:", response.status);
		console.log(
			"[DEBUG] getSessionUser: Response status text:",
			response.statusText,
		);
		console.log(
			"[DEBUG] getSessionUser: Response headers:",
			Object.fromEntries([...response.headers]),
		);

		if (response.status === 401 || !response.ok) {
			console.error(
				"[DEBUG] getSessionUser: Unauthorized or invalid response",
				response.status,
			);
			localStorage.removeItem("token"); // Clear invalid token
			throw new Error("Unauthorized access or invalid response");
		}

		// Get the raw text first to debug JSON parsing issues
		const rawText = await response.text();
		console.log(
			"[DEBUG] getSessionUser: Raw response length:",
			rawText?.length || 0,
		);
		console.log(
			"[DEBUG] getSessionUser: Raw response first 200 chars:",
			rawText?.substring(0, 200),
		);

		if (!rawText || rawText.trim() === "") {
			console.error("[DEBUG] getSessionUser: Empty response received");
			throw new Error("Empty response received from server");
		}

		// Check if response is HTML (common in production with proxies/gateways)
		if (
			rawText.trim().toLowerCase().startsWith("<!doctype") ||
			rawText.trim().toLowerCase().startsWith("<html")
		) {
			console.error(
				"[DEBUG] getSessionUser: HTML response received instead of JSON",
			);
			console.error(
				"[DEBUG] getSessionUser: HTML content:",
				rawText.substring(0, 500),
			);

			// Clear token as it may be invalid
			localStorage.removeItem("token");

			throw new Error(
				"Authentication error: Server returned HTML instead of JSON. This typically happens when there is a proxy or authentication portal in the way.",
			);
		}

		let userData;
		try {
			// Check if it's a valid JSON format
			if (rawText.trim().startsWith("{") || rawText.trim().startsWith("[")) {
				console.log(
					"[DEBUG] getSessionUser: Response appears to be JSON, parsing...",
				);
				userData = JSON.parse(rawText);
				console.log("[DEBUG] getSessionUser: Parsed user data successfully");
			} else {
				console.error(
					"[DEBUG] getSessionUser: Response is not JSON format. First char:",
					rawText.trim().charAt(0),
				);
				console.error(
					"[DEBUG] getSessionUser: Raw text first 20 chars codes:",
					rawText
						.substring(0, 20)
						.split("")
						.map((c) => c.charCodeAt(0)),
				);
				throw new Error("Server returned an invalid response format");
			}
		} catch (parseError: any) {
			console.error(
				"[DEBUG] getSessionUser: JSON parse error:",
				parseError.message,
			);
			console.error(
				"[DEBUG] getSessionUser: Error position:",
				parseError.message.match(/position (\d+)/)?.[1],
			);

			// If there's a position in the error, show the problematic part of the text
			const position = parseError.message.match(/position (\d+)/)?.[1];
			if (position) {
				const pos = parseInt(position, 10);
				console.error("[DEBUG] getSessionUser: Text around error:", {
					before: rawText.substring(Math.max(0, pos - 20), pos),
					errorChar: rawText.substring(pos, pos + 1),
					after: rawText.substring(pos + 1, pos + 21),
				});
			}

			throw new Error(`Failed to parse user data: ${parseError.message}`);
		}

		return userData;
	} catch (error: any) {
		console.error(
			"[DEBUG] getSessionUser: Error fetching user data:",
			error.message,
		);
		throw error;
	}
};

export const ldapUserSignIn = async (user: string, password: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/auths/ldap`, {
		method: "POST",
		headers: {
			"Content-Type": "application/json",
		},
		body: JSON.stringify({
			user: user,
			password: password,
		}),
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			const data = await res.json();
			if (data.token) {
				localStorage.setItem("token", data.token);
			}
			return data;
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

export const getLdapConfig = async (token: string = "") => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/auths/admin/config/ldap`, {
		method: "GET",
		headers: {
			"Content-Type": "application/json",
			...(token && { authorization: `Bearer ${token}` }),
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

export const updateLdapConfig = async (
	token: string = "",
	enable_ldap: boolean,
) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/auths/admin/config/ldap`, {
		method: "POST",
		headers: {
			"Content-Type": "application/json",
			...(token && { authorization: `Bearer ${token}` }),
		},
		body: JSON.stringify({
			enable_ldap: enable_ldap,
		}),
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

export const getLdapServer = async (token: string = "") => {
	let error = null;

	const res = await fetch(
		`${WEBUI_API_BASE_URL}/auths/admin/config/ldap/server`,
		{
			method: "GET",
			headers: {
				"Content-Type": "application/json",
				...(token && { authorization: `Bearer ${token}` }),
			},
		},
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

export const updateLdapServer = async (token: string = "", body: object) => {
	let error = null;

	const res = await fetch(
		`${WEBUI_API_BASE_URL}/auths/admin/config/ldap/server`,
		{
			method: "POST",
			headers: {
				"Content-Type": "application/json",
				...(token && { authorization: `Bearer ${token}` }),
			},
			body: JSON.stringify(body),
		},
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

export const userSignIn = async (email: string, password: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/auths/signin`, {
		method: "POST",
		headers: {
			"Content-Type": "application/json",
		},
		body: JSON.stringify({
			email: email,
			password: password,
		}),
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			const data = await res.json();
			if (data.token) {
				localStorage.setItem("token", data.token);
				localStorage.setItem("auth_type", data.auth_type || "regular");
			}
			return data;
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
	profile_image_url: string,
) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/auths/signup`, {
		method: "POST",
		headers: {
			"Content-Type": "application/json",
		},
		body: JSON.stringify({
			name: name,
			email: email,
			password: password,
			profile_image_url: profile_image_url,
		}),
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			const data = await res.json();
			if (data.token) {
				localStorage.setItem("token", data.token);
			}
			return data;
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

export const userSignOut = async () => {
	let error = null;
	const authType = localStorage.getItem("auth_type") || "regular";

	const res = await fetch(`${WEBUI_API_BASE_URL}/auths/prepare-logout`, {
		method: "GET",
		headers: {
			"Content-Type": "application/json",
			Authorization: `Bearer ${localStorage.getItem("token")}`,
		},
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.log("error signing out: ", err);
			error = err.detail;
			return null;
		});

	if (error) {
		throw error;
	}

	// If the response is a redirect (for OAuth logout) and we're using pro-connect
	if (res?.url && authType === "pro-connect") {
		window.location.href = res.url;
		return;
	}

	// Clear all auth-related data from localStorage
	localStorage.removeItem("token");
	localStorage.removeItem("auth_type");
	localStorage.removeItem("locale");

	// Clear session storage
	sessionStorage.clear();

	// Clear specific auth-related cookies
	const cookieOptions =
		"path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT; SameSite=Strict";
	document.cookie = `token=;${cookieOptions}`;
	document.cookie = `session=;${cookieOptions}`;

	// Clear all other cookies efficiently
	const cookies = document.cookie.split("; ");
	for (const cookie of cookies) {
		const [name] = cookie.split("=");
		document.cookie = `${name}=;${cookieOptions}`;
	}
};

export const addUser = async (
	token: string,
	name: string,
	email: string,
	password: string,
	role: string = "pending",
) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/auths/add`, {
		method: "POST",
		headers: {
			"Content-Type": "application/json",
			...(token && { authorization: `Bearer ${token}` }),
		},
		body: JSON.stringify({
			name: name,
			email: email,
			password: password,
			role: role,
		}),
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

export const updateUserProfile = async (
	token: string,
	name: string,
	profileImageUrl: string,
) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/auths/update/profile`, {
		method: "POST",
		headers: {
			"Content-Type": "application/json",
			...(token && { authorization: `Bearer ${token}` }),
		},
		body: JSON.stringify({
			name: name,
			profile_image_url: profileImageUrl,
		}),
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

export const updateUserPassword = async (
	token: string,
	password: string,
	newPassword: string,
) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/auths/update/password`, {
		method: "POST",
		headers: {
			"Content-Type": "application/json",
			...(token && { authorization: `Bearer ${token}` }),
		},
		body: JSON.stringify({
			password: password,
			new_password: newPassword,
		}),
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
		method: "GET",
		headers: {
			"Content-Type": "application/json",
			Authorization: `Bearer ${token}`,
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

export const getDefaultUserRole = async (token: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/auths/signup/user/role`, {
		method: "GET",
		headers: {
			"Content-Type": "application/json",
			Authorization: `Bearer ${token}`,
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

export const updateDefaultUserRole = async (token: string, role: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/auths/signup/user/role`, {
		method: "POST",
		headers: {
			"Content-Type": "application/json",
			Authorization: `Bearer ${token}`,
		},
		body: JSON.stringify({
			role: role,
		}),
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
		method: "GET",
		headers: {
			"Content-Type": "application/json",
			Authorization: `Bearer ${token}`,
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

export const getJWTExpiresDuration = async (token: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/auths/token/expires`, {
		method: "GET",
		headers: {
			"Content-Type": "application/json",
			Authorization: `Bearer ${token}`,
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

export const updateJWTExpiresDuration = async (
	token: string,
	duration: string,
) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/auths/token/expires/update`, {
		method: "POST",
		headers: {
			"Content-Type": "application/json",
			Authorization: `Bearer ${token}`,
		},
		body: JSON.stringify({
			duration: duration,
		}),
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

	const res = await fetch(`${WEBUI_API_BASE_URL}/auths/api_key`, {
		method: "POST",
		headers: {
			"Content-Type": "application/json",
			Authorization: `Bearer ${token}`,
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
	return res.api_key;
};

export const getAPIKey = async (token: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/auths/api_key`, {
		method: "GET",
		headers: {
			"Content-Type": "application/json",
			Authorization: `Bearer ${token}`,
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
	return res.api_key;
};

export const deleteAPIKey = async (token: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/auths/api_key`, {
		method: "DELETE",
		headers: {
			"Content-Type": "application/json",
			Authorization: `Bearer ${token}`,
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
