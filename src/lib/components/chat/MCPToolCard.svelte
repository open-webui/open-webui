<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Switch from '$lib/components/common/Switch.svelte';

	const dispatch = createEventDispatcher();

	export let tool: {
		name: string;
		displayName: string;
		fullName: string;
		description: string;
		serverName: string;
		isGlobal: boolean;
		scopePrefix: string;
		enabled: boolean;
		specs: any[];
		hasStructuredOutput: boolean;
		supportsJsonResponse: boolean;
		outputSchema: any;
	};
	export let toolId: string;

	const toggleTool = () => {
		dispatch('toggle', { toolId });
	};
</script>

<div
	class="p-4 border border-gray-200 dark:border-gray-700 rounded-lg transition-colors text-left bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-750 {tool.enabled
		? 'ring-2 ring-purple-500 border-purple-500'
		: ''}"
>
	<!-- Tool header with icon and name -->
	<div class="flex items-start gap-3 mb-3">
		<div class="flex-shrink-0 mt-1">
			<svg
				xmlns="http://www.w3.org/2000/svg"
				fill="none"
				viewBox="0 0 24 24"
				stroke-width="1.5"
				stroke="currentColor"
				class="size-8 text-purple-500 bg-purple-50 dark:bg-purple-900/20 rounded-lg p-1.5"
			>
				<path
					stroke-linecap="round"
					stroke-linejoin="round"
					d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z"
				/>
			</svg>
		</div>

		<div class="flex-1 min-w-0">
			<div class="flex items-center gap-2 mb-1">
				<div class="font-medium text-gray-900 dark:text-white flex items-center gap-1.5">
					<!-- Scope indicator icon -->
					{#if tool.isGlobal}
						<Tooltip content="Global tool - Available to all users (configured by admin)">
							<svg
								xmlns="http://www.w3.org/2000/svg"
								fill="none"
								viewBox="0 0 24 24"
								stroke-width="1.5"
								stroke="currentColor"
								class="size-3 text-blue-500 flex-shrink-0"
							>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									d="M12 21a9.004 9.004 0 008.716-6.747M12 21a9.004 9.004 0 01-8.716-6.747M12 21c2.485 0 4.5-4.03 4.5 9S14.485 3 12 3s-4.5 4.03-4.5 9 2.015 9 4.5 9z"
								/>
							</svg>
						</Tooltip>
					{:else}
						<Tooltip content="Personal tool - Only available to you (from your MCP servers)">
							<svg
								xmlns="http://www.w3.org/2000/svg"
								fill="none"
								viewBox="0 0 24 24"
								stroke-width="1.5"
								stroke="currentColor"
								class="size-3 text-orange-500 flex-shrink-0"
							>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z"
								/>
							</svg>
						</Tooltip>
					{/if}
					<span class="break-words">{tool.displayName}</span>
				</div>
			</div>
			<div class="text-xs text-purple-600 dark:text-purple-400 font-medium">
				{tool.serverName}
			</div>
		</div>

		<!-- Enable/Disable switch -->
		<div class="flex-shrink-0">
			<Switch state={tool.enabled} on:change={toggleTool} />
		</div>
	</div>

	<!-- Description -->
	<div class="text-sm text-gray-600 dark:text-gray-300 mb-3">
		{tool.description}
	</div>

	<!-- Tool specs/parameters info -->
	{#if tool.specs && tool.specs.length > 0}
		<div class="text-xs text-gray-500 dark:text-gray-400">
			<span>
				{tool.specs.length} parameter{tool.specs.length !== 1 ? 's' : ''}
			</span>
		</div>
	{/if}
</div>
