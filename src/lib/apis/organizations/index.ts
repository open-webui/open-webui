import { WEBUI_API_BASE_URL } from '$lib/constants';

//////////////////////////
// Client Organizations API
//////////////////////////

export const getOpenRouterClientSettings = async (token: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/client_organizations/settings`, {
		method: 'GET',
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
		.catch((err) => {
			console.log(err);
			error = err.detail ?? 'Server connection failed';
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const updateOpenRouterClientSettings = async (token: string, settings: object) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/client_organizations/settings`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify(settings)
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.log(err);
			error = err.detail ?? 'Server connection failed';
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getClientOrganizations = async (token: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/client_organizations/clients`, {
		method: 'GET',
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
		.catch((err) => {
			console.log(err);
			error = err.detail ?? 'Server connection failed';
			return null;
		});

	if (error) {
		throw error;
	}

	return res || [];
};

export const createClientOrganization = async (token: string, clientData: object) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/client_organizations/clients`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify(clientData)
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.log(err);
			error = err.detail ?? 'Server connection failed';
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const updateClientOrganization = async (token: string, clientId: string, updates: object) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/client_organizations/clients/${clientId}`, {
		method: 'PATCH',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify(updates)
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.log(err);
			error = err.detail ?? 'Server connection failed';
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const deactivateClientOrganization = async (token: string, clientId: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/client_organizations/clients/${clientId}`, {
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
		.catch((err) => {
			console.log(err);
			error = err.detail ?? 'Server connection failed';
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getUserMappings = async (token: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/client_organizations/user-mappings`, {
		method: 'GET',
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
		.catch((err) => {
			console.log(err);
			error = err.detail ?? 'Server connection failed';
			return null;
		});

	if (error) {
		throw error;
	}

	return res || [];
};

export const createUserMapping = async (token: string, mappingData: object) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/client_organizations/user-mappings`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify(mappingData)
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.log(err);
			error = err.detail ?? 'Server connection failed';
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const deactivateUserMapping = async (token: string, userId: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/client_organizations/user-mappings/${userId}`, {
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
		.catch((err) => {
			console.log(err);
			error = err.detail ?? 'Server connection failed';
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getClientUsageSummary = async (token: string, clientId?: string) => {
	let error = null;

	// Use the my-organization endpoint for regular users
	const url = clientId 
		? `${WEBUI_API_BASE_URL}/client_organizations/usage/summary?client_id=${clientId}`
		: `${WEBUI_API_BASE_URL}/client_organizations/usage/my-organization`;

	const res = await fetch(url, {
		method: 'GET',
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
		.catch((err) => {
			console.log(err);
			error = err.detail ?? 'Server connection failed';
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getTodayUsage = async (token: string, clientId: string) => {
	let error = null;

	// Use the my-organization endpoint for 'current' client ID
	const url = clientId === 'current'
		? `${WEBUI_API_BASE_URL}/client_organizations/usage/my-organization/today`
		: `${WEBUI_API_BASE_URL}/client_organizations/usage/today?client_id=${clientId}`;

	const res = await fetch(url, {
		method: 'GET',
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
		.catch((err) => {
			console.log(err);
			error = err.detail ?? 'Server connection failed';
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getBillingSummary = async (token: string, daysBack: number = 30) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/client_organizations/usage/billing?days_back=${daysBack}`, {
		method: 'GET',
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
		.catch((err) => {
			console.log(err);
			error = err.detail ?? 'Server connection failed';
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getUsageByUser = async (token: string, clientId: string, startDate?: string, endDate?: string) => {
	let error = null;
	let url = `${WEBUI_API_BASE_URL}/client-organizations/usage/by-user/${clientId}`;
	
	const params = new URLSearchParams();
	if (startDate) params.append('start_date', startDate);
	if (endDate) params.append('end_date', endDate);
	if (params.toString()) url += `?${params.toString()}`;

	const res = await fetch(url, {
		method: 'GET',
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
		.catch((err) => {
			console.log(err);
			error = err.detail ?? 'Failed to fetch user usage';
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getUsageByModel = async (token: string, clientId: string, startDate?: string, endDate?: string) => {
	let error = null;
	let url = `${WEBUI_API_BASE_URL}/client-organizations/usage/by-model/${clientId}`;
	
	const params = new URLSearchParams();
	if (startDate) params.append('start_date', startDate);
	if (endDate) params.append('end_date', endDate);
	if (params.toString()) url += `?${params.toString()}`;

	const res = await fetch(url, {
		method: 'GET',
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
		.catch((err) => {
			console.log(err);
			error = err.detail ?? 'Failed to fetch model usage';
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};