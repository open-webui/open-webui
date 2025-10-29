import { WEBUI_API_BASE_URL } from '$lib/constants';

export interface ChildProfile {
	id: string;
	user_id: string;
	name: string;
	child_age?: string;
	child_gender?: string;
	child_characteristics?: string;
	parenting_style?: string;
	// New optional research fields
	is_only_child?: boolean;
	child_has_ai_use?: 'yes' | 'no' | 'unsure';
	child_ai_use_contexts?: string[];
	parent_llm_monitoring_level?: 'active_rules' | 'occasional_guidance' | 'plan_to' | 'no_monitoring' | 'prefer_not_to_say';
	created_at: number;
	updated_at: number;
}

export interface ChildProfileForm {
	name: string;
	child_age?: string;
	child_gender?: string;
	child_characteristics?: string;
	parenting_style?: string;
	// New optional research fields
	is_only_child?: boolean;
	child_has_ai_use?: 'yes' | 'no' | 'unsure';
	child_ai_use_contexts?: string[];
	parent_llm_monitoring_level?: 'active_rules' | 'occasional_guidance' | 'plan_to' | 'no_monitoring' | 'prefer_not_to_say';
}

export const getChildProfiles = async (token: string = '') => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/child-profiles`, {
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

export const getChildProfileById = async (token: string = '', profileId: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/child-profiles/${profileId}`, {
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

export const createChildProfile = async (token: string = '', formData: ChildProfileForm) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/child-profiles`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify(formData)
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			if ('detail' in err) {
				error = err.detail;
			} else {
				error = err;
			}
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const updateChildProfile = async (
	token: string = '',
	profileId: string,
	formData: ChildProfileForm
) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/child-profiles/${profileId}`, {
		method: 'PUT',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify(formData)
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			if ('detail' in err) {
				error = err.detail;
			} else {
				error = err;
			}
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const deleteChildProfile = async (token: string = '', profileId: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/child-profiles/${profileId}`, {
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
			console.error(err);
			if ('detail' in err) {
				error = err.detail;
			} else {
				error = err;
			}
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};
