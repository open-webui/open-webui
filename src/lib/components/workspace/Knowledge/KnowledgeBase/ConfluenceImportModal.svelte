<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { getContext, onMount } from 'svelte';
	const i18n = getContext('i18n');

	import { config, settings } from '$lib/stores';
	import { updateUserSettings } from '$lib/apis/users';

	import Modal from '$lib/components/common/Modal.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import SensitiveInput from '$lib/components/common/SensitiveInput.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import ChevronRight from '$lib/components/icons/ChevronRight.svelte';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import Minus from '$lib/components/icons/Minus.svelte';

	import {
		testConfluenceConnection,
		getConfluenceSpaces,
		getConfluenceSpacePages,
		importConfluenceContent,
		type ConfluenceConnectionConfig,
		type ConfluenceSpace,
		type ConfluencePage
	} from '$lib/apis/retrieval';

	export let show = false;
	export let onImport: (documents: any[]) => void = () => {};

	// Admin-configured values (read-only for users)
	$: adminBaseUrl = $config?.confluence?.base_url ?? '';
	$: adminDeploymentType = ($config?.confluence?.deployment_type ?? 'cloud') as
		| 'cloud'
		| 'datacenter';

	// User credentials
	let email = '';
	let apiToken = '';
	let personalAccessToken = '';

	// State
	type Step = 'config' | 'spaces' | 'pages';
	
	type PageNode = ConfluencePage & {
		children: PageNode[];
		level: number;
		expanded: boolean;
		parent?: PageNode;
	};

	let step: Step = 'config';
	let loading = false;
	let connectionTested = false;
	let spaces: ConfluenceSpace[] = [];
	let selectedSpaceKeys: Set<string> = new Set();
	let spacePages: Record<string, PageNode[]> = {};
	let selectedPageIds: Set<string> = new Set();
	type NodeCheckState = 'checked' | 'indeterminate' | 'unchecked';
	let nodeStateCache: Map<string, NodeCheckState> = new Map();
	let spaceCheckState: Record<string, NodeCheckState> = {};
	let importing = false;
	let fetchingPages = false;
	let fetchingSpaces = false;
	let spaceFilter = '';
	let pageFilter = '';

	$: filteredSpaces = spaceFilter
		? spaces.filter(
				(s) =>
					s.name.toLowerCase().includes(spaceFilter.toLowerCase()) ||
					s.key.toLowerCase().includes(spaceFilter.toLowerCase())
			)
		: spaces;

	$: allFilteredSelected =
		filteredSpaces.length > 0 && filteredSpaces.every((s) => selectedSpaceKeys.has(s.key));

	$: allFilteredPages = Object.entries(spacePages).flatMap(([spaceKey, pages]) => {
		if (!selectedSpaceKeys.has(spaceKey)) return [];
		return pages.filter(p => p.title.toLowerCase().includes(pageFilter.toLowerCase()));
	});

	$: allFilteredPagesSelected = allFilteredPages.length > 0 && allFilteredPages.every((p) => selectedPageIds.has(p.id));

	$: {
		const _ids = selectedPageIds;
		const cache = new Map<string, NodeCheckState>();

		function computeNodeState(node: PageNode): NodeCheckState {
			const selfSelected = _ids.has(node.id);
			if (node.children.length === 0) {
				const s: NodeCheckState = selfSelected ? 'checked' : 'unchecked';
				cache.set(node.id, s);
				return s;
			}
			let allChecked = selfSelected;
			let anyChecked = selfSelected;
			for (const child of node.children) {
				const cs = computeNodeState(child);
				if (cs !== 'checked') allChecked = false;
				if (cs !== 'unchecked') anyChecked = true;
			}
			const s: NodeCheckState = allChecked ? 'checked' : anyChecked ? 'indeterminate' : 'unchecked';
			cache.set(node.id, s);
			return s;
		}

		for (const nodes of Object.values(spacePages)) {
			for (const root of nodes.filter(n => !n.parent)) computeNodeState(root);
		}
		nodeStateCache = cache;
	}

	$: {
		const _cache = nodeStateCache;
		const result: Record<string, NodeCheckState> = {};
		for (const [spaceKey, nodes] of Object.entries(spacePages)) {
			if (!selectedSpaceKeys.has(spaceKey)) continue;
			const roots = nodes.filter(n => !n.parent);
			if (roots.length === 0) { result[spaceKey] = 'unchecked'; continue; }
			let allChecked = true, anyChecked = false;
			for (const root of roots) {
				const s = _cache.get(root.id) ?? 'unchecked';
				if (s !== 'checked') allChecked = false;
				if (s !== 'unchecked') anyChecked = true;
			}
			result[spaceKey] = allChecked ? 'checked' : anyChecked ? 'indeterminate' : 'unchecked';
		}
		spaceCheckState = result;
	}

	// Helper to build tree structure from flat list of pages
	function buildPageTree(pages: ConfluencePage[]): PageNode[] {
		const pageMap = new Map<string, PageNode>();
		
		// 1. Create nodes
		pages.forEach(p => {
			pageMap.set(p.id, {
				...p,
				children: [],
				level: 0,
				expanded: true, // Expand by default to show hierarchy
			});
		});

		const roots: PageNode[] = [];

		// 2. Link nodes
		pages.forEach(p => {
			const node = pageMap.get(p.id)!;
			// The last ancestor is the direct parent
			const parentId = p.ancestors && p.ancestors.length > 0
				? p.ancestors[p.ancestors.length - 1].id
				: null;

			if (parentId && pageMap.has(parentId)) {
				const parent = pageMap.get(parentId)!;
				parent.children.push(node);
				node.parent = parent;
			} else {
				roots.push(node);
			}
		});

		// 3. Set levels
		const setLevel = (nodes: PageNode[], level: number) => {
			nodes.forEach(node => {
				node.level = level;
				if (node.children.length > 0) {
					setLevel(node.children, level + 1);
				}
			});
		};
		setLevel(roots, 0);

		// 4. Sort by title
		const sortNodes = (nodes: PageNode[]) => {
			nodes.sort((a, b) => a.title.localeCompare(b.title));
			nodes.forEach(n => sortNodes(n.children));
		};
		sortNodes(roots);

		// Return all nodes (linked)
		return Array.from(pageMap.values());
	}

	// Helper to get visible nodes (flattened tree) based on expanded state
	function getVisibleNodes(nodes: PageNode[]): PageNode[] {
		// Roots are nodes without a parent in the current set
		const roots = nodes.filter(n => !n.parent).sort((a, b) => a.title.localeCompare(b.title));
		const visible: PageNode[] = [];

		const traverse = (node: PageNode) => {
			visible.push(node);
			if (node.expanded && node.children.length > 0) {
				// Children are already sorted in buildPageTree
				node.children.forEach(traverse);
			}
		};

		roots.forEach(traverse);
		return visible;
	}

	function toggleNodeExpanded(node: PageNode) {
		node.expanded = !node.expanded;
		// Trigger reactivity
		spacePages = { ...spacePages };
	}

	function toggleNodeSelection(node: PageNode, recursive: boolean = false) {
		const currentState = nodeStateCache.get(node.id) ?? 'unchecked';
		const shouldSelect = currentState !== 'checked'; // indeterminate → select-all

		if (recursive) {
			const traverse = (n: PageNode) => {
				if (shouldSelect) selectedPageIds.add(n.id);
				else selectedPageIds.delete(n.id);
				for (const child of n.children) traverse(child);
			};
			traverse(node);
		} else {
			if (selectedPageIds.has(node.id)) selectedPageIds.delete(node.id);
			else selectedPageIds.add(node.id);
		}

		selectedPageIds = selectedPageIds;
	}

	// Load saved credentials from user settings
	function loadFromSettings() {
		const confluenceSettings = $settings?.confluence ?? {};
		email = confluenceSettings.email ?? '';
		apiToken = confluenceSettings.api_token ?? '';
		personalAccessToken = confluenceSettings.personal_access_token ?? '';
	}

	// Save credentials to user settings (persisted server-side)
	async function saveToSettings() {
		const confluenceSettings: Record<string, string> = {};
		if (adminDeploymentType === 'cloud') {
			confluenceSettings.email = email.trim();
			confluenceSettings.api_token = apiToken.trim();
		} else {
			if (personalAccessToken.trim()) {
				confluenceSettings.personal_access_token = personalAccessToken.trim();
			}
		}

		await settings.set({ ...$settings, confluence: confluenceSettings });
		await updateUserSettings(localStorage.token, { ui: $settings });
	}

	// Load saved settings whenever modal opens
	$: if (show) {
		loadFromSettings();
	}

	function getConfig(): ConfluenceConnectionConfig {
		// base_url and auth_type come from admin config — not sent by user
		const cfg: ConfluenceConnectionConfig = {
			base_url: adminBaseUrl,
			auth_type: adminDeploymentType
		};
		if (adminDeploymentType === 'cloud') {
			cfg.email = email.trim();
			cfg.api_token = apiToken.trim();
		} else {
			cfg.personal_access_token = personalAccessToken.trim();
		}
		return cfg;
	}

	function validateConfig(): boolean {
		if (!adminBaseUrl) {
			toast.error(
				$i18n.t(
					'Confluence base URL is not configured. Please ask your administrator to set it in the admin settings.'
				)
			);
			return false;
		}
		if (adminDeploymentType === 'cloud') {
			if (!email.trim() || !apiToken.trim()) {
				toast.error($i18n.t('Please enter your email and API token.'));
				return false;
			}
		} else {
			if (!personalAccessToken.trim()) {
				toast.error($i18n.t('Please enter your Personal Access Token.'));
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

		fetchingSpaces = true;
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
			fetchingSpaces = false;
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

	function toggleAllFilteredPages() {
		if (allFilteredPagesSelected) {
			for (const p of allFilteredPages) {
				selectedPageIds.delete(p.id);
			}
		} else {
			for (const p of allFilteredPages) {
				selectedPageIds.add(p.id);
			}
		}
		selectedPageIds = selectedPageIds;
	}

	function toggleSpacePages(spaceKey: string) {
		const state = spaceCheckState[spaceKey] ?? 'unchecked';
		const shouldSelect = state !== 'checked';
		for (const node of (spacePages[spaceKey] ?? [])) {
			if (shouldSelect) selectedPageIds.add(node.id);
			else selectedPageIds.delete(node.id);
		}
		selectedPageIds = selectedPageIds;
	}

	async function handleNextToPages() {
		if (selectedSpaceKeys.size === 0) {
			toast.error($i18n.t('Please select at least one space.'));
			return;
		}

		fetchingPages = true;
		try {
			const cfg = getConfig();
			const newSpacePages: Record<string, PageNode[]> = {};
			for (const spaceKey of selectedSpaceKeys) {
				const res = await getConfluenceSpacePages(localStorage.token, spaceKey, cfg);
				if (res && res.pages) {
					// Build tree structure
					newSpacePages[spaceKey] = buildPageTree(res.pages);
				} else {
					newSpacePages[spaceKey] = [];
				}
			}
			spacePages = newSpacePages;
			
			// Auto-select all pages by default
			const newSelectedPageIds = new Set<string>();
			for (const spaceKey of Object.keys(spacePages)) {
				for (const page of spacePages[spaceKey]) {
					newSelectedPageIds.add(page.id);
				}
			}
			selectedPageIds = newSelectedPageIds;
			
			step = 'pages';
		} catch (e) {
			toast.error(`${e}`);
		} finally {
			fetchingPages = false;
		}
	}

	async function handleImport() {
		if (selectedPageIds.size === 0) {
			toast.error($i18n.t('Please select at least one page.'));
			return;
		}

		importing = true;
		try {
			const cfg = getConfig();
			const space_page_map: Record<string, string[]> = {};
			for (const spaceKey of selectedSpaceKeys) {
				const selectedInSpace = spacePages[spaceKey]
					?.filter(p => selectedPageIds.has(p.id))
					.map(p => p.id) || [];
				if (selectedInSpace.length > 0) {
					space_page_map[spaceKey] = selectedInSpace;
				}
			}

			const res = await importConfluenceContent(localStorage.token, {
				...cfg,
				space_keys: Array.from(selectedSpaceKeys),
				content_types: ['page'],
				space_page_map
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
		spacePages = {};
		selectedPageIds = new Set();
		connectionTested = false;
		spaceFilter = '';
		pageFilter = '';
		show = false;
	}

	function handleBack() {
		if (step === 'pages') {
			step = 'spaces';
			pageFilter = '';
		} else {
			step = 'config';
			spaces = [];
			selectedSpaceKeys = new Set();
			spaceFilter = '';
		}
	}
</script>

<Modal bind:show size="md">
	<div class="flex flex-col h-full max-h-[80vh]">
		<div class="flex justify-between items-center dark:text-gray-100 px-5 pt-4 pb-2">
			<div class="flex items-center gap-2">
				{#if step === 'spaces' || step === 'pages'}
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
					{:else if step === 'spaces'}
						{$i18n.t('Select Spaces')}
					{:else}
						{$i18n.t('Select Pages')}
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
				<!-- Admin-configured endpoint info (read-only) -->
				<div
					class="mb-3 px-3 py-2 rounded-lg bg-gray-50 dark:bg-gray-850 text-xs text-gray-500 dark:text-gray-400"
				>
					<div class="font-medium text-gray-700 dark:text-gray-300 mb-1">
						{$i18n.t('Confluence Endpoint')}
					</div>
					{#if adminBaseUrl}
						<div class="flex items-center gap-2">
							<span class="truncate">{adminBaseUrl}</span>
							<span
								class="shrink-0 px-1.5 py-0.5 rounded text-xs bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-300"
							>
								{adminDeploymentType === 'cloud'
									? $i18n.t('Cloud')
									: $i18n.t('Data Center')}
							</span>
						</div>
					{:else}
						<span class="text-red-500 dark:text-red-400">
							{$i18n.t('Not configured — ask your administrator to set the Confluence URL.')}
						</span>
					{/if}
				</div>

				<form on:submit|preventDefault={handleFetchSpaces} class="flex flex-col gap-3">
					{#if adminDeploymentType === 'cloud'}
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
						<!-- Data Center: PAT only -->
						<div>
							<label
								class="block text-xs text-gray-500 dark:text-gray-400 mb-1"
								for="confluence-pat"
							>
								{$i18n.t('Personal Access Token')}
							</label>
							<SensitiveInput
								placeholder={$i18n.t('Personal Access Token')}
								bind:value={personalAccessToken}
								required={true}
								on:input={() => {
									connectionTested = false;
								}}
							/>
							<p class="text-xs text-gray-400 mt-1">
								{$i18n.t('Generate in Confluence: Profile → Personal Access Tokens')}
							</p>
						</div>
					{/if}

					<!-- Actions -->
					<div class="flex justify-between items-center gap-2 pt-2">
						<button
							class="px-3.5 py-1.5 text-sm font-medium border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800 transition rounded-full"
							type="button"
							disabled={loading || !adminBaseUrl}
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
							disabled={loading || fetchingSpaces || !adminBaseUrl}
						>
							{#if fetchingSpaces}
								<div class="flex items-center gap-2">
									<Spinner className="size-3" />
									{$i18n.t('Loading Spaces...')}
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

				<!-- Next button -->
				<div class="flex justify-end gap-2 pt-3">
					<button
						class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-800 text-white dark:bg-white dark:text-black dark:hover:bg-gray-200 transition rounded-full disabled:opacity-50"
						disabled={selectedSpaceKeys.size === 0 || fetchingPages}
						on:click={handleNextToPages}
					>
						{#if fetchingPages}
							<div class="flex items-center gap-2">
								<Spinner className="size-3" />
								{$i18n.t('Loading Pages...')}
							</div>
						{:else}
							{$i18n.t('Select Pages')}
						{/if}
					</button>
				</div>
			</div>
		{:else if step === 'pages'}
			<div class="flex flex-col flex-1 min-h-0 px-5 pb-4">
				<!-- Search filter -->
				<div class="mb-3">
					<input
						type="text"
						class="w-full text-sm bg-gray-50 dark:bg-gray-850 rounded-xl px-3 py-2 outline-none"
						bind:value={pageFilter}
						placeholder={$i18n.t('Filter pages...')}
					/>
				</div>

				<!-- Select all toggle -->
				<div class="flex items-center justify-between mb-2 px-1">
					<button
						class="text-xs text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 transition"
						on:click={toggleAllFilteredPages}
					>
						{#if allFilteredPagesSelected}
							{$i18n.t('Deselect All')}
						{:else}
							{$i18n.t('Select All')}
						{/if}
					</button>
					<span class="text-xs text-gray-400">
						{selectedPageIds.size}
						{$i18n.t('selected')}
					</span>
				</div>

				<!-- Pages list -->
				<div
					class="flex-1 overflow-y-auto border border-gray-100 dark:border-gray-800 rounded-xl"
				>
					{#if allFilteredPages.length === 0}
						<div
							class="flex items-center justify-center h-full text-sm text-gray-400 py-8"
						>
							{#if Object.values(spacePages).flat().length === 0}
								{$i18n.t('No pages found in selected spaces.')}
							{:else}
								{$i18n.t('No pages match your filter.')}
							{/if}
						</div>
					{:else}
						{#each Array.from(selectedSpaceKeys) as spaceKey}
							{#if spacePages[spaceKey] && spacePages[spaceKey].length > 0}
								{@const spaceState = spaceCheckState[spaceKey] ?? 'unchecked'}
								<div class="px-3 py-1.5 bg-gray-50 dark:bg-gray-800 border-b border-gray-100 dark:border-gray-800/50 text-xs font-semibold text-gray-600 dark:text-gray-300 sticky top-0 z-10 shadow-sm flex items-center justify-between">
									<span>{spaces.find(s => s.key === spaceKey)?.name || spaceKey}</span>
									<button
										class="flex items-center gap-1.5 transition"
										on:click={() => toggleSpacePages(spaceKey)}
										title={spaceState === 'checked' ? $i18n.t('Deselect all in space') : $i18n.t('Select all in space')}
									>
										<div class="w-4 h-4 rounded border-2 flex items-center justify-center shrink-0 transition
											{spaceState === 'unchecked' ? 'border-gray-300 dark:border-gray-600' : 'bg-black dark:bg-white border-black dark:border-white'}">
											{#if spaceState === 'checked'}
												<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="3" stroke="currentColor" class="w-3 h-3 text-white dark:text-black">
													<path stroke-linecap="round" stroke-linejoin="round" d="M4.5 12.75l6 6 9-13.5" />
												</svg>
											{:else if spaceState === 'indeterminate'}
												<Minus className="w-3 h-3 text-white dark:text-black" strokeWidth="3" />
											{/if}
										</div>
									</button>
								</div>
								
								{#if pageFilter}
									<!-- Flat list when filtering -->
									{#each spacePages[spaceKey].filter(p => p.title.toLowerCase().includes(pageFilter.toLowerCase())) as page (page.id)}
										{@const pageState = nodeStateCache.get(page.id) ?? 'unchecked'}
										<button
											class="w-full flex items-center gap-3 px-3 py-2 text-left hover:bg-gray-50 dark:hover:bg-gray-800/50 transition border-b border-gray-50 dark:border-gray-800/50 last:border-b-0"
											on:click={() => toggleNodeSelection(page, true)}
										>
											<div class="w-4 h-4 rounded border-2 flex items-center justify-center shrink-0 transition {pageState === 'unchecked'
												? 'border-gray-300 dark:border-gray-600'
												: 'bg-black dark:bg-white border-black dark:border-white'}"
											>
												{#if pageState === 'checked'}
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
												{:else if pageState === 'indeterminate'}
													<Minus className="w-3 h-3 text-white dark:text-black" strokeWidth="3" />
												{/if}
											</div>
											<div class="flex-1 min-w-0">
												<div class="text-sm font-medium truncate">
													{page.title || $i18n.t('Untitled')}
												</div>
											</div>
										</button>
									{/each}
								{:else}
									<!-- Tree view -->
									{#each getVisibleNodes(spacePages[spaceKey]) as node (node.id)}
										{@const nodeState = nodeStateCache.get(node.id) ?? 'unchecked'}
										<div
											class="flex items-center gap-2 px-3 py-1.5 text-left hover:bg-gray-50 dark:hover:bg-gray-800/50 transition border-b border-gray-50 dark:border-gray-800/50 last:border-b-0"
											style="padding-left: {node.level * 1.5 + 0.75}rem"
										>
											<button
												class="w-4 h-4 flex items-center justify-center text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 transition shrink-0"
												on:click={() => toggleNodeExpanded(node)}
											>
												{#if node.children.length > 0}
													{#if node.expanded}
														<ChevronDown className="size-3.5" />
													{:else}
														<ChevronRight className="size-3.5" />
													{/if}
												{:else}
													<!-- Placeholder for alignment -->
													<span class="size-3.5"></span>
												{/if}
											</button>

											<button
												class="flex-1 flex items-center gap-3 min-w-0"
												on:click={() => toggleNodeSelection(node, true)}
											>
												<div class="w-4 h-4 rounded border-2 flex items-center justify-center shrink-0 transition
													{nodeState === 'unchecked' ? 'border-gray-300 dark:border-gray-600' : 'bg-black dark:bg-white border-black dark:border-white'}">
													{#if nodeState === 'checked'}
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
													{:else if nodeState === 'indeterminate'}
														<Minus className="w-3 h-3 text-white dark:text-black" strokeWidth="3" />
													{/if}
												</div>
												<div class="truncate text-sm font-medium">
													{node.title || $i18n.t('Untitled')}
												</div>
											</button>
										</div>
									{/each}
								{/if}
							{/if}
						{/each}
					{/if}
				</div>

				<!-- Import button -->
				<div class="flex justify-end gap-2 pt-3">
					<button
						class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-800 text-white dark:bg-white dark:text-black dark:hover:bg-gray-200 transition rounded-full disabled:opacity-50"
						disabled={selectedPageIds.size === 0 || importing}
						on:click={handleImport}
					>
						{#if importing}
							<div class="flex items-center gap-2">
								<Spinner className="size-3" />
								{$i18n.t('Importing...')}
							</div>
						{:else}
							{$i18n.t('Import {{count}} page(s)', {
								count: selectedPageIds.size
							})}
						{/if}
					</button>
				</div>
			</div>
		{/if}
	</div>
</Modal>