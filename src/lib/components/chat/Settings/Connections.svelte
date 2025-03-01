<script lang="ts">
	import { preventDefault } from 'svelte/legacy';
	import { onMount, getContext } from 'svelte';
	import { getModels as _getModels } from '$lib/apis';

	import { getI18nContext } from '$lib/contexts';
const i18n = getContext('i18n');

	import {
		settings,
		type DirectConnectionsSettings as DirectConnectionsSettingsType,
		type Connection as ConnectionType,
		type ConnectionConfig as ConnectionConfigType
	} from '$lib/stores';

	import Spinner from '$lib/components/common/Spinner.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import Connection from './Connections/Connection.svelte';

	import AddConnectionModal from '$lib/components/AddConnectionModal.svelte';

	interface Props {
		saveSettings: Function;
	}

	let { saveSettings }: Props = $props();

	let config = $state<DirectConnectionsSettingsType>({
		ENABLE_OPENAI_API: true,
		OPENAI_API_BASE_URLS: [],
		OPENAI_API_KEYS: [],
		OPENAI_API_CONFIGS: {}
	});

	let showConnectionModal = $state(false);

	const addConnectionHandler = async (
		connection: ConnectionType & { config: ConnectionConfigType }
	) => {
		if (!config) {
			return;
		}
		config.OPENAI_API_BASE_URLS.push(connection.url);
		config.OPENAI_API_KEYS.push(connection.key);
		config.OPENAI_API_CONFIGS[config.OPENAI_API_BASE_URLS.length - 1] = connection.config;

		await updateHandler();
	};

	const updateHandler = async () => {
		if (!config) {
			return;
		}
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
		if ($settings.directConnections) {
			config = $settings.directConnections;
		}
	});
</script>

<AddConnectionModal direct onSubmit={addConnectionHandler} bind:show={showConnectionModal} />

<form
	class="flex flex-col h-full justify-between text-sm"
	onsubmitcapture={(e) => {
		e.preventDefault();
		updateHandler();
	}}
>
	<div class=" overflow-y-scroll scrollbar-hidden h-full">
		{#if config !== null}
			<div class="">
				<div class="pr-1.5">
					<div class="">
						<div class="flex justify-between items-center mb-0.5">
							<div class="font-medium">{$i18n.t('Manage Direct Connections')}</div>

							<Tooltip content={$i18n.t(`Add Connection`)}>
								<button
									class="px-1"
									onclick={() => {
										showConnectionModal = true;
									}}
									type="button"
								>
									<Plus />
								</button>
							</Tooltip>
						</div>

						<div class="flex flex-col gap-1.5">
							{#each config?.OPENAI_API_BASE_URLS ?? [] as _, idx}
								<Connection
									onDelete={() => {
										config.OPENAI_API_BASE_URLS = config.OPENAI_API_BASE_URLS.filter(
											(url, urlIdx) => idx !== urlIdx
										);
										config.OPENAI_API_KEYS = config.OPENAI_API_KEYS.filter(
											(key, keyIdx) => idx !== keyIdx
										);

										const newConfig = [];
										config.OPENAI_API_BASE_URLS.forEach((url, newIdx) => {
											newConfig[newIdx] =
												config.OPENAI_API_CONFIGS[newIdx < idx ? newIdx : newIdx + 1];
										});
										config.OPENAI_API_CONFIGS = newConfig;
									}}
									onSubmit={() => {
										updateHandler();
									}}
									bind:url={config.OPENAI_API_BASE_URLS[idx]}
									bind:key={config.OPENAI_API_KEYS[idx]}
									bind:config={config.OPENAI_API_CONFIGS[idx]}
								/>
							{/each}
						</div>
					</div>

					<div class="my-1.5">
						<div class="text-xs text-gray-500">
							{$i18n.t('Connect to your own OpenAI compatible API endpoints.')}
							<br />
							{$i18n.t(
								'CORS must be properly configured by the provider to allow requests from Open WebUI.'
							)}
						</div>
					</div>
				</div>
			</div>
		{:else}
			<div class="flex h-full justify-center">
				<div class="my-auto">
					<Spinner className="size-6" />
				</div>
			</div>
		{/if}
	</div>

	<div class="flex justify-end pt-3 text-sm font-medium">
		<button
			class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full"
			type="submit"
		>
			{$i18n.t('Save')}
		</button>
	</div>
</form>
