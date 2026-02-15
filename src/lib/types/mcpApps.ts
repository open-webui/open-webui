/**
 * MCP Apps TypeScript types.
 *
 * These types define the state management and component props
 * for the MCP Apps extension in Open WebUI.
 */

/**
 * CSP configuration from resource metadata per MCP ext-apps spec.
 * @see https://github.com/modelcontextprotocol/ext-apps/blob/main/specification/2026-01-26/apps.mdx
 */
export interface McpUiResourceCsp {
	/** Origins for network requests (fetch/XHR/WebSocket) - maps to connect-src */
	connectDomains?: string[];
	/** Origins for static resources (scripts, images, styles, fonts) */
	resourceDomains?: string[];
	/** Origins for nested iframes - maps to frame-src */
	frameDomains?: string[];
	/** Allowed base URIs - maps to base-uri */
	baseUriDomains?: string[];
}

/**
 * UI resource fetched from MCP server.
 * Per MCP ext-apps spec: _meta.ui contains csp and permissions.
 */
export interface MCPAppResource {
	uri: string;
	content: string;
	mimeType: string;
	/** CSP configuration from resource _meta.ui.csp */
	csp?: McpUiResourceCsp;
	/** Permissions from resource _meta.ui.permissions */
	permissions?: MCPUIPermissions;
}

/**
 * Permissions for iframe capabilities.
 * Values are empty objects when enabled (not booleans).
 */
export interface MCPUIPermissions {
	camera?: Record<string, never>;
	microphone?: Record<string, never>;
	geolocation?: Record<string, never>;
	clipboardWrite?: Record<string, never>;
}

/**
 * Display mode for MCP App.
 */
export type MCPAppDisplayMode = 'inline' | 'fullscreen' | 'pip';

/**
 * State of an MCP App instance.
 */
export type MCPAppState = 'loading' | 'initializing' | 'ready' | 'error' | 'closed';

/**
 * MCP App instance managed by the store.
 */
export interface MCPAppInstance {
	/** Unique instance identifier */
	instanceId: string;

	/** MCP server ID */
	serverId: string;

	/** Tool that triggered this app */
	toolName: string;

	/** Fetched UI resource */
	resource: MCPAppResource;

	/** Current state */
	state: MCPAppState;

	/** Current display mode */
	displayMode: MCPAppDisplayMode;

	/** Current height (from app resize requests) */
	height: number;

	/** App-set title */
	title: string;

	/** Error message if state is 'error' */
	error?: string;

	/** Tool invocation ID for result correlation */
	toolCallId?: string | number;

	/** Timestamp of creation */
	createdAt: number;
}

/**
 * Props for MCPAppView component.
 */
export interface MCPAppViewProps {
	instanceId: string;
	resource: MCPAppResource;
	toolName: string;
	serverId: string;
	toolResult?: unknown;
	toolCallId?: string | number;
}

/**
 * Tool result in MCP content format.
 */
export interface MCPToolResult {
	content: Array<{
		type: 'text' | 'image' | 'audio';
		text?: string;
		data?: string;
		mimeType?: string;
	}>;
	structuredContent?: unknown;
	isError: boolean;
}

/**
 * Event emitted when app state changes.
 */
export interface MCPAppStateEvent {
	instanceId: string;
	state: MCPAppState;
	error?: string;
}

/**
 * Event emitted when app requests display mode change.
 */
export interface MCPAppDisplayModeEvent {
	instanceId: string;
	requestedMode: MCPAppDisplayMode;
	actualMode: MCPAppDisplayMode;
}

/**
 * Configuration for MCP Apps feature.
 */
export interface MCPAppsConfig {
	enabled: boolean;
}

/**
 * Build iframe allow attribute from permissions.
 * This is a helper for when SDK's buildAllowAttribute is not available.
 */
export function buildAllowAttribute(permissions?: MCPUIPermissions): string {
	if (!permissions) return '';

	const allows: string[] = [];
	if (permissions.camera) allows.push('camera');
	if (permissions.microphone) allows.push('microphone');
	if (permissions.geolocation) allows.push('geolocation');
	if (permissions.clipboardWrite) allows.push('clipboard-write');

	return allows.join('; ');
}
