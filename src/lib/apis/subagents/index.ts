import { SUBAGENTS_API_BASE_URL } from '$lib/constants';

export type SubagentsConfig = {
	ENABLE_SUBAGENTS: boolean;
	SUBAGENT_DEFAULT_MODEL: string;
	SUBAGENT_SYSTEM_PROMPT: string;
	SUBAGENT_SYSTEM_PROMPT_APPEND: string;
	SUBAGENT_PARENT_PROMPT: string;
	// Empty string = let the model use its own default. Otherwise one of
	// minimal / low / medium / high / xhigh (or any provider-specific value).
	SUBAGENT_DEFAULT_REASONING_EFFORT: string;
	// Empty string = don't send a `service_tier` field (provider uses its own
	// default). Otherwise: any string the chosen provider accepts (e.g.
	// `default`, `flex`, `priority`). Per-chat `chat.params.subagentServiceTier`
	// overrides this when set.
	SUBAGENT_DEFAULT_SERVICE_TIER: string;
};

export type SubagentsConfigUpdate = Partial<SubagentsConfig>;

export const getSubagentsConfig = async (token: string): Promise<SubagentsConfig> => {
	let error: any = null;

	const res = await fetch(`${SUBAGENTS_API_BASE_URL}/config`, {
		method: 'GET',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		}
	})
		.then(async (r) => {
			if (!r.ok) throw await r.json();
			return r.json();
		})
		.catch((err) => {
			console.error(err);
			error = err?.detail ?? err;
			return null;
		});

	if (error) {
		throw error;
	}

	return res as SubagentsConfig;
};

export const updateSubagentsConfig = async (
	token: string,
	payload: SubagentsConfigUpdate
): Promise<SubagentsConfig> => {
	let error: any = null;

	const res = await fetch(`${SUBAGENTS_API_BASE_URL}/config/update`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify({ ...payload })
	})
		.then(async (r) => {
			if (!r.ok) throw await r.json();
			return r.json();
		})
		.catch((err) => {
			console.error(err);
			error = err?.detail ?? err;
			return null;
		});

	if (error) {
		throw error;
	}

	return res as SubagentsConfig;
};

export type SubagentRerunScope = 'this_turn' | 'from_launch';

export type SubagentRerunPayload = {
	parent_chat_id: string;
	parent_message_id: string;
	session_id: string;
	entry_key: string;
	scope: SubagentRerunScope;
};

/**
 * Trigger a user-initiated rerun of a subagent turn. The backend kicks the
 * actual rerun off as a background task; live progress streams back through
 * the same `chat:subagent:update` socket events the original launch used,
 * so the SubagentBlock refreshes in place — no need to poll or block here.
 */
export const rerunSubagent = async (
	token: string,
	payload: SubagentRerunPayload
): Promise<{ status: boolean }> => {
	let error: any = null;

	const res = await fetch(`${SUBAGENTS_API_BASE_URL}/rerun`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify({ ...payload })
	})
		.then(async (r) => {
			if (!r.ok) throw await r.json();
			return r.json();
		})
		.catch((err) => {
			console.error(err);
			error = err?.detail ?? err;
			return null;
		});

	if (error) {
		throw error;
	}

	return res as { status: boolean };
};
