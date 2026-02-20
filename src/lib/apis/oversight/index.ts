import { WEBUI_API_BASE_URL } from '$lib/constants';

export interface OversightTarget {
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

export interface OversightAssignment {
	id: string;
	overseer_id: string;
	target_id: string;
	created_by: string;
	created_at: number;
	source?: string;
}

export const getOversightTargets = async (token: string): Promise<OversightTarget[] | null> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/oversight/targets`, {
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

export const getOversightTargetChats = async (
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
		`${WEBUI_API_BASE_URL}/oversight/targets/${userId}/chats?${searchParams.toString()}`,
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

export const getOversightAssignments = async (
	token: string
): Promise<OversightAssignment[] | null> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/oversight/assignments`, {
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

export const createOversightAssignment = async (
	token: string,
	targetId: string,
	overseerId?: string,
	source?: string
): Promise<OversightAssignment | null> => {
	let error = null;

	const body: Record<string, string> = { target_id: targetId };
	if (overseerId) body.overseer_id = overseerId;
	if (source) body.source = source;

	const res = await fetch(`${WEBUI_API_BASE_URL}/oversight/assignments`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify(body)
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

export const deleteOversightAssignment = async (
	token: string,
	overseerId: string,
	targetId: string
): Promise<boolean | null> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/oversight/assignments/${overseerId}/${targetId}`, {
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

export const bulkAssignFromGroup = async (
	token: string,
	groupId: string,
	overseerId: string
): Promise<OversightAssignment[] | null> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/oversight/assignments/bulk`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify({ group_id: groupId, overseer_id: overseerId })
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
