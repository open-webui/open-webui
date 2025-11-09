import { WEBUI_API_BASE_URL } from '$lib/constants';

export type MCPPrompt = {
	name: string;
	description?: string;
	arguments?: Array<{
		name: string;
		description?: string;
		required?: boolean;
	}>;
	server_id: string;
	server_name: string;
	command: string;
};

export type MCPPromptContent = {
	name: string;
	description?: string;
	messages: Array<{
		role: string;
		content: string;
	}>;
	server_id: string;
};

export const getMCPPrompts = async (token: string = ''): Promise<MCPPrompt[]> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/mcp-prompts/`, {
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
			return [];
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getMCPPromptContent = async (
	token: string,
	serverId: string,
	promptName: string,
	promptArgs?: Record<string, any>
): Promise<MCPPromptContent> => {
	let error = null;

	const url = new URL(`${WEBUI_API_BASE_URL}/mcp-prompts/${serverId}/${promptName}`);
	if (promptArgs && Object.keys(promptArgs).length > 0) {
		url.searchParams.set('arguments', JSON.stringify(promptArgs));
	}

	const res = await fetch(url.toString(), {
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
