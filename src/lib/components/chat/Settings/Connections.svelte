<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { createEventDispatcher, onMount, getContext, tick } from 'svelte';
	import { getModels as _getModels } from '$lib/apis';

	const dispatch = createEventDispatcher();
	const i18n = getContext('i18n');

	import { models, settings, user } from '$lib/stores';

	import Switch from '$lib/components/common/Switch.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import Connection from './Connections/Connection.svelte';

	import AddConnectionModal from '$lib/components/AddConnectionModal.svelte';

	export let saveSettings: Function;

	let config = null;

	let showConnectionModal = false;

	const addConnectionHandler = async (connection) => {
		config.OPENAI_API_BASE_URLS.push(connection.url);
		config.OPENAI_API_KEYS.push(connection.key);
		config.OPENAI_API_CONFIGS[config.OPENAI_API_BASE_URLS.length - 1] = connection.config;

		await updateHandler();
	};

	const updateHandler = async () => {
		// Remove trailing slashes
		config.OPENAI_API_BASE_URLS = config.OPENAI_API_BASE_URLS.map((url) => url.replace(/\/$/, ''));

		// Check if API KEYS length is same than API URLS length
		if (config.OPENAI_API_KEYS.length !== config.OPENAI_API_BASE_URLS.length) {
			// if there are more keys than urls, remove the extra keys
			if (config.OPENAI_API_KEYS.length > config.OPENAI_API_BASE_URLS.length) {
				config.OPENAI_API_KEYS = config.OPENAI_API_KEYS.slice(
					0,
					config.OPENAI_API_BASE_URLS.length
				);
			}

			// if there are more urls than keys, add empty keys
			if (config.OPENAI_API_KEYS.length < config.OPENAI_API_BASE_URLS.length) {
				const diff = config.OPENAI_API_BASE_URLS.length - config.OPENAI_API_KEYS.length;
				for (let i = 0; i < diff; i++) {
					config.OPENAI_API_KEYS.push('');
				}
			}
		}

		await saveSettings({
			directConnections: config
		});
	};

	onMount(async () => {
		config = $settings?.directConnections ?? {
			OPENAI_API_BASE_URLS: [],
			OPENAI_API_KEYS: [],
			OPENAI_API_CONFIGS: {}
		};
	});
</script>

<AddConnectionModal direct bind:show={showConnectionModal} onSubmit={addConnectionHandler} />

<form
	class="flex flex-col h-full justify-between"
	on:submit|preventDefault={() => {
		updateHandler();
	}}
>
	<div class="space-y-6 overflow-y-auto">
		{#if config !== null}
			<!-- Direct Connections Section -->
			<div class="space-y-4">
				<div class="flex items-start justify-between gap-4">
					<div class="flex-1">
						<h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-1">
							{$i18n.t('Manage Direct Connections')}
						</h3>
						<p class="text-sm text-gray-500 dark:text-gray-400">
							Connect to your own OpenAI compatible API endpoints
						</p>
					</div>
					<Tooltip content={$i18n.t(`Add Connection`)}>
						<button
							class="flex items-center gap-2 px-4 py-2 text-sm font-medium bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors shadow-sm hover:shadow-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
							on:click={() => {
								showConnectionModal = true;
							}}
							type="button"
						>
							<Plus />
							<span>{$i18n.t('Add Connection')}</span>
						</button>
					</Tooltip>
				</div>

				<!-- Connections List -->
				{#if config?.OPENAI_API_BASE_URLS?.length > 0}
					<div class="space-y-3">
						{#each config?.OPENAI_API_BASE_URLS ?? [] as url, idx}
							<div class="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-4">
								<Connection
									bind:url
									bind:key={config.OPENAI_API_KEYS[idx]}
									bind:config={config.OPENAI_API_CONFIGS[idx]}
									onSubmit={() => {
										updateHandler();
									}}
									onDelete={() => {
										config.OPENAI_API_BASE_URLS = config.OPENAI_API_BASE_URLS.filter(
											(url, urlIdx) => idx !== urlIdx
										);
										config.OPENAI_API_KEYS = config.OPENAI_API_KEYS.filter(
											(key, keyIdx) => idx !== keyIdx
										);

										let newConfig = {};
										config.OPENAI_API_BASE_URLS.forEach((url, newIdx) => {
											newConfig[newIdx] =
												config.OPENAI_API_CONFIGS[newIdx < idx ? newIdx : newIdx + 1];
										});
										config.OPENAI_API_CONFIGS = newConfig;
									}}
								/>
							</div>
						{/each}
					</div>
				{:else}
					<div class="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-8 text-center">
						<div class="flex flex-col items-center gap-3">
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
										d="M13.19 8.688a4.5 4.5 0 011.242 7.244l-4.5 4.5a4.5 4.5 0 01-6.364-6.364l1.757-1.757m13.35-.622l1.757-1.757a4.5 4.5 0 00-6.364-6.364l-4.5 4.5a4.5 4.5 0 001.242 7.244"
									/>
								</svg>
							</div>
							<div>
								<div class="text-sm font-medium text-gray-900 dark:text-white mb-1">
									No connections configured
								</div>
								<div class="text-xs text-gray-500 dark:text-gray-400">
									Click "Add Connection" to get started
								</div>
							</div>
						</div>
					</div>
				{/if}

				<!-- Info Box -->
				<div
					class="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4"
				>
					<div class="flex gap-3">
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
							<div class="text-sm font-medium text-blue-900 dark:text-blue-100 mb-1">
								Important Information
							</div>
							<div class="text-xs text-blue-800 dark:text-blue-200 space-y-1">
								<p>
									{$i18n.t('Connect to your own OpenAI compatible API endpoints.')}
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
			</div>
		{:else}
			<!-- Loading State -->
			<div class="flex h-full items-center justify-center py-12">
				<div class="flex flex-col items-center gap-3">
					<Spinner className="size-8" />
					<div class="text-sm text-gray-500 dark:text-gray-400">Loading connections...</div>
				</div>
			</div>
		{/if}
	</div>

	<!-- Save Button -->
	<div class="flex justify-end pt-6 border-t border-gray-200 dark:border-gray-700 mt-6">
		<button
			class="px-6 py-2.5 text-sm font-medium bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors shadow-sm hover:shadow-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
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