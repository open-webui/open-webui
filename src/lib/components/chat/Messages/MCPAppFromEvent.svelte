<script lang="ts">
	/**
	 * MCPAppFromEvent - Detects and renders MCP Apps from tool call events.
	 *
	 * Checks if a tool call has a UI resource URI in _meta.ui.resourceUri
	 * and renders the MCPAppView component if so.
	 */
	import { onMount } from 'svelte';
	import { readResource } from '$lib/apis/mcp';
	import { createAppInstance, addApp } from '$lib/stores/mcpApps';
	import type { MCPAppResource } from '$lib/types/mcpApps';
	import MCPAppView from './MCPAppView.svelte';

	// Props
	export let toolCall: {
		name: string;
		arguments?: Record<string, unknown>;
		_meta?: {
			ui?: {
				resourceUri?: string;
				visibility?: string[];
				permissions?: Record<string, unknown>;
			};
			'ui/resourceUri'?: string;
		};
	};
	export let toolResult: unknown = null;
	export let toolCallId: string | number | undefined = undefined;
	export let serverId: string;
	export let token: string;

	// State
	let resource: MCPAppResource | null = null;
	let instanceId: string | null = null;
	let loading = false;
	let error: string | null = null;

	/**
	 * Extract UI resource URI from tool metadata.
	 * Supports both nested and flat formats.
	 */
	function getResourceUri(): string | null {
		const meta = toolCall._meta;
		if (!meta) return null;

		// Nested format: _meta.ui.resourceUri
		if (meta.ui?.resourceUri) {
			const uri = meta.ui.resourceUri;
			if (typeof uri === 'string' && uri.startsWith('ui://')) {
				return uri;
			}
		}

		// Flat format: _meta["ui/resourceUri"]
		const flatUri = meta['ui/resourceUri'];
		if (typeof flatUri === 'string' && flatUri.startsWith('ui://')) {
			return flatUri;
		}

		return null;
	}

	/**
	 * Check if the tool is app-only (not visible to model).
	 * If so, we might want to handle it differently.
	 */
	function isAppOnly(): boolean {
		const visibility = toolCall._meta?.ui?.visibility;
		if (Array.isArray(visibility)) {
			return visibility.length === 1 && visibility[0] === 'app';
		}
		return false;
	}

	/**
	 * Fetch the UI resource and create app instance.
	 */
	async function loadResource() {
		const uri = getResourceUri();
		if (!uri) return;

		loading = true;
		error = null;

		try {
			const fetchedResource = await readResource(token, serverId, uri);
			resource = fetchedResource;

			// Create app instance
			const instance = createAppInstance({
				serverId,
				toolName: toolCall.name,
				resource: fetchedResource,
				toolCallId
			});

			instanceId = instance.instanceId;
			addApp(instance);
		} catch (e) {
			console.error('MCPAppFromEvent: Failed to load resource:', e);
			error = String(e);
		} finally {
			loading = false;
		}
	}

	onMount(() => {
		const uri = getResourceUri();
		if (uri) {
			loadResource();
		}
	});

	// Reactive: Check if this tool has a UI resource
	$: hasUiResource = getResourceUri() !== null;
</script>

{#if hasUiResource}
	{#if loading}
		<div class="mcp-app-loading flex items-center justify-center p-4 text-gray-500 border border-gray-200 dark:border-gray-700 rounded-lg">
			<div class="animate-spin rounded-full h-5 w-5 border-b-2 border-gray-500 mr-2"></div>
			<span>Loading MCP App...</span>
		</div>
	{:else if error}
		<div class="mcp-app-error p-4 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 rounded-lg border border-red-200 dark:border-red-800">
			<strong>Failed to load app:</strong> {error}
		</div>
	{:else if resource && instanceId}
		<MCPAppView
			{instanceId}
			{resource}
			toolName={toolCall.name}
			{serverId}
			{toolResult}
			{toolCallId}
			{token}
		/>
	{/if}
{/if}
