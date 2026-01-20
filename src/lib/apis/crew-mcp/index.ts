import { WEBUI_API_BASE_PATH } from '$lib/constants';
import { get } from 'svelte/store';
import { socket } from '$lib/stores';
import type { Socket } from 'socket.io-client';
import canchatAPI from '$lib/apis/canchatAPI';

export const getCrewMCPStatus = async (token: string = '') => {
	let error = null;

	const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/crew-mcp/status`, {
		method: 'GET'
	})
		.then(async (res) => {
			return res.data;
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

	const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/crew-mcp/tools`, {
		method: 'GET'
	})
		.then(async (res) => {
			return res.data;
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
	const timeoutId = setTimeout(() => controller.abort(), 600000); // 10 minutes timeout

	const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/crew-mcp/query`, {
		method: 'POST',
		data: {
			query: query,
			model: model,
			selected_tools: selectedTools,
			chat_id: chatId,
			session_id: sessionId
		},
		signal: controller.signal
	})
		.then(async (res) => {
			clearTimeout(timeoutId);
			return res.data;
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

export const queryCrewMCPWebSocket = async (
	query: string,
	model: string = '',
	selectedTools: string[] = [],
	chatId: string = '',
	onStatus?: (message: string) => void
): Promise<{ result: string; tools_used: string[]; success: boolean }> => {
	return new Promise((resolve, reject) => {
		const _socket = get(socket) as Socket | null;

		if (!_socket || !_socket.connected) {
			reject(new Error('WebSocket not connected'));
			return;
		}

		// Set up timeout (10 minutes for very long operations)
		const timeoutId = setTimeout(() => {
			_socket.off('crew-mcp-status');
			_socket.off('crew-mcp-result');
			_socket.off('crew-mcp-error');
			reject(new Error('CrewAI MCP: Request timeout after 10 minutes'));
		}, 600000);

		// Listen for status updates
		const statusHandler = (data: { status: string; message: string }) => {
			console.log('CrewMCP status:', data);
			if (onStatus) {
				onStatus(data.message);
			}
		};

		// Listen for result
		const resultHandler = (data: { result: string; tools_used: string[]; success: boolean }) => {
			clearTimeout(timeoutId);
			_socket.off('crew-mcp-status', statusHandler);
			_socket.off('crew-mcp-result', resultHandler);
			_socket.off('crew-mcp-error', errorHandler);
			resolve(data);
		};

		// Listen for errors
		const errorHandler = (data: { error: string; code?: number }) => {
			clearTimeout(timeoutId);
			_socket.off('crew-mcp-status', statusHandler);
			_socket.off('crew-mcp-result', resultHandler);
			_socket.off('crew-mcp-error', errorHandler);
			reject(new Error(`CrewAI MCP: ${data.error}`));
		};

		_socket.on('crew-mcp-status', statusHandler);
		_socket.on('crew-mcp-result', resultHandler);
		_socket.on('crew-mcp-error', errorHandler);

		// Emit query
		_socket.emit('crew-mcp-query', {
			query: query,
			model: model,
			selected_tools: selectedTools,
			chat_id: chatId
		});
	});
};
