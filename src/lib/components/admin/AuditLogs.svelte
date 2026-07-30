<script lang="ts">
	import { getContext, onMount, onDestroy } from 'svelte';
	import dayjs from 'dayjs';
	import relativeTime from 'dayjs/plugin/relativeTime';
	import localizedFormat from 'dayjs/plugin/localizedFormat';
	dayjs.extend(relativeTime);
	dayjs.extend(localizedFormat);

	import { toast } from 'svelte-sonner';

	import {
		getAuditLogs,
		getAuditLogFacets,
		type AuditLogItemSummary,
		type AuditLogFacets,
		type AuditLogQueryParams
	} from '$lib/apis/audit-logs';

	import FilterBar from './AuditLogs/FilterBar.svelte';
	import DetailModal from './AuditLogs/DetailModal.svelte';

	import Pagination from '$lib/components/common/Pagination.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Eye from '$lib/components/icons/Eye.svelte';
	import ChevronUp from '$lib/components/icons/ChevronUp.svelte';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';

	const i18n: any = getContext('i18n');

	let page = 1;
	const limit = 30;

	let logs: AuditLogItemSummary[] | null = null;
	let total: number | null = null;

	let facets: AuditLogFacets | null = null;

	let initialLoading = true;
	let refreshing = false;

	// Filter state
	let query = '';
	let timeRange: '24h' | '7d' | '30d' | 'custom' = '24h';
	let customStartAt = '';
	let customEndAt = '';

	let selectedEndpoint = '';
	let selectedUser = '';
	let selectedRequestModel = '';
	let selectedResponseModel = '';
	let selectedSkills: string[] = [];
	let selectedStatus: string[] = [];
	let sourceIp = '';
	let selectedBodyState: string[] = [];

	let orderBy = 'created_at';
	let direction = 'desc';

	// Selected log item for DetailModal
	let selectedLogId: string | null = null;
	let showDetailModal = false;

	const computeTimeParams = () => {
		const now = Date.now();
		let startAt: number | undefined = undefined;
		let endAt: number | undefined = undefined;

		if (timeRange === '24h') {
			startAt = now - 24 * 60 * 60 * 1000;
		} else if (timeRange === '7d') {
			startAt = now - 7 * 24 * 60 * 60 * 1000;
		} else if (timeRange === '30d') {
			startAt = now - 30 * 24 * 60 * 60 * 1000;
		} else if (timeRange === 'custom') {
			if (customStartAt) startAt = new Date(customStartAt).getTime();
			if (customEndAt) endAt = new Date(customEndAt).getTime();
		}

		return { startAt, endAt };
	};

	const fetchLogs = async () => {
		if (logs !== null) refreshing = true;

		const { startAt, endAt } = computeTimeParams();

		const params: AuditLogQueryParams = {
			start_at: startAt,
			end_at: endAt,
			q: query.trim() || undefined,
			user_id: selectedUser.trim() || undefined,
			endpoint: selectedEndpoint.trim() || undefined,
			request_model: selectedRequestModel.trim() || undefined,
			response_model: selectedResponseModel.trim() || undefined,
			request_skill_ids: selectedSkills.length > 0 ? selectedSkills : undefined,
			status_classes: selectedStatus.length > 0 ? selectedStatus : undefined,
			source_ip: sourceIp.trim() || undefined,
			body_state: selectedBodyState.length > 0 ? selectedBodyState : undefined,
			order_by: orderBy,
			direction: direction,
			page: page,
			limit: limit
		};

		try {
			const res = await getAuditLogs(localStorage.token, params);
			if (res) {
				logs = res.items;
				total = res.total;
			}
		} catch (err: any) {
			toast.error(`${err}`);
		} finally {
			initialLoading = false;
			refreshing = false;
		}
	};

	const fetchFacetsData = async () => {
		const { startAt, endAt } = computeTimeParams();
		try {
			facets = await getAuditLogFacets(localStorage.token, startAt, endAt);
		} catch (err) {
			console.error('Failed to fetch audit log facets', err);
		}
	};

	const handleFilterChange = () => {
		if (page !== 1) {
			page = 1;
		} else {
			fetchLogs();
		}
		fetchFacetsData();
	};

	const sortState = (key: string) =>
		orderBy === key ? (direction === 'asc' ? 'ascending' : 'descending') : 'none';

	const setSortKey = (key: string) => {
		if (orderBy === key) {
			direction = direction === 'asc' ? 'desc' : 'asc';
		} else {
			orderBy = key;
			direction = 'desc';
		}
		if (page !== 1) {
			page = 1;
		} else {
			fetchLogs();
		}
	};

	const openDetail = (id: string) => {
		selectedLogId = id;
		showDetailModal = true;
	};

	const statusColorDot = (code: number) => {
		if (!code) return 'bg-gray-400';
		if (code >= 200 && code < 300) return 'bg-green-500';
		if (code >= 400 && code < 500) return 'bg-amber-500';
		if (code >= 500) return 'bg-red-500';
		return 'bg-gray-400';
	};

	$: if (page) {
		fetchLogs();
	}

	onMount(() => {
		fetchLogs();
		fetchFacetsData();
	});
</script>

<DetailModal bind:show={showDetailModal} logId={selectedLogId} />

<div class="px-3.5 lg:px-6 py-2 flex flex-col h-full w-full max-w-full">
	<!-- Filter Bar Component -->
	<FilterBar
		bind:query
		bind:timeRange
		bind:customStartAt
		bind:customEndAt
		bind:selectedEndpoint
		bind:selectedUser
		bind:selectedRequestModel
		bind:selectedResponseModel
		bind:selectedSkills
		bind:selectedStatus
		bind:sourceIp
		bind:selectedBodyState
		{facets}
		loading={refreshing}
		on:change={handleFilterChange}
	/>

	{#if initialLoading}
		<div class="my-20 flex flex-col items-center justify-center gap-2">
			<Spinner className="size-6 text-gray-500" />
			<span class="text-xs text-gray-400 font-medium">{$i18n.t('Loading audit logs...')}</span>
		</div>
	{:else if logs === null || logs.length === 0}
		<!-- Empty State -->
		<div class="my-16 flex flex-col items-center justify-center text-center p-6 rounded-2xl bg-gray-50/50 dark:bg-gray-850/30 border border-gray-100 dark:border-gray-800">
			<div class="p-3 rounded-full bg-gray-100 dark:bg-gray-800 mb-3 text-gray-400">
				<Eye className="size-6" />
			</div>
			<h4 class="text-sm font-semibold text-gray-800 dark:text-gray-200">
				{$i18n.t('No audit logs found')}
			</h4>
			<p class="text-xs text-gray-500 dark:text-gray-400 mt-1 max-w-xs">
				{$i18n.t('Try adjusting your search query, date range, or filter conditions.')}
			</p>
		</div>
	{:else}
		<!-- Main Results Table -->
		<div class="relative flex-1 min-h-0 flex flex-col">
			{#if refreshing}
				<div class="absolute top-0 right-0 z-20 p-1">
					<Spinner className="size-4 text-blue-500" />
				</div>
			{/if}

			<div class="scrollbar-hidden relative whitespace-nowrap overflow-x-auto max-w-full rounded-xl border border-gray-100 dark:border-gray-850 bg-white/50 dark:bg-gray-900/50 backdrop-blur-xs">
				<table class="w-full text-xs text-left text-gray-500 dark:text-gray-400 table-auto max-w-full">
					<thead class="text-[11px] font-semibold uppercase tracking-wider text-gray-700 dark:text-gray-300 bg-gray-50/80 dark:bg-gray-850/80 border-b border-gray-200/80 dark:border-gray-800/80">
						<tr>
							<!-- Time Column -->
							<th scope="col" class="font-normal select-none" aria-sort={sortState('created_at')}>
								<button
									type="button"
									class="flex w-full items-center gap-1 px-3 py-2 text-left hover:text-gray-900 dark:hover:text-white transition"
									on:click={() => setSortKey('created_at')}
								>
									{$i18n.t('Time')}
									{#if orderBy === 'created_at'}
										<span>
											{#if direction === 'asc'}
												<ChevronUp className="size-3" />
											{:else}
												<ChevronDown className="size-3" />
											{/if}
										</span>
									{/if}
								</button>
							</th>

							<!-- User Column -->
							<th scope="col" class="font-normal select-none" aria-sort={sortState('user_id')}>
								<button
									type="button"
									class="flex w-full items-center gap-1 px-3 py-2 text-left hover:text-gray-900 dark:hover:text-white transition"
									on:click={() => setSortKey('user_id')}
								>
									{$i18n.t('User')}
									{#if orderBy === 'user_id'}
										<span>
											{#if direction === 'asc'}
												<ChevronUp className="size-3" />
											{:else}
												<ChevronDown className="size-3" />
											{/if}
										</span>
									{/if}
								</button>
							</th>

							<!-- Endpoint Column -->
							<th scope="col" class="font-normal select-none" aria-sort={sortState('request_path')}>
								<button
									type="button"
									class="flex w-full items-center gap-1 px-3 py-2 text-left hover:text-gray-900 dark:hover:text-white transition"
									on:click={() => setSortKey('request_path')}
								>
									{$i18n.t('Endpoint')}
									{#if orderBy === 'request_path'}
										<span>
											{#if direction === 'asc'}
												<ChevronUp className="size-3" />
											{:else}
												<ChevronDown className="size-3" />
											{/if}
										</span>
									{/if}
								</button>
							</th>

							<!-- Method Column -->
							<th scope="col" class="px-3 py-2 font-normal select-none">
								{$i18n.t('Method')}
							</th>

							<!-- Status Column -->
							<th scope="col" class="font-normal select-none" aria-sort={sortState('response_status_code')}>
								<button
									type="button"
									class="flex w-full items-center gap-1 px-3 py-2 text-left hover:text-gray-900 dark:hover:text-white transition"
									on:click={() => setSortKey('response_status_code')}
								>
									{$i18n.t('Status')}
									{#if orderBy === 'response_status_code'}
										<span>
											{#if direction === 'asc'}
												<ChevronUp className="size-3" />
											{:else}
												<ChevronDown className="size-3" />
											{/if}
										</span>
									{/if}
								</button>
							</th>

							<!-- Source IP Column -->
							<th scope="col" class="px-3 py-2 font-normal select-none">
								{$i18n.t('Source IP')}
							</th>

							<!-- Level Column -->
							<th scope="col" class="px-3 py-2 font-normal select-none">
								{$i18n.t('Level')}
							</th>

							<!-- Details Column -->
							<th scope="col" class="px-3 py-2 font-normal text-right select-none">
								{$i18n.t('Details')}
							</th>
						</tr>
					</thead>

					<tbody class="divide-y divide-gray-100 dark:divide-gray-850">
						{#each logs as item (item.id)}
							<tr
								class="hover:bg-gray-50/70 dark:hover:bg-gray-850/50 transition cursor-pointer"
								on:click={() => openDetail(item.id)}
							>
								<!-- Time -->
								<td class="px-3 py-2 font-mono text-[11px] whitespace-nowrap text-gray-900 dark:text-gray-100">
									<Tooltip content={dayjs(item.created_at).format('YYYY-MM-DD HH:mm:ss.SSS')}>
										<span>{dayjs(item.created_at).fromNow()}</span>
									</Tooltip>
								</td>

								<!-- User -->
								<td class="px-3 py-2 max-w-44 truncate">
									{#if item.user?.name}
										<div class="font-medium text-gray-900 dark:text-gray-100 truncate">
											{item.user.name}
										</div>
										{#if item.user?.email}
											<div class="text-[10px] text-gray-400 truncate">{item.user.email}</div>
										{/if}
									{:else if item.user?.id}
										<div class="font-mono text-[10px] text-gray-500 truncate">{item.user.id}</div>
									{:else}
										<span class="text-gray-400 italic">{$i18n.t('Anonymous')}</span>
									{/if}
								</td>

								<!-- Endpoint -->
								<td class="px-3 py-2 max-w-64 font-mono text-[11px] truncate text-gray-800 dark:text-gray-200">
									<Tooltip content={item.request_path}>
										<span class="truncate block">{item.request_path}</span>
									</Tooltip>
								</td>

								<!-- Verb / Method -->
								<td class="px-3 py-2">
									<span class="px-1.5 py-0.5 rounded text-[10px] font-mono font-bold bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 border border-gray-200/60 dark:border-gray-700/60">
										{item.verb}
									</span>
								</td>

								<!-- Status -->
								<td class="px-3 py-2 whitespace-nowrap font-mono text-[11px]">
									<div class="flex items-center gap-1.5">
										<span class="size-1.5 rounded-full {statusColorDot(item.response_status_code)}"></span>
										<span class="font-semibold text-gray-900 dark:text-gray-100">
											{item.response_status_code || '-'}
										</span>
									</div>
								</td>

								<!-- Source IP -->
								<td class="px-3 py-2 font-mono text-[11px] text-gray-600 dark:text-gray-400">
									{item.source_ip || '-'}
								</td>

								<!-- Audit Level -->
								<td class="px-3 py-2">
									<span class="px-1.5 py-0.5 rounded text-[10px] font-medium bg-blue-50 dark:bg-blue-950/40 text-blue-600 dark:text-blue-400 border border-blue-200/50 dark:border-blue-800/50">
										{item.audit_level}
									</span>
								</td>

								<!-- Details Eye Button -->
								<td class="px-3 py-2 text-right">
									<Tooltip content={$i18n.t('View details')}>
										<button
											type="button"
											class="p-1 rounded-lg hover:bg-gray-200/60 dark:hover:bg-gray-700/60 text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition"
											on:click={(e) => {
												e.stopPropagation();
												openDetail(item.id);
											}}
											aria-label={$i18n.t('View details')}
										>
											<Eye className="size-3.5" />
										</button>
									</Tooltip>
								</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>

			<!-- Pagination Control -->
			{#if total !== null && total > limit}
				<div class="mt-3 flex justify-end">
					<Pagination bind:page count={total} perPage={limit} />
				</div>
			{/if}
		</div>
	{/if}
</div>
