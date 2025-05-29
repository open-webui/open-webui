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
 * Executes a locally discovered MCPO tool operation.
 *
 * @param serverConfig The configuration of the MCPO server hosting the tool.
 * @param operationName The name (typically operationId) of the tool/operation to call.
 * @param toolArgs The arguments for the tool call, provided by the LLM.
 * @returns A promise that resolves to the tool's execution result.
 */
export async function executeLocalMcpoTool(
	serverConfig: LocalMcpoToolConfig,
	operationName: string,
	toolArgs: Record<string, any>
): Promise<ExecutionResult> {
	if (!serverConfig || !serverConfig.spec || !serverConfig.spec.paths) {
		const errorMsg = `Invalid server configuration provided for operation "${operationName}".`;
		console.error(errorMsg, serverConfig);
		toast.error(errorMsg);
		return { success: false, error: errorMsg };
	}

	let operationDetails: { path: string; method: string; operationSpec: any } | null = null;

	// Find the operation within the server's spec
	for (const pathRoute in serverConfig.spec.paths) {
		const pathItem = serverConfig.spec.paths[pathRoute];
		if (typeof pathItem !== 'object' || pathItem === null) continue;

		for (const httpMethod in pathItem) {
			const operation = pathItem[httpMethod];
			if (typeof operation !== 'object' || operation === null) continue;

			// Check if operationId matches, or if summary/description could be a fallback (though operationId is standard)
			if (operation.operationId === operationName) {
				operationDetails = {
					path: pathRoute,
					method: httpMethod.toLowerCase(),
					operationSpec: operation
				};
				break;
			}
		}
		if (operationDetails) break;
	}

	if (!operationDetails) {
		const errorMsg = `Operation "${operationName}" not found in the spec of server "${serverConfig.name}".`;
		console.error(errorMsg, serverConfig.spec);
		toast.error(errorMsg);
		return { success: false, error: errorMsg };
	}

	const operationPathKey = operationDetails.path;
	const operationMethodKey = operationDetails.method;
	
	// Extract the path prefix from the OpenAPI path (e.g., '/mcp_in_memory/openapi.json' -> '/mcp_in_memory')
	let pathPrefix = '';
	if (serverConfig.openapiPath) {
		const pathParts = serverConfig.openapiPath.split('/');
		// Remove the last part (openapi.json) and rejoin
		if (pathParts.length > 1 && pathParts[pathParts.length -1].endsWith('.json')) { // Ensure there's a file to remove
			pathPrefix = pathParts.slice(0, -1).join('/');
		} else if (pathParts.length > 0) { // Handle cases where openapiPath might just be a directory
            pathPrefix = serverConfig.openapiPath.endsWith('/') ? serverConfig.openapiPath.slice(0,-1) : serverConfig.openapiPath;
        }
	}
	
	const finalRequestUrl = `${serverConfig.baseUrl}${pathPrefix}${operationPathKey}`;
	console.log(`[executeLocalMcpoTool] Constructed URL: ${finalRequestUrl} (baseUrl: ${serverConfig.baseUrl}, pathPrefix: ${pathPrefix}, operationPath: ${operationPathKey})`);

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
