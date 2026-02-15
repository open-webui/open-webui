<script lang="ts">
	/**
	 * MCPAppView - Renders MCP App UI in a secure sandboxed iframe.
	 *
	 * Uses the official @modelcontextprotocol/ext-apps SDK for communication
	 * with the app via JSON-RPC over postMessage.
	 */
	import { onMount, onDestroy } from 'svelte';
	import { callTool } from '$lib/apis/mcp';
	import {
		updateAppState,
		updateAppHeight,
		updateAppDisplayMode
	} from '$lib/stores/mcpApps';
	import type {
		MCPAppResource,
		MCPAppDisplayMode
	} from '$lib/types/mcpApps';
	import { buildAllowAttribute } from '$lib/types/mcpApps';

	// SDK imports
	import {
		AppBridge,
		PostMessageTransport
	} from '@modelcontextprotocol/ext-apps/app-bridge';
	import type { CallToolResult, TextContent } from '@modelcontextprotocol/sdk/types.js';

	// Props
	export let instanceId: string;
	export let resource: MCPAppResource;
	export let toolName: string;
	export let serverId: string;
	export let toolResult: unknown = null;
	export let toolCallId: string | number | undefined = undefined;
	export let token: string = '';

	// State
	let bridge: AppBridge | null = null;
	let outerIframe: HTMLIFrameElement | null = null;
	let state: 'loading' | 'initializing' | 'ready' | 'error' | 'closed' = 'loading';
	let displayMode: MCPAppDisplayMode = 'inline';
	let height = 400;
	let title = toolName;
	let error: string | null = null;
	let initialized = false;

	// Host context
	let theme: 'light' | 'dark' = 'dark';
	let locale = 'en-US';
	let timeZone = Intl.DateTimeFormat().resolvedOptions().timeZone;

	// Container dimensions
	let containerWidth = 600;
	let containerMaxHeight = 600;

	// Detect theme from document
	function detectTheme(): 'light' | 'dark' {
		if (typeof document !== 'undefined') {
			return document.documentElement.classList.contains('dark') ? 'dark' : 'light';
		}
		return 'dark';
	}

	// Update theme when it changes
	$: {
		const detectedTheme = detectTheme();
		if (detectedTheme !== theme) {
			theme = detectedTheme;
			if (bridge && initialized) {
				bridge.setHostContext({ theme });
			}
		}
	}

	// Host capabilities - must be objects, not booleans!
	const hostCapabilities = {
		openLinks: {},
		serverTools: { listChanged: false },
		message: { text: {} },
		logging: {}
	};

	// Host info
	const hostInfo = {
		name: 'Open WebUI',
		version: '1.0.0'
	};

	/**
	 * Get current host context for the app.
	 */
	function getHostContext() {
		return {
			theme,
			locale,
			timeZone,
			displayMode,
			availableDisplayModes: ['inline', 'fullscreen', 'pip'] as MCPAppDisplayMode[],
			containerDimensions: {
				width: containerWidth,
				maxHeight: containerMaxHeight
			},
			platform: 'web' as const
		};
	}

	/**
	 * Create the sandbox proxy blob URL.
	 * Per MCP ext-apps spec: https://github.com/modelcontextprotocol/ext-apps/blob/main/specification/2026-01-26/apps.mdx
	 *
	 * The proxy:
	 * 1. Sends ui/notifications/sandbox-proxy-ready when loaded
	 * 2. Receives ui/notifications/sandbox-resource-ready with HTML
	 * 3. Creates inner iframe with sandbox + CSP
	 * 4. Transparently relays all messages between host and inner iframe
	 */
	function createSandboxProxyScript(): string {
		const script = `<!DOCTYPE html>
<html>
<head>
	<meta charset="utf-8">
	<style>
		* { margin: 0; padding: 0; box-sizing: border-box; }
		html, body { width: 100%; height: 100%; overflow: hidden; }
		iframe { width: 100%; height: 100%; border: none; }
	</style>
</head>
<body>
<script>
let innerFrame = null;

// Build CSP string from McpUiResourceCsp object per spec
function buildCspString(cspObj) {
	if (!cspObj) {
		// Restrictive default per spec
		return "default-src 'none'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; media-src 'self' data:; connect-src 'none'";
	}

	let parts = ["default-src 'none'"];

	const resourceDomains = (cspObj.resourceDomains || []).join(' ');
	const connectDomains = (cspObj.connectDomains || []).join(' ');
	const frameDomains = (cspObj.frameDomains || []).join(' ');
	const baseUriDomains = (cspObj.baseUriDomains || []).join(' ');

	parts.push("script-src 'self' 'unsafe-inline'" + (resourceDomains ? ' ' + resourceDomains : ''));
	parts.push("style-src 'self' 'unsafe-inline'" + (resourceDomains ? ' ' + resourceDomains : ''));
	parts.push("img-src 'self' data:" + (resourceDomains ? ' ' + resourceDomains : ''));
	parts.push("font-src 'self'" + (resourceDomains ? ' ' + resourceDomains : ''));
	parts.push("media-src 'self' data:" + (resourceDomains ? ' ' + resourceDomains : ''));
	parts.push("connect-src" + (connectDomains ? ' ' + connectDomains : " 'none'"));
	parts.push("frame-src" + (frameDomains ? ' ' + frameDomains : " 'none'"));
	parts.push("object-src 'none'");
	parts.push("base-uri" + (baseUriDomains ? ' ' + baseUriDomains : " 'self'"));

	return parts.join('; ');
}

// Build allow attribute from permissions per spec
function buildAllowAttr(permissions) {
	if (!permissions) return '';
	const perms = [];
	if (permissions.camera) perms.push('camera');
	if (permissions.microphone) perms.push('microphone');
	if (permissions.geolocation) perms.push('geolocation');
	if (permissions.clipboardWrite) perms.push('clipboard-write');
	return perms.join('; ');
}

// Message relay - transparent forwarding per spec
window.addEventListener('message', (event) => {
	// From parent (host)
	if (event.source === window.parent) {
		if (event.data?.method === 'ui/notifications/sandbox-resource-ready') {
			// Create inner iframe with app content
			const params = event.data.params || {};
			const html = params.html || '';
			const sandbox = params.sandbox || 'allow-scripts allow-same-origin';
			const cspString = buildCspString(params.csp);
			const allowAttr = buildAllowAttr(params.permissions);

			innerFrame = document.createElement('iframe');
			innerFrame.sandbox = sandbox;
			if (allowAttr) innerFrame.allow = allowAttr;

			// Inject CSP via meta tag
			let finalHtml = html;
			const metaTag = '<meta http-equiv="Content-Security-Policy" content="' + cspString + '">';
			if (finalHtml.includes('<head>')) {
				finalHtml = finalHtml.replace('<head>', '<head>' + metaTag);
			} else if (finalHtml.includes('<html>')) {
				finalHtml = finalHtml.replace('<html>', '<html><head>' + metaTag + '</head>');
			} else {
				finalHtml = '<head>' + metaTag + '</head>' + finalHtml;
			}

			// Load via blob URL (different origin)
			const blob = new Blob([finalHtml], { type: 'text/html' });
			innerFrame.src = URL.createObjectURL(blob);
			document.body.appendChild(innerFrame);
		} else if (innerFrame && innerFrame.contentWindow) {
			// Forward all other messages to inner iframe (transparent relay)
			innerFrame.contentWindow.postMessage(event.data, '*');
		}
	}
	// From inner iframe (app) - forward to host (transparent relay)
	else if (innerFrame && event.source === innerFrame.contentWindow) {
		window.parent.postMessage(event.data, '*');
	}
});

// Signal ready per spec - sent automatically when proxy loads
window.parent.postMessage({
	jsonrpc: '2.0',
	method: 'ui/notifications/sandbox-proxy-ready',
	params: {}
}, '*');
<\/script>
</body>
</html>`;
		return URL.createObjectURL(new Blob([script], { type: 'text/html' }));
	}

	/**
	 * Get container dimensions based on display mode.
	 */
	function getContainerDimensions() {
		switch (displayMode) {
			case 'fullscreen':
				return {
					width: window.innerWidth,
					height: window.innerHeight,
					maxWidth: window.innerWidth,
					maxHeight: window.innerHeight
				};
			case 'pip':
				return {
					width: 400,
					maxHeight: 300
				};
			default:
				return {
					width: containerWidth,
					maxHeight: containerMaxHeight
				};
		}
	}

	/**
	 * Send tool result to the app.
	 */
	function sendToolResult(result: unknown) {
		if (!bridge || !initialized) {
			console.warn('MCPAppView: Cannot send tool result, bridge not initialized');
			return;
		}

		// Format as MCP content
		const mcpResult = formatToolResult(result);
		bridge.sendToolResult(mcpResult);
	}

	/**
	 * Format tool result to MCP CallToolResult format.
	 */
	function formatToolResult(result: unknown): CallToolResult {
		// If already in CallToolResult format
		if (result && typeof result === 'object' && 'content' in result && Array.isArray((result as CallToolResult).content)) {
			return result as CallToolResult;
		}

		// Wrap in text content
		const textContent: TextContent = {
			type: 'text',
			text: typeof result === 'string' ? result : JSON.stringify(result)
		};

		return {
			content: [textContent],
			isError: false
		};
	}

	/**
	 * Handle escape key to exit fullscreen/pip modes.
	 */
	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Escape' && displayMode !== 'inline') {
			displayMode = 'inline';
			updateAppDisplayMode(instanceId, displayMode);
			if (bridge) {
				bridge.setHostContext({
					displayMode,
					containerDimensions: getContainerDimensions()
				});
			}
		}
	}

	/**
	 * Cleanup on destroy.
	 */
	async function cleanup() {
		if (bridge && initialized) {
			try {
				await bridge.teardownResource({});
			} catch (e) {
				console.warn('MCPAppView: Teardown failed:', e);
			}
		}
		bridge = null;
	}

	onMount(async () => {
		console.log('MCPAppView: Resource received:', { uri: resource.uri, csp: resource.csp, permissions: resource.permissions });

		// Create outer iframe element (don't add to DOM yet)
		const proxyUrl = createSandboxProxyScript();

		outerIframe = document.createElement('iframe');
		outerIframe.src = proxyUrl;
		// Per spec: outer iframe sandbox = "allow-scripts allow-same-origin"
		outerIframe.sandbox = 'allow-scripts allow-same-origin';
		outerIframe.style.width = '100%';
		outerIframe.style.height = `${height}px`;
		outerIframe.style.border = 'none';
		outerIframe.style.borderRadius = '0.5rem';

		// Set allow attribute from permissions
		if (resource.permissions) {
			const allow = buildAllowAttribute(resource.permissions);
			if (allow) {
				outerIframe.allow = allow;
			}
		}

		const container = document.getElementById(`mcp-app-container-${instanceId}`);
		if (!container) {
			console.error('MCPAppView: Container not found');
			return;
		}

		// IMPORTANT: Initialize bridge BEFORE adding iframe to DOM
		// This ensures we're listening for sandbox-proxy-ready before it's sent
		try {
			// Create AppBridge without MCP client (we handle tool calls manually)
			bridge = new AppBridge(null, hostInfo, hostCapabilities, {
				hostContext: getHostContext()
			});

			// Register all callbacks BEFORE connecting
			bridge.oninitialized = () => {
				console.log('MCPAppView: App initialized');
				initialized = true;
				state = 'ready';
				updateAppState(instanceId, 'ready');

				// Send tool input (arguments) after initialization
				if (toolResult !== null) {
					sendToolResult(toolResult);
				}
			};

			bridge.onsandboxready = () => {
				console.log('MCPAppView: Sandbox proxy ready, sending HTML with CSP:', resource.csp);
				state = 'initializing';
				updateAppState(instanceId, 'initializing');

				// Send HTML content to sandbox per spec
				// CSP and permissions come from resource._meta.ui
				bridge?.sendSandboxResourceReady({
					html: resource.content,
					sandbox: 'allow-scripts allow-same-origin',
					csp: resource.csp,
					permissions: resource.permissions
				});
			};

			bridge.onsizechange = ({ width, height: newHeight }) => {
				if (newHeight != null && newHeight > 0) {
					height = newHeight;
					updateAppHeight(instanceId, height);
				}
			};

			bridge.onopenlink = async ({ url }) => {
				try {
					window.open(url, '_blank', 'noopener,noreferrer');
					return {};
				} catch (e) {
					console.error('MCPAppView: Failed to open link:', e);
					return { isError: true };
				}
			};

			bridge.onrequestdisplaymode = async ({ mode }) => {
				const availableModes: MCPAppDisplayMode[] = ['inline', 'fullscreen', 'pip'];
				if (availableModes.includes(mode as MCPAppDisplayMode)) {
					displayMode = mode as MCPAppDisplayMode;
					updateAppDisplayMode(instanceId, displayMode);
					bridge?.setHostContext({
						displayMode,
						containerDimensions: getContainerDimensions()
					});
				}
				return { mode: displayMode };
			};

			bridge.onloggingmessage = ({ level, logger, data }) => {
				const logFn = level === 'error' ? console.error : console.log;
				logFn(`[MCP App${logger ? ` - ${logger}` : ''}] ${level}:`, data);
			};

			bridge.oncalltool = async (params): Promise<CallToolResult> => {
				try {
					const result = await callTool(token, serverId, params.name, params.arguments || {});
					return formatToolResult(result);
				} catch (e) {
					console.error('MCPAppView: Tool call failed:', e);
					const errorContent: TextContent = { type: 'text', text: String(e) };
					return {
						content: [errorContent],
						isError: true
					};
				}
			};

			// NOW add iframe to DOM - this triggers the proxy script
			container.appendChild(outerIframe);

			// Connect transport IMMEDIATELY after adding to DOM
			// contentWindow is available as soon as iframe is in DOM
			// Don't wait for onload - we need to start listening before proxy sends sandbox-proxy-ready
			const transport = new PostMessageTransport(
				outerIframe.contentWindow!,
				outerIframe.contentWindow!
			);

			await bridge.connect(transport);
			console.log('MCPAppView: Bridge connected, listening for sandbox-proxy-ready');

		} catch (e) {
			console.error('MCPAppView: Failed to initialize bridge:', e);
			error = String(e);
			state = 'error';
			updateAppState(instanceId, 'error', error);
		}

		// Add keyboard listener
		window.addEventListener('keydown', handleKeydown);
	});

	onDestroy(() => {
		cleanup();
		window.removeEventListener('keydown', handleKeydown);
	});

	// Reactive: Send tool result when it changes
	$: if (toolResult !== null && initialized && bridge) {
		sendToolResult(toolResult);
	}

	// Reactive: Update iframe height
	$: if (outerIframe) {
		outerIframe.style.height = `${height}px`;
	}
</script>

<div
	id="mcp-app-container-{instanceId}"
	class="mcp-app-container {displayMode === 'fullscreen' ? 'mcp-app-fullscreen' : ''} {displayMode === 'pip' ? 'mcp-app-pip' : ''}"
	class:mcp-app-inline={displayMode === 'inline'}
>
	{#if state === 'loading' || state === 'initializing'}
		<div class="mcp-app-loading flex items-center justify-center p-4 text-gray-500">
			<div class="animate-spin rounded-full h-6 w-6 border-b-2 border-gray-500 mr-2"></div>
			<span>{state === 'loading' ? 'Loading app...' : 'Initializing...'}</span>
		</div>
	{/if}

	{#if state === 'error'}
		<div class="mcp-app-error p-4 bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-200 rounded-lg">
			<strong>Error:</strong> {error}
		</div>
	{/if}

	{#if displayMode === 'fullscreen'}
		<div class="mcp-app-fullscreen-header flex items-center justify-between p-2 bg-gray-800 text-white">
			<span class="font-semibold">{title}</span>
			<button
				type="button"
				class="p-1 hover:bg-gray-700 rounded"
				aria-label="Close fullscreen"
				on:click={() => {
					displayMode = 'inline';
					updateAppDisplayMode(instanceId, displayMode);
					if (bridge) {
						bridge.setHostContext({
							displayMode,
							containerDimensions: getContainerDimensions()
						});
					}
				}}
			>
				<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
				</svg>
			</button>
		</div>
	{/if}
</div>

<style>
	.mcp-app-container {
		position: relative;
		min-height: 100px;
		border: 1px solid var(--border-color, #e5e7eb);
		border-radius: 0.5rem;
		overflow: hidden;
		background: var(--bg-color, #ffffff);
	}

	:global(.dark) .mcp-app-container {
		--border-color: #374151;
		--bg-color: #1f2937;
	}

	.mcp-app-inline {
		/* Inline mode - contained within chat flow */
	}

	.mcp-app-fullscreen {
		position: fixed;
		inset: 0;
		z-index: 9999;
		border-radius: 0;
		border: none;
	}

	.mcp-app-fullscreen :global(iframe) {
		height: calc(100% - 40px) !important;
	}

	.mcp-app-pip {
		position: fixed;
		bottom: 1rem;
		right: 1rem;
		width: 400px;
		max-height: 300px;
		z-index: 9998;
		box-shadow: 0 10px 25px rgba(0, 0, 0, 0.2);
	}

	.mcp-app-loading {
		min-height: 100px;
	}

	.mcp-app-fullscreen-header {
		height: 40px;
	}
</style>
