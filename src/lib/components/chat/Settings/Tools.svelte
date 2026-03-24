<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { createEventDispatcher, onMount, getContext, tick } from 'svelte';
	import { getModels as _getModels, getToolServersData } from '$lib/apis';

	const dispatch = createEventDispatcher();
	const i18n = getContext('i18n');

	import { models, settings, toolServers, user } from '$lib/stores';

	import Switch from '$lib/components/common/Switch.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import Connection from './Tools/Connection.svelte';

	import AddServerModal from '$lib/components/AddServerModal.svelte';

	export let saveSettings: Function;

	let servers = null;
	let showConnectionModal = false;

	const addConnectionHandler = async (server) => {
		servers = [...servers, server];
		await updateHandler();
	};

	const updateHandler = async () => {
		await saveSettings({
			toolServers: servers
		});

		toolServers.set(await getToolServersData($i18n, $settings?.toolServers ?? []));
	};

	onMount(async () => {
		servers = $settings?.toolServers ?? [];
	});
</script>

<AddServerModal bind:show={showConnectionModal} onSubmit={addConnectionHandler} direct />

<form
	class="flex flex-col h-full justify-between"
	on:submit|preventDefault={() => {
		updateHandler();
	}}
>
	<div class="space-y-4 sm:space-y-6 overflow-y-auto">
		{#if servers !== null}
			<!-- Tool Servers Section -->
			<div class="space-y-3 sm:space-y-4">
				<div class="flex flex-col sm:flex-row sm:items-start justify-between gap-3 sm:gap-4">
					<div class="flex-1">
						<h3 class="text-base sm:text-lg font-semibold text-gray-900 dark:text-white mb-1">
							{$i18n.t('Manage Tool Servers')}
						</h3>
						<p class="text-xs sm:text-sm text-gray-500 dark:text-gray-400">
							Connect to your own OpenAPI compatible external tool servers
						</p>
					</div>
					<Tooltip content={$i18n.t(`Add Connection`)}>
						<button
							class="w-full sm:w-auto flex items-center justify-center sm:justify-start gap-2 px-3 sm:px-4 py-2 text-xs sm:text-sm font-medium bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors shadow-sm hover:shadow-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
							on:click={() => {
								showConnectionModal = true;
							}}
							type="button"
						>
							<Plus />
							<span>{$i18n.t('Add Server')}</span>
						</button>
					</Tooltip>
				</div>

				<!-- Tool Servers List -->
				{#if servers?.length > 0}
					<div class="space-y-2 sm:space-y-3">
						{#each servers as server, idx}
							<div class="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-3 sm:p-4">
								<Connection
									bind:connection={server}
									direct
									onSubmit={() => {
										updateHandler();
									}}
									onDelete={() => {
										servers = servers.filter((_, i) => i !== idx);
										updateHandler();
									}}
								/>
							</div>
						{/each}
					</div>
				{:else}
					<div class="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-6 sm:p-8 text-center">
						<div class="flex flex-col items-center gap-2 sm:gap-3">
							<div
								class="w-12 h-12 rounded-full bg-gray-200 dark:bg-gray-700 flex items-center justify-center"
							>
								<svg
									xmlns="http://www.w3.org/2000/svg"
									fill="none"
									viewBox="0 0 24 24"
									stroke-width="1.5"
									stroke="currentColor"
									class="w-6 h-6 text-gray-400 dark:text-gray-500"
								>
									<path
										stroke-linecap="round"
										stroke-linejoin="round"
										d="M11.42 15.17L17.25 21A2.652 2.652 0 0021 17.25l-5.877-5.877M11.42 15.17l2.496-3.03c.317-.384.74-.626 1.208-.766M11.42 15.17l-4.655 5.653a2.548 2.548 0 11-3.586-3.586l6.837-5.63m5.108-.233c.55-.164 1.163-.188 1.743-.14a4.5 4.5 0 004.486-6.336l-3.276 3.277a3.004 3.004 0 01-2.25-2.25l3.276-3.276a4.5 4.5 0 00-6.336 4.486c.091 1.076-.071 2.264-.904 2.95l-.102.085m-1.745 1.437L5.909 7.5H4.5L2.25 3.75l1.5-1.5L7.5 4.5v1.409l4.26 4.26m-1.745 1.437l1.745-1.437m6.615 8.206L15.75 15.75M4.867 19.125h.008v.008h-.008v-.008z"
									/>
								</svg>
							</div>
							<div>
								<div class="text-xs sm:text-sm font-medium text-gray-900 dark:text-white mb-1">
									No tool servers configured
								</div>
								<div class="text-xs text-gray-500 dark:text-gray-400">
									Click "Add Server" to connect your first tool server
								</div>
							</div>
						</div>
					</div>
				{/if}

				<!-- Info Box -->
				<div
					class="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-3 sm:p-4"
				>
					<div class="flex gap-2 sm:gap-3">
						<div class="flex-shrink-0">
							<svg
								xmlns="http://www.w3.org/2000/svg"
								fill="none"
								viewBox="0 0 24 24"
								stroke-width="1.5"
								stroke="currentColor"
								class="w-5 h-5 text-blue-600 dark:text-blue-400"
							>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									d="M11.25 11.25l.041-.02a.75.75 0 011.063.852l-.708 2.836a.75.75 0 001.063.853l.041-.021M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9-3.75h.008v.008H12V8.25z"
								/>
							</svg>
						</div>
						<div class="flex-1">
							<div class="text-xs sm:text-sm font-medium text-blue-900 dark:text-blue-100 mb-1">
								Important Information
							</div>
							<div class="text-xs text-blue-800 dark:text-blue-200 space-y-1">
								<p>
									{$i18n.t('Connect to your own OpenAPI compatible external tool servers.')}
								</p>
								<p>
									{$i18n.t(
										'CORS must be properly configured by the provider to allow requests from Open WebUI.'
									)}
								</p>
							</div>
						</div>
					</div>
				</div>

				<!-- Documentation Link -->
				<div
					class="bg-gray-50 dark:bg-gray-800/50 border border-gray-200 dark:border-gray-700 rounded-lg p-4"
				>
					<div class="flex items-start gap-3">
						<div class="flex-shrink-0">
							<svg
								xmlns="http://www.w3.org/2000/svg"
								fill="none"
								viewBox="0 0 24 24"
								stroke-width="1.5"
								stroke="currentColor"
								class="w-5 h-5 text-gray-600 dark:text-gray-400"
							>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									d="M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25"
								/>
							</svg>
						</div>
						<div class="flex-1">
							<div class="text-sm font-medium text-gray-900 dark:text-white mb-1">
								Documentation
							</div>
							<p class="text-xs text-gray-600 dark:text-gray-400">
								<a
									class="text-blue-600 dark:text-blue-400 hover:underline font-medium"
									href="https://github.com/open-webui/openapi-servers"
									target="_blank"
									rel="noopener noreferrer"
								>
									{$i18n.t('Learn more about OpenAPI tool servers.')}
								</a>
							</p>
						</div>
					</div>
				</div>
			</div>
		{:else}
			<!-- Loading State -->
			<div class="flex h-full items-center justify-center py-12">
				<div class="flex flex-col items-center gap-3">
					<Spinner className="size-8" />
					<div class="text-sm text-gray-500 dark:text-gray-400">Loading tool servers...</div>
				</div>
			</div>
		{/if}
	</div>

	<!-- Save Button -->
	<div class="flex justify-end pt-6 border-t border-gray-200 dark:border-gray-700 mt-6">
		<button
			class="px-6 py-2.5 text-sm font-medium bg-orange-600 hover:bg-orange-700 text-white rounded-lg transition-colors shadow-sm hover:shadow-md focus:outline-none focus:ring-2 focus:ring-orange-500 focus:ring-offset-2"
			type="submit"
		>
			{$i18n.t('Save')}
		</button>
	</div>
</form>

<style>
	/* Custom scrollbar styling */
	::-webkit-scrollbar {
		width: 8px;
		height: 8px;
	}

	::-webkit-scrollbar-track {
		background: transparent;
	}

	::-webkit-scrollbar-thumb {
		background: rgba(156, 163, 175, 0.5);
		border-radius: 4px;
	}

	::-webkit-scrollbar-thumb:hover {
		background: rgba(156, 163, 175, 0.7);
	}

	:global(.dark) ::-webkit-scrollbar-thumb {
		background: rgba(75, 85, 99, 0.5);
	}

	:global(.dark) ::-webkit-scrollbar-thumb:hover {
		background: rgba(75, 85, 99, 0.7);
	}
</style>