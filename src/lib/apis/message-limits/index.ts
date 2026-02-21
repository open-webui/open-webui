import { WEBUI_API_BASE_URL } from '$lib/constants';

export interface MessageLimit {
	id: string;
	scope_type: 'system' | 'role' | 'user';
	role_id: string | null;
	user_id: string | null;
	max_messages_per_day: number;
	created_by: string | null;
	created_at: number;
	updated_at: number;
}

export interface MessageLimitForm {
	scope_type: 'system' | 'role' | 'user';
	role_id?: string | null;
	user_id?: string | null;
	max_messages_per_day: number;
}

export interface UserLimitStatus {
	effective_limit: number;
	used_today: number;
	remaining: number;
	resets_at: number;
	scope_source: string;
}

export const getMessageLimits = async (token: string): Promise<MessageLimit[]> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/message-limits/`, {
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
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const upsertMessageLimit = async (
	token: string,
	form: MessageLimitForm
): Promise<MessageLimit> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/message-limits/`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify(form)
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

export const deleteMessageLimit = async (token: string, limitId: string): Promise<boolean> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/message-limits/${limitId}`, {
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
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getMyLimitStatus = async (token: string): Promise<UserLimitStatus> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/message-limits/status`, {
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
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getUserLimitStatus = async (
	token: string,
	userId: string
): Promise<UserLimitStatus> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/message-limits/status/${userId}`, {
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
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};
