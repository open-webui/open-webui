import { WEBUI_API_BASE_URL } from '$lib/constants';

export interface OversightUser {
	id: string;
	name: string;
	email: string;
	role: string;
	groups: { id: string; name: string }[];
}

export interface OversightChat {
	id: string;
	title: string;
	updated_at: number;
	created_at: number;
}

export interface OversightGroup {
	id: string;
	name: string;
	description: string;
	member_count: number;
}

export interface GroupExclusion {
	id: string;
	group_id: string;
	user_id: string;
	created_at: number;
}

export const getOversightUsers = async (token: string): Promise<OversightUser[] | null> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/oversight/users`, {
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

export const getOversightUserChats = async (
	token: string,
	userId: string,
	skip: number = 0,
	limit: number = 50
): Promise<OversightChat[] | null> => {
	let error = null;

	const searchParams = new URLSearchParams();
	searchParams.append('skip', String(skip));
	searchParams.append('limit', String(limit));

	const res = await fetch(
		`${WEBUI_API_BASE_URL}/oversight/users/${userId}/chats?${searchParams.toString()}`,
		{
			method: 'GET',
			headers: {
				Accept: 'application/json',
				'Content-Type': 'application/json',
				authorization: `Bearer ${token}`
			}
		}
	)
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

export const getOversightGroups = async (token: string): Promise<OversightGroup[] | null> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/oversight/groups`, {
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

export const getGroupExclusions = async (
	token: string,
	groupId: string
): Promise<GroupExclusion[] | null> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/oversight/groups/id/${groupId}/exclusions`, {
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

export const addGroupExclusion = async (
	token: string,
	groupId: string,
	userId: string
): Promise<GroupExclusion | null> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/oversight/groups/id/${groupId}/exclusions`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify({ user_id: userId })
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

export const removeGroupExclusion = async (
	token: string,
	groupId: string,
	userId: string
): Promise<boolean | null> => {
	let error = null;

	const res = await fetch(
		`${WEBUI_API_BASE_URL}/oversight/groups/id/${groupId}/exclusions/${userId}`,
		{
			method: 'DELETE',
			headers: {
				Accept: 'application/json',
				'Content-Type': 'application/json',
				authorization: `Bearer ${token}`
			}
		}
	)
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

export const setGroupMemberRole = async (
	token: string,
	groupId: string,
	userId: string,
	role: string
): Promise<boolean | null> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/groups/id/${groupId}/members/${userId}/role`, {
		method: 'PUT',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify({ role })
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
