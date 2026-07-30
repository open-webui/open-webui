<script lang="ts">
	import { getContext, createEventDispatcher } from 'svelte';
	import type { AuditLogFacets } from '$lib/apis/audit-logs';

	import Search from '$lib/components/icons/Search.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import AdjustmentsHorizontal from '$lib/components/icons/AdjustmentsHorizontal.svelte';
	import Reset from '$lib/components/icons/Reset.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';

	const i18n: any = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let query: string = '';
	export let timeRange: '24h' | '7d' | '30d' | 'custom' = '24h';
	export let customStartAt: string = '';
	export let customEndAt: string = '';

	export let selectedEndpoint: string = '';
	export let selectedUser: string = '';
	export let selectedRequestModel: string = '';
	export let selectedResponseModel: string = '';
	export let selectedSkills: string[] = [];
	export let selectedStatus: string[] = [];
	export let sourceIp: string = '';
	export let selectedBodyState: string[] = [];

	export let facets: AuditLogFacets | null = null;
	export let loading: boolean = false;

	let showFilterPanel: boolean = false;
	let searchTimer: ReturnType<typeof setTimeout>;

	$: hasCustomFilters =
		timeRange !== '24h' ||
		!!customStartAt ||
		!!customEndAt ||
		!!selectedEndpoint ||
		!!selectedUser ||
		!!selectedRequestModel ||
		!!selectedResponseModel ||
		selectedSkills.length > 0 ||
		selectedStatus.length > 0 ||
		!!sourceIp ||
		selectedBodyState.length > 0;

	$: activeFilterCount =
		(selectedEndpoint ? 1 : 0) +
		(selectedUser ? 1 : 0) +
		(selectedRequestModel ? 1 : 0) +
		(selectedResponseModel ? 1 : 0) +
		selectedSkills.length +
		selectedStatus.length +
		(sourceIp ? 1 : 0) +
		selectedBodyState.length;

	const handleInput = () => {
		clearTimeout(searchTimer);
		searchTimer = setTimeout(() => {
			dispatch('change');
		}, 300);
	};

	const handleTimeRangeChange = (e: Event) => {
		const val = (e.target as HTMLSelectElement).value as any;
		timeRange = val;
		dispatch('change');
	};

	const handleFilterChange = () => {
		dispatch('change');
	};

	const resetFilters = () => {
		query = '';
		timeRange = '24h';
		customStartAt = '';
		customEndAt = '';
		selectedEndpoint = '';
		selectedUser = '';
		selectedRequestModel = '';
		selectedResponseModel = '';
		selectedSkills = [];
		selectedStatus = [];
		sourceIp = '';
		selectedBodyState = [];
		dispatch('change');
	};

	const toggleStatus = (val: string) => {
		if (selectedStatus.includes(val)) {
			selectedStatus = selectedStatus.filter((s) => s !== val);
		} else {
			selectedStatus = [...selectedStatus, val];
		}
		handleFilterChange();
	};

	const toggleBodyState = (val: string) => {
		if (selectedBodyState.includes(val)) {
			selectedBodyState = selectedBodyState.filter((b) => b !== val);
		} else {
			selectedBodyState = [...selectedBodyState, val];
		}
		handleFilterChange();
	};

	const toggleSkill = (val: string) => {
		if (selectedSkills.includes(val)) {
			selectedSkills = selectedSkills.filter((s) => s !== val);
		} else {
			selectedSkills = [...selectedSkills, val];
		}
		handleFilterChange();
	};
</script>

<div class="flex flex-col gap-2 w-full mb-3 select-none">
	<!-- Top Search & Main Controls Toolbar (Height ~h-8) -->
	<div class="flex h-8 w-full items-center gap-2">
		<!-- Search Bar -->
		<div class="flex min-w-0 flex-1 items-center rounded-lg bg-gray-50 dark:bg-gray-850 px-2 py-1 border border-gray-200 dark:border-gray-800 focus-within:ring-1 focus-within:ring-blue-500">
			<div class="self-center ml-0.5 mr-2 text-gray-400">
				<Search className="size-3.5" />
			</div>
			<input
				class="w-full text-xs outline-hidden bg-transparent text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500"
				bind:value={query}
				on:input={handleInput}
				aria-label={$i18n.t('Search path, user, IP, or request ID')}
				placeholder={$i18n.t('Search path, user, IP, or request ID')}
			/>

			{#if query}
				<button
					class="p-0.5 rounded-full hover:bg-gray-200 dark:hover:bg-gray-700 transition text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
					aria-label={$i18n.t('Clear search')}
					on:click={() => {
						query = '';
						dispatch('change');
					}}
				>
					<XMark className="size-3" strokeWidth="2" />
				</button>
			{/if}
		</div>

		<!-- Time Range Select -->
		<div class="relative shrink-0">
			<select
				class="h-8 rounded-lg bg-gray-50 dark:bg-gray-850 px-2.5 py-1 text-xs text-gray-900 dark:text-gray-100 border border-gray-200 dark:border-gray-800 outline-hidden cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-800 transition pr-6"
				value={timeRange}
				on:change={handleTimeRangeChange}
			>
				<option value="24h">{$i18n.t('Last 24 hours')}</option>
				<option value="7d">{$i18n.t('Last 7 days')}</option>
				<option value="30d">{$i18n.t('Last 30 days')}</option>
				<option value="custom">{$i18n.t('Custom range')}</option>
			</select>
		</div>

		<!-- Filter Toggle Button -->
		<Tooltip content={$i18n.t('Filter options')}>
			<button
				type="button"
				class="h-8 shrink-0 flex items-center gap-1.5 rounded-lg px-2.5 py-1 text-xs transition border {showFilterPanel || activeFilterCount > 0
					? 'bg-blue-50 dark:bg-blue-950/40 text-blue-600 dark:text-blue-400 border-blue-200 dark:border-blue-800 font-medium'
					: 'bg-gray-50 dark:bg-gray-850 text-gray-700 dark:text-gray-300 border-gray-200 dark:border-gray-800 hover:bg-gray-100 dark:hover:bg-gray-800'}"
				on:click={() => {
					showFilterPanel = !showFilterPanel;
				}}
			>
				<AdjustmentsHorizontal className="size-3.5" />
				<span class="hidden sm:inline">{$i18n.t('Filters')}</span>
				{#if activeFilterCount > 0}
					<span class="ml-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-blue-600 text-[10px] text-white px-1 font-semibold">
						{activeFilterCount}
					</span>
				{/if}
			</button>
		</Tooltip>

		<!-- Reset Button (only shown when non-default filters exist) -->
		{#if hasCustomFilters || query}
			<Tooltip content={$i18n.t('Reset all filters')}>
				<button
					type="button"
					class="h-8 shrink-0 flex items-center justify-center rounded-lg bg-gray-50 dark:bg-gray-850 px-2 py-1 text-xs text-gray-500 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-100 border border-gray-200 dark:border-gray-800 hover:bg-gray-100 dark:hover:bg-gray-800 transition"
					on:click={resetFilters}
					aria-label={$i18n.t('Reset all filters')}
				>
					<Reset className="size-3.5" />
				</button>
			</Tooltip>
		{/if}
	</div>

	<!-- Custom Date Range Picker (if timeRange === 'custom') -->
	{#if timeRange === 'custom'}
		<div class="flex flex-wrap items-center gap-2 p-2 rounded-lg bg-gray-50/80 dark:bg-gray-850/80 border border-gray-200 dark:border-gray-800 text-xs">
			<span class="text-gray-500 dark:text-gray-400 font-medium">{$i18n.t('Start')}:</span>
			<input
				type="datetime-local"
				class="rounded-md bg-white dark:bg-gray-900 px-2 py-1 border border-gray-200 dark:border-gray-800 text-xs text-gray-900 dark:text-gray-100"
				bind:value={customStartAt}
				on:change={handleFilterChange}
			/>
			<span class="text-gray-500 dark:text-gray-400 font-medium ml-2">{$i18n.t('End')}:</span>
			<input
				type="datetime-local"
				class="rounded-md bg-white dark:bg-gray-900 px-2 py-1 border border-gray-200 dark:border-gray-800 text-xs text-gray-900 dark:text-gray-100"
				bind:value={customEndAt}
				on:change={handleFilterChange}
			/>
		</div>
	{/if}

	<!-- Expandable Advanced Filter Grid Panel -->
	{#if showFilterPanel}
		<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2.5 p-3 rounded-xl bg-gray-50/70 dark:bg-gray-850/50 border border-gray-200/80 dark:border-gray-800/80 text-xs">
			<!-- Endpoint Filter -->
			<div class="flex flex-col gap-1">
				<label class="text-[11px] font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider">
					{$i18n.t('Endpoint')}
				</label>
				{#if facets?.endpoints && facets.endpoints.length > 0}
					<select
						class="w-full rounded-lg bg-white dark:bg-gray-900 px-2 py-1 border border-gray-200 dark:border-gray-800 text-xs text-gray-900 dark:text-gray-100 outline-hidden"
						bind:value={selectedEndpoint}
						on:change={handleFilterChange}
					>
						<option value="">{$i18n.t('All Endpoints')}</option>
						{#each facets.endpoints as ep}
							<option value={ep}>{ep}</option>
						{/each}
					</select>
				{:else}
					<input
						type="text"
						class="w-full rounded-lg bg-white dark:bg-gray-900 px-2 py-1 border border-gray-200 dark:border-gray-800 text-xs text-gray-900 dark:text-gray-100 outline-hidden"
						placeholder={$i18n.t('e.g. /api/v1/chat/completions')}
						bind:value={selectedEndpoint}
						on:change={handleFilterChange}
					/>
				{/if}
			</div>

			<!-- User ID / Filter -->
			<div class="flex flex-col gap-1">
				<label class="text-[11px] font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider">
					{$i18n.t('User ID / Email')}
				</label>
				<input
					type="text"
					class="w-full rounded-lg bg-white dark:bg-gray-900 px-2 py-1 border border-gray-200 dark:border-gray-800 text-xs text-gray-900 dark:text-gray-100 outline-hidden"
					placeholder={$i18n.t('Filter by User ID or Email')}
					bind:value={selectedUser}
					on:change={handleFilterChange}
				/>
			</div>

			<!-- Request Model -->
			<div class="flex flex-col gap-1">
				<label class="text-[11px] font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider">
					{$i18n.t('Request Model')}
				</label>
				{#if facets?.request_models && facets.request_models.length > 0}
					<select
						class="w-full rounded-lg bg-white dark:bg-gray-900 px-2 py-1 border border-gray-200 dark:border-gray-800 text-xs text-gray-900 dark:text-gray-100 outline-hidden"
						bind:value={selectedRequestModel}
						on:change={handleFilterChange}
					>
						<option value="">{$i18n.t('All Request Models')}</option>
						{#each facets.request_models as rm}
							<option value={rm}>{rm}</option>
						{/each}
					</select>
				{:else}
					<input
						type="text"
						class="w-full rounded-lg bg-white dark:bg-gray-900 px-2 py-1 border border-gray-200 dark:border-gray-800 text-xs text-gray-900 dark:text-gray-100 outline-hidden"
						placeholder={$i18n.t('Filter by request model')}
						bind:value={selectedRequestModel}
						on:change={handleFilterChange}
					/>
				{/if}
			</div>

			<!-- Response Model -->
			<div class="flex flex-col gap-1">
				<label class="text-[11px] font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider">
					{$i18n.t('Response Model')}
				</label>
				{#if facets?.response_models && facets.response_models.length > 0}
					<select
						class="w-full rounded-lg bg-white dark:bg-gray-900 px-2 py-1 border border-gray-200 dark:border-gray-800 text-xs text-gray-900 dark:text-gray-100 outline-hidden"
						bind:value={selectedResponseModel}
						on:change={handleFilterChange}
					>
						<option value="">{$i18n.t('All Response Models')}</option>
						{#each facets.response_models as rm}
							<option value={rm}>{rm}</option>
						{/each}
					</select>
				{:else}
					<input
						type="text"
						class="w-full rounded-lg bg-white dark:bg-gray-900 px-2 py-1 border border-gray-200 dark:border-gray-800 text-xs text-gray-900 dark:text-gray-100 outline-hidden"
						placeholder={$i18n.t('Filter by response model')}
						bind:value={selectedResponseModel}
						on:change={handleFilterChange}
					/>
				{/if}
			</div>

			<!-- Source IP -->
			<div class="flex flex-col gap-1">
				<label class="text-[11px] font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider">
					{$i18n.t('Source IP')}
				</label>
				<input
					type="text"
					class="w-full rounded-lg bg-white dark:bg-gray-900 px-2 py-1 border border-gray-200 dark:border-gray-800 text-xs text-gray-900 dark:text-gray-100 outline-hidden"
					placeholder={$i18n.t('Exact IP or CIDR prefix')}
					bind:value={sourceIp}
					on:change={handleFilterChange}
				/>
			</div>

			<!-- HTTP Status Code -->
			<div class="flex flex-col gap-1">
				<label class="text-[11px] font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider">
					{$i18n.t('HTTP Status')}
				</label>
				<div class="flex flex-wrap gap-1 mt-0.5">
					{#each ['2xx', '4xx', '5xx', 'no_response'] as st}
						<button
							type="button"
							class="px-2 py-0.5 rounded-md text-[11px] font-medium transition border {selectedStatus.includes(st)
								? 'bg-blue-500 text-white border-blue-600'
								: 'bg-white dark:bg-gray-900 text-gray-700 dark:text-gray-300 border-gray-200 dark:border-gray-800 hover:bg-gray-100 dark:hover:bg-gray-800'}"
							on:click={() => toggleStatus(st)}
						>
							{st === 'no_response' ? $i18n.t('No response') : st}
						</button>
					{/each}
				</div>
			</div>

			<!-- Body Capture State -->
			<div class="flex flex-col gap-1">
				<label class="text-[11px] font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider">
					{$i18n.t('Body State')}
				</label>
				<div class="flex flex-wrap gap-1 mt-0.5">
					<button
						type="button"
						class="px-2 py-0.5 rounded-md text-[11px] font-medium transition border {selectedBodyState.includes('request')
							? 'bg-blue-500 text-white border-blue-600'
							: 'bg-white dark:bg-gray-900 text-gray-700 dark:text-gray-300 border-gray-200 dark:border-gray-800 hover:bg-gray-100 dark:hover:bg-gray-800'}"
						on:click={() => toggleBodyState('request')}
					>
						{$i18n.t('Req Captured')}
					</button>
					<button
						type="button"
						class="px-2 py-0.5 rounded-md text-[11px] font-medium transition border {selectedBodyState.includes('response')
							? 'bg-blue-500 text-white border-blue-600'
							: 'bg-white dark:bg-gray-900 text-gray-700 dark:text-gray-300 border-gray-200 dark:border-gray-800 hover:bg-gray-100 dark:hover:bg-gray-800'}"
						on:click={() => toggleBodyState('response')}
					>
						{$i18n.t('Res Captured')}
					</button>
					<button
						type="button"
						class="px-2 py-0.5 rounded-md text-[11px] font-medium transition border {selectedBodyState.includes('truncated')
							? 'bg-blue-500 text-white border-blue-600'
							: 'bg-white dark:bg-gray-900 text-gray-700 dark:text-gray-300 border-gray-200 dark:border-gray-800 hover:bg-gray-100 dark:hover:bg-gray-800'}"
						on:click={() => toggleBodyState('truncated')}
					>
						{$i18n.t('Truncated')}
					</button>
				</div>
			</div>

			<!-- Request Skills -->
			{#if facets?.request_skill_ids && facets.request_skill_ids.length > 0}
				<div class="flex flex-col gap-1">
					<label class="text-[11px] font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider">
						{$i18n.t('Request Skills')}
					</label>
					<div class="flex flex-wrap gap-1 max-h-16 overflow-y-auto pr-1">
						{#each facets.request_skill_ids as sk}
							<button
								type="button"
								class="px-2 py-0.5 rounded-md text-[11px] font-medium transition border {selectedSkills.includes(sk)
									? 'bg-blue-500 text-white border-blue-600'
									: 'bg-white dark:bg-gray-900 text-gray-700 dark:text-gray-300 border-gray-200 dark:border-gray-800 hover:bg-gray-100 dark:hover:bg-gray-800'}"
								on:click={() => toggleSkill(sk)}
							>
								{sk}
							</button>
						{/each}
					</div>
				</div>
			{/if}
		</div>
	{/if}

	<!-- Active Filter Chips Row -->
	{#if activeFilterCount > 0}
		<div class="flex flex-wrap items-center gap-1.5 text-[11px] mt-1">
			<span class="text-gray-400 font-medium">{$i18n.t('Active filters')}:</span>

			{#if selectedEndpoint}
				<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-blue-50 dark:bg-blue-950/60 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-800">
					Endpoint: <strong class="font-mono">{selectedEndpoint}</strong>
					<button on:click={() => { selectedEndpoint = ''; handleFilterChange(); }} class="hover:text-blue-900 dark:hover:text-white">
						<XMark className="size-2.5" strokeWidth="2.5" />
					</button>
				</span>
			{/if}

			{#if selectedUser}
				<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-blue-50 dark:bg-blue-950/60 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-800">
					User: <strong>{selectedUser}</strong>
					<button on:click={() => { selectedUser = ''; handleFilterChange(); }} class="hover:text-blue-900 dark:hover:text-white">
						<XMark className="size-2.5" strokeWidth="2.5" />
					</button>
				</span>
			{/if}

			{#if selectedRequestModel}
				<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-blue-50 dark:bg-blue-950/60 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-800">
					Req Model: <strong>{selectedRequestModel}</strong>
					<button on:click={() => { selectedRequestModel = ''; handleFilterChange(); }} class="hover:text-blue-900 dark:hover:text-white">
						<XMark className="size-2.5" strokeWidth="2.5" />
					</button>
				</span>
			{/if}

			{#if selectedResponseModel}
				<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-blue-50 dark:bg-blue-950/60 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-800">
					Res Model: <strong>{selectedResponseModel}</strong>
					<button on:click={() => { selectedResponseModel = ''; handleFilterChange(); }} class="hover:text-blue-900 dark:hover:text-white">
						<XMark className="size-2.5" strokeWidth="2.5" />
					</button>
				</span>
			{/if}

			{#if sourceIp}
				<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-blue-50 dark:bg-blue-950/60 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-800">
					IP: <strong class="font-mono">{sourceIp}</strong>
					<button on:click={() => { sourceIp = ''; handleFilterChange(); }} class="hover:text-blue-900 dark:hover:text-white">
						<XMark className="size-2.5" strokeWidth="2.5" />
					</button>
				</span>
			{/if}

			{#each selectedStatus as st}
				<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-blue-50 dark:bg-blue-950/60 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-800">
					Status: <strong>{st}</strong>
					<button on:click={() => toggleStatus(st)} class="hover:text-blue-900 dark:hover:text-white">
						<XMark className="size-2.5" strokeWidth="2.5" />
					</button>
				</span>
			{/each}

			{#each selectedBodyState as bs}
				<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-blue-50 dark:bg-blue-950/60 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-800">
					Body: <strong>{bs}</strong>
					<button on:click={() => toggleBodyState(bs)} class="hover:text-blue-900 dark:hover:text-white">
						<XMark className="size-2.5" strokeWidth="2.5" />
					</button>
				</span>
			{/each}

			{#each selectedSkills as sk}
				<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-blue-50 dark:bg-blue-950/60 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-800">
					Skill: <strong>{sk}</strong>
					<button on:click={() => toggleSkill(sk)} class="hover:text-blue-900 dark:hover:text-white">
						<XMark className="size-2.5" strokeWidth="2.5" />
					</button>
				</span>
			{/each}
		</div>
	{/if}
</div>
