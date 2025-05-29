import { localMcpoTools } from '$lib/stores';
import type { LocalMcpoToolConfig, OpenAPISpec } from '$lib/types/tools';
import { toast } from 'svelte-sonner';

export const DEFAULT_MCPO_BASE_URL = 'http://localhost:8000'; // Export this constant
const LOCAL_MCPO_ENABLED_STATES_KEY = 'localMcpoToolEnabledStates';

/**
 * Parses the info.description field of an MCPO OpenAPI spec to find sub-tool paths.
 * Assumes sub-tool paths are listed in the description, e.g.,
 * "Proxied MCP services available at: /tool1/openapi.json, /tool2/openapi.json"
 * or simply listed as paths: "/tool1/openapi.json", "/tool2/openapi.json".
 * @param description The description string from openapi.info.description
 * @returns An array of sub-tool OpenAPI paths.
 */
function parseSubToolPathsFromDescription(description: string): string[] {
	if (!description) {
		return [];
	}

	const markdownLinkRegex = /\[[^\]]+\]\(([^)]+)\)/g; // Regex to find markdown links and capture the path
	const openApiPaths: string[] = [];
	let match;

	// First, try to parse markdown links
	while ((match = markdownLinkRegex.exec(description)) !== null) {
		let path = match[1]; // The captured path, e.g., /time/docs

		if (path.endsWith('/docs')) {
			openApiPaths.push(path.replace(/\/docs$/, '/openapi.json'));
		} else if (path.endsWith('/openapi.json')) {
			// If the link directly points to an openapi.json
			openApiPaths.push(path);
		} else {
			// Log paths that don't fit the expected patterns for markdown links
			console.warn(`Markdown link path does not end in /docs or /openapi.json: ${path}`);
		}
	}

	// Second, as a fallback or for non-markdown plain paths, look for direct openapi.json paths
	// This ensures that if the description contains direct paths not in markdown, they are also found.
	const directPathRegex = /(\/[a-zA-Z0-9_-]+(?:[a-zA-Z0-9_-]+\/)*openapi\.json)/g;
	let directMatch;
	while ((directMatch = directPathRegex.exec(description)) !== null) {
		// Add only if not already captured through markdown links to avoid duplicates
		if (!openApiPaths.includes(directMatch[0])) {
			openApiPaths.push(directMatch[0]);
		}
	}
	
	return Array.from(new Set(openApiPaths)); // Return unique paths found
}

/**
 * Fetches and processes the main MCPO OpenAPI specification and any sub-tool specs.
 * Updates the localMcpoTools store with discovered tools.
 */
export async function discoverLocalMcpoTools(): Promise<void> {
	const mainOpenApiPath = `${DEFAULT_MCPO_BASE_URL}/openapi.json`;
	let discoveredTools: LocalMcpoToolConfig[] = [];

	try {
		console.log(`Attempting to discover local MCPO tools at ${mainOpenApiPath}`);
		const response = await fetch(mainOpenApiPath);

		if (!response.ok) {
			if (response.status === 404) {
				console.info(`Local MCPO server not found at ${mainOpenApiPath} (404). This is not necessarily an error.`);
			} else {
				console.error(`Failed to fetch main MCPO OpenAPI spec from ${mainOpenApiPath}. Status: ${response.status}`);
				toast.error(`Error connecting to local MCPO server: ${response.statusText} (${response.status})`);
			}
			localMcpoTools.set([]); // Clear any existing tools if discovery fails
			return;
		}

		const mainSpec = (await response.json()) as OpenAPISpec;
		console.log('Successfully fetched main MCPO OpenAPI spec:', mainSpec);

		const subToolPaths = parseSubToolPathsFromDescription(mainSpec.info?.description ?? '');
		let processedTools: LocalMcpoToolConfig[] = [];

		if (subToolPaths.length > 0) {
			console.log('Found sub-tool paths in description, processing them:', subToolPaths);
			const toolPromises = subToolPaths.map(async (subPath) => {
				const toolSpecUrl = `${DEFAULT_MCPO_BASE_URL}${subPath}`;
				try {
					const toolResponse = await fetch(toolSpecUrl);
					if (!toolResponse.ok) {
						console.error(`Failed to fetch sub-tool spec from ${toolSpecUrl}. Status: ${toolResponse.status}`);
						toast.warning(`Failed to load MCPO tool: ${subPath.split('/')[1] || subPath}`);
						return null;
					}
					const toolSpec = (await toolResponse.json()) as OpenAPISpec;
					return {
						id: `${DEFAULT_MCPO_BASE_URL}${subPath}`, 
						name: toolSpec.info?.title || subPath.split('/')[1] || 'Unnamed SubTool',
						baseUrl: DEFAULT_MCPO_BASE_URL,
						openapiPath: subPath,
						spec: toolSpec,
						enabled: true 
					} as LocalMcpoToolConfig;
				} catch (error) {
					console.error(`Error fetching/parsing sub-tool spec from ${toolSpecUrl}:`, error);
					toast.error(`Error loading MCPO tool spec: ${subPath}`);
					return null;
				}
			});
			processedTools = (await Promise.all(toolPromises)).filter((tool): tool is LocalMcpoToolConfig => tool !== null);
		} else if (mainSpec.paths && Object.keys(mainSpec.paths).length > 0 && (Object.keys(mainSpec.paths).length > 1 || !mainSpec.paths['/'])) {
			// No sub-tools in description. Check if mainSpec.paths defines operations directly.
			// An actual tool path would not typically be just '/' for an operation.
			// Filter out common server root paths if they don't look like tool operations.
			const potentiallyToolPaths = Object.entries(mainSpec.paths).filter(([path]) => path !== '/');

			if (potentiallyToolPaths.length > 0) {
				console.log('No sub-tool paths in description. Parsing operations from mainSpec.paths.');
				for (const [pathKey, pathItemObject] of potentiallyToolPaths) {
					if (typeof pathItemObject !== 'object' || pathItemObject === null) continue;

					for (const methodKey of Object.keys(pathItemObject)) {
						const operationObject = pathItemObject[methodKey];
						if (typeof operationObject !== 'object' || operationObject === null || ['get', 'post', 'put', 'delete', 'patch', 'options', 'head', 'trace'].indexOf(methodKey.toLowerCase()) === -1) {
							continue; // Skip if not a valid HTTP method or operationObject is invalid
						}

						const operationSummary = operationObject.summary || '';
						const operationId = operationObject.operationId || '';
						const toolName = operationSummary || operationId || `${methodKey.toUpperCase()} ${pathKey}`;
						
						// Ensure a name is present, fallback if both summary and operationId are empty
						const finalToolName = toolName.trim() === '' ? `Operation: ${methodKey.toUpperCase()} ${pathKey}` : toolName;

						const toolConfig: LocalMcpoToolConfig = {
							id: `${DEFAULT_MCPO_BASE_URL}/openapi.json${pathKey}_${methodKey}`, // Unique ID for the operation
							name: finalToolName,
							baseUrl: DEFAULT_MCPO_BASE_URL,
							openapiPath: '/openapi.json', // Source is the main spec
							spec: mainSpec, // The whole mainSpec is the context
							enabled: true, // Default to enabled
							pathKey: pathKey,
							methodKey: methodKey.toLowerCase(),
							operationId: operationId || undefined
						};
						processedTools.push(toolConfig);
					}
				}
			} else {
				console.log('No sub-tool paths found in description, and main spec paths are empty or non-specific for tools.');
			}
		}

		// Load enabled states from localStorage and apply them
		if (processedTools.length > 0) {
			try {
				const storedStatesRaw = localStorage.getItem(LOCAL_MCPO_ENABLED_STATES_KEY);
				if (storedStatesRaw) {
					const storedStates: Record<string, boolean> = JSON.parse(storedStatesRaw);
					discoveredTools = processedTools.map(tool => {
						if (storedStates.hasOwnProperty(tool.id)) {
							return { ...tool, enabled: storedStates[tool.id] };
						}
						// If tool.id from a single tool spec changed due to new ID generation,
						// old localStorage state might not match. This is a limitation.
						// A more robust ID generation or migration would be needed for existing states.
						return tool; 
					});
				} else {
					discoveredTools = processedTools; // No stored states, use as is
				}
			} catch (e) {
				console.error('Failed to parse local MCPO tool enabled states from localStorage:', e);
				discoveredTools = processedTools; // Fallback to defaults
			}
		} else {
			discoveredTools = [];
		}

		if (discoveredTools.length > 0) {
			console.log('Discovered local MCPO tools:', discoveredTools);
			toast.success(`Discovered ${discoveredTools.length} local MCPO tool(s).`);
		} else {
			console.log('No local MCPO tools discovered or loaded.');
			// toast.info('No local MCPO tools found.'); // Potentially too noisy
		}
		localMcpoTools.set(discoveredTools);

	} catch (error) {
		console.error('Error during local MCPO tool discovery:', error);
		if (error instanceof TypeError && error.message.includes('fetch')) {
			// This typically means localhost refused connection (server not running)
			console.info(`Local MCPO server likely not running at ${DEFAULT_MCPO_BASE_URL}.`);
		} else {
			toast.error('An unexpected error occurred while discovering local MCPO tools.');
		}
		localMcpoTools.set([]); // Clear tools on error
	}
}
