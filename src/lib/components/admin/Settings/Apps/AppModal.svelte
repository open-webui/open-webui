<script lang="ts">
	import { getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	import {
		createNewApp,
		updateAppById,
		getAppById,
		deleteAppById,
		previewAppManifest,
		connectAppById,
		type App
	} from '$lib/apis/apps';
	import Modal from '$lib/components/common/Modal.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import Search from '$lib/components/icons/Search.svelte';
	import Refresh from '$lib/components/icons/Refresh.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import AccessButton from '$lib/components/common/AccessButton.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import AccessControlModal from '$lib/components/workspace/common/AccessControlModal.svelte';
	import AdminSettingSection from '../AdminSettingSection.svelte';
	import AdminSettingRow from '../AdminSettingRow.svelte';
	import AdminSettingField from '../AdminSettingField.svelte';
	const i18n = getContext<any>('i18n');
	export let show = false;
	export let app: App | null = null;
	export let onChange: () => Promise<void>;
	let url = '',
		apiKey = '',
		slug = app?.slug ?? '',
		name = app?.name ?? '',
		error = '';
	let manifest: any = app?.data.manifest ?? null;
	let scopes = [...(app?.data.granted_scopes ?? [])];
	// Preserve the previous access label in the translation catalogs.
	// $i18n.t('Who can use this app?');
	let grants: any[] = [];
	let busy = false,
		loading = !!app,
		showGrants = false,
		confirm = false;
	let showScopes = false;
	// Preserve the previous scope description in the translation catalogs.
	// $i18n.t('Choose the scopes to grant this app.');
	let scopeMode: 'granted' | 'requested' = 'granted';
	let manifestUpdated = false;
	let manual = false;
	let scopeQuery = '';
	$: availableScopes =
		scopeMode === 'requested' ? Object.keys(scopeLabels) : (manifest?.requested_scopes ?? []);
	$: filteredScopes = availableScopes.filter((scope: string) =>
		`${scope} ${$i18n.t(scopeLabels[scope] ?? scope)}`
			.toLowerCase()
			.includes(scopeQuery.trim().toLowerCase())
	);
	const inputClass =
		'w-full min-w-0 bg-transparent text-sm outline-hidden placeholder:text-gray-300 dark:placeholder:text-gray-700 disabled:text-gray-400 dark:disabled:text-gray-600';
	const buttonClass =
		'flex h-7 shrink-0 items-center justify-center gap-1.5 rounded-lg bg-gray-900 px-2.5 text-xs font-normal text-white transition hover:bg-black disabled:opacity-60 dark:bg-gray-100 dark:text-gray-900 dark:hover:bg-white';
	// Keep the dynamic scope label visible to i18next-parser.
	// $i18n.t('Read messages and history in joined channels');
	const scopeLabels: Record<string, string> = {
		'channels:mentions:read': 'Read app mentions in joined channels',
		'channels:messages:read': 'Read messages and history in joined channels',
		'channels:messages:write': 'Send messages and edit own messages in joined channels',
		'channels:read': 'Read joined channel details'
	};
	async function run(task: () => Promise<void>) {
		busy = true;
		error = '';
		try {
			await task();
		} catch (e) {
			error = String(e);
		} finally {
			busy = false;
		}
	}
	function editDetailsManually() {
		manual = true;
		manifest = manifest ?? { id: '', name: '', public_key: '', requested_scopes: [] };
		manifestUpdated = !!app;
	}
	async function submit() {
		await run(async () => {
			if (!manifest) {
				manifest = await previewAppManifest(localStorage.token, url, {
					...(apiKey ? { api_key: apiKey } : {}),
					...(app ? { app_id: app.id } : {})
				});
				manual = false;
				name = manifest.name;
				slug =
					manifest.id
						.toLowerCase()
						.replace(/[^a-z0-9-]/g, '-')
						.replace(/^[^a-z]+/, '')
						.slice(0, 40) || 'app';
				scopes = [...manifest.requested_scopes];
				scopeQuery = '';
				showScopes = true;
			} else {
				if (manual) {
					manifest = {
						...manifest,
						id: manifest.id || slug,
						name: app ? manifest.name : name
					};
					manifestUpdated = !!app && JSON.stringify(manifest) !== JSON.stringify(app.data.manifest);
				}
				if (!app) {
					manifest = { ...manifest, name };
					app = await createNewApp(localStorage.token, {
						manifest,
						url,
						api_key: apiKey,
						slug,
						granted_scopes: scopes,
						access_grants: grants
					});
					apiKey = '';
				} else {
					app = await updateAppById(localStorage.token, app.id, {
						name,
						access_grants: grants,
						granted_scopes: scopes,
						...(manifestUpdated ? { manifest } : {})
					});
					manifestUpdated = false;
				}
				try {
					if (!app!.is_active || apiKey) {
						app = await connectAppById(
							localStorage.token,
							app!.id,
							apiKey ? { api_key: apiKey } : {}
						);
						apiKey = '';
					}
				} finally {
					await onChange();
				}
				toast.success($i18n.t('App settings updated'));
				show = false;
			}
		});
	}
	async function destructive() {
		await run(async () => {
			await deleteAppById(localStorage.token, app!.id);
			show = false;
			await onChange();
		});
	}
	let opened = false;
	async function initialize() {
		manifestUpdated = false;
		manual = false;
		showScopes = false;
		scopeMode = 'granted';
		scopeQuery = '';
		url = app?.data.url ?? '';
		apiKey = '';
		slug = app?.slug ?? '';
		name = app?.name ?? '';
		error = '';
		manifest = app?.data.manifest ? { ...app.data.manifest } : null;
		scopes = [...(app?.data.granted_scopes ?? [])];
		grants = app ? [] : [{ principal_type: 'user', principal_id: '*', permission: 'read' }];
		apiKey = '';
		loading = !!app;
		if (app)
			await run(async () => {
				grants = (await getAppById(localStorage.token, app!.id)).access_grants;
			});
		loading = false;
	}
	$: if (show && !opened) {
		opened = true;
		initialize();
	} else if (!show) {
		opened = false;
		apiKey = '';
	}
</script>

<AccessControlModal
	bind:show={showGrants}
	bind:accessGrants={grants}
	accessRoles={['read']}
	labels={{
		title: $i18n.t('Access'),
		public: $i18n.t('Everyone'),
		private: $i18n.t('Restricted'),
		read: $i18n.t('Use'),
		empty: $i18n.t('Only admins can use this app. Add users or groups to allow others.')
	}}
	onChange={(value) => {
		grants = value;
	}}
/>
<ConfirmDialog
	bind:show={confirm}
	title={$i18n.t('Uninstall app')}
	message={$i18n.t(
		'Credentials and channel memberships will be removed. Existing messages will remain.'
	)}
	on:confirm={destructive}
/>
<Modal size="sm" bind:show>
	<div class="flex justify-between dark:text-gray-100 px-5 pt-4 pb-2">
		<h1 class="text-lg font-medium self-center font-primary">
			{showScopes
				? scopeMode === 'requested'
					? $i18n.t('Requested scopes')
					: $i18n.t('Scopes')
				: app
					? $i18n.t('Configure app')
					: $i18n.t('Add app')}
		</h1>
		<button
			type="button"
			aria-label={$i18n.t('Close app settings')}
			class="self-center"
			on:click={() => {
				show = false;
			}}><XMark className="size-5" /></button
		>
	</div>
	{#if showScopes}
		<div class="px-5 pb-4 text-sm dark:text-gray-200">
			<p class="mb-3 text-xs text-gray-500 dark:text-gray-400">
				{scopeMode === 'requested'
					? $i18n.t('Enter the scopes requested by the app.')
					: app
						? $i18n.t('Scopes requested by {{APP_NAME}}', { APP_NAME: name })
						: $i18n.t('Review the scopes this app is requesting before adding it.')}
			</p>
			{#if availableScopes.length > 8}
				<div class="mb-3 flex items-center gap-2 text-gray-500">
					<Search className="size-4 shrink-0" />
					<input
						type="search"
						aria-label={$i18n.t('Search scopes')}
						placeholder={$i18n.t('Search scopes')}
						class={inputClass}
						bind:value={scopeQuery}
					/>
				</div>
			{/if}
			<!-- svelte-ignore a11y_no_noninteractive_tabindex (The scrollable scope list must support keyboard scrolling.) -->
			<div
				class="max-h-[45dvh] overflow-y-auto overscroll-contain scrollbar-hover pr-1.5"
				role="region"
				aria-label={$i18n.t('App scopes')}
				tabindex="0"
			>
				<div class="flex flex-col gap-3">
					{#each filteredScopes as scope (scope)}
						<AdminSettingRow label={$i18n.t(scopeLabels[scope] ?? scope)} let:labelId>
							<div slot="label" class="break-words">
								{$i18n.t(scopeLabels[scope] ?? scope)}
								{#if scopeLabels[scope]}<div
										class="mt-0.5 break-all font-mono text-[0.6875rem] text-gray-400 dark:text-gray-600"
									>
										{scope}
									</div>{/if}
							</div>
							<Switch
								state={(scopeMode === 'requested' ? manifest.requested_scopes : scopes).includes(
									scope
								)}
								ariaLabelledbyId={labelId}
								on:change={(event) => {
									if (scopeMode === 'requested') {
										manifest.requested_scopes = event.detail
											? [...manifest.requested_scopes, scope]
											: manifest.requested_scopes.filter((s) => s !== scope);
										scopes = scopes.filter((s) => manifest.requested_scopes.includes(s));
									} else {
										scopes = event.detail ? [...scopes, scope] : scopes.filter((s) => s !== scope);
									}
								}}
							/>
						</AdminSettingRow>
					{:else}
						<p class="py-3 text-xs text-gray-400 dark:text-gray-600">
							{scopeQuery ? $i18n.t('No matching scopes.') : $i18n.t('No scopes requested.')}
						</p>
					{/each}
				</div>
			</div>
			<div class="mt-5 flex justify-end">
				<button
					type="button"
					class={buttonClass}
					on:click={() => {
						showScopes = false;
					}}>{$i18n.t('Continue')}</button
				>
			</div>
		</div>
	{:else}
		<form class="px-5 pb-4 text-sm dark:text-gray-200" on:submit|preventDefault={submit}>
			{#if loading}<div class="flex justify-center py-4"><Spinner className="size-5" /></div>
			{:else}
				{#if !manifest}<AdminSettingField
						label={$i18n.t('App URL')}
						forId="app-url"
						description={$i18n.t(
							'Manifest discovery is recommended. You can also enter app details manually.'
						)}
					>
						<input
							id="app-url"
							type="url"
							required
							bind:value={url}
							class={inputClass}
							placeholder="https://app.example.com/events"
						/>
					</AdminSettingField>
					<AdminSettingField
						label={$i18n.t('API Key')}
						forId="app-api-key"
						description={app?.configured
							? $i18n.t('Leave empty to keep the current API key.')
							: $i18n.t('Enter the API key provided by the app.')}
					>
						<input
							id="app-api-key"
							type="password"
							autocomplete="new-password"
							class={inputClass}
							bind:value={apiKey}
							required={!app?.configured}
							maxlength="4096"
							placeholder={app?.configured ? '••••••••' : $i18n.t('API Key')}
						/>
					</AdminSettingField>
				{:else}
					<div class="flex gap-3">
						<AdminSettingField label={$i18n.t('Name')} forId="app-name" className="min-w-0 flex-1"
							><input
								id="app-name"
								class={inputClass}
								bind:value={name}
								required
								maxlength="100"
							/></AdminSettingField
						>
						<AdminSettingField
							label={$i18n.t('App handle')}
							forId="app-handle"
							className="min-w-0 flex-1"
							><input
								id="app-handle"
								class={`${inputClass} font-mono`}
								bind:value={slug}
								disabled={!!app}
								required
								pattern={'[a-z][a-z0-9-]{0,39}'}
							/></AdminSettingField
						>
					</div>
					{#if manual}
						<AdminSettingField
							label={$i18n.t('Public key')}
							forId="app-public-key"
							className="mt-4"
							description={$i18n.t('Enter the Ed25519 public key provided by the app.')}
						>
							<textarea
								id="app-public-key"
								class={`${inputClass} font-mono`}
								rows="3"
								required
								maxlength="2000"
								spellcheck="false"
								bind:value={manifest.public_key}
								placeholder="-----BEGIN PUBLIC KEY-----"
							></textarea>
						</AdminSettingField>
						<button
							type="button"
							class="mt-2 text-xs text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white hover:underline"
							on:click={() => {
								scopeQuery = '';
								scopeMode = 'requested';
								showScopes = true;
							}}>{$i18n.t('Requested scopes')}</button
						>
					{/if}
					<AdminSettingSection title={$i18n.t('Connection')}>
						<div class="flex items-center gap-2">
							<p class="min-w-0 flex-1 break-all text-xs text-gray-600 dark:text-gray-400">{url}</p>
							{#if app}
								<Tooltip content={$i18n.t('Update app')}>
									<button
										type="button"
										aria-label={$i18n.t('Update app')}
										disabled={busy}
										class="self-center flex size-6 shrink-0 items-center justify-center bg-transparent hover:bg-gray-100 dark:hover:bg-gray-850 rounded-lg transition disabled:opacity-50"
										on:click={() =>
											run(async () => {
												manifest = await previewAppManifest(localStorage.token, url, {
													...(apiKey ? { api_key: apiKey } : {}),
													app_id: app!.id
												});
												manual = false;
												scopeMode = 'granted';
												scopes = scopes.filter((scope) =>
													manifest.requested_scopes.includes(scope)
												);
												manifestUpdated = true;
												showScopes = true;
											})}
									>
										{#if busy}<Spinner className="size-3.5" />{:else}<Refresh
												className="size-3.5"
											/>{/if}
									</button>
								</Tooltip>
							{/if}
						</div>
						{#if app && !manual}
							<button
								type="button"
								disabled={busy}
								class="mt-2 text-xs text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white hover:underline"
								on:click={editDetailsManually}>{$i18n.t('Edit details manually')}</button
							>
						{/if}
						{#if manifestUpdated}
							<p class="mt-2 text-xs text-gray-500">
								{$i18n.t('Saving approves the updated app identity and selected scopes.')}
							</p>
						{/if}

						<AdminSettingField
							label={$i18n.t('API Key')}
							forId="app-api-key"
							description={app?.configured
								? $i18n.t('Leave empty to keep the current API key.')
								: $i18n.t('Enter the API key provided by the app.')}
						>
							<input
								id="app-api-key"
								type="password"
								autocomplete="new-password"
								class={inputClass}
								bind:value={apiKey}
								required={!app?.configured}
								maxlength="4096"
								placeholder={app?.configured ? '••••••••' : $i18n.t('API Key')}
							/>
						</AdminSettingField>
					</AdminSettingSection>
					<AdminSettingSection>
						<AdminSettingRow label={$i18n.t('Scopes')}>
							<div class="flex items-center gap-3 text-xs">
								<span class="text-gray-400 dark:text-gray-600"
									>{$i18n.t('{{COUNT}} selected', {
										COUNT: scopes.length
									})}</span
								>
								<button
									type="button"
									class="text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white hover:underline"
									on:click={() => {
										scopeQuery = '';
										scopeMode = 'granted';
										showScopes = true;
									}}
								>
									{app ? $i18n.t('Edit') : $i18n.t('Review')}
								</button>
							</div>
						</AdminSettingRow>
					</AdminSettingSection>
					<AccessButton
						label={$i18n.t('Access')}
						className="mt-5"
						on:click={() => {
							showGrants = true;
						}}
					/>
				{/if}
				{#if error}<p role="alert" class="mt-3 text-xs text-red-600 dark:text-red-400">
						{error}
					</p>{/if}
				<div class="mt-5 flex items-center justify-between gap-2">
					<div>
						{#if app?.configured}<button
								type="button"
								disabled={busy}
								class="px-1 py-1.5 text-sm font-medium text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 hover:underline transition disabled:opacity-50"
								on:click={() => {
									confirm = true;
								}}>{$i18n.t('Uninstall')}</button
							>{:else if manifest && !app}<button
								type="button"
								disabled={busy}
								class="text-xs text-gray-500 hover:text-gray-900 dark:hover:text-white"
								on:click={() => {
									manifest = null;
									manual = false;
								}}>{$i18n.t('Back')}</button
							>{:else if !manifest}<button
								type="button"
								disabled={busy}
								class="text-xs text-gray-500 hover:text-gray-900 dark:hover:text-white"
								on:click={(event) => {
									if (event.currentTarget.form?.reportValidity()) editDetailsManually();
								}}>{$i18n.t('Enter details manually')}</button
							>{/if}
					</div>
					<button type="submit" disabled={busy} class={buttonClass}>
						{#if busy}<Spinner className="size-3" />{/if}
						{!manifest
							? $i18n.t('Continue')
							: !app
								? $i18n.t('Connect')
								: app.is_active && !apiKey
									? $i18n.t('Save')
									: $i18n.t('Connect')}
					</button>
				</div>
			{/if}
		</form>
	{/if}
</Modal>
