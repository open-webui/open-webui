<script lang="ts">
	import { getContext } from 'svelte';
	import { get } from 'svelte/store';
	import { allAvailableTools, localMcpoTools, tools as globalToolsStore, toolServers as globalToolServersStore } from '$lib/stores';
	import type { Tool, LocalMcpoToolConfig, ToolServerConnection } from '$lib/types/tools';
	import type { Writable } from 'svelte/store';

	import { toast } from 'svelte-sonner';
	// import { copyToClipboard } from '$lib/utils'; // Removed unused import

	import Modal from '../common/Modal.svelte';
	// import Link from '../icons/Link.svelte'; // Removed unused icon
	// import Collapsible from '../common/Collapsible.svelte'; // Removed unused import
	// Assuming a simple checkbox for toggle for now, or a Toggle component if available
	// import Toggle from '../common/Toggle.svelte';


	export let show = false;
	export let selectedToolIds: string[] = []; // Explicitly type prop

	const i18n: Writable<any> = getContext('i18n'); // Added type cast

	// Reactive statement to filter tools based on props and stores
	$: displayedToolsList = ($allAvailableTools || []).filter(tool => selectedToolIds.includes(tool.id));


	const LOCAL_MCPO_ENABLED_STATES_KEY = 'localMcpoToolEnabledStates';

	function handleToggleChange(event: Event, toolId: string) {
		const target = event.currentTarget as HTMLInputElement;
		toggleToolEnabled(toolId, target.checked);
	}

	function saveLocalMcpoToolEnabledStates(toolsToSave: LocalMcpoToolConfig[]) {
		const statesToSave: Record<string, boolean | undefined> = {};
		toolsToSave.forEach(tool => {
			statesToSave[tool.id] = tool.enabled;
		});
		localStorage.setItem(LOCAL_MCPO_ENABLED_STATES_KEY, JSON.stringify(statesToSave));
	}

	function toggleToolEnabled(toolId: string, newEnabledState: boolean) {
		const currentAllTools = get(allAvailableTools);
		const toolToUpdate = currentAllTools.find(t => t.id === toolId);

		if (!toolToUpdate) return;

		// Update the specific tool's enabled status in its source store
		if (toolToUpdate.type === 'local_mcpo') {
			localMcpoTools.update(currentLocalTools => {
				const updatedTools = currentLocalTools.map(lt => 
					lt.id === toolId ? { ...lt, enabled: newEnabledState } : lt
				);
				saveLocalMcpoToolEnabledStates(updatedTools); // Persist to localStorage
				return updatedTools;
			});
			toast.success(`Local tool '${toolToUpdate.name}' ${newEnabledState ? 'enabled' : 'disabled'}.`);
		} else {
			// For non-local_mcpo tools, persistence of 'enabled' is not defined by this PRD.
			// We can update its state in the allAvailableTools derived store's source if possible,
			// but this might be temporary if not persisted by their respective stores/mechanisms.
			// For now, this will primarily affect local_mcpo tools correctly.
			// We might need to update $tools or $toolServers if they are the source.
			// This part needs more thought on how 'enabled' for other tool types is handled globally.
			console.warn(`Toggling non-local MCPO tool '${toolToUpdate.name}'. Persistence not fully implemented for this type.`);
			// To make the UI reflect the change for non-local tools temporarily,
			// we'd need to ensure allAvailableTools correctly re-derives.
			// This might require making the 'enabled' property on the Tool interface in allAvailableTools reactive.
			// The current structure of allAvailableTools should pick up changes if source stores are updated.
			// toolToUpdate.enabled = newEnabledState; // This direct mutation was not reactive for non-local tools.

			let sourceUpdated = false;
			// Try to update in globalToolsStore (internal python tools)
			const currentGlobalTools = get(globalToolsStore);
			if (currentGlobalTools && Array.isArray(currentGlobalTools)) {
				const toolIndex = currentGlobalTools.findIndex(t => t.id === toolId);
				if (toolIndex !== -1) {
					globalToolsStore.update(arr => {
						if (arr === null) return null; // Handle null case for arr
						const newArr = [...arr];
						newArr[toolIndex] = { ...newArr[toolIndex], enabled: newEnabledState };
						return newArr;
					});
					sourceUpdated = true;
				}
			}

			// If not found or not updated, try to update in globalToolServersStore (external OpenAPI tools)
			if (!sourceUpdated) {
				globalToolServersStore.update(servers => {
					return servers.map(server => {
						if (server.tools) {
							const toolIndex = server.tools.findIndex(t => t.id === toolId);
							if (toolIndex !== -1) {
								sourceUpdated = true; // Mark as updated if found and changed here
								const newTools = [...server.tools];
								newTools[toolIndex] = { ...newTools[toolIndex], enabled: newEnabledState };
								return { ...server, tools: newTools };
							}
						}
						return server;
					});
				});
			}
			
			if (sourceUpdated) {
				toast.success(`Tool '${toolToUpdate.name}' ${newEnabledState ? 'enabled' : 'disabled'}.`);
			} else {
				// Fallback if tool not found in source stores, though it should be.
				// This might mean the tool's 'enabled' state cannot be reactively updated from here.
				toolToUpdate.enabled = newEnabledState; // Keep direct mutation as last resort for UI hint
				console.warn(`Tool '${toolToUpdate.name}' was toggled, but its source store for reactive update was not definitively found. UI might not fully reflect persisted state for this tool type without further specific handling.`);
				toast.info(`Toggled '${toolToUpdate.name}'. Full reactivity for this tool type might require further setup.`);
			}
		}
	}

</script>

<Modal bind:show size="lg"> <!-- Increased size for more content -->
	<div class="flex flex-col h-full">
		<div class="flex justify-between items-center dark:text-gray-300 px-5 pt-4 pb-2 border-b dark:border-gray-700">
			<div class="text-lg font-medium">{$i18n.t('Available Tools')}</div>
			<button
				class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
				on:click={() => {
					show = false;
				}}
			>
				<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-5 h-5">
					<path d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z" />
				</svg>
			</button>
		</div>

		<div class="flex-grow overflow-y-auto p-5 space-y-3">
			{#if displayedToolsList.length > 0}
				{#each displayedToolsList as tool (tool.id)}
					<div class="p-3 border rounded-lg dark:border-gray-700 bg-white dark:bg-gray-800 shadow-sm">
						<div class="flex items-center justify-between">
							<div class="flex-1 min-w-0">
								<div class="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
									{tool.name}
									{#if tool.type === 'local_mcpo'}
										<span class="ml-2 text-xs font-semibold px-2 py-0.5 rounded-full bg-blue-100 text-blue-800 dark:bg-blue-700 dark:text-blue-200">
											Local (MCPO)
										</span>
									{:else if tool.type === 'openapi'}
										<span class="ml-2 text-xs font-semibold px-2 py-0.5 rounded-full bg-green-100 text-green-800 dark:bg-green-700 dark:text-green-200">
											OpenAPI
										</span>
									{:else if tool.type === 'python_internal'}
										<span class="ml-2 text-xs font-semibold px-2 py-0.5 rounded-full bg-yellow-100 text-yellow-800 dark:bg-yellow-700 dark:text-yellow-200">
											Internal
										</span>
									{/if}
								</div>
								{#if tool.description}
									<p class="text-xs text-gray-500 dark:text-gray-400 mt-0.5 truncate" title={tool.description}>
										{tool.description}
									</p>
								{/if}
								{#if tool.metadata?.serverName}
									<p class="text-xs text-gray-400 dark:text-gray-500 mt-0.5">
										Server: {tool.metadata.serverName}
									</p>
								{/if}
							</div>
							<div class="ml-4 flex-shrink-0">
								<!-- Basic checkbox as a toggle -->
								<label class="flex items-center cursor-pointer">
									<input 
										type="checkbox" 
										class="sr-only peer" 
										checked={tool.enabled ?? true} 
										on:change={(e) => handleToggleChange(e, tool.id)}
									/>
									<div class="relative w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 dark:peer-focus:ring-blue-800 rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full rtl:peer-checked:after:-translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-blue-600"></div>
								</label>
							</div>
						</div>
						<!-- Optional: Collapsible content for more details -->
						<!-- 
						<Collapsible buttonClassName="w-full mt-2 text-xs" chevron>
							<span slot="button">Details</span>
							<div slot="content" class="mt-2 text-xs text-gray-500 dark:text-gray-400">
								<pre>{JSON.stringify(tool.spec || tool.metadata, null, 2)}</pre>
							</div>
						</Collapsible> 
						-->
					</div>
				{/each}
			{:else}
				<p class="text-sm text-gray-500 dark:text-gray-400 text-center py-4">
					{$i18n.t('No tools available or selected.')}
				</p>
			{/if}
		</div>

		<div class="px-5 py-3 border-t dark:border-gray-700">
			<p class="text-xs text-gray-600 dark:text-gray-400">
				{$i18n.t('Tools enhance functionality. Enable tools relevant to your tasks.')}
				{#if $allAvailableTools.some(t => t.type === 'openapi' || t.type === 'local_mcpo')}
				<br />
				{$i18n.t('OpenAPI and Local (MCPO) tools are called based on their OpenAPI specifications.')}
				<a class="underline" href="https://github.com/open-webui/openapi-servers" target="_blank">{$i18n.t('Learn more.')}</a>
				{/if}
			</p>
		</div>
	</div>
</Modal>
