import { WEBUI_API_BASE_URL } from '$lib/constants';

export interface ProlificAuthRequest {
	prolific_pid: string;
	study_id: string;
	session_id: string;
	name?: string;
}

export interface ProlificAuthResponse {
	token: string;
	user: {
		id: string;
		name: string;
		email: string;
		role: string;
		prolific_pid?: string;
		study_id?: string;
		current_session_id?: string;
		session_number: number;
	};
	session_number: number;
	is_new_user: boolean;
    new_child_id?: string | null;
    has_exit_quiz?: boolean;
}

export interface SessionInfo {
	prolific_pid?: string;
	study_id?: string;
	current_session_id?: string;
	session_number: number;
	is_prolific_user: boolean;
}

export interface AvailableScenariosResponse {
	available_scenarios: number[];
	total_seen: number;
	total_available: number;
	session_number: number;
}

export const authenticateWithProlific = async (
	prolificPid: string,
	studyId: string,
	sessionId: string,
	name?: string
): Promise<ProlificAuthResponse> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/prolific/auth`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json'
		},
		body: JSON.stringify({
			prolific_pid: prolificPid,
			study_id: studyId,
			session_id: sessionId,
			...(name && { name })
		})
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			error = err.detail || err.message || 'Authentication failed';
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getCurrentSession = async (token: string): Promise<SessionInfo> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/workflow/session-info`, {
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
			console.error(err);
			error = err.detail || err.message || 'Failed to get session info';
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getAvailableScenarios = async (
	token: string,
	childId: string
): Promise<AvailableScenariosResponse> => {
	let error = null;

	const res = await fetch(
		`${WEBUI_API_BASE_URL}/moderation/scenarios/available?child_id=${encodeURIComponent(childId)}`,
		{
			method: 'GET',
			headers: {
				'Content-Type': 'application/json',
				...(token && { authorization: `Bearer ${token}` })
			}
		}
	)
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			error = err.detail || err.message || 'Failed to get available scenarios';
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};
