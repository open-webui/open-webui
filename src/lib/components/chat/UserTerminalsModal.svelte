<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { v4 as uuidv4 } from 'uuid';
	import Modal from '$lib/components/common/Modal.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import DropdownMenu from '$lib/components/common/DropdownMenu.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import AccessButton from '$lib/components/common/AccessButton.svelte';
	import SettingsSelect from '$lib/components/common/SettingsSelect.svelte';
	import UserSettingSection from '$lib/components/chat/Settings/UserSettingSection.svelte';
	import UserSettingRow from '$lib/components/chat/Settings/UserSettingRow.svelte';
	import UserSettingField from '$lib/components/chat/Settings/UserSettingField.svelte';
	import EllipsisHorizontal from '$lib/components/icons/EllipsisHorizontal.svelte';
	import ArrowPath from '$lib/components/icons/ArrowPath.svelte';
	import GarbageBin from '$lib/components/icons/GarbageBin.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import ChevronRight from '$lib/components/icons/ChevronRight.svelte';
	import ModelSettingsLabel from '$lib/components/workspace/Models/ModelSettingsLabel.svelte';
	import AccessControl from '$lib/components/workspace/common/AccessControl.svelte';
	import {
		templatesApi,
		getTerminalServers,
		resolveTerminalTarget,
		type TerminalTarget
	} from '$lib/apis/terminal';
	import { terminalServers, user } from '$lib/stores';
	import TerminalSystemInfoModal from './TerminalSystemInfoModal.svelte';
	import Activity from '$lib/components/icons/Activity.svelte';
	import Folder from '$lib/components/icons/Folder.svelte';
	import Stop from '$lib/components/icons/Stop.svelte';
	import Play from '$lib/components/icons/Play.svelte';
	import TerminalFilesModal from './TerminalFilesModal.svelte';

	/** Edits one terminal, or creates one when `terminalId` is null. */
	export let show = true;
	export let terminalId: string | null = null;
	/** Connections the user may create terminals on. */
	export let connections: { id: string; name: string }[] = [];
	export let onCreate: (id: string) => Promise<void> = async () => {};

	const i18n = getContext<any>('i18n');
	const path = (id: string) => `/${encodeURIComponent(id)}`;
	const connectionOf = (id: string) => id.slice('template:'.length, id.lastIndexOf(':'));

	// '' is no scope: one machine for everyone with access.
	const scopes = [
		{ value: '', label: 'None', hint: 'All chats share one machine.' },
		{ value: 'user', label: 'User', hint: 'Each person gets their own machine.' },
		{ value: 'chat', label: 'Chat', hint: 'Each chat gets its own machine.' },
		{ value: 'model', label: 'Model', hint: 'Each model gets its own machine.' }
	];
	// Open Terminal reads these at start-up; the dialog gives them their own fields.
	const START_DIR = 'OPEN_TERMINAL_START_DIR';
	const SETUP_SCRIPT = 'OPEN_TERMINAL_SETUP_SCRIPT';
	const defaultImages = ['latest', 'agents', 'cuda', 'slim', 'alpine', 'openshift'].map(
		(tag) => `ghcr.io/open-webui/open-terminal:${tag}`
	);

	const inputClass =
		'h-7 w-full rounded-lg border border-gray-100/50 bg-gray-50/40 px-2 text-xs text-gray-700 outline-hidden transition-colors placeholder:text-gray-300 focus:border-blue-400 dark:border-white/[0.04] dark:bg-white/[0.03] dark:text-gray-300 dark:placeholder:text-gray-700 dark:focus:border-blue-500';
	const textareaClass =
		'w-full resize-y rounded-lg border border-gray-100/50 bg-gray-50/40 px-2 py-1.5 font-mono text-xs text-gray-700 outline-hidden transition-colors placeholder:text-gray-300 focus:border-blue-400 dark:border-white/[0.04] dark:bg-white/[0.03] dark:text-gray-300 dark:placeholder:text-gray-700 dark:focus:border-blue-500';
	const actionButtonClass =
		'text-xs text-gray-500 transition-colors hover:text-gray-900 dark:text-gray-500 dark:hover:text-white';
	const item =
		'select-none flex h-[1.6875rem] w-full items-center gap-2 rounded-xl px-2 text-[0.8125rem] hover:bg-gray-50/40 dark:hover:bg-gray-800/40 transition';

	let busy = false;
	let loading = !!terminalId;
	let error = '';
	let connectionId = connections[0]?.id ?? '';
	let name = '';
	let scope = '';
	let image = '';
	let cpu = '';
	let memory = '';
	let storage = '';
	let network = '';
	let env: { key: string; value: string }[] = [];
	let startDir = '';
	let setupScript = '';
	let showAdvanced = false;
	let status: any = null;
	let machines: any[] = [];
	let accessGrants: any[] = [];
	let showAccess = false;
	let confirmation: {
		title: string;
		message: string;
		label: string;
		run: () => Promise<void>;
	} | null = null;
	let showConfirm = false;

	$: serverId = terminalId ? connectionOf(terminalId) : connectionId;
	$: loadStatus(serverId);
	$: images = (status?.allowed_images ?? '')
		.split(',')
		.map((value: string) => value.trim())
		.filter((value: string) => value && !value.includes('*'));
	$: scopeLocked = !!terminalId && machines.length > 0;
	$: cpuMessage = cpuError(cpu, status?.max_cpu);
	$: memoryMessage = sizeError(memory, status?.max_memory);
	$: storageMessage = sizeError(storage, status?.max_storage);
	$: invalid = !!(cpuMessage || memoryMessage || storageMessage);
	$: summary = [
		startDir.trim(),
		setupScript.trim() && $i18n.t('Setup script'),
		image && image.split(':').pop(),
		cpu && `${cpu} CPU`,
		memory,
		storage,
		network,
		env.some((row) => row.key.trim()) &&
			$i18n.t('{{count}} variables', { count: env.filter((row) => row.key.trim()).length })
	]
		.filter(Boolean)
		.join(' · ');

	async function loadStatus(id: string) {
		status = null;
		if (!id) return;
		status = await templatesApi(`/connections/${encodeURIComponent(id)}/status`).catch(() => null);
	}

	const units: Record<string, number> = {
		'': 1,
		k: 1e3,
		m: 1e6,
		g: 1e9,
		t: 1e12,
		ki: 2 ** 10,
		mi: 2 ** 20,
		gi: 2 ** 30,
		ti: 2 ** 40
	};
	const bytes = (value: string) => {
		const match = /^(\d+(?:\.\d+)?)\s*([kmgt]i?)?b?$/i.exec(value.trim());
		return match ? Number(match[1]) * units[(match[2] ?? '').toLowerCase()] : null;
	};
	const limit = (max?: string | null) => (max ? $i18n.t('Up to {{max}}.', { max }) : '');
	function cpuError(value: string, max?: string | null) {
		if (!value.trim()) return '';
		const amount = Number(value);
		if (!Number.isFinite(amount) || amount <= 0) return $i18n.t('Enter a number, like 2.');
		return max && amount > Number(max) ? $i18n.t('Maximum is {{max}}.', { max }) : '';
	}
	function sizeError(value: string, max?: string | null) {
		if (!value.trim()) return '';
		const amount = bytes(value);
		if (amount === null) return $i18n.t('Enter a size, like 2Gi.');
		const cap = max ? bytes(max) : null;
		return cap !== null && amount > cap ? $i18n.t('Maximum is {{max}}.', { max }) : '';
	}

	async function run(work: () => Promise<void>) {
		busy = true;
		error = '';
		try {
			await work();
		} catch (e) {
			error = e instanceof Error ? e.message : String(e);
		} finally {
			busy = false;
		}
	}

	const refreshServers = async () =>
		terminalServers.set(await getTerminalServers(localStorage.token));

	async function loadMachines() {
		if (terminalId) machines = await templatesApi(`${path(terminalId)}/instances`);
	}

	async function load() {
		if (!terminalId) return;
		// The form fills from the terminal alone; machines and access load beside it.
		const [template, grants] = await Promise.all([
			templatesApi(path(terminalId)),
			templatesApi(`${path(terminalId)}/access`).catch(() => []),
			loadMachines().catch(() => (machines = []))
		]);
		const data = template?.data ?? {};
		name = data.name ?? '';
		scope = data.scope ?? '';
		image = data.image ?? '';
		cpu = data.cpu_limit ?? '';
		memory = data.memory_limit ?? '';
		storage = data.storage ?? '';
		network = data.network_profile ?? '';
		const { [START_DIR]: start, [SETUP_SCRIPT]: script, ...variables } = data.env ?? {};
		startDir = start ?? '';
		setupScript = script ?? '';
		env = Object.entries(variables).map(([key, value]) => ({ key, value: String(value) }));
		accessGrants = grants;
	}

	function payload() {
		const variables: Record<string, string> = Object.fromEntries(
			env
				.filter((row) => row.key.trim() && ![START_DIR, SETUP_SCRIPT].includes(row.key.trim()))
				.map((row) => [row.key.trim(), row.value])
		);
		if (startDir.trim()) variables[START_DIR] = startDir.trim();
		if (setupScript.trim()) variables[SETUP_SCRIPT] = setupScript;
		return {
			name: name.trim(),
			scope: scope || null,
			image: image.trim() || null,
			cpu_limit: cpu.trim() || null,
			memory_limit: memory.trim() || null,
			storage: storage.trim() || null,
			network_profile: network.trim() || null,
			env: Object.keys(variables).length ? variables : null
		};
	}

	async function save() {
		if (invalid) return;
		await run(async () => {
			const data = payload();
			if (!data.name) throw new Error($i18n.t('Enter a name.'));
			if (terminalId) {
				await templatesApi(path(terminalId), 'PATCH', data);
				await refreshServers();
			} else {
				const row = await templatesApi('', 'POST', {
					id: uuidv4(),
					connection_id: connectionId,
					data
				});
				await refreshServers();
				await onCreate(row.terminal_id);
			}
			show = false;
		});
	}

	async function saveAccess() {
		if (!terminalId) return;
		busy = true;
		try {
			await templatesApi(`${path(terminalId)}/access`, 'POST', { access_grants: accessGrants });
			toast.success($i18n.t('Saved'));
		} catch (e) {
			toast.error(`${e}`);
			accessGrants = await templatesApi(`${path(terminalId)}/access`).catch(() => accessGrants);
		} finally {
			busy = false;
		}
	}

	function confirm(title: string, message: string, label: string, work: () => Promise<void>) {
		confirmation = { title, message, label, run: work };
		showConfirm = true;
	}

	function machineName(machine: any) {
		const kind = (machine.context_id ?? '').split(':')[0];
		if (kind === 'default') return name || $i18n.t('Terminal');
		if (kind === 'chat') return machine.label ?? $i18n.t('Deleted chat');
		if (kind === 'user') return machine.label ?? $i18n.t('Deleted user');
		return machine.label ?? machine.context_id;
	}

	let info: { target: TerminalTarget; label: string } | null = null;
	let files: { target: TerminalTarget; label: string } | null = null;
	// Requests carry the viewer's identity, so another person's machine can't be reached this way.
	// Only running machines offer System info and files: Terminals won't start one for System info.
	function machineTarget(machine: any) {
		if (!terminalId || machine.status !== 'running') return null;
		const context = machine.context ?? {};
		if (context.user_id && context.user_id !== $user?.id) return null;
		return resolveTerminalTarget(terminalId, $terminalServers ?? [], [], localStorage.token ?? '', {
			chatId: context.chat_id ?? null,
			modelId: context.model_id ?? null
		});
	}

	const machineCopy = {
		restart: [
			'Restart {{name}}?',
			'Running work stops and the machine starts again. Files are kept.',
			'Restart'
		],
		stop: [
			'Stop {{name}}?',
			'Running work stops. Files are kept, and the machine starts again when it is next used.',
			'Stop'
		],
		delete: ['Delete {{name}}?', 'The machine and its files are deleted.', 'Delete']
	};

	const sendMachineAction = async (
		machine: any,
		action: 'restart' | 'stop' | 'start' | 'delete'
	) => {
		await templatesApi(
			`${path(terminalId!)}/${action === 'delete' ? 'instance' : action}`,
			action === 'delete' ? 'DELETE' : 'POST',
			machine.context ?? {}
		);
		await loadMachines();
	};

	function machineAction(machine: any, action: 'restart' | 'stop' | 'start' | 'delete') {
		// Starting changes nothing that is running, so it needs no confirmation.
		if (action === 'start') return run(() => sendMachineAction(machine, action));
		const [heading, message, button] = machineCopy[action];
		confirm(
			$i18n.t(heading, { name: machineName(machine) }),
			$i18n.t(message),
			$i18n.t(button),
			() => sendMachineAction(machine, action)
		);
	}

	function deleteTerminal() {
		confirm(
			$i18n.t('Delete {{name}}?', { name }),
			machines.length
				? $i18n.t('This deletes {{count}} machines and their files.', { count: machines.length })
				: $i18n.t('This terminal is deleted.'),
			$i18n.t('Delete'),
			async () => {
				await templatesApi(path(terminalId!), 'DELETE');
				await refreshServers();
				show = false;
			}
		);
	}

	onMount(() => {
		if (terminalId) run(load).finally(() => (loading = false));
	});
</script>

<Modal
	bind:show
	size="sm"
	ariaLabel={terminalId ? $i18n.t('Terminal settings') : $i18n.t('New terminal')}
>
	<div class="text-gray-900 dark:text-gray-100">
		<div class="flex items-center justify-between gap-2 px-5 pb-2 pt-4">
			<h2 class="font-primary min-w-0 truncate text-sm font-medium">
				{terminalId ? name || $i18n.t('Terminal settings') : $i18n.t('New terminal')}
			</h2>
			<div class="flex shrink-0 items-center gap-2">
				{#if terminalId && !loading}
					<AccessButton
						disabled={busy}
						label={accessGrants.length ? $i18n.t('Shared') : $i18n.t('Private')}
						on:click={() => (showAccess = true)}
					/>
				{/if}
				<button
					type="button"
					class="self-center text-gray-500 hover:text-gray-900 dark:hover:text-gray-100"
					on:click={() => (show = false)}
					aria-label={$i18n.t('Close')}><XMark className="size-4" /></button
				>
			</div>
		</div>

		{#if loading}
			<div class="flex justify-center py-10"><Spinner className="size-4" /></div>
		{:else}
			<form
				class="max-h-[min(40rem,80dvh)] overflow-y-auto px-5 pb-4"
				aria-busy={busy}
				on:submit|preventDefault={save}
			>
				{#if error}<p role="alert" class="mb-2 text-xs text-gray-700 dark:text-gray-300">
						{error}
					</p>{/if}

				<UserSettingSection first>
					<UserSettingField label={$i18n.t('Name')} forId="terminal-name">
						<input
							id="terminal-name"
							class={inputClass}
							bind:value={name}
							placeholder={$i18n.t('My terminal')}
							required
						/>
					</UserSettingField>

					{#if !terminalId && connections.length > 1}
						<UserSettingRow
							label={$i18n.t('Server')}
							description={$i18n.t('Choose the server that runs this terminal.')}
						>
							<SettingsSelect bind:value={connectionId} ariaLabel={$i18n.t('Server')}>
								{#each connections as connection}
									<option value={connection.id}>{connection.name}</option>
								{/each}
							</SettingsSelect>
						</UserSettingRow>
					{/if}

					<UserSettingRow
						label={$i18n.t('Separate machine per')}
						description={scopeLocked
							? $i18n.t('Delete all machines to change this.')
							: $i18n.t(scopes.find((option) => option.value === scope)?.hint ?? '')}
					>
						<SettingsSelect
							bind:value={scope}
							ariaLabel={$i18n.t('Separate machine per')}
							disabled={scopeLocked || busy}
						>
							{#each scopes as option}
								<option value={option.value}>{$i18n.t(option.label)}</option>
							{/each}
						</SettingsSelect>
					</UserSettingRow>
				</UserSettingSection>

				<div class="mt-1">
					<button
						type="button"
						class="grid w-full grid-cols-[7rem_minmax(0,1fr)_auto] items-center gap-2 rounded-md py-1.5 text-start text-xs font-normal focus-visible:outline focus-visible:outline-2 sm:grid-cols-[8rem_minmax(0,1fr)_auto]"
						aria-expanded={showAdvanced}
						on:click={() => (showAdvanced = !showAdvanced)}
					>
						<span class="text-gray-600 dark:text-gray-400"
							><ModelSettingsLabel
								label={$i18n.t('Advanced')}
								description={$i18n.t(
									'Image, resources, network, and environment variables. Unset values use the server defaults.'
								)}
							/></span
						>
						<span class="truncate text-gray-900 dark:text-gray-100">
							{summary || $i18n.t('Default')}
						</span>
						<ChevronRight
							className={`size-3 text-gray-400 transition-transform ${showAdvanced ? 'rotate-90' : ''}`}
						/>
					</button>

					{#if showAdvanced}
						<div class="mb-2 mt-1 grid grid-cols-1 gap-x-3 gap-y-2.5 sm:grid-cols-2">
							<UserSettingField
								className="sm:col-span-2"
								label={$i18n.t('Start directory')}
								forId="terminal-start-dir"
								description={$i18n.t(
									'Where every chat, shell, and command starts. Must be inside the home folder.'
								)}
							>
								<input
									id="terminal-start-dir"
									class="{inputClass} font-mono"
									bind:value={startDir}
									placeholder="~"
								/>
							</UserSettingField>

							<UserSettingField
								className="sm:col-span-2"
								label={$i18n.t('Setup script')}
								forId="terminal-setup-script"
								description={$i18n.t(
									'Runs in the start directory each time the machine starts, before it is ready. Only the home folder is kept between restarts, so make it safe to run again.'
								)}
							>
								<textarea
									id="terminal-setup-script"
									class={textareaClass}
									rows="4"
									spellcheck="false"
									bind:value={setupScript}
									placeholder={'test -d app || git clone https://github.com/acme/app app\ncd app && npm install'}
								></textarea>
							</UserSettingField>

							<UserSettingField
								className="sm:col-span-2"
								label={$i18n.t('Image')}
								forId="terminal-image"
								description={$i18n.t('Container image used to run the terminal.')}
							>
								<input
									id="terminal-image"
									list="terminal-image-options"
									class={inputClass}
									bind:value={image}
									placeholder={$i18n.t('Server default')}
								/>
								<datalist id="terminal-image-options">
									{#each images.length ? images : defaultImages as value}
										<option {value}></option>
									{/each}
								</datalist>
							</UserSettingField>

							<UserSettingField
								label={$i18n.t('CPU')}
								forId="terminal-cpu"
								description={cpuMessage ||
									[$i18n.t('CPU limit, for example 1 or 0.5.'), limit(status?.max_cpu)].join(' ')}
							>
								<input
									id="terminal-cpu"
									list="terminal-cpu-options"
									class={inputClass}
									bind:value={cpu}
									placeholder={$i18n.t('Server default')}
									aria-invalid={!!cpuMessage}
								/>
								<datalist id="terminal-cpu-options">
									{#each ['0.5', '1', '2', '4', '8'] as value}<option {value}></option>{/each}
								</datalist>
							</UserSettingField>

							<UserSettingField
								label={$i18n.t('Memory')}
								forId="terminal-memory"
								description={memoryMessage ||
									[$i18n.t('Memory limit, for example 2Gi.'), limit(status?.max_memory)].join(' ')}
							>
								<input
									id="terminal-memory"
									list="terminal-memory-options"
									class={inputClass}
									bind:value={memory}
									placeholder={$i18n.t('Server default')}
									aria-invalid={!!memoryMessage}
								/>
								<datalist id="terminal-memory-options">
									{#each ['512Mi', '1Gi', '2Gi', '4Gi', '8Gi', '16Gi'] as value}<option {value}
										></option>{/each}
								</datalist>
							</UserSettingField>

							<UserSettingField
								label={$i18n.t('Storage')}
								forId="terminal-storage"
								description={storageMessage ||
									[
										$i18n.t('Disk space for files, for example 10Gi.'),
										limit(status?.max_storage)
									].join(' ')}
							>
								<input
									id="terminal-storage"
									list="terminal-storage-options"
									class={inputClass}
									bind:value={storage}
									placeholder={$i18n.t('Server default')}
									aria-invalid={!!storageMessage}
								/>
								<datalist id="terminal-storage-options">
									{#each ['1Gi', '5Gi', '10Gi', '20Gi', '50Gi'] as value}<option {value}
										></option>{/each}
								</datalist>
							</UserSettingField>

							<UserSettingField
								label={$i18n.t('Network')}
								forId="terminal-network"
								description={$i18n.t('Network profile that controls outside access.')}
							>
								<input
									id="terminal-network"
									list="terminal-network-options"
									class={inputClass}
									bind:value={network}
									placeholder={$i18n.t('Server default')}
								/>
								<datalist id="terminal-network-options">
									{#each status?.network_profiles ?? [] as value}<option {value}></option>{/each}
								</datalist>
							</UserSettingField>

							<div class="sm:col-span-2">
								<div class="flex items-center justify-between">
									<span class="text-xs text-gray-600 dark:text-gray-400"
										>{$i18n.t('Environment variables')}</span
									>
									<button
										type="button"
										aria-label={$i18n.t('Add variable')}
										class="text-gray-500 hover:text-gray-900 dark:hover:text-white"
										on:click={() => (env = [...env, { key: '', value: '' }])}
										><Plus className="size-3.5" /></button
									>
								</div>
								{#each env as row, index}
									<div class="mt-1 flex items-center gap-1.5">
										<input
											class="{inputClass} font-mono"
											bind:value={row.key}
											placeholder="KEY"
											aria-label={$i18n.t('Variable name')}
										/>
										<input
											class={inputClass}
											bind:value={row.value}
											placeholder={$i18n.t('value')}
											aria-label={$i18n.t('Variable value')}
										/>
										<button
											type="button"
											aria-label={$i18n.t('Remove variable')}
											class="shrink-0 text-gray-400 hover:text-gray-900 dark:hover:text-white"
											on:click={() => (env = env.filter((_, i) => i !== index))}
											><XMark className="size-3.5" /></button
										>
									</div>
								{/each}
								<p class="mt-0.5 text-[0.6875rem] text-gray-400 dark:text-gray-600">
									{$i18n.t('Set when the machine starts.')}
								</p>
							</div>
						</div>
					{/if}
				</div>

				{#if terminalId}
					<section class="mt-4 w-full">
						<div class="mb-0.5 flex items-center gap-1.5 text-xs text-gray-600 dark:text-gray-400">
							{$i18n.t('Machines')}
							<span class="text-gray-400 dark:text-gray-600">{machines.length}</span>
						</div>
						<div class="flex flex-col gap-1 py-1">
							{#each machines as machine (machine.id)}
								{@const title = machineName(machine)}
								<div class="flex w-full items-center gap-1.5">
									<div class="min-w-0 flex-1 truncate text-xs text-gray-700 dark:text-gray-300">
										{title}{#if machine.user_name}<span class="text-gray-400 dark:text-gray-600">
												· {machine.user_name}</span
											>{/if}
									</div>
									<span class="shrink-0 text-xs text-gray-500">
										{machine.status === 'running' ? $i18n.t('Running') : $i18n.t('Stopped')}
									</span>
									<Dropdown align="end" closeOnSelect>
										<button
											type="button"
											class="flex size-6 shrink-0 items-center justify-center rounded-lg text-gray-400 hover:text-gray-700 dark:hover:text-gray-200"
											aria-label={$i18n.t('More options for {{name}}', { name: title })}
											disabled={busy}><EllipsisHorizontal className="size-3.5" /></button
										>
										<div slot="content">
											<DropdownMenu className="min-w-40">
												{@const target = machineTarget(machine)}
												{#if machine.status === 'running'}
													{#if target}
														<button
															type="button"
															class={item}
															on:click={() => (info = { target, label: title })}
															><Activity className="size-3.5" />{$i18n.t('System info')}</button
														>
														<button
															type="button"
															class={item}
															on:click={() => (files = { target, label: title })}
															><Folder className="size-3.5" />{$i18n.t('View files')}</button
														>
													{/if}
													<button
														type="button"
														class={item}
														on:click={() => machineAction(machine, 'restart')}
														><ArrowPath className="size-3.5" />{$i18n.t('Restart')}</button
													>
													<button
														type="button"
														class={item}
														on:click={() => machineAction(machine, 'stop')}
														><Stop className="size-3.5" />{$i18n.t('Stop')}</button
													>
												{:else}
													<button
														type="button"
														class={item}
														on:click={() => machineAction(machine, 'start')}
														><Play className="size-3.5" />{$i18n.t('Start')}</button
													>
												{/if}
												<hr class="border-gray-50 dark:border-gray-800/30 mx-1 my-0.5" />
												<button
													type="button"
													class={item}
													on:click={() => machineAction(machine, 'delete')}
													><GarbageBin className="size-3.5" />{$i18n.t('Delete machine')}</button
												>
											</DropdownMenu>
										</div>
									</Dropdown>
								</div>
							{:else}
								<div class="text-xs text-gray-400 dark:text-gray-600">
									{$i18n.t('No machines yet. One starts the first time the terminal is used.')}
								</div>
							{/each}
						</div>
					</section>
				{/if}

				<div class="flex items-center justify-between pt-4">
					<div>
						{#if terminalId}
							<button
								type="button"
								class={actionButtonClass}
								disabled={busy}
								on:click={deleteTerminal}>{$i18n.t('Delete terminal')}</button
							>
						{/if}
					</div>
					<button
						type="submit"
						class="flex h-7 shrink-0 items-center justify-center gap-1.5 rounded-lg bg-gray-900 px-2.5 text-xs font-normal text-white transition hover:bg-black disabled:opacity-60 dark:bg-gray-100 dark:text-gray-900 dark:hover:bg-white"
						disabled={busy || invalid || (!terminalId && !connectionId)}
					>
						{terminalId ? $i18n.t('Save') : $i18n.t('Create')}
						{#if busy}<Spinner className="size-3" />{/if}
					</button>
				</div>
			</form>
		{/if}
	</div>
</Modal>

{#if showAccess}
	<Modal ariaLabel={`${$i18n.t('Access')}: ${name}`} size="sm" bind:show={showAccess}>
		<div>
			<div class=" flex justify-between dark:text-gray-100 px-5 pt-3 pb-1">
				<div class=" text-sm self-center">
					{$i18n.t('Access')}: {name}
				</div>
				<button
					aria-label={$i18n.t('Close')}
					class="self-center rounded-lg py-1 text-gray-500 transition hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 px-0"
					on:click={() => (showAccess = false)}
				>
					<XMark className={'size-4'} />
				</button>
			</div>

			<div class="w-full px-5 pb-4 dark:text-white" inert={busy} aria-busy={busy}>
				<AccessControl
					bind:accessGrants
					labels={{ private: $i18n.t('Restricted') }}
					onChange={saveAccess}
					accessRoles={['read']}
					sharePublic={false}
					shareOpen={false}
				>
					<p class="text-xs text-gray-500 dark:text-gray-400">
						{$i18n.t('People with access can run commands and see every file on this terminal.')}
					</p>
				</AccessControl>
			</div>
		</div>
	</Modal>
{/if}

{#if info}
	{#key info}
		<TerminalSystemInfoModal
			target={info.target}
			label={info.label}
			onClose={() => (info = null)}
		/>
	{/key}
{/if}

{#if files}
	{#key files}
		<TerminalFilesModal target={files.target} label={files.label} onClose={() => (files = null)} />
	{/key}
{/if}

<ConfirmDialog
	bind:show={showConfirm}
	title={confirmation?.title ?? ''}
	message={confirmation?.message ?? ''}
	confirmLabel={confirmation?.label}
	onConfirm={() =>
		run(async () => {
			await confirmation?.run();
			showConfirm = false;
		})}
/>
