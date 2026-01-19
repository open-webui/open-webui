<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { createEventDispatcher, onMount, getContext, tick } from 'svelte';
	import { getModels as _getModels } from '$lib/apis';

	const dispatch = createEventDispatcher();
	import type { Writable } from 'svelte/store';
	const i18n: Writable<any> = getContext('i18n');

	import { models, settings, user, toolServersConfigCache } from '$lib/stores';

	import Switch from '$lib/components/common/Switch.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import Connection from '$lib/components/chat/Settings/Tools/Connection.svelte';

	import AddToolServerModal from '$lib/components/AddToolServerModal.svelte';
	import { getToolServerConnections, setToolServerConnections } from '$lib/apis/configs';

	let servers: any[] = [];
	let showConnectionModal = false;

	const addConnectionHandler = async (server: any) => {
		servers = [...servers, server];
		await updateHandler();
	};

	const updateHandler = async () => {
		const res = await setToolServerConnections(localStorage.token, {
			TOOL_SERVER_CONNECTIONS: servers
		}).catch((err) => {
			toast.error($i18n.t('Failed to save connections'));

			return null;
		});

		if (res) {
			// Update cache after save
			toolServersConfigCache.set({ TOOL_SERVER_CONNECTIONS: servers });
			toast.success($i18n.t('Connections saved successfully'));
		}
	};

	onMount(async () => {
		// Use cached config if available
		if ($toolServersConfigCache) {
			servers = $toolServersConfigCache.TOOL_SERVER_CONNECTIONS ?? [];
		} else {
			const res = await getToolServerConnections(localStorage.token);
			servers = res.TOOL_SERVER_CONNECTIONS;
			toolServersConfigCache.set(res);
		}
	});
</script>

<AddToolServerModal bind:show={showConnectionModal} onSubmit={addConnectionHandler} />

<form
	class="flex flex-col h-full justify-between text-sm"
	on:submit|preventDefault={() => {
		updateHandler();
	}}
>
	<div class="overflow-y-scroll scrollbar-hidden h-full">
		{#if servers !== null}
			<div class="max-w-5xl mx-auto">
				<div class="mb-3">
					<div class="mt-0.5 mb-2.5 text-base font-medium">{$i18n.t('Tools')}</div>
					<hr class="border-gray-100/30 dark:border-gray-850/30 my-2" />

					<div
						class="bg-gray-50 dark:bg-gray-850 rounded-lg p-5 border border-gray-100 dark:border-gray-800"
					>
						<div class="mb-2.5 flex flex-col w-full justify-between">
							<!-- {$i18n.t(`Failed to connect to {{URL}} OpenAPI tool server`, {
								URL: 'server?.url'
							})} -->
							<div class="flex items-center gap-2 mb-4">
								<div class="text-xs font-medium text-gray-500">{$i18n.t('Manage Tool Servers')}</div>

								<Tooltip content={$i18n.t(`Add Connection`)}>
									<button
										class="p-1 bg-gray-200 hover:bg-gray-100 dark:bg-gray-800 dark:hover:bg-gray-700 rounded-full transition"
										on:click={() => {
											showConnectionModal = true;
										}}
										type="button"
									>
										<Plus className="size-3.5" />
									</button>
								</Tooltip>
							</div>

							<div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
								{#each servers as server, idx}
									<Connection
										bind:connection={server}
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

							<div class="text-xs text-gray-500">
								{$i18n.t('Connect to your own OpenAPI compatible external tool servers.')}
							</div>
						</div>
					</div>

					<!-- <div class="mb-2.5 flex w-full justify-between">
						<div class=" text-xs font-medium">{$i18n.t('Arena Models')}</div>

						<Tooltip content={$i18n.t(`Message rating should be enabled to use this feature`)}>
							<Switch bind:state={evaluationConfig.ENABLE_EVALUATION_ARENA_MODELS} />
						</Tooltip>
					</div> -->
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
