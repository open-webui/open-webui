<script lang="ts">
	import { getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { v4 as uuidv4 } from 'uuid';
	import Modal from '$lib/components/common/Modal.svelte';
	import Collapsible from '$lib/components/common/Collapsible.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import ArrowPath from '$lib/components/icons/ArrowPath.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
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
	const input =
		'w-full min-w-0 bg-transparent py-0.5 text-sm text-gray-900 outline-hidden placeholder:text-gray-300 dark:text-gray-100 dark:placeholder:text-gray-700';
	const select =
		'min-w-0 bg-transparent pr-5 text-sm text-gray-900 outline-hidden dark:text-gray-100';
	const button =
		'flex h-7 items-center justify-center gap-1.5 rounded-lg px-2.5 text-xs font-normal transition hover:bg-gray-100 dark:hover:bg-gray-850 disabled:opacity-50';
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
		workingDirectoryContext = connection?.config?.working_directory_context ?? true;
		userShellTools = connection?.config?.user_shell_tools ?? 'auto';
		error = '';
		initialized = true;
	}
	$: if (!show) initialized = false;
	async function verify(announce = false) {
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
				enabled: connection?.enabled ?? true,
				forward_cookies: forwardCookies,
				server_type: serverType,
				config: configuration
			};
			for (const old of ['instances', 'policy_id', 'policy', 'lifecycle']) delete result[old];
			if (!direct) result.id = connection?.id || id.trim() || uuidv4();
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
	<div class="flex items-center justify-between px-5 pb-2 pt-4 dark:text-gray-100">
		<h2 class="font-primary text-lg font-medium">
			{$i18n.t(edit ? 'Edit Terminal Connection' : 'Add Terminal Connection')}
		</h2>
		<button
			type="button"
			class="shrink-0 self-center"
			on:click={() => (show = false)}
			aria-label={$i18n.t('Close')}><XMark className="size-5" /></button
		>
	</div>
	<form
		class="space-y-2 px-5 pb-4 text-gray-900 dark:text-gray-100"
		on:submit|preventDefault={save}
	>
		{#if error}<p role="alert" class="text-sm text-gray-700 dark:text-gray-300">{error}</p>{/if}
		<div class="flex gap-2">
			<div class="min-w-0 flex-1">
				<label for="terminal-name" class="mb-0.5 block text-xs text-gray-500"
					>{$i18n.t('Name')}</label
				>
				<input
					id="terminal-name"
					class={input}
					bind:value={name}
					placeholder={$i18n.t('My Terminal')}
					required
				/>
			</div>
			{#if !direct}
				<div class="min-w-0 flex-1">
					<label for="terminal-id" class="mb-0.5 block text-xs text-gray-500">
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
		<div class="flex items-end gap-2">
			<div class="min-w-0 flex-1">
				<label for="terminal-url" class="mb-0.5 block text-xs text-gray-500">{$i18n.t('URL')}</label
				>
				<input
					id="terminal-url"
					class={input}
					bind:value={url}
					type="url"
					placeholder="https://terminal.example.com"
					required
					on:input={() => (serverType = null)}
				/>
			</div>
			<Tooltip content={$i18n.t('Verify Connection')}>
				<button
					type="button"
					class="rounded-lg p-1 transition hover:bg-gray-100 disabled:opacity-50 dark:hover:bg-gray-850"
					disabled={busy || !url}
					on:click={() => verify(true)}
					aria-label={$i18n.t('Verify Connection')}
					>{#if busy}<Spinner className="size-4" />{:else}<ArrowPath
							className="size-4"
						/>{/if}</button
				>
			</Tooltip>
		</div>
		<div>
			<label for="terminal-auth-type" class="mb-0.5 block text-xs text-gray-500"
				>{$i18n.t('Auth')}</label
			>
			<div class="flex items-start gap-2">
				<select id="terminal-auth-type" class="{select} shrink-0 py-0.5" bind:value={auth_type}>
					<option value="bearer">{$i18n.t('Bearer')}</option>
					<option value="none">{$i18n.t('None')}</option>
					{#if !direct}
						<option value="session">{$i18n.t('Session')}</option>
						<option value="system_oauth">{$i18n.t('OAuth')}</option>
					{/if}
				</select>
				<div class="min-w-0 flex-1">
					<SensitiveInput bind:value={key} placeholder={$i18n.t('API Key')} />
					{#if auth_type === 'session'}
						<p class="mt-1 text-xs text-gray-500">
							{$i18n.t('Forwards system user session credentials to authenticate')}
						</p>
					{:else if auth_type === 'system_oauth'}
						<p class="mt-1 text-xs text-gray-500">
							{$i18n.t('Forwards system user OAuth access token to authenticate')}
						</p>
					{:else if auth_type === 'none'}
						<p class="mt-1 text-xs text-gray-500">{$i18n.t('No authentication')}</p>
					{/if}
				</div>
			</div>
		</div>
		{#if serverType === 'orchestrator'}
			<p class="text-xs text-gray-500">
				{$i18n.t('Create and configure terminals from the terminal selector.')}
			</p>
		{/if}
		<div>
			<label for="terminal-chat-uploads" class="mb-0.5 block text-xs text-gray-500"
				>{$i18n.t('Chat Uploads')}</label
			>
			<select id="terminal-chat-uploads" class="{select} w-full" bind:value={chatUploads}>
				<option value="default">{$i18n.t('Default')}</option>
				<option value="filesystem">{$i18n.t('Filesystem')}</option>
			</select>
		</div>
		{#if !direct}
			<Collapsible
				title={$i18n.t('Access')}
				buttonClassName="flex w-full py-1 text-xs text-gray-500 transition hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
				chevronClassName="size-3.5"
				chevronStrokeWidth="2"
			>
				<div slot="content" class="mt-2">
					<AccessControl bind:accessGrants accessRoles={['read', 'write']} onChange={() => {}} />
				</div>
			</Collapsible>
		{/if}
		<Collapsible
			title={$i18n.t('Advanced')}
			buttonClassName="flex w-full py-1 text-xs text-gray-500 transition hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
			chevronClassName="size-3.5"
			chevronStrokeWidth="2"
		>
			<div slot="content" class="mt-2 space-y-3">
				<div class="flex items-center justify-between gap-3">
					<div>
						<label for="working-directory-context" class="text-xs font-medium"
							>{$i18n.t('Working Directory Context')}</label
						>
						<p class="text-xs text-gray-500">
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
						<p class="text-xs text-gray-500">
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
				{#if !direct}
					<div class="flex items-center justify-between gap-3">
						<div>
							<label for="forward-cookies" class="text-xs font-medium"
								>{$i18n.t('Forward cookies')}</label
							>
							<p class="text-xs text-gray-500">
								{$i18n.t('Forward cookies from your Open WebUI request to this server.')}
							</p>
						</div>
						<Switch
							id="forward-cookies"
							ariaLabel={$i18n.t('Forward cookies')}
							bind:state={forwardCookies}
						/>
					</div>
				{/if}
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
					<p class="mt-1 break-all text-xs text-gray-500">
						{$i18n.t('WebUI will make requests to "{{url}}"', {
							url: path.includes('://') ? path : `${url}${path.startsWith('/') ? '' : '/'}${path}`
						})}
					</p>
				</div>
			</div>
		</Collapsible>
		<div class="flex items-center justify-between pt-3">
			<div>
				{#if edit}
					<button
						type="button"
						class="px-1 py-1.5 text-sm font-medium text-gray-500 transition hover:text-gray-700 hover:underline dark:text-gray-400 dark:hover:text-gray-200"
						disabled={busy}
						on:click={() => (showDelete = true)}>{$i18n.t('Delete')}</button
					>
				{/if}
			</div>
			<button
				class="{button} bg-gray-900 text-white hover:bg-black dark:bg-gray-100 dark:text-gray-900 dark:hover:bg-white"
				disabled={busy || !url}
			>
				{$i18n.t('Save')}
				{#if busy}<Spinner className="size-3" />{/if}
			</button>
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
