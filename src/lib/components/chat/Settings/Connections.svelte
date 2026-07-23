<script lang="ts">
	import { onMount, getContext } from 'svelte';

	const i18n = getContext('i18n');

	import { settings } from '$lib/stores';

	import Spinner from '$lib/components/common/Spinner.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import Connection from './Connections/Connection.svelte';
	import UserSettingSection from './UserSettingSection.svelte';

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
	id="tab-connections"
	class="flex flex-col h-full justify-between text-sm"
	on:submit|preventDefault={() => {
		updateHandler();
	}}
>
	<h2 class="text-sm font-medium text-gray-900 dark:text-white mb-4">{$i18n.t('Connections')}</h2>

	<div class="flex-1 min-h-0 overflow-y-auto scrollbar-hover pr-1.5">
		{#if config !== null}
			<UserSettingSection title={$i18n.t('Manage Direct Connections')} first>
				<div class="flex items-center justify-between gap-2.5">
					<div class="min-w-0 text-[0.6875rem] text-gray-400 dark:text-gray-600">
						{$i18n.t('Connect to your own OpenAI compatible API endpoints.')}
					</div>

					<Tooltip content={$i18n.t(`Add Connection`)}>
						<button
							class="flex size-6 items-center justify-center rounded-lg text-gray-400 transition-colors hover:text-gray-700 dark:text-gray-600 dark:hover:text-gray-300"
							aria-label={$i18n.t('Add Connection')}
							on:click={() => {
								showConnectionModal = true;
							}}
							type="button"
						>
							<Plus />
						</button>
					</Tooltip>
				</div>

				<div class="flex flex-col gap-2">
					{#each config?.OPENAI_API_BASE_URLS ?? [] as url, idx}
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
									newConfig[newIdx] = config.OPENAI_API_CONFIGS[newIdx < idx ? newIdx : newIdx + 1];
								});
								config.OPENAI_API_CONFIGS = newConfig;
							}}
						/>
					{/each}
				</div>

				<div class="text-[0.6875rem] text-gray-400 dark:text-gray-600">
					{$i18n.t(
						'CORS must be properly configured by the provider to allow requests from Open WebUI.'
					)}
				</div>
			</UserSettingSection>
		{:else}
			<div class="flex h-full justify-center">
				<div class="my-auto">
					<Spinner className="size-6" />
				</div>
			</div>
		{/if}
	</div>

	<div class="shrink-0 flex justify-end pt-3 text-sm font-normal">
		<button
			class="px-3.5 py-1.5 text-sm font-normal bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full"
			type="submit"
		>
			{$i18n.t('Save')}
		</button>
	</div>
</form>
