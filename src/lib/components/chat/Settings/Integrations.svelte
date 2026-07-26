<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { onMount, getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	import { getToolServersData } from '$lib/apis';

	const i18n = getContext<Writable<i18nType>>('i18n');

	import { settings, toolServers, terminalServers } from '$lib/stores';

	import Spinner from '$lib/components/common/Spinner.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import Connection from './Tools/Connection.svelte';
	import Terminals from './Integrations/Terminals.svelte';
	import UserSettingSection from './UserSettingSection.svelte';

	import AddToolServerModal from '$lib/components/AddToolServerModal.svelte';

	type TerminalServerConfig = {
		url: string;
		key?: string;
		name?: string;
		enabled: boolean;
		auth_type?: string;
		path?: string;
		[key: string]: any;
	};

	type ToolServerConnection = any;

	export let saveSettings: (settings: any) => void | Promise<void>;

	let servers: ToolServerConnection[] | null = null;
	let terminalServerConfigs: TerminalServerConfig[] = [];
	let showConnectionModal = false;
	const helpTextClass = 'text-[0.6875rem] text-gray-400 dark:text-gray-600';

	const addConnectionHandler = async (server: ToolServerConnection) => {
		servers = [...(servers ?? []), server];
		await updateHandler();
	};

	const updateHandler = async () => {
		await saveSettings({
			toolServers: servers,
			terminalServers: terminalServerConfigs
		});

		let toolServersData = await getToolServersData($settings?.toolServers ?? []);
		toolServersData = toolServersData.filter((data: any) => {
			if (data.error) {
				toast.error(
					$i18n.t(`Failed to connect to {{URL}} OpenAPI tool server`, { URL: data?.url })
				);
				return false;
			}
			return true;
		});
		toolServers.set(toolServersData as any);

		// Refresh terminal servers store (preserve system terminals)
		const existingSystemTerminals = (($terminalServers ?? []) as any[]).filter((t) => t.id);
		const activeTerminals = terminalServerConfigs.filter((s) => s.enabled);
		if (activeTerminals.length > 0) {
			let terminalServersData = await getToolServersData(
				activeTerminals.map((t) => ({
					url: t.url,
					auth_type: t.auth_type ?? 'bearer',
					key: t.key ?? '',
					path: t.path ?? '/openapi.json',
					config: { enable: true }
				}))
			);
			terminalServersData = terminalServersData.filter((data: any) => data && !data.error);
			terminalServers.set([...terminalServersData, ...existingSystemTerminals] as any);
		} else {
			terminalServers.set(existingSystemTerminals as any);
		}
	};

	onMount(async () => {
		servers = $settings?.toolServers ?? [];
		terminalServerConfigs = ($settings as any)?.terminalServers ?? [];
	});
</script>

<AddToolServerModal bind:show={showConnectionModal} onSubmit={addConnectionHandler} direct />

<form
	id="tab-tools"
	class="flex flex-col h-full justify-between text-sm"
	on:submit|preventDefault={() => {
		updateHandler();
	}}
>
	<h2 class="text-sm font-medium text-gray-900 dark:text-white mb-4">{$i18n.t('Integrations')}</h2>

	<div class="flex-1 min-h-0 overflow-y-auto scrollbar-hover pr-1.5">
		{#if servers !== null}
			<UserSettingSection title={$i18n.t('Tools')} first>
				<div>
					<div class="mb-2 flex items-center justify-between">
						<div class="text-xs text-gray-600 dark:text-gray-400">
							{$i18n.t('External Tool Servers')}
						</div>

						<Tooltip content={$i18n.t('Add Connection')}>
							<button
								aria-label={$i18n.t('Add Connection')}
								class="flex size-6 items-center justify-center rounded-lg text-gray-400 transition-colors hover:bg-black/5 hover:text-gray-900 dark:text-gray-600 dark:hover:bg-white/5 dark:hover:text-white"
								on:click={() => (showConnectionModal = true)}
								type="button"
							>
								<Plus />
							</button>
						</Tooltip>
					</div>

					<div class="flex flex-col gap-1">
						{#each servers as server, idx}
							<Connection
								bind:connection={server}
								direct
								onSubmit={() => updateHandler()}
								onDelete={() => {
									servers = (servers ?? []).filter((_, i) => i !== idx);
									updateHandler();
								}}
							/>
						{/each}
					</div>

					{#if (servers ?? []).length === 0}
						<div class={helpTextClass}>
							{$i18n.t('No tool server connections configured.')}
						</div>
					{/if}

					<div class="mt-1 {helpTextClass}">
						{$i18n.t('Connect to your own OpenAPI compatible external tool servers.')}
					</div>
					<div class={helpTextClass}>
						{$i18n.t(
							'CORS must be properly configured by the provider to allow requests from Open WebUI.'
						)}
						<a
							class="ml-1 text-gray-500 underline hover:text-gray-700 dark:text-gray-500 dark:hover:text-gray-300"
							href="https://github.com/open-webui/openapi-servers"
							target="_blank">{$i18n.t('Learn more about OpenAPI tool servers.')} ↗</a
						>
					</div>
				</div>
			</UserSettingSection>

			<UserSettingSection title={$i18n.t('Terminal')}>
				<Terminals bind:servers={terminalServerConfigs} onChange={() => updateHandler()} />

				<div class="mt-1 {helpTextClass}">
					{$i18n.t(
						'Connect to Open Terminal instances to browse files and use them as always-on tools. Only one can be active at a time.'
					)}
				</div>
				<a
					class="mt-0.5 block text-[0.6875rem] text-gray-500 underline hover:text-gray-700 dark:text-gray-500 dark:hover:text-gray-300"
					href="https://github.com/open-webui/open-terminal"
					target="_blank">{$i18n.t('Learn more about Open Terminal')} ↗</a
				>
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
