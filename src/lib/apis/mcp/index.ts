/**
 * MCP Apps API Client.
 *
 * Provides functions for fetching UI resources and calling tools
 * through the MCP backend.
 */

import { WEBUI_API_BASE_URL } from '$lib/constants';
import type { MCPAppResource, MCPToolResult } from '$lib/types/mcpApps';

/**
 * Read a UI resource from an MCP server.
 *
 * @param token - Auth token
 * @param serverId - MCP server ID
 * @param uri - Resource URI (ui://...)
 * @returns The fetched resource
 */
export const readResource = async (
	token: string,
	serverId: string,
	uri: string
): Promise<MCPAppResource> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/mcp/resource`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			server_id: serverId,
			uri: uri
		})
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			error = err.detail || err.message || 'Failed to fetch resource';
			return null;
		});

	if (error) {
		throw error;
	}

	return res.resource;
};

/**
 * Call a tool on an MCP server (from app context).
 *
 * @param token - Auth token
 * @param serverId - MCP server ID
 * @param toolName - Name of the tool to call
 * @param args - Tool arguments
 * @returns Tool result in MCP content format
 */
export const callTool = async (
	token: string,
	serverId: string,
	toolName: string,
	args: Record<string, unknown> = {}
): Promise<MCPToolResult> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/mcp/tool/call`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			server_id: serverId,
			tool_name: toolName,
			arguments: args
		})
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			error = err.detail || err.message || 'Failed to call tool';
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

/**
 * Get MCP Apps configuration.
 *
 * @param token - Auth token
 * @returns MCP Apps config with enabled state
 */
export const getMcpAppsConfig = async (token: string): Promise<{ enabled: boolean }> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/configs/mcp_apps`, {
		method: 'GET',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			error = err.detail || err.message || 'Failed to get MCP Apps config';
			return null;
		});

	if (error) {
		throw error;
	}

	// Map backend field name to frontend format
	return { enabled: res.ENABLE_MCP_APPS };
};

/**
 * Set MCP Apps configuration.
 *
 * @param token - Auth token
 * @param config - MCP Apps config with enabled state
 * @returns Updated config
 */
export const setMcpAppsConfig = async (
	token: string,
	config: { enabled: boolean }
): Promise<{ enabled: boolean }> => {
	let error = null;

	// Map frontend field name to backend format
	const res = await fetch(`${WEBUI_API_BASE_URL}/configs/mcp_apps`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify({ ENABLE_MCP_APPS: config.enabled })
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			error = err.detail || err.message || 'Failed to set MCP Apps config';
			return null;
		});

	if (error) {
		throw error;
	}

	// Map backend field name to frontend format
	return { enabled: res.ENABLE_MCP_APPS };
};

/**
 * List resources from an MCP server.
 *
 * @param token - Auth token
 * @param serverId - MCP server ID
 * @returns List of resources
 */
export const listResources = async (
	token: string,
	serverId: string
): Promise<Array<{ uri: string; name?: string; description?: string; mimeType?: string }>> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/mcp/resources`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			server_id: serverId
		})
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			error = err.detail || err.message || 'Failed to list resources';
			return null;
		});

	if (error) {
		throw error;
	}

	return res.resources || [];
};

/**
 * List prompts from an MCP server.
 *
 * @param token - Auth token
 * @param serverId - MCP server ID
 * @returns List of prompts
 */
export const listPrompts = async (
	token: string,
	serverId: string
): Promise<Array<{ name: string; description?: string }>> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/mcp/prompts`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			server_id: serverId
		})
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			error = err.detail || err.message || 'Failed to list prompts';
			return null;
		});

	if (error) {
		throw error;
	}

	return res.prompts || [];
};
