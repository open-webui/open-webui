<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { getContext, onMount } from 'svelte';
	const i18n = getContext('i18n');

	import { settings } from '$lib/stores';

	import Modal from '$lib/components/common/Modal.svelte';
	import SensitiveInput from '$lib/components/common/SensitiveInput.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import AccessControlModal from '$lib/components/workspace/common/AccessControlModal.svelte';
	import LockClosed from '$lib/components/icons/LockClosed.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import {
		detectTerminalServerType,
		verifyTerminalServerConnection,
		putOrchestratorPolicy
	} from '$lib/apis/configs';
	import { getTerminalConfig } from '$lib/apis/terminal';

	export let show = false;
	export let edit = false;
	export let direct = false;
	export let connection = null;

	export let onSubmit: Function = () => {};
	export let onDelete: () => void = () => {};

	let url = '';
	let key = '';
	let name = '';
	let id = '';
	let auth_type = 'bearer';
	let path = '/openapi.json';
	let enabled = false;
	let showAdvanced = false;
	let showAccessControlModal = false;
	let showDeleteConfirmDialog = false;
	let accessGrants: any[] = [];

	// Policy / auto-detect state
	let serverType: 'orchestrator' | 'terminal' | null = null;
	let verifying = false;
	let policyId = '';
	let policyImage = '';
	let policyEnvPairs: { key: string; value: string }[] = [];
	let policyCpu = '1';
	let policyMemory = '1Gi';
	let policyStorage = 'ephemeral';
	let policyStorageSize = '5Gi';
	let policyIdleTimeout = 30;

	const init = () => {
		if (connection) {
			id = connection?.id ?? '';
			url = connection.url;
			key = connection?.key ?? '';
			name = connection?.name ?? '';
			auth_type = connection?.auth_type ?? 'bearer';
			path = connection?.path ?? '/openapi.json';
			enabled = connection?.enabled ?? true;
			accessGrants = connection?.config?.access_grants ?? [];

			// Restore policy state
			serverType = connection?.server_type ?? null;
			policyId = connection?.policy_id ?? '';

			const p = connection?.policy ?? {};
			policyImage = p.image ?? '';
			policyIdleTimeout = p.idle_timeout_minutes ?? 30;
			policyStorage = p.storage ? 'persistent' : 'ephemeral';
			policyStorageSize = p.storage ?? '5Gi';

			// Restore env pairs
			const env = p.env ?? {};
			policyEnvPairs = Object.entries(env).map(([k, v]) => ({ key: k, value: v as string }));

			// Restore resources
			policyCpu = p.cpu_limit ?? '1';
			policyMemory = p.memory_limit ?? '1Gi';
		} else {
			id = '';
			url = '';
			key = '';
			name = '';
			auth_type = 'bearer';
			path = '/openapi.json';
			enabled = false;
			accessGrants = [];

			serverType = null;
			policyId = '';
			policyImage = '';
			policyEnvPairs = [];
			policyCpu = '1';
			policyMemory = '1Gi';
			policyStorage = 'ephemeral';
			policyStorageSize = '5Gi';
			policyIdleTimeout = 30;
		}
	};

	$: if (show) {
		init();
	}

	const verifyHandler = async () => {
		const _url = url.replace(/\/$/, '');
		if (!_url) {
			toast.error($i18n.t('Please enter a valid URL'));
			return;
		}

		verifying = true;
		try {
			if (!direct) {
				// System connection: proxy through backend to avoid CORS / key exposure
				const result = await verifyTerminalServerConnection(localStorage.token, {
					url: _url,
					key,
					auth_type
				});
				const type = result?.type ?? null;

				if (type) {
					serverType = type;
					toast.success(
						$i18n.t('Connected ({{type}})', {
							type: type === 'orchestrator' ? 'Orchestrator' : 'Terminal'
						})
					);
					// Default policy_id to connection id when orchestrator detected
					if (type === 'orchestrator' && !policyId) {
						policyId =
							id ||
							name
								.toLowerCase()
								.replace(/[^a-z0-9-]/g, '-')
								.replace(/-+/g, '-')
								.replace(/^-|-$/g, '') ||
							'default';
					}
				} else {
					serverType = null;
					toast.error($i18n.t('Server connection failed'));
				}
			} else {
				// Direct connection: verify from browser
				const res = await getTerminalConfig(_url, key);
				if (res) {
					toast.success($i18n.t('Server connection verified'));
				} else {
					toast.error($i18n.t('Server connection failed'));
				}
			}
		} catch {
			serverType = null;
			toast.error($i18n.t('Server connection failed'));
		} finally {
			verifying = false;
		}
	};

	const buildPolicyData = (): object => {
		const data: Record<string, any> = {};

		if (policyImage) data.image = policyImage;
		if (policyCpu) data.cpu_limit = policyCpu;
		if (policyMemory) data.memory_limit = policyMemory;

		if (policyStorage === 'persistent') {
			data.storage = policyStorageSize;
		}

		if (policyIdleTimeout > 0) {
			data.idle_timeout_minutes = policyIdleTimeout;
		}

		// Env vars
		const env: Record<string, string> = {};
		for (const pair of policyEnvPairs) {
			if (pair.key.trim()) {
				env[pair.key.trim()] = pair.value;
			}
		}
		if (Object.keys(env).length > 0) {
			data.env = env;
		}

		return data;
	};

	const submitHandler = async () => {
		if (url === '') {
			toast.error($i18n.t('Please enter a valid URL'));
			return;
		}

		// Remove trailing slash
		url = url.replace(/\/$/, '');

		// Save policy to orchestrator if applicable
		if (serverType === 'orchestrator' && !direct && policyId) {
			try {
				await putOrchestratorPolicy(localStorage.token, url, key, policyId, buildPolicyData());
			} catch (err) {
				toast.error($i18n.t('Failed to save policy: {{error}}', { error: err }));
				return;
			}
		}

		const result = {
			...(!direct && id.trim() ? { id: id.trim() } : {}),
			url,
			key,
			name,
			path,
			auth_type,
			enabled: enabled,
			config: {
				...(!direct ? { access_grants: accessGrants } : {})
			},
			// Policy fields
			...(serverType ? { server_type: serverType } : {}),
			...(serverType === 'orchestrator' && policyId ? { policy_id: policyId } : {}),
			...(serverType === 'orchestrator' ? { policy: buildPolicyData() } : {})
		};

		onSubmit(result);
		show = false;
	};
</script>

<Modal size="sm" bind:show>
	<div>
		<div class="flex justify-between dark:text-gray-100 px-5 pt-4 pb-2">
			<h1 class="text-lg font-medium self-center font-primary">
				{#if edit}
					{$i18n.t('Edit Terminal Connection')}
				{:else}
					{$i18n.t('Add Terminal Connection')}
				{/if}
			</h1>

			<button
				class="self-center"
				aria-label={$i18n.t('Close')}
				on:click={() => {
					show = false;
				}}
			>
				<XMark className={'size-5'} />
			</button>
		</div>

		<div class="flex flex-col md:flex-row w-full px-4 pb-4 md:space-x-4 dark:text-gray-200">
			<div class="flex flex-col w-full sm:flex-row sm:justify-center sm:space-x-6">
				<form class="flex flex-col w-full" on:submit|preventDefault={submitHandler}>
					<div class="px-1">
						<div class="flex gap-2">
							<div class="flex flex-col flex-1">
								<div class="flex justify-between mb-0.5">
									<label
										for="terminal-name"
										class={`text-xs ${($settings?.highContrastMode ?? false) ? 'text-gray-800 dark:text-gray-100' : 'text-gray-500'}`}
										>{$i18n.t('Name')}</label
									>
								</div>

								<div class="flex flex-1 items-center">
									<input
										id="terminal-name"
										class={`w-full flex-1 text-sm bg-transparent ${($settings?.highContrastMode ?? false) ? 'placeholder:text-gray-700 dark:placeholder:text-gray-100' : 'outline-hidden placeholder:text-gray-300 dark:placeholder:text-gray-700'}`}
										type="text"
										bind:value={name}
										placeholder={$i18n.t('My Terminal')}
										autocomplete="off"
									/>
								</div>
							</div>
							{#if !direct}
								<div class="flex flex-col flex-1">
									<div class="flex justify-between mb-0.5">
										<label
											for="terminal-id"
											class={`text-xs ${($settings?.highContrastMode ?? false) ? 'text-gray-800 dark:text-gray-100' : 'text-gray-500'}`}
											>{$i18n.t('ID')}
											<span class="opacity-50">({$i18n.t('optional')})</span></label
										>
									</div>
									<div class="flex flex-1 items-center">
										<input
											id="terminal-id"
											class={`w-full flex-1 text-sm bg-transparent font-mono ${($settings?.highContrastMode ?? false) ? 'placeholder:text-gray-700 dark:placeholder:text-gray-100' : 'outline-hidden placeholder:text-gray-300 dark:placeholder:text-gray-700'}`}
											type="text"
											bind:value={id}
											placeholder="auto"
											autocomplete="off"
										/>
									</div>
								</div>
							{/if}
						</div>

						<div class="flex gap-2 mt-2">
							<div class="flex flex-col w-full">
								<div class="flex justify-between mb-0.5">
									<label
										for="terminal-url"
										class={`text-xs ${($settings?.highContrastMode ?? false) ? 'text-gray-800 dark:text-gray-100' : 'text-gray-500'}`}
										>{$i18n.t('URL')}</label
									>
								</div>

								<div class="flex flex-1 items-center">
									<input
										id="terminal-url"
										class={`w-full flex-1 text-sm bg-transparent ${($settings?.highContrastMode ?? false) ? 'placeholder:text-gray-700 dark:placeholder:text-gray-100' : 'outline-hidden placeholder:text-gray-300 dark:placeholder:text-gray-700'}`}
										type="text"
										bind:value={url}
										placeholder="http://localhost:9900"
										required
										autocomplete="off"
									/>
								</div>
							</div>

							<Tooltip content={$i18n.t('Verify Connection')} className="self-end -mb-1">
								<button
									class="self-center p-1 bg-transparent hover:bg-gray-100 dark:hover:bg-gray-850 rounded-lg transition"
									on:click={() => {
										verifyHandler();
									}}
									type="button"
									disabled={verifying}
									aria-label={$i18n.t('Verify Connection')}
								>
									{#if verifying}
										<svg
											class="w-4 h-4 animate-spin"
											xmlns="http://www.w3.org/2000/svg"
											fill="none"
											viewBox="0 0 24 24"
										>
											<circle
												class="opacity-25"
												cx="12"
												cy="12"
												r="10"
												stroke="currentColor"
												stroke-width="4"
											></circle>
											<path
												class="opacity-75"
												fill="currentColor"
												d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
											></path>
										</svg>
									{:else}
										<svg
											xmlns="http://www.w3.org/2000/svg"
											viewBox="0 0 20 20"
											fill="currentColor"
											aria-hidden="true"
											class="w-4 h-4"
										>
											<path
												fill-rule="evenodd"
												d="M15.312 11.424a5.5 5.5 0 01-9.201 2.466l-.312-.311h2.433a.75.75 0 000-1.5H3.989a.75.75 0 00-.75.75v4.242a.75.75 0 001.5 0v-2.43l.31.31a7 7 0 0011.712-3.138.75.75 0 00-1.449-.39zm1.23-3.723a.75.75 0 00.219-.53V2.929a.75.75 0 00-1.5 0V5.36l-.31-.31A7 7 0 003.239 8.188a.75.75 0 101.448.389A5.5 5.5 0 0113.89 6.11l.311.31h-2.432a.75.75 0 000 1.5h4.243a.75.75 0 00.53-.219z"
												clip-rule="evenodd"
											/>
										</svg>
									{/if}
								</button>
							</Tooltip>
						</div>

						<!-- Policy section (orchestrator only, admin only) -->
						{#if serverType === 'orchestrator' && !direct}
							<div class="flex gap-2 mt-2">
								<div class="flex flex-col w-full">
									<div class="flex justify-between mb-0.5">
										<div
											class={`text-xs ${($settings?.highContrastMode ?? false) ? 'text-gray-800 dark:text-gray-100' : 'text-gray-500'}`}
										>
											{$i18n.t('Policy ID')}
										</div>
									</div>
									<div class="flex flex-1 items-center">
										<input
											id="policy-id"
											class={`w-full flex-1 text-sm bg-transparent font-mono ${($settings?.highContrastMode ?? false) ? 'placeholder:text-gray-700 dark:placeholder:text-gray-100' : 'outline-hidden placeholder:text-gray-300 dark:placeholder:text-gray-700'}`}
											type="text"
											bind:value={policyId}
											placeholder="python-ds"
											autocomplete="off"
											disabled={edit && !!connection?.policy_id}
										/>
									</div>
								</div>
							</div>

							<div class="flex gap-2 mt-2">
								<div class="flex flex-col w-full">
									<div class="flex justify-between mb-0.5">
										<div
											class={`text-xs ${($settings?.highContrastMode ?? false) ? 'text-gray-800 dark:text-gray-100' : 'text-gray-500'}`}
										>
											{$i18n.t('Image')}
											<span class="opacity-50">({$i18n.t('optional')})</span>
										</div>
									</div>
									<div class="flex flex-1 items-center">
										<input
											id="policy-image"
											class={`w-full flex-1 text-sm bg-transparent font-mono ${($settings?.highContrastMode ?? false) ? 'placeholder:text-gray-700 dark:placeholder:text-gray-100' : 'outline-hidden placeholder:text-gray-300 dark:placeholder:text-gray-700'}`}
											type="text"
											bind:value={policyImage}
											placeholder="ghcr.io/open-webui/open-terminal:latest"
											autocomplete="off"
										/>
									</div>
								</div>
							</div>

							<div class="flex gap-2 mt-2">
								<div class="flex flex-col flex-1">
									<div class="flex justify-between mb-0.5">
										<div
											class={`text-xs ${($settings?.highContrastMode ?? false) ? 'text-gray-800 dark:text-gray-100' : 'text-gray-500'}`}
										>
											{$i18n.t('CPU')}
										</div>
									</div>
									<div class="flex flex-1 items-center">
										<input
											id="policy-cpu"
											class={`w-full flex-1 text-sm bg-transparent font-mono ${($settings?.highContrastMode ?? false) ? 'placeholder:text-gray-700 dark:placeholder:text-gray-100' : 'outline-hidden placeholder:text-gray-300 dark:placeholder:text-gray-700'}`}
											type="text"
											bind:value={policyCpu}
											placeholder="1"
											autocomplete="off"
										/>
									</div>
								</div>
								<div class="flex flex-col flex-1">
									<div class="flex justify-between mb-0.5">
										<div
											class={`text-xs ${($settings?.highContrastMode ?? false) ? 'text-gray-800 dark:text-gray-100' : 'text-gray-500'}`}
										>
											{$i18n.t('Memory')}
										</div>
									</div>
									<div class="flex flex-1 items-center">
										<input
											id="policy-memory"
											class={`w-full flex-1 text-sm bg-transparent font-mono ${($settings?.highContrastMode ?? false) ? 'placeholder:text-gray-700 dark:placeholder:text-gray-100' : 'outline-hidden placeholder:text-gray-300 dark:placeholder:text-gray-700'}`}
											type="text"
											bind:value={policyMemory}
											placeholder="1Gi"
											autocomplete="off"
										/>
									</div>
								</div>
							</div>

							<div class="flex gap-2 mt-2">
								<div class="flex flex-col flex-1">
									<div class="flex justify-between mb-0.5">
										<div
											class={`text-xs ${($settings?.highContrastMode ?? false) ? 'text-gray-800 dark:text-gray-100' : 'text-gray-500'}`}
										>
											{$i18n.t('Storage')}
										</div>
									</div>
									<div class="flex gap-2">
										<div class="flex-shrink-0 self-start">
											<select
												class={`dark:bg-gray-900 w-full text-sm bg-transparent pr-5 ${($settings?.highContrastMode ?? false) ? 'placeholder:text-gray-700 dark:placeholder:text-gray-100' : 'outline-hidden placeholder:text-gray-300 dark:placeholder:text-gray-700'}`}
												bind:value={policyStorage}
											>
												<option value="ephemeral">{$i18n.t('Ephemeral')}</option>
												<option value="persistent">{$i18n.t('Persistent')}</option>
											</select>
										</div>
										{#if policyStorage === 'persistent'}
											<div class="flex flex-1 items-center">
												<input
													id="policy-storage-size"
													class={`w-full flex-1 text-sm bg-transparent font-mono ${($settings?.highContrastMode ?? false) ? 'placeholder:text-gray-700 dark:placeholder:text-gray-100' : 'outline-hidden placeholder:text-gray-300 dark:placeholder:text-gray-700'}`}
													type="text"
													bind:value={policyStorageSize}
													placeholder="5Gi"
													autocomplete="off"
												/>
											</div>
										{/if}
									</div>
								</div>

								<div class="flex flex-col flex-1">
									<div class="flex justify-between mb-0.5">
										<div
											class={`text-xs ${($settings?.highContrastMode ?? false) ? 'text-gray-800 dark:text-gray-100' : 'text-gray-500'}`}
										>
											{$i18n.t('Idle Timeout')}
											<span class="opacity-50">({$i18n.t('min')})</span>
										</div>
									</div>
									<div class="flex flex-1 items-center">
										<input
											id="idle-timeout"
											class={`w-full flex-1 text-sm bg-transparent font-mono ${($settings?.highContrastMode ?? false) ? 'placeholder:text-gray-700 dark:placeholder:text-gray-100' : 'outline-hidden placeholder:text-gray-300 dark:placeholder:text-gray-700'}`}
											type="number"
											min="0"
											bind:value={policyIdleTimeout}
											placeholder="30"
											autocomplete="off"
										/>
									</div>
								</div>
							</div>

							<!-- Env Vars -->
							<div class="flex gap-2 mt-2">
								<div class="flex flex-col w-full">
									<div class="flex justify-between items-center mb-0.5">
										<div
											class={`text-xs ${($settings?.highContrastMode ?? false) ? 'text-gray-800 dark:text-gray-100' : 'text-gray-500'}`}
										>
											{$i18n.t('Environment Variables')}
										</div>
										<button
											type="button"
											class="text-xs text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition"
											on:click={() =>
												(policyEnvPairs = [...policyEnvPairs, { key: '', value: '' }])}
										>
											+ {$i18n.t('Add')}
										</button>
									</div>
									{#each policyEnvPairs as pair, idx}
										<div class="flex gap-1.5 mb-1">
											<input
												class={`flex-1 text-sm bg-transparent font-mono ${($settings?.highContrastMode ?? false) ? 'placeholder:text-gray-700 dark:placeholder:text-gray-100' : 'outline-hidden placeholder:text-gray-300 dark:placeholder:text-gray-700'}`}
												type="text"
												bind:value={pair.key}
												placeholder="KEY"
											/>
											<input
												class={`flex-[2] text-sm bg-transparent font-mono ${($settings?.highContrastMode ?? false) ? 'placeholder:text-gray-700 dark:placeholder:text-gray-100' : 'outline-hidden placeholder:text-gray-300 dark:placeholder:text-gray-700'}`}
												type="text"
												bind:value={pair.value}
												placeholder="value"
											/>
											<button
												type="button"
												class="text-xs text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition px-1"
												on:click={() =>
													(policyEnvPairs = policyEnvPairs.filter((_, i) => i !== idx))}
											>
												<XMark className={'size-3'} />
											</button>
										</div>
									{/each}
								</div>
							</div>
						{/if}

						<div class="flex items-center justify-between">
							<button
								type="button"
								class="flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition mt-2"
								on:click={() => (showAdvanced = !showAdvanced)}
							>
								<svg
									xmlns="http://www.w3.org/2000/svg"
									viewBox="0 0 20 20"
									fill="currentColor"
									class="w-3 h-3 transition-transform {showAdvanced ? 'rotate-90' : ''}"
								>
									<path
										fill-rule="evenodd"
										d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z"
										clip-rule="evenodd"
									/>
								</svg>
								{$i18n.t('Advanced')}
							</button>

							{#if !direct}
								<button
									class="bg-gray-50 hover:bg-gray-100 text-black dark:bg-gray-850 dark:hover:bg-gray-800 dark:text-white transition px-2 py-1 object-cover rounded-full flex gap-1 items-center mt-2"
									type="button"
									on:click={() => {
										showAccessControlModal = true;
									}}
								>
									<LockClosed strokeWidth="2.5" className="size-3.5 shrink-0" />

									<div class="text-xs font-medium shrink-0">
										{$i18n.t('Access')}
									</div>
								</button>
							{/if}
						</div>

						{#if showAdvanced}
							<div class="flex gap-2 mt-2">
								<div class="flex flex-col w-full">
									<div class="flex justify-between items-center mb-0.5">
										<div class="flex gap-2 items-center">
											<div
												class={`text-xs ${($settings?.highContrastMode ?? false) ? 'text-gray-800 dark:text-gray-100' : 'text-gray-500'}`}
											>
												{$i18n.t('OpenAPI Spec')}
											</div>
										</div>
									</div>

									<div class="flex gap-2">
										<div class="flex flex-1 items-center">
											<div class="flex-1 flex items-center">
												<label for="openapi-path" class="sr-only"
													>{$i18n.t('openapi.json URL or Path')}</label
												>
												<input
													class={`w-full text-sm bg-transparent ${($settings?.highContrastMode ?? false) ? 'placeholder:text-gray-700 dark:placeholder:text-gray-100' : 'outline-hidden placeholder:text-gray-300 dark:placeholder:text-gray-700'}`}
													type="text"
													id="openapi-path"
													bind:value={path}
													placeholder={$i18n.t('openapi.json URL or Path')}
													autocomplete="off"
													required
												/>
											</div>
										</div>
									</div>

									<div
										class={`text-xs mt-1 ${($settings?.highContrastMode ?? false) ? 'text-gray-800 dark:text-gray-100' : 'text-gray-500'}`}
									>
										{$i18n.t(`WebUI will make requests to "{{url}}"`, {
											url: path.includes('://')
												? path
												: `${url}${path.startsWith('/') ? '' : '/'}${path}`
										})}
									</div>
								</div>
							</div>
						{/if}

						<div class="flex gap-2 mt-2">
							<div class="flex flex-col w-full">
								<div class="flex justify-between items-center">
									<div class="flex gap-2 items-center">
										<div
											class={`text-xs ${($settings?.highContrastMode ?? false) ? 'text-gray-800 dark:text-gray-100' : 'text-gray-500'}`}
										>
											{$i18n.t('Auth')}
										</div>
									</div>
								</div>

								<div class="flex gap-2">
									<div class="flex-shrink-0 self-start">
										<select
											class={`dark:bg-gray-900 w-full text-sm bg-transparent pr-5 ${($settings?.highContrastMode ?? false) ? 'placeholder:text-gray-700 dark:placeholder:text-gray-100' : 'outline-hidden placeholder:text-gray-300 dark:placeholder:text-gray-700'}`}
											bind:value={auth_type}
										>
											<option value="none">{$i18n.t('None')}</option>
											<option value="bearer">{$i18n.t('Bearer')}</option>
											{#if !direct}
												<option value="session">{$i18n.t('Session')}</option>
												<option value="system_oauth">{$i18n.t('OAuth')}</option>
											{/if}
										</select>
									</div>

									<div class="flex flex-1 items-center">
										{#if auth_type === 'bearer'}
											<SensitiveInput
												bind:value={key}
												placeholder={$i18n.t('API Key')}
												required={false}
											/>
										{:else if auth_type === 'none'}
											<div
												class={`text-xs self-center translate-y-[1px] ${($settings?.highContrastMode ?? false) ? 'text-gray-800 dark:text-gray-100' : 'text-gray-500'}`}
											>
												{$i18n.t('No authentication')}
											</div>
										{:else if auth_type === 'session'}
											<div
												class={`text-xs self-center translate-y-[1px] ${($settings?.highContrastMode ?? false) ? 'text-gray-800 dark:text-gray-100' : 'text-gray-500'}`}
											>
												{$i18n.t('Forwards system user session credentials to authenticate')}
											</div>
										{:else if auth_type === 'system_oauth'}
											<div
												class={`text-xs self-center translate-y-[1px] ${($settings?.highContrastMode ?? false) ? 'text-gray-800 dark:text-gray-100' : 'text-gray-500'}`}
											>
												{$i18n.t('Forwards system user OAuth access token to authenticate')}
											</div>
										{/if}
									</div>
								</div>
							</div>
						</div>

						<div class="flex justify-between items-center pt-3 text-sm font-medium">
							<div>
								{#if edit}
									<button
										class="px-1 py-1.5 text-sm font-medium text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 hover:underline transition"
										type="button"
										on:click={() => {
											showDeleteConfirmDialog = true;
										}}
									>
										{$i18n.t('Delete')}
									</button>
								{/if}
							</div>

							<button
								class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full flex flex-row space-x-1 items-center"
								type="submit"
							>
								{$i18n.t('Save')}
							</button>
						</div>
					</div>
				</form>
			</div>
		</div>
	</div>
</Modal>

<AccessControlModal bind:show={showAccessControlModal} bind:accessGrants />

<ConfirmDialog
	bind:show={showDeleteConfirmDialog}
	message={$i18n.t(
		'Are you sure you want to delete this connection? This action cannot be undone.'
	)}
	confirmLabel={$i18n.t('Delete')}
	on:confirm={() => {
		onDelete();
		show = false;
	}}
/>
