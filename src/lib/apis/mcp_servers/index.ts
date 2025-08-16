import { WEBUI_API_BASE_URL } from '$lib/constants';

export type MCPServerStatus = 'connected' | 'disconnected' | 'error' | 'connecting';

export interface MCPServerForm {
	name: string;
	http_url: string;
	headers?: Record<string, string>;
	oauth_config?: any;
	access_control?: Record<string, any>;
}

export interface MCPServerUpdateForm {
	name?: string;
	http_url?: string;
	headers?: Record<string, string>;
	oauth_config?: any;
	access_control?: Record<string, any>;
	is_active?: boolean;
}

export interface MCPServerModel {
	id: string;
	user_id: string;
	name: string;
	connection_type: 'http_stream';
	http_url: string;
	headers?: Record<string, string>;
	oauth_config?: any;
	oauth_tokens?: Record<string, string>;
	token_expires_at?: number;
	status: MCPServerStatus;
	last_connected_at?: number;
	error_message?: string;
	capabilities?: Record<string, any>;
	available_tools?: Array<Record<string, any>>;
	is_active: boolean;
	created_at: number;
	updated_at: number;
	access_control?: Record<string, any>;
}

export interface MCPServerUserResponse {
	id: string;
	name: string;
	status: MCPServerStatus;
	capabilities?: Record<string, any>;
	is_active: boolean;
	is_public: boolean;
}

export interface MCPServerTestRequest {
	http_url: string;
	headers?: Record<string, string>;
}

export interface MCPServerTestResponse {
	success: boolean;
	message: string;
	tools?: Array<Record<string, any>>;
}

class MCPServersAPI {
	private baseUrl: string;

	constructor(baseUrl: string = WEBUI_API_BASE_URL) {
		this.baseUrl = baseUrl;
	}

	async getMCPServers(token: string): Promise<MCPServerUserResponse[]> {
		const res = await fetch(`${this.baseUrl}/mcp-servers/`, {
			method: 'GET',
			headers: {
				'Content-Type': 'application/json',
				Authorization: `Bearer ${token}`
			}
		});

		if (!res.ok) {
			throw new Error(`Failed to get MCP servers: ${res.statusText}`);
		}

		return res.json();
	}

	async getAllMCPServers(token: string): Promise<MCPServerModel[]> {
		const res = await fetch(`${this.baseUrl}/mcp-servers/admin`, {
			method: 'GET',
			headers: {
				'Content-Type': 'application/json',
				Authorization: `Bearer ${token}`
			}
		});

		if (!res.ok) {
			throw new Error(`Failed to get all MCP servers: ${res.statusText}`);
		}

		return res.json();
	}

	async getMCPServerById(token: string, serverId: string): Promise<MCPServerModel> {
		const res = await fetch(`${this.baseUrl}/mcp-servers/${serverId}`, {
			method: 'GET',
			headers: {
				'Content-Type': 'application/json',
				Authorization: `Bearer ${token}`
			}
		});

		if (!res.ok) {
			throw new Error(`Failed to get MCP server: ${res.statusText}`);
		}

		return res.json();
	}

	async createMCPServer(token: string, server: MCPServerForm): Promise<MCPServerModel> {
		const res = await fetch(`${this.baseUrl}/mcp-servers/`, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json',
				Authorization: `Bearer ${token}`
			},
			body: JSON.stringify(server)
		});

		if (!res.ok) {
			let errorMessage = `HTTP ${res.status}: Failed to create MCP server`;
			try {
				const errorData = await res.json();
				if (errorData.detail) {
					// Handle both string and object detail formats
					if (typeof errorData.detail === 'string') {
						errorMessage = `HTTP ${res.status}: ${errorData.detail}`;
					} else {
						errorMessage = `HTTP ${res.status}: ${errorData.detail.message || res.statusText}`;
					}
				} else {
					errorMessage = `HTTP ${res.status}: ${res.statusText}`;
				}
			} catch (e) {
				// If we can't parse the error response, use the status text
				errorMessage = `HTTP ${res.status}: ${res.statusText}`;
			}
			throw new Error(errorMessage);
		}

		return res.json();
	}

	async updateMCPServer(
		token: string,
		serverId: string,
		server: MCPServerUpdateForm
	): Promise<MCPServerModel> {
		const res = await fetch(`${this.baseUrl}/mcp-servers/${serverId}`, {
			method: 'PUT',
			headers: {
				'Content-Type': 'application/json',
				Authorization: `Bearer ${token}`
			},
			body: JSON.stringify(server)
		});

		if (!res.ok) {
			let errorMessage = `HTTP ${res.status}: Failed to update MCP server`;
			try {
				const errorData = await res.json();
				if (errorData.detail) {
					errorMessage = `HTTP ${res.status}: ${errorData.detail}`;
				}
			} catch (e) {
				errorMessage = `HTTP ${res.status}: ${res.statusText}`;
			}
			throw new Error(errorMessage);
		}

		// Gracefully handle empty/204 responses by not forcing JSON parsing
		try {
			const text = await res.text();
			if (!text) {
				return {} as unknown as MCPServerModel;
			}
			return JSON.parse(text);
		} catch (_) {
			return {} as unknown as MCPServerModel;
		}
	}

	async toggleMCPServer(
		token: string,
		serverId: string
	): Promise<{ success: boolean; message: string; is_active: boolean }> {
		const res = await fetch(`${this.baseUrl}/mcp-servers/${serverId}/toggle`, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json',
				Authorization: `Bearer ${token}`
			}
		});

		if (!res.ok) {
			throw new Error(`Failed to toggle MCP server: ${res.statusText}`);
		}

		return res.json();
	}

	async deleteMCPServer(token: string, serverId: string): Promise<{ success: boolean }> {
		const res = await fetch(`${this.baseUrl}/mcp-servers/${serverId}`, {
			method: 'DELETE',
			headers: {
				'Content-Type': 'application/json',
				Authorization: `Bearer ${token}`
			}
		});

		if (!res.ok) {
			throw new Error(`Failed to delete MCP server: ${res.statusText}`);
		}

		return res.json();
	}

	async testMCPServer(
		token: string,
		serverId: string
	): Promise<{
		success: boolean;
		error_type?: string;
		message?: string;
		challenge_type?: string;
		server_id?: string;
		server_name?: string;
		instructions?: string;
	}> {
		const res = await fetch(`${this.baseUrl}/mcp-servers/${serverId}/test`, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json',
				Authorization: `Bearer ${token}`
			}
		});

		// Handle both success and error responses uniformly
		try {
			const responseData = await res.json();
			
			if (!res.ok) {
				// If it's a structured error (like auth challenges), return it directly
				if (responseData.detail && typeof responseData.detail === 'object') {
					return responseData.detail;
				}
				// For non-structured errors, create a structured response
				const message = responseData.detail || responseData.message || res.statusText;
				const errorMsg = `HTTP ${res.status}: ${message}`;
				return {
					success: false,
					message: errorMsg
				};
			}
			
			// Success response
			return responseData;
		} catch (parseError) {
			// If we can't parse JSON, return structured error
			return {
				success: false,
				message: `HTTP ${res.status}: ${res.statusText}`
			};
		}
	}

	async testMCPServerConfig(
		token: string,
		config: MCPServerTestRequest
	): Promise<MCPServerTestResponse> {
		const res = await fetch(`${this.baseUrl}/mcp-servers/test`, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json',
				Authorization: `Bearer ${token}`
			},
			body: JSON.stringify(config)
		});

		if (!res.ok) {
			throw new Error(`Failed to test MCP server config: ${res.statusText}`);
		}

		return res.json();
	}

	async getUserMCPServers(token: string): Promise<MCPServerUserResponse[]> {
		const res = await fetch(`${this.baseUrl}/mcp-servers/user`, {
			method: 'GET',
			headers: {
				'Content-Type': 'application/json',
				Authorization: `Bearer ${token}`
			}
		});

		if (!res.ok) {
			throw new Error(`Failed to get user MCP servers: ${res.statusText}`);
		}

		return res.json();
	}



	async syncServerTools(
		token: string,
		serverId: string
	): Promise<{
		success: boolean;
		message: string;
		error_type?: string;
		challenge_type?: string;
		server_id?: string;
		server_name?: string;
		instructions?: string;
	}> {
		const res = await fetch(`${this.baseUrl}/mcp-servers/${serverId}/sync-tools`, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json',
				Authorization: `Bearer ${token}`
			}
		});

		if (!res.ok) {
			// Try to get structured error response from backend
			try {
				const errorData = await res.json();
				// If it's a structured error (like auth challenges), preserve it
				if (errorData.detail && typeof errorData.detail === 'object') {
					// Return the structured error response for special handling
					return errorData.detail;
				}
				// Otherwise throw a proper error with status info
				const message = errorData.detail || errorData.message || res.statusText;
				throw new Error(`HTTP ${res.status}: ${message}`);
			} catch (parseError) {
				// If we can't parse JSON, throw with status code
				throw new Error(`HTTP ${res.status}: ${res.statusText}`);
			}
		}

		return res.json();
	}

	async syncSingleTool(
		token: string,
		serverId: string,
		toolName: string
	): Promise<{ success: boolean; message: string }> {
		const res = await fetch(
			`${this.baseUrl}/mcp-servers/${serverId}/tools/${encodeURIComponent(toolName)}/sync`,
			{
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: `Bearer ${token}`
				}
			}
		);

		if (!res.ok) {
			throw new Error(`Failed to sync tool: ${res.statusText}`);
		}

		return res.json();
	}
}

export const mcpServersApi = new MCPServersAPI();
export default mcpServersApi;

// Batch sync removed: no scheduler/admin batch sync in app; keep per-server sync only.

