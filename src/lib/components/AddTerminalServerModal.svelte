<script lang="ts">
	import { getContext } from 'svelte';
	import { v4 as uuidv4 } from 'uuid';
	import Modal from '$lib/components/common/Modal.svelte';
	import Collapsible from '$lib/components/common/Collapsible.svelte';
	import SettingsSelect from '$lib/components/common/SettingsSelect.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import SensitiveInput from '$lib/components/common/SensitiveInput.svelte';
	import AccessControl from '$lib/components/workspace/common/AccessControl.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import { detectTerminalServerType, verifyTerminalServerConnection } from '$lib/apis/configs';
	const i18n = getContext<any>('i18n');
	export let show = false;
	export let edit = false;
	export let direct = false;
	export let connection: any = null;
	export let onSubmit: Function = () => {};
	export let onDelete: () => void = () => {};
	let initialized = false;
	let url = '';
	let key = '';
	let name = '';
	let auth_type = 'bearer';
	let enabled = true;
	let forwardCookies = false;
	let chatUploads = 'default';
	let workingDirectoryContext = true;
	let userShellTools = 'auto';
	let path = '/openapi.json';
	let serverType: string | null = null;
	let accessGrants: any[] = [];
	let busy = false;
	let error = '';
	let showDelete = false;
	const input =
		'mt-1 w-full min-w-0 bg-transparent py-1 text-sm outline-hidden placeholder:text-gray-400 dark:placeholder:text-gray-600';
	const button =
		'flex h-7 items-center justify-center gap-1.5 rounded-lg px-2.5 text-xs font-normal transition hover:bg-gray-100 dark:hover:bg-gray-850 disabled:opacity-50';
	$: if (show && !initialized) {
		url = connection?.url ?? '';
		key = connection?.key ?? '';
		name = connection?.name ?? '';
		auth_type = connection?.auth_type ?? 'bearer';
		enabled = connection?.enabled ?? true;
		forwardCookies = connection?.forward_cookies ?? false;
		path = connection?.path ?? '/openapi.json';
		serverType = connection?.server_type ?? null;
		accessGrants = connection?.config?.access_grants ?? [];
		chatUploads = connection?.config?.chat_uploads ?? 'default';
		workingDirectoryContext = connection?.config?.working_directory_context ?? true;
		userShellTools = connection?.config?.user_shell_tools ?? 'auto';
		error = '';
		initialized = true;
	}
	$: if (!show) initialized = false;
	async function verify() {
		busy = true;
		error = '';
		try {
			const type = direct
				? await detectTerminalServerType(url, key)
				: (await verifyTerminalServerConnection(localStorage.token, { url, key, auth_type })).type;
			if (!type) throw new Error('Failed to connect to the terminal server');
			if (direct && type === 'orchestrator')
				throw new Error('Add Terminals as an administrator-managed connection.');
			serverType = type;
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
			const configuration = {
				...(connection?.config ?? {}),
				chat_uploads: chatUploads,
				working_directory_context: workingDirectoryContext,
				user_shell_tools: userShellTools
			};
			delete configuration.contexts;
			if (!direct) configuration.access_grants = accessGrants;
			else delete configuration.access_grants;
			const result = {
				...(connection ?? {}),
				url: url.trim().replace(/\/$/, ''),
				key,
				name: name.trim(),
				path,
				auth_type: serverType === 'orchestrator' ? 'bearer' : auth_type,
				enabled,
				forward_cookies: forwardCookies,
				server_type: serverType,
				config: configuration
			};
			for (const old of ['instances', 'policy_id', 'policy', 'lifecycle']) delete result[old];
			if (!direct) result.id = connection?.id ?? uuidv4();
			await onSubmit(result);
			show = false;
		} catch (e) {
			error = e instanceof Error ? e.message : String(e);
		} finally {
			busy = false;
		}
	}
</script>

<Modal
	bind:show
	size="sm"
	ariaLabel={$i18n.t(edit ? 'Edit Terminal Connection' : 'Add Terminal Connection')}
>
	<form
		class="space-y-3 px-4 pb-4 pt-3 text-gray-900 dark:text-gray-100"
		on:submit|preventDefault={save}
	>
		<div class="flex items-center justify-between">
			<h2 class="text-sm font-medium">
				{$i18n.t(edit ? 'Edit Terminal Connection' : 'Add Terminal Connection')}
			</h2>
			<button
				type="button"
				class="shrink-0 rounded-lg py-1 text-gray-500 transition hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
				on:click={() => (show = false)}
				aria-label={$i18n.t('Close')}><XMark className="size-4" /></button
			>
		</div>
		{#if error}<p role="alert" class="text-sm text-red-500">{error}</p>{/if}
		<label class="block text-xs"
			>{$i18n.t('Name')}<input class={input} bind:value={name} required /></label
		>
		<label class="block text-xs"
			>URL<input
				class={input}
				bind:value={url}
				type="url"
				required
				on:input={() => (serverType = null)}
			/></label
		>
		<label class="block text-xs"
			>{$i18n.t('Authentication')}<SettingsSelect
				bind:value={auth_type}
				className="mt-1 w-full"
				ariaLabel={$i18n.t('Authentication')}
				><option value="bearer">Bearer</option><option value="none">None</option
				>{#if !direct}<option value="session">Session</option><option value="system_oauth"
						>OAuth</option
					>{/if}</SettingsSelect
			></label
		>
		<label class="block text-xs">{$i18n.t('API Key')}<SensitiveInput bind:value={key} /></label>
		<div class="flex items-center gap-3">
			<button type="button" class={button} disabled={busy || !url} on:click={verify}
				>{$i18n.t('Verify Connection')}</button
			>{#if serverType}<span class="text-xs text-gray-500"
					>{serverType === 'orchestrator' ? 'Terminals' : 'Open Terminal'}</span
				>{/if}
		</div>
		{#if serverType === 'orchestrator'}<p class="text-xs text-gray-500">
				{$i18n.t('Create and configure terminals from the terminal selector.')}
			</p>{/if}
		{#if !direct}<Collapsible
				title={$i18n.t('Access')}
				buttonClassName="flex w-full py-1 text-xs text-gray-500 transition hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
				chevronClassName="size-3.5"
				chevronStrokeWidth="2"
				><div slot="content" class="mt-3">
					<AccessControl bind:accessGrants accessRoles={['read', 'write']} onChange={() => {}} />
				</div></Collapsible
			>{/if}
		<Collapsible
			title={$i18n.t('Advanced')}
			buttonClassName="flex w-full py-1 text-xs text-gray-500 transition hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
			chevronClassName="size-3.5"
			chevronStrokeWidth="2"
			><div slot="content" class="mt-3 space-y-3">
				<label class="block text-xs"
					>{$i18n.t('OpenAPI path')}<input class={input} bind:value={path} /></label
				>
				<label class="flex items-center gap-2 text-xs"
					><input type="checkbox" bind:checked={enabled} />{$i18n.t('Enabled')}</label
				>
				{#if !direct}<label class="flex items-center gap-2 text-xs"
						><input type="checkbox" bind:checked={forwardCookies} />{$i18n.t(
							'Forward cookies'
						)}</label
					>{/if}
				<label class="flex items-center gap-2 text-xs"
					><input type="checkbox" bind:checked={workingDirectoryContext} />{$i18n.t(
						'Working directory context'
					)}</label
				>
				<label class="block text-xs"
					>{$i18n.t('Chat uploads')}<SettingsSelect
						bind:value={chatUploads}
						className="mt-1 w-full"
						ariaLabel={$i18n.t('Chat uploads')}
						><option value="default">Default</option><option value="filesystem">Filesystem</option
						></SettingsSelect
					></label
				>
				<label class="block text-xs"
					>{$i18n.t('Shell tools')}<SettingsSelect
						bind:value={userShellTools}
						className="mt-1 w-full"
						ariaLabel={$i18n.t('Shell tools')}
						><option value="auto">Auto</option><option value="always">Always</option
						></SettingsSelect
					></label
				>
			</div></Collapsible
		>
		<div class="flex justify-between">
			{#if edit}<button
					type="button"
					class={button}
					disabled={busy}
					on:click={() => (showDelete = true)}>{$i18n.t('Delete')}</button
				>{:else}<span />{/if}<button
				class={`${button} bg-gray-900 text-white dark:bg-gray-100 dark:text-black`}
				disabled={busy || !url}>{$i18n.t('Save')}</button
			>
		</div>
	</form>
</Modal>
<ConfirmDialog
	bind:show={showDelete}
	message={$i18n.t('Delete this connection?')}
	confirmLabel={$i18n.t('Delete')}
	on:confirm={() => {
		onDelete();
		show = false;
	}}
/>
