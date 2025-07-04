export interface McpCommand {
  type: 'widget';
  name: 'file-upload';
  // Add any other properties specific to the file-upload widget command
}

export const parseMcpCommand = (content: string): McpCommand | null => {
    try {
        // Use a regular expression to find a JSON object within the content.
        const jsonRegex = /({[\s\S]*})/;
        const match = content.match(jsonRegex);

        if (!match) {
            return null;
        }

        const jsonString = match[1];
        const parsed = JSON.parse(jsonString);

        if (
            typeof parsed === 'object' &&
            parsed !== null &&
            parsed.type === 'widget' &&
            parsed.name === 'file-upload'
        ) {
            return parsed as McpCommand;
        }
        return null;
    } catch (error) {
        // This will catch JSON parsing errors if the matched string is not valid JSON.
        // console.error('Error parsing MCP command:', error);
        return null;
    }
};
