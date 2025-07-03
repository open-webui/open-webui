// Helper function to extract tool name from MCP display name
const extractToolName = (displayName: string): string => {
	// If it starts with "MCP: ", remove that prefix
	if (displayName.startsWith('MCP: ')) {
		return displayName.substring(5);
	}
	return displayName;
};

// Helper function to get localized MCP tool descriptions
const getMCPToolDescription = (toolName: string, i18n: any): string => {
	// Extract the actual function name
	const actualToolName = extractToolName(toolName);

	// Map tool names to English descriptions (which serve as translation keys)
	const toolDescriptions: Record<string, string> = {
		get_current_time: 'Get current date and time in any timezone',
		get_top_headlines: 'Get latest news headlines from around the world'
	};

	const englishDescription = toolDescriptions[actualToolName];
	if (englishDescription) {
		const translated = i18n.t(englishDescription);
		return translated;
	}

	// Fallback to formatted tool name (short and clean)
	const fallback = actualToolName.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase());
	return fallback;
};

// Helper function to get localized MCP tool name
export const getMCPToolName = (toolName: string, i18n: any): string => {
	// Extract the actual function name
	const actualToolName = extractToolName(toolName);

	// Map tool names to English display names (which serve as translation keys)
	const toolNames: Record<string, string> = {
		get_current_time: 'MCP: Current Time',
		get_top_headlines: 'MCP: News Headlines'
	};

	const englishName = toolNames[actualToolName];
	if (englishName) {
		const translated = i18n.t(englishName);
		return translated;
	}

	// Fallback to formatted tool name with MCP prefix
	const fallback =
		'MCP: ' + actualToolName.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase());
	return fallback;
};

// Helper function to get display name for any tool
export const getToolDisplayName = (tool: any, i18n: any): string => {
	if (tool?.meta?.manifest?.is_mcp_tool) {
		// Use originalName (the actual function name) for translation lookup
		const toolNameForTranslation = tool.meta?.manifest?.original_name || tool.name;
		return getMCPToolName(toolNameForTranslation, i18n);
	}
	return tool.name;
};

// Helper function to get tooltip content for tools
export const getToolTooltipContent = (tool: any, i18n: any): string => {
	if (tool.isMcp) {
		// Use originalName (the actual function name) for translation lookup
		const toolNameForTranslation = tool.meta?.manifest?.original_name || tool.name;
		const localizedDescription = getMCPToolDescription(toolNameForTranslation, i18n);
		return localizedDescription;
	}
	return tool.originalDescription || '';
};
