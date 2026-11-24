<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { createEventDispatcher, onDestroy, onMount, getContext, tick } from 'svelte';
	import { v4 as uuidv4 } from 'uuid';
	import { getBackendConfig, getModels as _getModels } from '$lib/apis';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';

	const dispatch = createEventDispatcher();
	const i18n = getContext<Writable<i18nType>>('i18n');

	import { config, models, settings, user, machines, socket } from '$lib/stores';
	import { getMachines, templatesApi } from '$lib/apis/machines';
	import { WEBUI_API_BASE_URL } from '$lib/constants';

	import Switch from '$lib/components/common/Switch.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import Cog6 from '$lib/components/icons/Cog6.svelte';
	import Cloud from '$lib/components/icons/Cloud.svelte';
	import Connection from '$lib/components/chat/Settings/Tools/Connection.svelte';
	import SensitiveInput from '$lib/components/common/SensitiveInput.svelte';

	import AddToolServerModal from '$lib/components/AddToolServerModal.svelte';
	import AddMachineModal from '$lib/components/AddMachineModal.svelte';
	import UserMachinesModal from '$lib/components/chat/UserMachinesModal.svelte';
	import ExternalKnowledge from './ExternalKnowledge.svelte';
	import Apps from './Apps.svelte';
	import AdminSettingSection from './AdminSettingSection.svelte';
	import AdminSettingRow from './AdminSettingRow.svelte';

	import {
		getToolServerConnections,
		setToolServerConnections,
		getMachineConnections,
		setMachineConnections
	} from '$lib/apis/configs';

	export let saveSettings: Function;

	type ToolServerConnection = any;
	type MachineConnection = {
		id?: string;
		url?: string;
		name?: string;
		key?: string;
		enabled?: boolean;
		[key: string]: any;
	};

	let servers: ToolServerConnection[] | null = null;
	let showConnectionModal = false;

	// Machine admin connections
	let machineConnections: MachineConnection[] | null = null;
	let showAddMachineModal = false;
	let editMachineIdx: number | null = null;

	// Terminals connections and their machines: the same dialog the machine menu opens.
	let writable: { id: string; name: string }[] = [];
	$: if ($machines)
		templatesApi('/connections')
			.then((rows) => (writable = rows))
			.catch(() => (writable = []));
	let showMachine = false;
	let machineId: string | null = null;
	let machineConnection: { id: string; name: string } | null = null;
	const openMachine = (connection: { id: string; name: string }, id: string | null = null) => {
		machineConnection = connection;
		machineId = id;
		showMachine = true;
	};
	const machinesOf = (items: any[] | null, connectionId: string) =>
		(items ?? []).filter(
			(m) => m.template_id && m.id.slice(0, m.id.lastIndexOf(':')) === `template:${connectionId}`
		);

	// Every section loads in parallel behind one spinner.
	let connectionsLoaded = false;
	let knowledgeLoaded = false;
	let appsLoaded = false;

	$: loaded =
		connectionsLoaded && knowledgeLoaded && (appsLoaded || !$config?.features?.enable_apps);

	const addConnectionHandler = async (server: ToolServerConnection) => {
		servers = [...(servers ?? []), server];
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
			toast.success($i18n.t('Connections saved successfully'));
		}
	};

	const saveMachines = async () => {
		const res = await setMachineConnections(localStorage.token, {
			MACHINE_CONNECTIONS: machineConnections
		}).catch((err) => {
			toast.error($i18n.t('Failed to save machines'));
			return null;
		});

		if (res) {
			toast.success($i18n.t('Machines saved'));
			await config.set(await getBackendConfig());

			// Refresh the machines store so changes are reflected immediately
			const systemMachines = await getMachines(localStorage.token);
			const systemEntries = systemMachines.map((t) => ({
				...t,
				url: `${WEBUI_API_BASE_URL}/machines/${t.id}`,
				name: t.name,
				key: localStorage.token,
				config: t.config ?? {}
			}));
			machines.set(systemEntries as any);
		}
	};

	const addMachineConnection = async (server: MachineConnection) => {
		if (/^(ssh|local):\/\//.test(String(server.url ?? ''))) {
			// Installed over SSH or on this computer: the backend already saved the machine.
			// Reload the list, then apply the rest of the form (name, access, options) to it.
			const res = await getMachineConnections(localStorage.token).catch(() => null);
			machineConnections = (res?.MACHINE_CONNECTIONS ?? machineConnections) as MachineConnection[];
			machineConnections = (machineConnections ?? []).map((c) =>
				c.id === server.id
					? {
							...c,
							...server,
							name: server.name || c.name, // an empty Name keeps the default the backend picked
							url: c.url,
							key: c.key,
							ssh: c.ssh,
							local: c.local
						}
					: c
			);
			await saveMachines();
			return;
		}
		machineConnections = [...(machineConnections ?? []), { ...server, id: server.id ?? uuidv4() }];
		saveMachines();
	};

	const updateMachineConnection = (idx: number, updated: MachineConnection) => {
		machineConnections = (machineConnections ?? []).map((c, i) =>
			i === idx ? { ...c, ...updated, id: updated.id ?? c.id } : c
		);
		saveMachines();
	};

	const removeMachineConnection = (idx: number) => {
		machineConnections = (machineConnections ?? []).filter((_, i) => i !== idx);
		saveMachines();
	};

	onMount(async () => {
		$socket?.on('events', machinesChanged);

		const [serverRes, machineRes] = await Promise.all([
			getToolServerConnections(localStorage.token).catch(() => null),
			getMachineConnections(localStorage.token).catch(() => null)
		]);

		// A list that failed to load stays null, so saving can't overwrite what is stored.
		if (serverRes) {
			servers = (serverRes.TOOL_SERVER_CONNECTIONS ?? []) as ToolServerConnection[];
		} else {
			toast.error($i18n.t('Failed to load connections'));
		}
		if (machineRes) {
			machineConnections = (machineRes.MACHINE_CONNECTIONS ?? []) as MachineConnection[];
		} else {
			toast.error($i18n.t('Failed to load machines'));
		}
		connectionsLoaded = true;
	});

	// An SSH install or upgrade finished (here or in another tab): show the machine's new state.
	const machinesChanged = async (event: { data?: { type?: string } }) => {
		if (event?.data?.type !== 'machines:changed') return;
		const res = await getMachineConnections(localStorage.token).catch(() => null);
		if (res?.MACHINE_CONNECTIONS) {
			machineConnections = res.MACHINE_CONNECTIONS as MachineConnection[];
		}
	};

	onDestroy(() => $socket?.off('events', machinesChanged));
</script>

<AddToolServerModal bind:show={showConnectionModal} onSubmit={addConnectionHandler} />

<AddMachineModal
	bind:show={showAddMachineModal}
	edit={editMachineIdx !== null}
	connection={editMachineIdx !== null ? (machineConnections?.[editMachineIdx] ?? null) : null}
	allowLocal={!(machineConnections ?? []).some((c) => c.local)}
	onSubmit={(c: MachineConnection) => {
		if (editMachineIdx !== null) {
			updateMachineConnection(editMachineIdx, c);
			editMachineIdx = null;
		} else {
			addMachineConnection(c);
		}
	}}
	onDelete={() => {
		if (editMachineIdx !== null) {
			removeMachineConnection(editMachineIdx);
			editMachineIdx = null;
		}
	}}
/>

{#if showMachine && machineConnection}
	<UserMachinesModal bind:show={showMachine} {machineId} connections={[machineConnection]} />
{/if}

<form
	class="flex h-full flex-col justify-between text-sm"
	on:submit|preventDefault={() => {
		updateHandler();
	}}
>
	<h2 class="text-sm font-medium text-base-900 dark:text-base-0 mb-4">
		{$i18n.t('settings.admin.integrations.title')}
	</h2>

	<div class="flex-1 min-h-0 overflow-y-auto scrollbar-hover pr-1.5">
		{#if !loaded}
			<div class="flex h-full justify-center">
				<div class="my-auto">
					<Spinner className="size-6" />
				</div>
			</div>
		{/if}

		<!-- Mounted while hidden so the sections inside can load. -->
		<div class={loaded ? '' : 'hidden'}>
			<fieldset
				disabled={!$config?.features?.enable_tool_servers}
				class="min-w-0 disabled:opacity-50"
			>
				<AdminSettingSection
					title={$i18n.t('settings.admin.integrations.sections.tools.title')}
					first
				>
					<div>
						<div class="mb-2 flex items-center justify-between">
							<Tooltip
								content={$i18n.t('Connect to your own OpenAPI compatible external tool servers.')}
								placement="top-start"
								className="w-fit"
							>
								<div
									class="text-xs text-base-600 dark:text-base-400 underline decoration-dotted decoration-base-400/70 underline-offset-4 dark:decoration-base-500 cursor-help"
								>
									{$i18n.t('settings.admin.integrations.externalToolServers.label')}
								</div>
							</Tooltip>

							<Tooltip content={$i18n.t('settings.admin.integrations.addConnection.label')}>
								<button
									aria-label={$i18n.t('settings.admin.integrations.addConnection.label')}
									disabled={servers === null}
									class="flex size-6 items-center justify-center rounded-lg text-base-400 transition-colors hover:bg-base-1000/5 hover:text-base-900 disabled:opacity-50 disabled:pointer-events-none dark:text-base-600 dark:hover:bg-base-0/5 dark:hover:text-base-0"
									on:click={() => {
										showConnectionModal = true;
									}}
									type="button"
								>
									<Plus />
								</button>
							</Tooltip>
						</div>

						<div class="flex flex-col gap-1">
							{#each servers ?? [] as server, idx}
								<Connection
									bind:connection={server}
									onSubmit={() => {
										updateHandler();
									}}
									onDelete={() => {
										servers = (servers ?? []).filter((_, i) => i !== idx);
										updateHandler();
									}}
								/>
							{/each}
						</div>

						{#if (servers ?? []).length === 0}
							<div class="text-[0.6875rem] text-base-400 dark:text-base-600">
								{servers === null
									? $i18n.t('Failed to load connections')
									: $i18n.t('No tool server connections configured.')}
							</div>
						{/if}
					</div>
				</AdminSettingSection>

				<AdminSettingSection title={$i18n.t('settings.admin.integrations.sections.machines.title')}>
					<div>
						<div class="mb-2 flex items-center justify-between">
							<div class="flex items-center gap-1.5 text-xs text-base-600 dark:text-base-400">
								<Tooltip
									content={$i18n.t(
										'Machines run Open Terminal. Admins and users granted access can browse files and use terminal tools on them.'
									)}
									placement="top-start"
									className="w-fit"
								>
									<div
										class="underline decoration-dotted decoration-base-400/70 underline-offset-4 dark:decoration-base-500 cursor-help"
									>
										{$i18n.t('settings.admin.integrations.openTerminal.label')}
									</div>
								</Tooltip>
								<Tooltip content={$i18n.t('Learn more about Open Terminal')}>
									<a
										class="text-base-400 transition-colors hover:text-base-700 dark:text-base-600 dark:hover:text-base-300"
										href="https://github.com/open-webui/open-terminal"
										target="_blank"
										rel="noopener noreferrer"
										aria-label={$i18n.t('Learn more about Open Terminal')}>↗</a
									>
								</Tooltip>
							</div>

							<Tooltip content={$i18n.t('Add Machine')}>
								<button
									aria-label={$i18n.t('Add Machine')}
									disabled={machineConnections === null}
									class="flex size-6 items-center justify-center rounded-lg text-base-400 transition-colors hover:bg-base-1000/5 hover:text-base-900 disabled:opacity-50 disabled:pointer-events-none dark:text-base-600 dark:hover:bg-base-0/5 dark:hover:text-base-0"
									on:click={() => {
										editMachineIdx = null;
										showAddMachineModal = true;
									}}
									type="button"
								>
									<Plus />
								</button>
							</Tooltip>
						</div>

						<div class="flex flex-col gap-1.5">
							{#each machineConnections ?? [] as connection, idx}
								{@const server = writable.find((c) => c.id === connection.id)}
								<div class="group/setting-row flex w-full gap-2 items-center">
									<Tooltip className="w-full relative" content={''} placement="top-start">
										<div class="flex w-full">
											<div
												class="flex-1 relative flex gap-1.5 items-center {connection?.enabled ===
												false
													? 'opacity-50'
													: ''}"
											>
												<Tooltip
													content={$i18n.t('settings.admin.integrations.openTerminal.label')}
												>
													<Cloud className="size-4" strokeWidth="1.5" />
												</Tooltip>

												<button
													type="button"
													on:click={() => {
														editMachineIdx = idx;
														showAddMachineModal = true;
													}}
													class="outline-hidden w-full min-w-0 truncate text-left cursor-pointer bg-transparent text-xs text-base-600 dark:text-base-400 transition-colors duration-150 group-hover/setting-row:text-base-900 group-focus-within/setting-row:text-base-900 dark:group-hover/setting-row:text-white dark:group-focus-within/setting-row:text-white"
												>
													{connection.name ||
														(connection.local ? $i18n.t('Local') : connection.url) ||
														$i18n.t('New Machine')}
												</button>
											</div>
										</div>
									</Tooltip>

									<div class="flex gap-1 items-center">
										{#if server}
											<Tooltip content={$i18n.t('New machine')}>
												<button
													aria-label={`${$i18n.t('New machine')}: ${server.name}`}
													class="flex size-6 items-center justify-center rounded-lg text-base-400 transition-colors hover:bg-base-1000/5 hover:text-base-900 dark:text-base-600 dark:hover:bg-base-0/5 dark:hover:text-base-0"
													on:click={() => openMachine(server)}
													type="button"
												>
													<Plus />
												</button>
											</Tooltip>
										{/if}

										<Tooltip content={$i18n.t('Configure')}>
											<button
												aria-label={$i18n.t('Configure')}
												class="self-center p-1 bg-transparent hover:bg-base-1000/5 dark:hover:bg-base-0/5 rounded-lg transition"
												on:click={() => {
													editMachineIdx = idx;
													showAddMachineModal = true;
												}}
												type="button"
											>
												<Cog6 />
											</button>
										</Tooltip>

										<Tooltip
											content={connection?.enabled !== false
												? $i18n.t('Enabled')
												: $i18n.t('Disabled')}
										>
											<Switch
												id={`terminal-${idx}-control`}
												state={connection?.enabled !== false}
												ariaLabel={`${$i18n.t('Enabled')}: ${connection.name || (connection.local ? $i18n.t('Local') : connection.url) || $i18n.t('New Machine')}`}
												on:change={() => {
													machineConnections = (machineConnections ?? []).map((c, i) =>
														i === idx ? { ...c, enabled: !(c?.enabled !== false) } : c
													);
													saveMachines();
												}}
											/>
										</Tooltip>
									</div>
								</div>
								{#if server}
									{#each machinesOf($machines, server.id) as machine (machine.id)}
										<!-- The name lines up with the connection's name, the gear with its gear. -->
										<div
											class="group/setting-row flex w-full gap-2 items-center pl-[1.375rem] pr-[2.125rem]"
										>
											<button
												type="button"
												on:click={() => openMachine(server, machine.id)}
												class="flex-1 outline-hidden min-w-0 truncate text-left cursor-pointer bg-transparent text-xs text-base-600 dark:text-base-400 transition-colors duration-150 group-hover/setting-row:text-base-900 group-focus-within/setting-row:text-base-900 dark:group-hover/setting-row:text-white dark:group-focus-within/setting-row:text-white"
											>
												{machine.name}
											</button>

											<Tooltip content={$i18n.t('Configure')}>
												<button
													aria-label={`${$i18n.t('Configure')}: ${machine.name}`}
													class="self-center p-1 bg-transparent hover:bg-base-1000/5 dark:hover:bg-base-0/5 rounded-lg transition"
													on:click={() => openMachine(server, machine.id)}
													type="button"
												>
													<Cog6 />
												</button>
											</Tooltip>
										</div>
									{/each}
								{/if}
							{/each}
						</div>

						{#if (machineConnections ?? []).length === 0}
							<div class="text-[0.6875rem] text-base-400 dark:text-base-600">
								{machineConnections === null
									? $i18n.t('Failed to load machines')
									: $i18n.t('No machines configured.')}
							</div>
						{/if}
					</div>
				</AdminSettingSection>
			</fieldset>

			<AdminSettingSection title={$i18n.t('settings.admin.integrations.sections.knowledge.title')}>
				<ExternalKnowledge bind:loaded={knowledgeLoaded} />
			</AdminSettingSection>

			{#if $config?.features?.enable_apps}
				<Apps bind:loaded={appsLoaded} />
			{/if}
		</div>
	</div>

	<div class="flex justify-end pt-6 text-sm font-normal">
		<button
			class="flex h-7 shrink-0 items-center justify-center gap-1.5 rounded-lg bg-base-900 px-2.5 text-xs font-normal text-base-0 transition hover:bg-base-1000 disabled:opacity-60 dark:bg-base-100 dark:text-base-900 dark:hover:bg-base-0"
			type="submit"
			disabled={!loaded || servers === null}
		>
			{$i18n.t('Save')}
		</button>
	</div>
</form>
