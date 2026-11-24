<script lang="ts">
	import { getContext, onDestroy, tick } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { v4 as uuidv4 } from 'uuid';
	import Modal from '$lib/components/common/Modal.svelte';
	import Collapsible from '$lib/components/common/Collapsible.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import ArrowPath from '$lib/components/icons/ArrowPath.svelte';
	import Check from '$lib/components/icons/Check.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import SensitiveInput from '$lib/components/common/SensitiveInput.svelte';
	import AccessControl from '$lib/components/workspace/common/AccessControl.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import ExperimentalBadge from '$lib/components/common/ExperimentalBadge.svelte';
	import { getMachineConnections, verifyMachineConnection } from '$lib/apis/configs';
	import {
		configureMachine,
		createSSHKeypair,
		formatSSHUrl,
		getLocalMachineDefaults,
		getMachineLogs,
		installLocalMachine,
		installMachinePackages,
		installSSHKey,
		installSSHMachine,
		parseSSHUrl,
		probeSSHMachine,
		removeMachine,
		restartMachine,
		upgradeMachine,
		type ManagedMachineInfo,
		type SSHMachineInfo
	} from '$lib/apis/machines';
	import { socket } from '$lib/stores';
	import { copyToClipboard } from '$lib/utils';
	const i18n = getContext<any>('i18n');
	export let show = false;
	export let edit = false;
	export let connection: any = null;
	export let onSubmit: Function = () => {};
	export let onDelete: () => void = () => {};
	// Offer the Local type (experimental): Open WebUI runs Open Terminal on its own server.
	export let allowLocal = true;
	let initialized = false;
	let url = '';
	let key = '';
	let name = '';
	let id = '';
	let auth_type = 'bearer';
	let forwardCookies = false;
	let chatUploads = 'filesystem';
	let workingDirectoryContext = true;
	let userShellTools = 'auto';
	let path = '/openapi.json';
	let serverType: string | null = null;
	let accessGrants: any[] = [];
	let busy = false;
	let error = '';
	let showDelete = false;
	// SSH: an ssh://user@host URL installs Open Terminal on that machine instead of connecting to one.
	const SSH_STEPS = ['connect', 'detect', 'install', 'configure', 'start', 'health', 'ready'];
	// SSH only: what `open-terminal install-deps` adds to the machine, typed as names separated by
	// spaces. These are the names it knows itself; any other name is an apt package.
	const INSTALL_DEPS = ['desktop', 'browser'];
	let toInstall = '';
	// The Install button: only that step runs, and what it reports shows under the field.
	let installingPackages = false;
	let packagesResult: { text: string; failed: boolean } | null = null;
	// How Open WebUI logs in the first time to add its own key. Nothing here is stored.
	let signIn: 'password' | 'key' | 'manual' = 'password';
	let password = '';
	let privateKey = '';
	let openTerminalVersion = ''; // empty means latest
	// Type when adding: Remote (a URL or ssh://) or Local (the server Open WebUI runs on).
	let target: 'url' | 'local' = 'url';
	let startDir = ''; // where terminal sessions start; empty is the default
	let flags = ''; // extra flags for `open-terminal run`
	let localDefaults: { start_dir: string; added: boolean } | null = null;
	let passphrase = '';
	let keyFileInput: HTMLInputElement;
	let sshPhase: 'form' | 'fingerprint' | 'authorize' | 'installing' = 'form';
	let hostKey: { host_key: string; fingerprint: string } | null = null;
	let keypair: { id: string; public_key: string } | null = null;
	let steps: string[] = [];
	let running = false;
	let logs: string | null = null;
	let logsElement: HTMLPreElement;
	let showForceDelete = false;
	let stopListening: (() => void) | null = null;
	const input =
		'w-full min-w-0 bg-transparent py-0.5 text-sm text-base-900 outline-hidden placeholder:text-base-300 dark:text-base-100 dark:placeholder:text-base-700';
	const select =
		'min-w-0 bg-transparent pr-5 text-sm text-base-900 outline-hidden dark:text-base-100';
	// Quiet text actions, matching the Delete and Back links.
	const action =
		'text-xs text-base-500 transition hover:text-base-800 hover:underline disabled:opacity-50 disabled:no-underline dark:text-base-400 dark:hover:text-base-200';
	const button =
		'flex h-7 items-center justify-center gap-1.5 rounded-lg px-2.5 text-xs font-normal transition hover:bg-base-100 dark:hover:bg-base-850 disabled:opacity-50';
	// Machines Open WebUI installed Open Terminal on: over SSH, or on this computer.
	$: managed = (connection?.ssh ?? connection?.local ?? null) as ManagedMachineInfo | null;
	$: sshMachine = (connection?.ssh ?? null) as SSHMachineInfo | null;
	$: localMachine = !!connection?.local;
	$: installingLocal = !connection && target === 'local';
	$: installingSSH = !managed && !installingLocal && url.trim().toLowerCase().startsWith('ssh://');
	$: installing = installingSSH || installingLocal;
	$: sshTarget = installingSSH ? parseSSHUrl(url) : null;
	$: installNames = toInstall.trim().split(/\s+/).filter(Boolean);
	$: installForm = {
		deps: installNames.filter((name) => INSTALL_DEPS.includes(name)),
		packages: installNames.filter((name) => !INSTALL_DEPS.includes(name))
	};
	$: installSteps = installNames.length
		? SSH_STEPS.flatMap((step) => (step === 'install' ? [step, 'packages'] : [step]))
		: SSH_STEPS;
	$: showLocalOption = allowLocal && !connection && localDefaults !== null && !localDefaults.added;
	$: if (show && !initialized) {
		url = connection?.url ?? '';
		key = connection?.key ?? '';
		name = connection?.name ?? '';
		id = connection?.id ?? '';
		auth_type = connection?.auth_type ?? 'bearer';
		forwardCookies = connection?.forward_cookies ?? false;
		path = connection?.path ?? '/openapi.json';
		serverType = connection?.server_type ?? null;
		accessGrants = connection?.config?.access_grants ?? [];
		chatUploads = connection ? (connection.config?.chat_uploads ?? 'default') : 'filesystem';
		const current = connection?.ssh ?? connection?.local;
		openTerminalVersion =
			current?.requested_version && current.requested_version !== 'latest'
				? current.requested_version
				: '';
		startDir = current?.start_dir ?? '';
		flags = current?.flags ?? '';
		toInstall = [...(current?.deps ?? []), ...(current?.packages ?? [])].join(' ');
		target = 'url';
		localDefaults = null;
		if (allowLocal && !connection) {
			getLocalMachineDefaults(localStorage.token)
				.then((defaults) => (localDefaults = defaults))
				.catch(() => {});
		}
		workingDirectoryContext = connection?.config?.working_directory_context ?? true;
		userShellTools = connection?.config?.user_shell_tools ?? 'auto';
		error = '';
		signIn = 'password';
		password = '';
		privateKey = '';
		passphrase = '';
		resetSSH();
		logs = null;
		installingPackages = false;
		packagesResult = null;
		initialized = true;
	}
	$: if (!show) {
		initialized = false;
		stopListening?.();
	}
	onDestroy(() => stopListening?.());
	function resetSSH() {
		sshPhase = 'form';
		hostKey = null;
		keypair = null;
		steps = [];
	}
	function stepLabel(step: string) {
		switch (step) {
			case 'connect':
				return $i18n.t('Connecting');
			case 'detect':
				return $i18n.t('Checking the machine');
			case 'install':
				return $i18n.t('Installing Open Terminal');
			case 'packages':
				return $i18n.t('Installing packages');
			case 'configure':
				return $i18n.t('Configuring');
			case 'start':
				return $i18n.t('Starting Open Terminal');
			case 'health':
				return $i18n.t('Checking that it responds');
			default:
				return $i18n.t('Ready');
		}
	}
	// Follow `machines:progress` events for one machine until it is ready or fails.
	function follow(
		machineId: string,
		onDone: (ok: boolean, message?: string, output?: string) => void
	) {
		stopListening?.();
		steps = [];
		running = true;
		const handler = (event: any) => {
			const data = event?.data;
			if (data?.type !== 'machines:progress' || data.id !== machineId) return;
			if (data.step === 'error') {
				stop();
				onDone(false, data.message);
				return;
			}
			steps = [...steps.filter((step) => step !== data.step), data.step];
			if (data.step === 'ready') {
				stop();
				// A message here is a warning: ready, but packages are missing.
				onDone(true, data.message, data.output);
			}
		};
		const stop = () => {
			$socket?.off('events', handler);
			running = false;
			stopListening = null;
		};
		$socket?.on('events', handler);
		stopListening = stop;
	}
	function configuration() {
		const result = {
			...(connection?.config ?? {}),
			chat_uploads: chatUploads,
			working_directory_context: workingDirectoryContext,
			user_shell_tools: userShellTools
		};
		delete result.contexts;
		result.access_grants = accessGrants;
		return result;
	}
	async function verify(announce = false) {
		busy = true;
		error = '';
		try {
			const type = (await verifyMachineConnection(localStorage.token, { url, key, auth_type }))
				.type;
			if (!type) throw new Error('Failed to connect to the machine');
			serverType = type;
			if (announce) toast.success($i18n.t('Server connection verified'));
			return true;
		} catch (e) {
			error = e instanceof Error ? e.message : String(e);
			return false;
		} finally {
			busy = false;
		}
	}
	async function save() {
		if (!serverType && !(await verify())) return;
		busy = true;
		error = '';
		try {
			if (
				managed &&
				(startDir.trim() !== (managed.start_dir ?? '') || flags.trim() !== (managed.flags ?? ''))
			) {
				await configureMachine(localStorage.token, connection.id, {
					start_dir: startDir.trim(),
					flags: flags.trim()
				});
			}
			const result = {
				...(connection ?? {}),
				url: url.trim().replace(/\/$/, ''),
				key,
				name: name.trim(),
				path,
				auth_type: serverType === 'orchestrator' ? 'bearer' : auth_type,
				enabled: connection?.enabled ?? true,
				forward_cookies: forwardCookies,
				server_type: serverType,
				config: configuration()
			};
			for (const old of ['instances', 'policy_id', 'policy', 'lifecycle']) delete result[old];
			result.id = connection?.id || id.trim() || uuidv4();
			await onSubmit(result);
			show = false;
		} catch (e) {
			error = e instanceof Error ? e.message : String(e);
		} finally {
			busy = false;
		}
	}
	async function submit() {
		if (installingLocal) return startLocalInstall();
		if (!installingSSH) return save();
		if (sshPhase === 'form') return hostKey ? authorize() : checkHost();
		if (sshPhase === 'fingerprint') return authorize();
		if (sshPhase === 'authorize') return startInstall();
	}
	async function run(action: () => Promise<void>) {
		busy = true;
		error = '';
		try {
			await action();
		} catch (e) {
			error = e instanceof Error ? e.message : String(e);
		} finally {
			busy = false;
		}
	}
	// 1. Show the host key so the admin can confirm it is the machine they expect.
	const checkHost = () =>
		run(async () => {
			if (!sshTarget) throw new Error($i18n.t('Use ssh://user@host or ssh://user@host:port'));
			hostKey = await probeSSHMachine(localStorage.token, sshTarget);
			sshPhase = 'fingerprint';
		});
	// 2. Log in once with the password or private key to add Open WebUI's key, then install.
	//    With "Add key myself", show the command to run on the machine instead.
	const authorize = () =>
		run(async () => {
			if (!sshTarget || !hostKey) return;
			keypair ??= await createSSHKeypair(localStorage.token);
			if (signIn === 'manual') {
				sshPhase = 'authorize';
				return;
			}
			try {
				await installSSHKey(localStorage.token, {
					...sshTarget,
					host_key: hostKey.host_key,
					id: keypair.id,
					public_key: keypair.public_key,
					...(signIn === 'key' ? { private_key: privateKey, passphrase } : { password })
				});
			} catch (e) {
				// Refused: show the error, and the command that adds the key by hand. Back returns to the form.
				sshPhase = 'authorize';
				throw e;
			}
			password = privateKey = passphrase = '';
			await startInstall();
		});
	async function loadKeyFile(event: Event) {
		const file = (event.currentTarget as HTMLInputElement).files?.[0];
		if (file) privateKey = (await file.text()).trim();
		(event.currentTarget as HTMLInputElement).value = '';
	}
	// 3. Install Open Terminal and follow its progress.
	async function startInstall() {
		if (!sshTarget || !hostKey || !keypair) return;
		const machine = keypair;
		await install(machine.id, 'ssh', () =>
			installSSHMachine(localStorage.token, {
				...sshTarget!,
				host_key: hostKey!.host_key,
				id: machine.id,
				name: name.trim(),
				version: openTerminalVersion.trim() || 'latest',
				start_dir: startDir.trim(),
				flags: flags.trim(),
				...installForm
			})
		);
	}
	// Local: no sign-in, install right away.
	async function startLocalInstall() {
		const machineId = `m_${uuidv4().replace(/-/g, '').slice(0, 8)}`;
		await install(machineId, 'local', () =>
			installLocalMachine(localStorage.token, {
				id: machineId,
				name: name.trim(),
				version: openTerminalVersion.trim() || 'latest',
				start_dir: startDir.trim(),
				flags: flags.trim()
			})
		);
	}
	async function install(
		machineId: string,
		kind: 'ssh' | 'local',
		request: () => Promise<unknown>
	) {
		sshPhase = 'installing';
		error = '';
		follow(machineId, async (ok, message) => {
			if (!ok) {
				error = message ?? $i18n.t('Installation failed');
				sshPhase = 'form';
				return;
			}
			try {
				// The machine is saved; apply the rest of this form to it.
				await onSubmit({
					id: machineId,
					url: `${kind}://${machineId}`,
					name: name.trim(),
					path: '/openapi.json',
					auth_type: 'bearer',
					enabled: true,
					forward_cookies: forwardCookies,
					server_type: 'terminal',
					config: configuration(),
					[kind]: {}
				});
				if (message) toast.warning(message);
				show = false;
			} catch (e) {
				error = e instanceof Error ? e.message : String(e);
				sshPhase = 'form';
			}
		});
		try {
			await request();
		} catch (e) {
			stopListening?.();
			error = e instanceof Error ? e.message : String(e);
			sshPhase = 'form';
		}
	}
	const authorizeCommand = (publicKey: string) =>
		`mkdir -p ~/.ssh && chmod 700 ~/.ssh && echo '${publicKey}' >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys`;
	// Existing machines Open WebUI installed (SSH or this computer)
	// Show what the machine has now: its version, packages, and any warning.
	async function refreshManaged() {
		const res = await getMachineConnections(localStorage.token).catch(() => null);
		const updated = res?.MACHINE_CONNECTIONS?.find((c: any) => c.id === connection.id);
		if (updated?.ssh) connection = { ...connection, ssh: updated.ssh };
		if (updated?.local) connection = { ...connection, local: updated.local };
	}
	const upgrade = () =>
		run(async () => {
			installingPackages = false;
			follow(connection.id, async (ok, message) => {
				if (!ok) {
					error = message ?? $i18n.t('Upgrade failed');
					return;
				}
				if (message) toast.warning(message);
				else toast.success($i18n.t('Machine upgraded'));
				await refreshManaged();
			});
			try {
				await upgradeMachine(localStorage.token, connection.id, {
					version: openTerminalVersion.trim() || 'latest',
					...(sshMachine ? installForm : {})
				});
			} catch (e) {
				stopListening?.();
				throw e;
			}
		});
	const installPackages = () =>
		run(async () => {
			installingPackages = true;
			packagesResult = null;
			follow(connection.id, async (ok, message, output) => {
				installingPackages = false;
				steps = [];
				packagesResult = ok
					? { text: output?.trim() || $i18n.t('Packages installed'), failed: false }
					: { text: message ?? $i18n.t('Installation failed'), failed: true };
				if (ok) await refreshManaged();
			});
			try {
				await installMachinePackages(localStorage.token, connection.id, installForm);
			} catch (e) {
				stopListening?.();
				installingPackages = false;
				packagesResult = { text: e instanceof Error ? e.message : String(e), failed: true };
			}
		});
	const restart = () =>
		run(async () => {
			await restartMachine(localStorage.token, connection.id);
			toast.success($i18n.t('Machine restarted'));
		});
	const toggleLogs = () =>
		run(async () => {
			logs = logs === null ? (await getMachineLogs(localStorage.token, connection.id)).logs : null;
			await tick();
			if (logsElement) logsElement.scrollTop = logsElement.scrollHeight; // show the newest lines
		});
	const remove = (force = false) =>
		run(async () => {
			if (managed) {
				try {
					await removeMachine(localStorage.token, connection.id, force);
				} catch (e) {
					if (force) throw e;
					showForceDelete = true;
					return;
				}
			}
			onDelete();
			show = false;
		});
</script>

<Modal bind:show size="sm" ariaLabel={edit ? $i18n.t('Edit Machine') : $i18n.t('Add Machine')}>
	<div class="flex items-center justify-between px-4 pb-2 pt-3 dark:text-base-100">
		<h2 class="text-sm font-medium">
			{edit ? $i18n.t('Edit Machine') : $i18n.t('Add Machine')}
		</h2>
		<button
			type="button"
			class="shrink-0 self-center"
			on:click={() => (show = false)}
			aria-label={$i18n.t('Close')}><XMark className="size-4" /></button
		>
	</div>
	<form
		class="space-y-2 px-4 pb-4 text-base-900 dark:text-base-100"
		on:submit|preventDefault={submit}
	>
		{#if error}<p role="alert" class="text-sm text-base-700 dark:text-base-300">{error}</p>{/if}
		{#if showLocalOption || localMachine}
			<div class="flex items-center justify-between">
				<div class="text-xs text-base-500">{$i18n.t('Type')}</div>
				<button
					type="button"
					class="flex items-center gap-1.5 text-xs text-base-700 dark:text-base-300"
					disabled={localMachine || sshPhase !== 'form'}
					on:click={() => {
						target = target === 'local' ? 'url' : 'local';
						error = '';
						resetSSH();
					}}
				>
					{#if localMachine || target === 'local'}
						{$i18n.t('Local')}
						<ExperimentalBadge />
					{:else}
						{$i18n.t('Remote')}
					{/if}
				</button>
			</div>
		{/if}
		<div class="flex gap-2">
			<div class="min-w-0 flex-1">
				<!-- Earlier wording, kept so i18n:parse does not drop its translations: $i18n.t('My Terminal') -->
				<label for="terminal-name" class="mb-0.5 block text-xs text-base-500"
					>{$i18n.t('Name')}</label
				>
				<input
					id="terminal-name"
					class={input}
					bind:value={name}
					placeholder={installingLocal ? $i18n.t('Local') : $i18n.t('My Machine')}
					required={!installingLocal}
				/>
			</div>
			{#if !installing && !managed}
				<div class="min-w-0 flex-1">
					<label for="terminal-id" class="mb-0.5 block text-xs text-base-500">
						{$i18n.t('ID')} <span class="opacity-50">({$i18n.t('optional')})</span>
					</label>
					<input
						id="terminal-id"
						class="{input} font-mono"
						bind:value={id}
						placeholder="auto"
						disabled={!!connection?.id}
						autocomplete="off"
					/>
				</div>
			{/if}
		</div>
		{#if !installingLocal && !localMachine}
			<div class="flex items-end gap-2">
				<div class="min-w-0 flex-1">
					<label for="terminal-url" class="mb-0.5 block text-xs text-base-500"
						>{$i18n.t('URL')}</label
					>
					{#if sshMachine}
						<input id="terminal-url" class={input} value={formatSSHUrl(sshMachine)} disabled />
					{:else}
						<input
							id="terminal-url"
							class={input}
							bind:value={url}
							type="url"
							placeholder="https://machine.example.com or ssh://user@host"
							required
							disabled={sshPhase !== 'form'}
							on:input={() => {
								serverType = null;
								resetSSH();
							}}
						/>
					{/if}
				</div>
				{#if !installingSSH}
					<Tooltip content={$i18n.t('Verify Connection')}>
						<button
							type="button"
							class="rounded-lg p-1 transition hover:bg-base-100 disabled:opacity-50 dark:hover:bg-base-850"
							disabled={busy || !url}
							on:click={() => verify(true)}
							aria-label={$i18n.t('Verify Connection')}
							>{#if busy}<Spinner className="size-4" />{:else}<ArrowPath
									className="size-4"
								/>{/if}</button
						>
					</Tooltip>
				{/if}
			</div>
		{/if}
		{#if installingSSH}
			{#if sshPhase === 'form'}
				<div>
					<label for="ssh-sign-in" class="mb-0.5 block text-xs text-base-500"
						>{$i18n.t('Sign in with')}</label
					>
					<div class="flex items-start gap-2">
						<select id="ssh-sign-in" class="{select} shrink-0 py-0.5" bind:value={signIn}>
							<option value="password">{$i18n.t('Password')}</option>
							<option value="key">{$i18n.t('Private key')}</option>
							<option value="manual">{$i18n.t('Add key myself')}</option>
						</select>
						<div class="min-w-0 flex-1">
							{#if signIn === 'password'}
								<SensitiveInput
									id="ssh-password"
									bind:value={password}
									placeholder={$i18n.t('SSH password')}
								/>
							{:else if signIn === 'key'}
								<textarea
									id="ssh-private-key"
									class="{input} h-16 resize-none font-mono text-xs"
									bind:value={privateKey}
									placeholder="-----BEGIN OPENSSH PRIVATE KEY-----"
									aria-label={$i18n.t('Private key')}
									spellcheck="false"
									autocomplete="off"
									required
								></textarea>
								<div class="flex items-center gap-2">
									<SensitiveInput
										id="ssh-passphrase"
										bind:value={passphrase}
										placeholder={$i18n.t('Passphrase (if the key has one)')}
										required={false}
									/>
									<button
										type="button"
										class="shrink-0 text-xs text-base-500 hover:text-base-800 hover:underline dark:hover:text-base-200"
										on:click={() => keyFileInput.click()}>{$i18n.t('Upload')}</button
									>
									<input
										bind:this={keyFileInput}
										type="file"
										class="hidden"
										accept=".pem,.key,.ppk,text/plain,application/x-pem-file"
										on:change={loadKeyFile}
									/>
								</div>
							{:else}
								<p class="py-0.5 text-xs text-base-500">
									{$i18n.t('You will get a command to run on the machine.')}
								</p>
							{/if}
						</div>
					</div>
					{#if signIn !== 'manual'}
						<p class="mt-1 text-xs text-base-500">
							{$i18n.t('Used once to authorize Open WebUI, never stored.')}
						</p>
					{/if}
				</div>
			{:else if sshPhase === 'fingerprint' && hostKey}
				<div class="rounded-lg bg-base-50 p-2.5 text-xs dark:bg-base-850">
					<p class="text-base-600 dark:text-base-300">
						{$i18n.t('Confirm this is the machine you expect. Its host key fingerprint is:')}
					</p>
					<p class="mt-1 break-all font-mono">{hostKey.fingerprint}</p>
				</div>
			{:else if sshPhase === 'authorize' && keypair}
				<div class="rounded-lg bg-base-50 p-2.5 text-xs dark:bg-base-850">
					<p class="text-base-600 dark:text-base-300">
						{signIn === 'manual'
							? $i18n.t('Run this on the machine as {{user}}, then continue:', {
									user: sshTarget?.username ?? ''
								})
							: $i18n.t('Or run this on the machine as {{user}}, then continue:', {
									user: sshTarget?.username ?? ''
								})}
					</p>
					<pre
						class="mt-1.5 whitespace-pre-wrap break-all font-mono text-[0.6875rem]">{authorizeCommand(
							keypair.public_key
						)}</pre>
					<button
						type="button"
						class="mt-1.5 text-xs text-base-500 hover:text-base-800 hover:underline dark:hover:text-base-200"
						on:click={async () => {
							if (keypair && (await copyToClipboard(authorizeCommand(keypair.public_key))))
								toast.success($i18n.t('Copied to clipboard'));
						}}>{$i18n.t('Copy')}</button
					>
				</div>
			{/if}
		{:else if managed}
			<div>
				<div class="mb-0.5 text-xs text-base-500">{$i18n.t('Status')}</div>
				<div class="flex items-center justify-between gap-3">
					<div class="flex min-w-0 items-center gap-1.5 py-0.5 text-sm">
						<span
							class="size-1.5 shrink-0 rounded-full {managed.status === 'error'
								? 'bg-red-500'
								: running || managed.status === 'installing'
									? 'bg-yellow-500'
									: 'bg-green-500'}"
						></span>
						<span
							>{managed.status === 'error'
								? $i18n.t('Error')
								: running || managed.status === 'installing'
									? $i18n.t('Installing')
									: $i18n.t('Ready')}</span
						>
						<span class="truncate text-xs text-base-500"
							>{$i18n.t('Open Terminal {{version}}', { version: managed.version ?? '' })}</span
						>
					</div>
					<div class="flex shrink-0 items-center gap-3">
						{#if busy}<Spinner className="size-3" />{/if}
						<button type="button" class={action} disabled={busy || running} on:click={upgrade}
							>{$i18n.t('Upgrade')}</button
						>
						<button type="button" class={action} disabled={busy || running} on:click={restart}
							>{$i18n.t('Restart')}</button
						>
						<button type="button" class={action} disabled={busy || running} on:click={toggleLogs}
							>{logs === null ? $i18n.t('Logs') : $i18n.t('Hide logs')}</button
						>
					</div>
				</div>
				{#if managed.status === 'error' && managed.error}
					<p class="mt-0.5 text-xs text-base-700 dark:text-base-300">{managed.error}</p>
				{/if}
				{#if logs !== null}
					<pre
						bind:this={logsElement}
						class="mt-2 max-h-48 overflow-auto whitespace-pre rounded-lg bg-base-50 p-2 font-mono text-[0.6875rem] leading-relaxed text-base-600 dark:bg-base-850 dark:text-base-400">{logs ||
							$i18n.t('No logs yet.')}</pre>
				{/if}
			</div>
		{:else if !installingLocal}
			<div>
				<label for="terminal-auth-type" class="mb-0.5 block text-xs text-base-500"
					>{$i18n.t('Auth')}</label
				>
				<div class="flex items-start gap-2">
					<select id="terminal-auth-type" class="{select} shrink-0 py-0.5" bind:value={auth_type}>
						<option value="bearer">{$i18n.t('Bearer')}</option>
						<option value="none">{$i18n.t('None')}</option>
						<option value="session">{$i18n.t('Session')}</option>
						<option value="system_oauth">{$i18n.t('OAuth')}</option>
					</select>
					<div class="min-w-0 flex-1">
						<SensitiveInput bind:value={key} placeholder={$i18n.t('API Key')} required={false} />
						{#if auth_type === 'session'}
							<p class="mt-1 text-xs text-base-500">
								{$i18n.t('Forwards system user session credentials to authenticate')}
							</p>
						{:else if auth_type === 'system_oauth'}
							<p class="mt-1 text-xs text-base-500">
								{$i18n.t('Forwards system user OAuth access token to authenticate')}
							</p>
						{:else if auth_type === 'none'}
							<p class="mt-1 text-xs text-base-500">{$i18n.t('No authentication')}</p>
						{/if}
					</div>
				</div>
			</div>
		{/if}
		{#if (installing && sshPhase === 'form') || managed}
			<div class="flex items-center gap-2 text-xs">
				<Tooltip
					className="shrink-0"
					placement="top-start"
					content={managed
						? $i18n.t('Added to "open-terminal run". Saving a change restarts Open Terminal.')
						: $i18n.t('Added to "open-terminal run".')}
				>
					<label
						for="open-terminal-flags"
						class="cursor-help text-base-500 underline decoration-dotted decoration-base-400/70 underline-offset-4 dark:decoration-base-500"
						>{$i18n.t('Flags')}</label
					>
				</Tooltip>
				<input
					id="open-terminal-flags"
					class="w-full min-w-0 bg-transparent py-0.5 font-mono text-xs text-base-900 outline-hidden placeholder:text-base-300 dark:text-base-100 dark:placeholder:text-base-700"
					bind:value={flags}
					placeholder="--desktop-mode host"
					autocomplete="off"
					autocapitalize="off"
					spellcheck="false"
				/>
			</div>
			{#if installingSSH || sshMachine}
				<div class="flex items-center gap-2 text-xs">
					<Tooltip
						className="shrink-0"
						placement="top-start"
						content={$i18n.t(
							'Installed with apt, using sudo without a password. "desktop" and "browser" add a desktop and Chrome; any other name is an apt package.'
						)}
					>
						<label
							for="machine-packages"
							class="cursor-help text-base-500 underline decoration-dotted decoration-base-400/70 underline-offset-4 dark:decoration-base-500"
							>{$i18n.t('Packages')}</label
						>
					</Tooltip>
					<input
						id="machine-packages"
						class="w-full min-w-0 bg-transparent py-0.5 font-mono text-xs text-base-900 outline-hidden placeholder:text-base-300 dark:text-base-100 dark:placeholder:text-base-700"
						bind:value={toInstall}
						placeholder="desktop browser ffmpeg"
						pattern="\s*([a-z0-9][a-z0-9+.\-]*\s*)*"
						autocomplete="off"
						spellcheck="false"
					/>
					{#if managed}
						<button
							type="button"
							class="{action} shrink-0"
							disabled={busy || running || !installNames.length}
							on:click={installPackages}>{$i18n.t('Install')}</button
						>
					{/if}
				</div>
				{#if installingPackages}
					<div class="flex items-center gap-1.5 text-xs text-base-500" aria-live="polite">
						<Spinner className="size-3" />{$i18n.t('Installing packages')}
					</div>
				{:else if packagesResult || managed?.warning}
					<pre
						role={packagesResult?.failed ? 'alert' : undefined}
						class="max-h-32 overflow-auto whitespace-pre-wrap break-words font-mono text-xs {packagesResult &&
						!packagesResult.failed
							? 'text-base-500'
							: 'text-base-700 dark:text-base-300'}">{packagesResult?.text ??
							managed?.warning}</pre>
				{/if}
			{/if}
			<div class="flex items-center gap-2 text-xs">
				<Tooltip
					className="shrink-0"
					placement="top-start"
					content={managed
						? $i18n.t('Leave empty for the latest release. Upgrade installs this version.')
						: $i18n.t('Leave empty for the latest release.')}
				>
					<label
						for="open-terminal-version"
						class="cursor-help text-base-500 underline decoration-dotted decoration-base-400/70 underline-offset-4 dark:decoration-base-500"
						>{$i18n.t('Version')}</label
					>
				</Tooltip>
				<input
					id="open-terminal-version"
					class="w-full min-w-0 bg-transparent py-0.5 font-mono text-xs text-base-900 outline-hidden placeholder:text-base-300 dark:text-base-100 dark:placeholder:text-base-700"
					bind:value={openTerminalVersion}
					placeholder="latest"
					pattern="latest|\d+\.\d+\.\d+"
					autocomplete="off"
				/>
			</div>
			<div>
				<div class="mb-0.5 flex text-xs text-base-500">
					<Tooltip placement="top-start" content={$i18n.t('Where terminal sessions start.')}>
						<label
							for="machine-start-dir"
							class="cursor-help underline decoration-dotted decoration-base-400/70 underline-offset-4 dark:decoration-base-500"
							>{$i18n.t('Start directory')}</label
						>
					</Tooltip>
				</div>
				<input
					id="machine-start-dir"
					class={input}
					bind:value={startDir}
					placeholder={installingLocal || localMachine
						? (localDefaults?.start_dir ?? $i18n.t('Project folder'))
						: $i18n.t('Home folder')}
					autocomplete="off"
					spellcheck="false"
				/>
			</div>
			{#if installingLocal || localMachine}
				<p class="text-xs text-base-500">
					{$i18n.t(
						'Runs on the server Open WebUI runs on. Anyone you share it with can run commands there.'
					)}
				</p>
			{/if}
		{/if}
		{#if !installingPackages && (sshPhase === 'installing' || running || steps.length)}
			<ol class="space-y-1 text-xs" aria-live="polite">
				{#each installSteps as step}
					{@const index = steps.indexOf(step)}
					{@const current = running && index === steps.length - 1}
					<li
						class="flex items-center gap-1.5 {index < 0
							? 'text-base-400 dark:text-base-600'
							: 'text-base-700 dark:text-base-300'}"
					>
						<span class="flex size-3.5 items-center justify-center">
							{#if current}<Spinner className="size-3" />{:else if index >= 0}<Check
									className="size-3"
									strokeWidth="2.5"
								/>{/if}
						</span>
						{stepLabel(step)}
					</li>
				{/each}
			</ol>
		{/if}
		{#if serverType === 'orchestrator'}
			<p class="text-xs text-base-500">
				{$i18n.t('Create and configure machines from the machine selector.')}
			</p>
		{/if}
		<div>
			<label for="terminal-chat-uploads" class="mb-0.5 block text-xs text-base-500"
				>{$i18n.t('Chat Uploads')}</label
			>
			<select id="terminal-chat-uploads" class="{select} w-full" bind:value={chatUploads}>
				<option value="default">{$i18n.t('Default')}</option>
				<option value="filesystem">{$i18n.t('Filesystem')}</option>
			</select>
		</div>
		<Collapsible
			title={$i18n.t('Advanced')}
			buttonClassName="flex w-full py-1 text-xs text-base-500 transition hover:text-base-700 dark:text-base-400 dark:hover:text-base-200"
			chevronClassName="size-3.5"
			chevronStrokeWidth="2"
		>
			<div slot="content" class="mt-2 space-y-3">
				<div class="flex items-center justify-between gap-3">
					<div>
						<label for="working-directory-context" class="text-xs font-medium"
							>{$i18n.t('Working Directory Context')}</label
						>
						<p class="text-xs text-base-500">
							{$i18n.t('Include the current directory in tool instructions.')}
						</p>
					</div>
					<Switch
						id="working-directory-context"
						ariaLabel={$i18n.t('Working Directory Context')}
						bind:state={workingDirectoryContext}
					/>
				</div>
				<div class="flex items-center justify-between gap-3">
					<div>
						<label for="user-shell-tools" class="text-xs font-medium"
							>{$i18n.t('User Shell Tools')}</label
						>
						<p class="text-xs text-base-500">
							{#if userShellTools === 'auto'}
								{$i18n.t('Include tools only while your shell is connected.')}
							{:else}
								{$i18n.t('Keep tools listed even while your shell is closed.')}
							{/if}
						</p>
					</div>
					<select
						id="user-shell-tools"
						class="{select} max-w-[45%] shrink-0 text-xs"
						bind:value={userShellTools}
					>
						<option value="auto">{$i18n.t('Automatic')}</option>
						<option value="always">{$i18n.t('Always Include')}</option>
					</select>
				</div>
				<div class="flex items-center justify-between gap-3">
					<div>
						<label for="forward-cookies" class="text-xs font-medium"
							>{$i18n.t('Forward cookies')}</label
						>
						<p class="text-xs text-base-500">
							{$i18n.t('Forward cookies from your Open WebUI request to this server.')}
						</p>
					</div>
					<Switch
						id="forward-cookies"
						ariaLabel={$i18n.t('Forward cookies')}
						bind:state={forwardCookies}
					/>
				</div>
				{#if !installing && !managed}
					<div>
						<label for="openapi-path" class="mb-0.5 block text-xs font-medium"
							>{$i18n.t('OpenAPI Spec')}</label
						>
						<input
							id="openapi-path"
							class={input}
							bind:value={path}
							placeholder={$i18n.t('openapi.json URL or Path')}
						/>
						<p class="mt-1 break-all text-xs text-base-500">
							{$i18n.t('WebUI will make requests to "{{url}}"', {
								url: path.includes('://') ? path : `${url}${path.startsWith('/') ? '' : '/'}${path}`
							})}
						</p>
					</div>
				{/if}
			</div>
		</Collapsible>
		<Collapsible
			title={$i18n.t('Access')}
			buttonClassName="flex w-full py-1 text-xs text-base-500 transition hover:text-base-700 dark:text-base-400 dark:hover:text-base-200"
			chevronClassName="size-3.5"
			chevronStrokeWidth="2"
		>
			<div slot="content" class="mt-2">
				<AccessControl bind:accessGrants accessRoles={['read', 'write']} onChange={() => {}} />
			</div>
		</Collapsible>
		<div class="flex items-center justify-between pt-3">
			<div>
				{#if edit}
					<button
						type="button"
						class="px-1 py-1.5 text-xs text-base-500 transition hover:text-base-700 hover:underline dark:text-base-400 dark:hover:text-base-200"
						disabled={busy}
						on:click={() => (showDelete = true)}>{$i18n.t('Delete')}</button
					>
				{:else if installingSSH && (sshPhase === 'fingerprint' || sshPhase === 'authorize')}
					<button
						type="button"
						class="px-1 py-1.5 text-xs text-base-500 transition hover:text-base-700 hover:underline dark:text-base-400 dark:hover:text-base-200"
						disabled={busy}
						on:click={() => (sshPhase = 'form')}>{$i18n.t('Back')}</button
					>
				{/if}
			</div>
			<button
				class="{button} bg-base-900 text-base-0 hover:bg-base-1000 dark:bg-base-100 dark:text-base-900 dark:hover:bg-base-0"
				disabled={busy || (!url && !installingLocal) || sshPhase === 'installing'}
			>
				{#if !installing}
					{$i18n.t('Save')}
				{:else if sshPhase === 'fingerprint'}
					{$i18n.t('Trust and install')}
				{:else if sshPhase === 'authorize'}
					{$i18n.t('Continue')}
				{:else if sshPhase === 'installing'}
					{$i18n.t('Installing')}
				{:else}
					{$i18n.t('Install')}
				{/if}
				{#if busy || sshPhase === 'installing'}<Spinner className="size-3" />{/if}
			</button>
		</div>
	</form>
</Modal>
<ConfirmDialog
	bind:show={showDelete}
	message={managed
		? $i18n.t('Remove this machine? This also uninstalls Open Terminal from it.')
		: $i18n.t('Delete this connection?')}
	confirmLabel={$i18n.t('Delete')}
	on:confirm={() => remove()}
/>
<ConfirmDialog
	bind:show={showForceDelete}
	message={$i18n.t(
		"Couldn't reach the machine to uninstall Open Terminal. Remove it from Open WebUI anyway?"
	)}
	confirmLabel={$i18n.t('Remove')}
	on:confirm={() => remove(true)}
/>
