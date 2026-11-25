import type { AgentModel } from '$lib/stores';
import { WEBUI_API_BASE_URL } from '$lib/constants';
import { extractInputVariables } from '$lib/utils';

export type AutomationMachineConfig = {
	server_id: string;
	cwd?: string;
};

export type AutomationTarget = {
	type: 'chat' | 'channel';
	channel_id?: string | null;
	/** Off: every run continues one chat, which the first run creates (chat_id is set by the server). */
	new_chat?: boolean;
	chat_id?: string | null;
	/** Off: every run continues one channel thread, which the first run starts (thread_id is set by the server). */
	new_thread?: boolean;
	thread_id?: string | null;
	/** Off: the reply posts in the channel instead of under the run's message. An ongoing thread always replies in it. */
	reply_in_thread?: boolean;
};

/** Whether each run starts a new chat (or channel thread); targets saved before the option existed do. */
export const startsNew = (target?: AutomationTarget | null) =>
	(target?.type === 'channel' ? target?.new_thread : target?.new_chat) !== false;

/** Whether a channel run's reply goes in a thread; targets saved before the option existed do. */
export const repliesInThread = (target?: AutomationTarget | null) =>
	target?.reply_in_thread !== false;

export type AutomationWebhook = {
	/** Set by the server. */
	token?: string | null;
	allow_get?: boolean;
};

export type AutomationData = {
	prompt: string;
	model_id: string;
	/** Empty: no schedule. */
	rrule: string;
	machine?: AutomationMachineConfig;
	terminal?: AutomationMachineConfig; // former name of machine, on automations saved before the rename
	target?: AutomationTarget | null;
	webhook?: AutomationWebhook | null;
};

// Filled by the server, not the Run form.
const BUILTIN_VARIABLE = /^(CURRENT_[A-Z_]+|USER_[A-Z_]+|CLIPBOARD)$/;

/** The prompt's input variables a manual run asks for. */
export const getRunVariables = (prompt: string): Record<string, any> =>
	Object.fromEntries(
		Object.entries(extractInputVariables(prompt)).filter(([name]) => !BUILTIN_VARIABLE.test(name))
	);

export const getAutomationHookUrl = (automation: { id: string; data: AutomationData }) =>
	automation.data.webhook?.token
		? `${window.location.origin}${WEBUI_API_BASE_URL}/automations/hooks/${automation.id}/${automation.data.webhook.token}`
		: '';

export type AutomationForm = {
	name: string;
	folder_id?: string | null;
	data: AutomationData;
	meta?: {
		system_prompt?: string;
		temperature?: number;
		max_tokens?: number;
		webhook?: string;
	};
	is_active?: boolean;
};

export type AutomationRunModel = {
	id: string;
	automation_id: string;
	chat_id: string | null;
	status: string;
	error: string | null;
	created_at: number;
};

export type AutomationResponse = {
	id: string;
	user_id: string;
	folder_id: string | null;
	name: string;
	data: AutomationData;
	meta: Record<string, any> | null;
	is_active: boolean;
	last_run_at: number | null;
	next_run_at: number | null;

	created_at: number;
	updated_at: number;
	last_run: AutomationRunModel | null;
	next_runs: number[] | null;

	/** The owner, as on workspace items. */
	user?: { id: string; name: string; role: string; email: string } | null;
	/** Rename, reschedule, pause and run. What a run does stays the owner's: it runs as them. */
	write_access?: boolean | null;
	/** For the owner or an admin. */
	access_grants?:
		| { id?: string; principal_type: string; principal_id: string; permission: string }[]
		| null;
};

export const updateAutomationAccessGrants = async (
	token: string,
	id: string,
	accessGrants: any[]
): Promise<AutomationResponse> => {
	const res = await fetch(`${WEBUI_API_BASE_URL}/automations/${id}/access/update`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify({ access_grants: accessGrants })
	});
	if (!res.ok) throw (await res.json())?.detail ?? res.statusText;
	return res.json();
};

export const getAutomationModels = async (
	token: string,
	machineId: string,
	cwd: string,
	automationId?: string
): Promise<AgentModel[]> => {
	const query = new URLSearchParams({ machine_id: machineId });
	if (cwd) query.set('cwd', cwd);
	if (automationId) query.set('automation_id', automationId);
	const response = await fetch(`${WEBUI_API_BASE_URL}/automations/models?${query}`, {
		headers: { authorization: `Bearer ${token}` }
	});
	if (!response.ok) throw await response.json();
	return response.json();
};

export const getAutomationItems = async (
	token: string,
	query: string | null,
	status: string | null,
	page: number,
	folder_id?: string | null,
	/** 'all' is yours plus those shared with you directly. */
	view: 'all' | 'mine' | 'shared' = 'all'
): Promise<{ items: AutomationResponse[]; total: number }> => {
	let error = null;

	const searchParams = new URLSearchParams();
	if (query) {
		searchParams.append('query', query);
	}
	if (view !== 'all') {
		searchParams.append('view', view);
	}
	if (status && status !== 'all') {
		searchParams.append('status', status);
	}
	if (page) {
		searchParams.append('page', page.toString());
	}
	if (folder_id !== undefined && folder_id !== null) {
		searchParams.append('folder_id', folder_id);
	}

	const res = await fetch(`${WEBUI_API_BASE_URL}/automations/list?${searchParams.toString()}`, {
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

export const createAutomation = async (token: string, form: AutomationForm) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/automations/create`, {
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

export const getAutomationById = async (token: string, id: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/automations/${id}`, {
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

export const updateAutomationById = async (token: string, id: string, form: AutomationForm) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/automations/${id}/update`, {
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

export const toggleAutomationById = async (token: string, id: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/automations/${id}/toggle`, {
		method: 'POST',
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

export const runAutomationById = async (
	token: string,
	id: string,
	variables?: Record<string, any>
) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/automations/${id}/run`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		...(variables ? { body: JSON.stringify({ variables }) } : {})
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

export const regenerateAutomationToken = async (token: string, id: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/automations/${id}/token/regenerate`, {
		method: 'POST',
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

export const deleteAutomationById = async (token: string, id: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/automations/${id}/delete`, {
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

export const getAutomationRuns = async (
	token: string,
	id: string,
	skip: number = 0,
	limit: number = 50,
	direction: 'asc' | 'desc' = 'desc'
) => {
	let error = null;

	const res = await fetch(
		`${WEBUI_API_BASE_URL}/automations/${id}/runs?skip=${skip}&limit=${limit}&direction=${direction}`,
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

/** An automation listed in a folder, with what the viewer may do with it. */
export type FolderAutomation = AutomationResponse & {
	user_name: string;
	can_edit: boolean;
	can_manage: boolean;
};

export const getFolderAutomations = async (
	token: string,
	folderId: string
): Promise<FolderAutomation[]> => {
	const res = await fetch(
		`${WEBUI_API_BASE_URL}/folders/${encodeURIComponent(folderId)}/automations`,
		{
			headers: {
				Accept: 'application/json',
				'Content-Type': 'application/json',
				authorization: `Bearer ${token}`
			}
		}
	);
	if (!res.ok) throw (await res.json().catch(() => ({})))?.detail ?? res.statusText;
	return res.json();
};
