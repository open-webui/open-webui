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
	class="flex flex-col h-full justify-between text-sm"
	on:submit|preventDefault={() => {
		updateHandler();
	}}
>
	<div class=" overflow-y-scroll scrollbar-hidden h-full">
		{#if servers !== null}
			<div class="">
				<div class="pr-1.5">
					<!-- {$i18n.t(`Failed to connect to {{URL}} OpenAPI tool server`, {
						URL: 'server?.url'
					})} -->
					<div class="">
						<div class="flex justify-between items-center mb-0.5">
							<div class="font-medium">{$i18n.t('Manage Tool Servers')}</div>

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

						<div class="flex flex-col gap-1.5">
							{#each servers as server, idx}
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
							{/each}
						</div>
					</div>

					<div class="my-1.5">
						<div class="text-xs text-gray-500">
							{$i18n.t('Connect to your own OpenAPI compatible external tool servers.')}
							<br />
							{$i18n.t(
								'CORS must be properly configured by the provider to allow requests from Open WebUI.'
							)}
						</div>
					</div>

					<div class=" text-xs text-gray-600 dark:text-gray-300 mb-2">
						<a
							class="underline"
							href="https://github.com/open-webui/openapi-servers"
							target="_blank">{$i18n.t('Learn more about OpenAPI tool servers.')}</a
						>
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
