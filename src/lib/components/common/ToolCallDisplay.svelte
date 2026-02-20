<script lang="ts">
	import { decode } from 'html-entities';
	import { v4 as uuidv4 } from 'uuid';
	import { onMount } from 'svelte';

	import { getContext } from 'svelte';
	const i18n = getContext('i18n');

	import { slide } from 'svelte/transition';
	import { quintOut } from 'svelte/easing';

	import ChevronUp from '../icons/ChevronUp.svelte';
	import ChevronDown from '../icons/ChevronDown.svelte';
	import Spinner from './Spinner.svelte';
	import Markdown from '../chat/Messages/Markdown.svelte';
	import Image from './Image.svelte';
	import FullHeightIframe from './FullHeightIframe.svelte';
	import MCPAppView from '../chat/Messages/MCPAppView.svelte';
	import { readResource } from '$lib/apis/mcp';
	import { createAppInstance, addApp } from '$lib/stores/mcpApps';
	import type { MCPAppResource } from '$lib/types/mcpApps';

	export let id: string = '';
	export let attributes: {
		type?: string;
		id?: string;
		name?: string;
		arguments?: string;
		result?: string;
		files?: string;
		embeds?: string;
		done?: string;
		mcp_app?: string;
	} = {};

	export let open = false;
	export let className = '';
	export let buttonClassName =
		'w-fit text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 transition';

	const componentId = id || uuidv4();

	function parseJSONString(str: string) {
		try {
			return parseJSONString(JSON.parse(str));
		} catch (e) {
			return str;
		}
	}

	function formatJSONString(str: string) {
		try {
			const parsed = parseJSONString(str);
			// If parsed is an object/array, then it's valid JSON
			if (typeof parsed === 'object') {
				return JSON.stringify(parsed, null, 2);
			} else {
				// It's a primitive value like a number, boolean, etc.
				return `${JSON.stringify(String(parsed))}`;
			}
		} catch (e) {
			// Not valid JSON, return as-is
			return str;
		}
	}

	// Decode and parse attributes
	$: args = decode(attributes?.arguments ?? '');
	$: result = decode(attributes?.result ?? '');
	$: files = parseJSONString(decode(attributes?.files ?? ''));
	$: embeds = parseJSONString(decode(attributes?.embeds ?? ''));
	$: isDone = attributes?.done === 'true';
	$: isExecuting = attributes?.done && attributes?.done !== 'true';

	// MCP App state
	let mcpApp: { resourceUri: string; serverId: string; visibility?: string[]; permissions?: Record<string, unknown> } | null = null;
	let mcpResource: MCPAppResource | null = null;
	let mcpInstanceId: string | null = null;
	let mcpLoading = false;
	let mcpError: string | null = null;

	// Parse MCP app attribute
	$: {
		if (attributes?.mcp_app) {
			try {
				const parsed = JSON.parse(decode(attributes.mcp_app));
				if (parsed?.resourceUri && parsed?.serverId) {
					mcpApp = parsed;
				}
			} catch (e) {
				console.error('Failed to parse mcp_app attribute:', e);
			}
		}
	}

	// Fetch MCP resource when mcpApp changes
	async function loadMcpResource() {
		if (!mcpApp) return;

		mcpLoading = true;
		mcpError = null;

		try {
			const token = localStorage.token;
			if (!token) {
				throw new Error('No auth token available');
			}

			const resource = await readResource(token, mcpApp.serverId, mcpApp.resourceUri);
			mcpResource = resource;

			// Create app instance
			const instance = createAppInstance({
				serverId: mcpApp.serverId,
				toolName: attributes.name || 'MCP App',
				resource: resource,
				toolCallId: attributes.id
			});

			mcpInstanceId = instance.instanceId;
			addApp(instance);
		} catch (e) {
			console.error('Failed to load MCP resource:', e);
			mcpError = String(e);
		} finally {
			mcpLoading = false;
		}
	}

	// Load resource when component mounts if mcpApp is present
	onMount(() => {
		if (mcpApp && isDone) {
			loadMcpResource();
		}
	});

	// Also react to mcpApp changes
	$: if (mcpApp && isDone && !mcpResource && !mcpLoading && !mcpError) {
		loadMcpResource();
	}
</script>

<div {id} class={className}>
	{#if mcpApp && isDone}
		<!-- MCP App Mode: Show MCP App UI -->
		<div class="py-1 w-full">
			<div class="w-full text-xs text-gray-500 mb-2">
				<div class="">
					{attributes.name}
				</div>
			</div>

			{#if mcpLoading}
				<div class="flex items-center justify-center p-4 text-gray-500 border border-gray-200 dark:border-gray-700 rounded-lg">
					<Spinner className="size-4 mr-2" />
					<span>{$i18n.t('Loading MCP App...')}</span>
				</div>
			{:else if mcpError}
				<div class="p-4 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 rounded-lg border border-red-200 dark:border-red-800">
					<strong>{$i18n.t('Failed to load app')}:</strong> {mcpError}
				</div>
			{:else if mcpResource && mcpInstanceId}
				<MCPAppView
					instanceId={mcpInstanceId}
					resource={mcpResource}
					toolName={attributes.name || 'MCP App'}
					serverId={mcpApp.serverId}
					toolArgs={args ? parseJSONString(args) : {}}
					toolResult={result ? parseJSONString(result) : null}
					toolCallId={attributes.id}
					token={localStorage.token || ''}
				/>
			{/if}
		</div>
	{:else if embeds && Array.isArray(embeds) && embeds.length > 0}
		<!-- Embed Mode: Show iframes without collapsible behavior -->
		<div class="py-1 w-full cursor-pointer">
			<div class="w-full text-xs text-gray-500">
				<div class="">
					{attributes.name}
				</div>
			</div>

			{#each embeds as embed, idx}
				<div class="my-2" id={`${componentId}-tool-call-embed-${idx}`}>
					<FullHeightIframe
						src={embed}
						{args}
						allowScripts={true}
						allowForms={true}
						allowSameOrigin={true}
						allowPopups={true}
					/>
				</div>
			{/each}
		</div>
	{:else}
		<!-- Standard collapsible tool call display -->
		<div
			class="{buttonClassName} cursor-pointer"
			on:pointerup={() => {
				open = !open;
			}}
		>
			<div
				class="w-full font-medium flex items-center justify-between gap-2 {isExecuting
					? 'shimmer'
					: ''}"
			>
				{#if isExecuting}
					<div>
						<Spinner className="size-4" />
					</div>
				{/if}

				<div class="">
					{#if isDone}
						<Markdown
							id={`${componentId}-tool-call-title`}
							content={$i18n.t('View Result from **{{NAME}}**', {
								NAME: attributes.name
							})}
						/>
					{:else}
						<Markdown
							id={`${componentId}-tool-call-executing`}
							content={$i18n.t('Executing **{{NAME}}**...', {
								NAME: attributes.name
							})}
						/>
					{/if}
				</div>

				<div class="flex self-center translate-y-[1px]">
					{#if open}
						<ChevronUp strokeWidth="3.5" className="size-3.5" />
					{:else}
						<ChevronDown strokeWidth="3.5" className="size-3.5" />
					{/if}
				</div>
			</div>
		</div>

		{#if open}
			<div transition:slide={{ duration: 300, easing: quintOut, axis: 'y' }}>
				{#if isDone}
					<Markdown
						id={`${componentId}-tool-call-result`}
						content={`> \`\`\`json
> ${formatJSONString(args)}
> ${formatJSONString(result)}
> \`\`\``}
					/>
				{:else}
					<Markdown
						id={`${componentId}-tool-call-args`}
						content={`> \`\`\`json
> ${formatJSONString(args)}
> \`\`\``}
					/>
				{/if}
			</div>
		{/if}
	{/if}

	<!-- Files display (images etc.) when done -->
	{#if isDone}
		{#if typeof files === 'object'}
			{#each files ?? [] as file, idx}
				{#if typeof file === 'string'}
					{#if file.startsWith('data:image/')}
						<Image id={`${componentId}-tool-call-result-${idx}`} src={file} alt="Image" />
					{/if}
				{:else if typeof file === 'object'}
					{#if (file.type === 'image' || (file?.content_type ?? '').startsWith('image/')) && file.url}
						<Image id={`${componentId}-tool-call-result-${idx}`} src={file.url} alt="Image" />
					{/if}
				{/if}
			{/each}
		{/if}
	{/if}
</div>
