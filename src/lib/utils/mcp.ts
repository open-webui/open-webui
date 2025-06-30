export interface McpCommand {
  type: 'widget';
  name: 'file-upload';
  // Add any other properties specific to the file-upload widget command
}

export const parseMcpCommand = (content: string): McpCommand | null => {
  try {
    const trimmedContent = content.trim();
    if (!trimmedContent.startsWith('{') || !trimmedContent.endsWith('}')) {
      return null;
    }
    const parsed = JSON.parse(trimmedContent);

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
    console.error('Error parsing MCP command:', error);
    return null;
  }
};
