<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { getContext, onMount } from 'svelte';
	const i18n = getContext('i18n');

	import { settings } from '$lib/stores';
	import { updateUserSettings } from '$lib/apis/users';

	import Modal from '$lib/components/common/Modal.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import SensitiveInput from '$lib/components/common/SensitiveInput.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';

	import {
		testConfluenceConnection,
		getConfluenceSpaces,
		importConfluenceContent,
		type ConfluenceConnectionConfig,
		type ConfluenceSpace
	} from '$lib/apis/retrieval';

	export let show = false;
	export let onImport: (documents: any[]) => void = () => {};

	// Connection config - loaded from user settings
	let authType: 'cloud' | 'datacenter' = 'cloud';
	let baseUrl = '';
	let email = '';
	let apiToken = '';
	let username = '';
	let password = '';
	let personalAccessToken = '';

	// State
	type Step = 'config' | 'spaces';
	let step: Step = 'config';
	let loading = false;
	let connectionTested = false;
	let spaces: ConfluenceSpace[] = [];
	let selectedSpaceKeys: Set<string> = new Set();
	let importing = false;
	let spaceFilter = '';

	$: filteredSpaces = spaceFilter
		? spaces.filter(
				(s) =>
					s.name.toLowerCase().includes(spaceFilter.toLowerCase()) ||
					s.key.toLowerCase().includes(spaceFilter.toLowerCase())
			)
		: spaces;

	$: allFilteredSelected =
		filteredSpaces.length > 0 && filteredSpaces.every((s) => selectedSpaceKeys.has(s.key));

	// Load saved credentials from user settings
	function loadFromSettings() {
		const confluenceSettings = $settings?.confluence ?? {};
		authType = confluenceSettings.auth_type ?? 'cloud';
		baseUrl = confluenceSettings.base_url ?? '';
		email = confluenceSettings.email ?? '';
		apiToken = confluenceSettings.api_token ?? '';
		username = confluenceSettings.username ?? '';
		personalAccessToken = confluenceSettings.personal_access_token ?? '';
		// Note: password is NOT persisted for security
	}

	// Save credentials to user settings (persisted server-side)
	async function saveToSettings() {
		const confluenceSettings: Record<string, string> = {
			auth_type: authType,
			base_url: baseUrl.trim()
		};
		if (authType === 'cloud') {
			confluenceSettings.email = email.trim();
			confluenceSettings.api_token = apiToken.trim();
		} else {
			if (personalAccessToken.trim()) {
				confluenceSettings.personal_access_token = personalAccessToken.trim();
			}
			if (username.trim()) {
				confluenceSettings.username = username.trim();
			}
			// Note: password is NOT persisted for security
		}

		await settings.set({ ...$settings, confluence: confluenceSettings });
		await updateUserSettings(localStorage.token, { ui: $settings });
	}

	// Load saved settings whenever modal opens
	$: if (show) {
		loadFromSettings();
	}

	function getConfig(): ConfluenceConnectionConfig {
		const config: ConfluenceConnectionConfig = {
			base_url: baseUrl.trim(),
			auth_type: authType
		};
		if (authType === 'cloud') {
			config.email = email.trim();
			config.api_token = apiToken.trim();
		} else {
			if (personalAccessToken.trim()) {
				config.personal_access_token = personalAccessToken.trim();
			} else {
				config.username = username.trim();
				config.password = password;
			}
		}
		return config;
	}

	function validateConfig(): boolean {
		if (!baseUrl.trim()) {
			toast.error($i18n.t('Please enter the Confluence base URL.'));
			return false;
		}
		if (authType === 'cloud') {
			if (!email.trim() || !apiToken.trim()) {
				toast.error($i18n.t('Please enter your email and API token.'));
				return false;
			}
		} else {
			if (!personalAccessToken.trim() && (!username.trim() || !password)) {
				toast.error(
					$i18n.t('Please enter a personal access token, or username and password.')
				);
				return false;
			}
		}
		return true;
	}

	async function handleTestConnection() {
		if (!validateConfig()) return;

		loading = true;
		connectionTested = false;
		try {
			await testConfluenceConnection(localStorage.token, getConfig());
			connectionTested = true;
			// Save credentials on successful connection
			await saveToSettings();
			toast.success($i18n.t('Connection successful!'));
		} catch (e) {
			toast.error(`${e}`);
		} finally {
			loading = false;
		}
	}

	async function handleFetchSpaces() {
		if (!validateConfig()) return;

		loading = true;
		try {
			const res = await getConfluenceSpaces(localStorage.token, getConfig());
			if (res && res.spaces) {
				spaces = res.spaces;
				selectedSpaceKeys = new Set();
				step = 'spaces';
				// Save credentials on successful connection
				await saveToSettings();
			} else {
				toast.error($i18n.t('No spaces found.'));
			}
		} catch (e) {
			toast.error(`${e}`);
		} finally {
			loading = false;
		}
	}

	function toggleSpace(key: string) {
		if (selectedSpaceKeys.has(key)) {
			selectedSpaceKeys.delete(key);
		} else {
			selectedSpaceKeys.add(key);
		}
		selectedSpaceKeys = selectedSpaceKeys;
	}

	function toggleAllFiltered() {
		if (allFilteredSelected) {
			for (const s of filteredSpaces) {
				selectedSpaceKeys.delete(s.key);
			}
		} else {
			for (const s of filteredSpaces) {
				selectedSpaceKeys.add(s.key);
			}
		}
		selectedSpaceKeys = selectedSpaceKeys;
	}

	async function handleImport() {
		if (selectedSpaceKeys.size === 0) {
			toast.error($i18n.t('Please select at least one space.'));
			return;
		}

		importing = true;
		try {
			const config = getConfig();
			const res = await importConfluenceContent(localStorage.token, {
				...config,
				space_keys: Array.from(selectedSpaceKeys),
				content_types: ['page']
			});

			if (res && res.documents && res.documents.length > 0) {
				toast.success(
					$i18n.t('Imported {{count}} pages from Confluence.', {
						count: res.documents.length
					})
				);
				onImport(res.documents);
				resetAndClose();
			} else {
				toast.warning($i18n.t('No content found in the selected spaces.'));
			}
		} catch (e) {
			toast.error(`${e}`);
		} finally {
			importing = false;
		}
	}

	function resetAndClose() {
		step = 'config';
		spaces = [];
		selectedSpaceKeys = new Set();
		connectionTested = false;
		spaceFilter = '';
		show = false;
	}

	function handleBack() {
		step = 'config';
		spaces = [];
		selectedSpaceKeys = new Set();
		spaceFilter = '';
	}
</script>

<Modal bind:show size="md">
	<div class="flex flex-col h-full max-h-[80vh]">
		<div class="flex justify-between items-center dark:text-gray-100 px-5 pt-4 pb-2">
			<div class="flex items-center gap-2">
				{#if step === 'spaces'}
					<button
						class="p-1 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition"
						on:click={handleBack}
					>
						<svg
							xmlns="http://www.w3.org/2000/svg"
							fill="none"
							viewBox="0 0 24 24"
							stroke-width="2"
							stroke="currentColor"
							class="w-4 h-4"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								d="M15.75 19.5L8.25 12l7.5-7.5"
							/>
						</svg>
					</button>
				{/if}
				<h1 class="text-lg font-medium font-primary">
					{#if step === 'config'}
						{$i18n.t('Connect to Confluence')}
					{:else}
						{$i18n.t('Select Spaces')}
					{/if}
				</h1>
			</div>
			<button
				class="self-center"
				aria-label={$i18n.t('Close modal')}
				on:click={resetAndClose}
			>
				<XMark className="size-5" />
			</button>
		</div>

		{#if step === 'config'}
			<div class="px-5 pb-4 overflow-y-auto">
				<form on:submit|preventDefault={handleFetchSpaces} class="flex flex-col gap-3">
					<!-- Deployment Type -->
					<div>
						<label
							class="block text-xs text-gray-500 dark:text-gray-400 mb-1"
							for="confluence-auth-type"
						>
							{$i18n.t('Deployment Type')}
						</label>
						<select
							id="confluence-auth-type"
							class="w-full text-sm bg-gray-50 dark:bg-gray-850 rounded-xl px-3 py-2 outline-none"
							bind:value={authType}
							on:change={() => {
								connectionTested = false;
							}}
						>
							<option value="cloud">{$i18n.t('Confluence Cloud')}</option>
							<option value="datacenter"
								>{$i18n.t('Confluence Data Center / Server')}</option
							>
						</select>
					</div>

					<!-- Base URL -->
					<div>
						<label
							class="block text-xs text-gray-500 dark:text-gray-400 mb-1"
							for="confluence-base-url"
						>
							{$i18n.t('Base URL')}
						</label>
						<input
							id="confluence-base-url"
							type="url"
							class="w-full text-sm bg-gray-50 dark:bg-gray-850 rounded-xl px-3 py-2 outline-none"
							bind:value={baseUrl}
							placeholder={authType === 'cloud'
								? 'https://yoursite.atlassian.net'
								: 'https://confluence.yourcompany.com'}
							required
							on:input={() => {
								connectionTested = false;
							}}
						/>
					</div>

					{#if authType === 'cloud'}
						<!-- Cloud: Email + API Token -->
						<div>
							<label
								class="block text-xs text-gray-500 dark:text-gray-400 mb-1"
								for="confluence-email"
							>
								{$i18n.t('Email')}
							</label>
							<input
								id="confluence-email"
								type="email"
								class="w-full text-sm bg-gray-50 dark:bg-gray-850 rounded-xl px-3 py-2 outline-none"
								bind:value={email}
								placeholder="you@company.com"
								required
								on:input={() => {
									connectionTested = false;
								}}
							/>
						</div>
						<div>
							<label
								class="block text-xs text-gray-500 dark:text-gray-400 mb-1"
								for="confluence-api-token"
							>
								{$i18n.t('API Token')}
							</label>
							<SensitiveInput
								placeholder={$i18n.t('Atlassian API Token')}
								bind:value={apiToken}
								required={true}
								on:input={() => {
									connectionTested = false;
								}}
							/>
							<p class="text-xs text-gray-400 mt-1">
								{$i18n.t('Generate at id.atlassian.com > Security > API tokens')}
							</p>
						</div>
					{:else}
						<!-- Data Center: PAT or Username/Password -->
						<div>
							<label
								class="block text-xs text-gray-500 dark:text-gray-400 mb-1"
								for="confluence-pat"
							>
								{$i18n.t('Personal Access Token')}
							</label>
							<SensitiveInput
								placeholder={$i18n.t('Personal Access Token (recommended)')}
								bind:value={personalAccessToken}
								required={false}
								on:input={() => {
									connectionTested = false;
								}}
							/>
						</div>

						<div class="flex items-center gap-2 text-xs text-gray-400">
							<div class="flex-1 border-t border-gray-200 dark:border-gray-700"
							></div>
							<span>{$i18n.t('or')}</span>
							<div class="flex-1 border-t border-gray-200 dark:border-gray-700"
							></div>
						</div>

						<div>
							<label
								class="block text-xs text-gray-500 dark:text-gray-400 mb-1"
								for="confluence-username"
							>
								{$i18n.t('Username')}
							</label>
							<input
								id="confluence-username"
								type="text"
								class="w-full text-sm bg-gray-50 dark:bg-gray-850 rounded-xl px-3 py-2 outline-none"
								bind:value={username}
								placeholder={$i18n.t('Username')}
								on:input={() => {
									connectionTested = false;
								}}
							/>
						</div>
						<div>
							<label
								class="block text-xs text-gray-500 dark:text-gray-400 mb-1"
								for="confluence-password"
							>
								{$i18n.t('Password')}
							</label>
							<input
								id="confluence-password"
								type="password"
								class="w-full text-sm bg-gray-50 dark:bg-gray-850 rounded-xl px-3 py-2 outline-none"
								bind:value={password}
								placeholder={$i18n.t('Password (not saved)')}
								on:input={() => {
									connectionTested = false;
								}}
							/>
							<p class="text-xs text-gray-400 mt-1">
								{$i18n.t('Password is not saved. Use a Personal Access Token for persistent access.')}
							</p>
						</div>
					{/if}

					<!-- Actions -->
					<div class="flex justify-between items-center gap-2 pt-2">
						<button
							class="px-3.5 py-1.5 text-sm font-medium border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800 transition rounded-full"
							type="button"
							disabled={loading}
							on:click={handleTestConnection}
						>
							{#if loading && !connectionTested}
								<div class="flex items-center gap-2">
									<Spinner className="size-3" />
									{$i18n.t('Testing...')}
								</div>
							{:else if connectionTested}
								<div class="flex items-center gap-1 text-green-600 dark:text-green-400">
									<svg
										xmlns="http://www.w3.org/2000/svg"
										fill="none"
										viewBox="0 0 24 24"
										stroke-width="2"
										stroke="currentColor"
										class="w-4 h-4"
									>
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											d="M4.5 12.75l6 6 9-13.5"
										/>
									</svg>
									{$i18n.t('Connected')}
								</div>
							{:else}
								{$i18n.t('Test Connection')}
							{/if}
						</button>

						<button
							class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-800 text-white dark:bg-white dark:text-black dark:hover:bg-gray-200 transition rounded-full disabled:opacity-50"
							type="submit"
							disabled={loading}
						>
							{#if loading && !connectionTested}
								<div class="flex items-center gap-2">
									<Spinner className="size-3" />
									{$i18n.t('Connecting...')}
								</div>
							{:else}
								{$i18n.t('Browse Spaces')}
							{/if}
						</button>
					</div>
				</form>
			</div>
		{:else if step === 'spaces'}
			<div class="flex flex-col flex-1 min-h-0 px-5 pb-4">
				<!-- Search filter -->
				<div class="mb-3">
					<input
						type="text"
						class="w-full text-sm bg-gray-50 dark:bg-gray-850 rounded-xl px-3 py-2 outline-none"
						bind:value={spaceFilter}
						placeholder={$i18n.t('Filter spaces...')}
					/>
				</div>

				<!-- Select all toggle -->
				<div class="flex items-center justify-between mb-2 px-1">
					<button
						class="text-xs text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 transition"
						on:click={toggleAllFiltered}
					>
						{#if allFilteredSelected}
							{$i18n.t('Deselect All')}
						{:else}
							{$i18n.t('Select All')}
						{/if}
					</button>
					<span class="text-xs text-gray-400">
						{selectedSpaceKeys.size}
						{$i18n.t('selected')}
					</span>
				</div>

				<!-- Space list -->
				<div
					class="flex-1 overflow-y-auto border border-gray-100 dark:border-gray-800 rounded-xl"
				>
					{#if filteredSpaces.length === 0}
						<div
							class="flex items-center justify-center h-full text-sm text-gray-400 py-8"
						>
							{#if spaces.length === 0}
								{$i18n.t('No spaces found.')}
							{:else}
								{$i18n.t('No spaces match your filter.')}
							{/if}
						</div>
					{:else}
						{#each filteredSpaces as space (space.key)}
							<button
								class="w-full flex items-start gap-3 px-3 py-2.5 text-left hover:bg-gray-50 dark:hover:bg-gray-800/50 transition border-b border-gray-50 dark:border-gray-800/50 last:border-b-0"
								on:click={() => toggleSpace(space.key)}
							>
								<div class="mt-0.5">
									<div
										class="w-4 h-4 rounded border-2 flex items-center justify-center transition {selectedSpaceKeys.has(
											space.key
										)
											? 'bg-black dark:bg-white border-black dark:border-white'
											: 'border-gray-300 dark:border-gray-600'}"
									>
										{#if selectedSpaceKeys.has(space.key)}
											<svg
												xmlns="http://www.w3.org/2000/svg"
												fill="none"
												viewBox="0 0 24 24"
												stroke-width="3"
												stroke="currentColor"
												class="w-3 h-3 text-white dark:text-black"
											>
												<path
													stroke-linecap="round"
													stroke-linejoin="round"
													d="M4.5 12.75l6 6 9-13.5"
												/>
											</svg>
										{/if}
									</div>
								</div>
								<div class="flex-1 min-w-0">
									<div class="text-sm font-medium truncate">
										{space.name}
									</div>
									<div class="text-xs text-gray-400 truncate">
										{space.key}
										{#if space.type}
											&middot; {space.type}
										{/if}
									</div>
									{#if space.description}
										<div class="text-xs text-gray-400 mt-0.5 line-clamp-1">
											{space.description}
										</div>
									{/if}
								</div>
							</button>
						{/each}
					{/if}
				</div>

				<!-- Import button -->
				<div class="flex justify-end gap-2 pt-3">
					<button
						class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-800 text-white dark:bg-white dark:text-black dark:hover:bg-gray-200 transition rounded-full disabled:opacity-50"
						disabled={selectedSpaceKeys.size === 0 || importing}
						on:click={handleImport}
					>
						{#if importing}
							<div class="flex items-center gap-2">
								<Spinner className="size-3" />
								{$i18n.t('Importing...')}
							</div>
						{:else}
							{$i18n.t('Import {{count}} space(s)', {
								count: selectedSpaceKeys.size
							})}
						{/if}
					</button>
				</div>
			</div>
		{/if}
	</div>
</Modal>
