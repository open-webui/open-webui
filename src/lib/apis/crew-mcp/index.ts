import { WEBUI_API_BASE_URL, WEBUI_BASE_URL } from '$lib/constants';

export const getCrewMCPStatus = async (token: string = '') => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/crew-mcp/status`, {
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
			error = `CrewAI MCP: ${err?.detail ?? err?.error?.message ?? err?.message ?? 'Network Problem'}`;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getCrewMCPTools = async (token: string = '') => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/crew-mcp/tools`, {
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
			error = `CrewAI MCP: ${err?.detail ?? err?.error?.message ?? err?.message ?? 'Network Problem'}`;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const queryCrewMCP = async (
	token: string = '',
	query: string,
	model: string = '',
	selectedTools: string[] = [],
	chatId: string = '',
	sessionId: string = ''
) => {
	let error = null;

	// Create an AbortController with extended timeout for long-running MCP operations
	// SharePoint document analysis can take 120-180 seconds in production
	const controller = new AbortController();
	const timeoutId = setTimeout(() => controller.abort(), 240000); // 4 minutes timeout

	const res = await fetch(`${WEBUI_API_BASE_URL}/crew-mcp/query`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			query: query,
			model: model,
			selected_tools: selectedTools,
			chat_id: chatId,
			session_id: sessionId
		}),
		signal: controller.signal
	})
		.then(async (res) => {
			clearTimeout(timeoutId);
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			clearTimeout(timeoutId);
			if (err.name === 'AbortError') {
				error =
					'CrewAI MCP: Request timeout after 3 minutes. The analysis may be too complex or the SharePoint site has too many documents.';
			} else {
				error = `CrewAI MCP: ${err?.detail ?? err?.error?.message ?? err?.message ?? 'Network Problem'}`;
			}
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};
