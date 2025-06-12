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

export const queryCrewMCP = async (token: string = '', query: string, model: string = 'gpt-4o-mini') => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/crew-mcp/query`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			query: query,
			model: model
		})
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

// Function to check if user has selected MCP tools that should use CrewAI
export function shouldUseCrewMCP(selectedToolIds: string[], tools: any[]): boolean {
	console.log('Checking if user selected MCP tools for CrewAI:', selectedToolIds);
	
	if (!selectedToolIds || selectedToolIds.length === 0) {
		return false;
	}
	
	// Check if any selected tool is an MCP tool
	const hasMCPTools = selectedToolIds.some(toolId => {
		const tool = tools?.find(t => t.id === toolId);
		const isMCP = tool?.meta?.manifest?.is_mcp_tool || 
					  tool?.name?.includes('get_current_time') || 
					  tool?.id?.includes('mcp_') ||
					  tool?.description?.toLowerCase().includes('mcp');
		console.log(`Tool ${toolId}: isMCP = ${isMCP}`, tool);
		return isMCP;
	});
	
	console.log('Has MCP tools selected:', hasMCPTools);
	return hasMCPTools;
}
