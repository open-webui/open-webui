<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { createEventDispatcher, onMount, getContext, tick } from 'svelte';
	import { getModels as _getModels } from '$lib/apis';

	const dispatch = createEventDispatcher();
	const i18n = getContext('i18n');

	import { models, user } from '$lib/stores';

	import Switch from '$lib/components/common/Switch.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import Connection from './Connections/Connection.svelte';

	import AddConnectionModal from '$lib/components/AddConnectionModal.svelte';

	const getModels = async () => {
		const models = await _getModels(localStorage.token);
		return models;
	};

	let config = null;

	let showConnectionModal = false;

	onMount(async () => {});

	const addConnectionHandler = async (connection) => {};

	const submitHandler = async () => {};
	const updateHandler = async () => {};
</script>

<AddConnectionModal direct bind:show={showConnectionModal} onSubmit={addConnectionHandler} />

<form class="flex flex-col h-full justify-between text-sm" on:submit|preventDefault={submitHandler}>
	<div class=" overflow-y-scroll scrollbar-hidden h-full">
		<div class="my-2">
			<div class="pr-1.5">
				<div class="">
					<div class="flex justify-between items-center">
						<div class="font-medium">{$i18n.t('Manage Direct Connections')}</div>

						<Tooltip content={$i18n.t(`Add Connection`)}>
							<button
								class="px-1"
								on:click={() => {
									showConnectionModal = true;
								}}
								type="button"
							>
								<Plus />
							</button>
						</Tooltip>
					</div>

					<div class="flex flex-col gap-1.5 mt-1.5">
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
										newConfig[newIdx] =
											config.OPENAI_API_CONFIGS[newIdx < idx ? newIdx : newIdx + 1];
									});
									config.OPENAI_API_CONFIGS = newConfig;
								}}
							/>
						{/each}
					</div>
				</div>

				<hr class=" border-gray-50 dark:border-gray-850" />

				<div class="mt-1.5">
					<div class="text-xs text-gray-500">
						{$i18n.t('Connect to your own OpenAI compatible API endpoints.')}
					</div>
				</div>
			</div>
		</div>
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
