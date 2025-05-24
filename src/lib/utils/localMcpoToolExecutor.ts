import { get } from 'svelte/store';
import { localMcpoTools } from '$lib/stores';
import type { LocalMcpoToolConfig, OpenAPISpec } from '$lib/types/tools';
import { toast } from 'svelte-sonner';

interface ExecutionResult {
	success: boolean;
	data?: any;
	error?: string;
}

/**
 * Executes a locally discovered MCPO tool.
 *
 * @param toolCallId The ID or name of the tool as determined by the LLM.
 * @param toolArgs The arguments for the tool call, provided by the LLM.
 * @returns A promise that resolves to the tool's execution result.
 */
export async function executeLocalMcpoTool(
	toolCallId: string,
	toolArgs: Record<string, any>
): Promise<ExecutionResult> {
	const tools = get(localMcpoTools);
	// Find tool by operationId, as data.name from backend event is the operationId
	const toolConfig = tools.find((t) => t.operationId === toolCallId);

	if (!toolConfig) {
		const errorMsg = `Local MCPO tool "${toolCallId}" not found or not enabled.`;
		console.error(errorMsg);
		toast.error(errorMsg);
		return { success: false, error: errorMsg };
	}

	const operationPathKey = toolConfig.pathKey;
	const operationMethodKey = toolConfig.methodKey.toLowerCase();
	const finalRequestUrl = `${toolConfig.baseUrl}${operationPathKey}`;

	try {
		const requestOptions: RequestInit = {
			method: operationMethodKey.toUpperCase(),
			headers: {
				'Content-Type': 'application/json',
				Accept: 'application/json',
				'Authorization': 'Bearer top-secret' // Add the API key here
			}
		};

		if (operationMethodKey === 'get') {
			const queryParams = new URLSearchParams();
			if (toolArgs) {
				for (const key in toolArgs) {
					queryParams.append(key, toolArgs[key]);
				}
			}
			const queryString = queryParams.toString();
			const urlForGet = queryString ? `${finalRequestUrl}?${queryString}` : finalRequestUrl;
			const response = await fetch(urlForGet, requestOptions);
			const responseData = await response.json();
			console.log('MCPO Tool GET Response:', responseData); // Simplified log
			return { success: response.ok, data: responseData, error: response.ok ? undefined : response.statusText };
		} else if (['post', 'put', 'patch'].includes(operationMethodKey)) {
			requestOptions.body = JSON.stringify(toolArgs);
			const response = await fetch(finalRequestUrl, requestOptions);
			const responseData = await response.json();
			console.log('MCPO Tool POST/PUT/PATCH Response:', responseData); // Simplified log
			return { success: response.ok, data: responseData, error: response.ok ? undefined : response.statusText };
		} else {
			console.error('Unsupported HTTP method:', operationMethodKey);
			return { success: false, error: 'Unsupported HTTP method' };
		}
	} catch (error: any) {
		console.error('MCPO Tool Fetch Error:', error); // Simplified error log
		return { success: false, error: error.message || 'Unknown fetch error' };
	}
}
