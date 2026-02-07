<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	import { toast } from 'svelte-sonner';

	import Spinner from '$lib/components/common/Spinner.svelte';
	import StatCard from './StatCard.svelte';
	import type { PromptGroupStats, PromptTrace } from '$lib/apis/prompt-groups';
	import { getPromptGroupUsage } from '$lib/apis/prompt-groups';

	const i18n: Writable<i18nType> = getContext('i18n');

	export let groupId: string;
	export let groupName: string = '';

	let stats = {
		total_calls: 0,
		avg_latency: 0,
		total_tokens: 0,
		users: [],
		total_count: undefined,
		fetched_count: undefined
	};
	let traces: PromptTrace[] = [];
	let loading = false;
	let selectedDays = 7;
	let currentPage = 1;
	let pageSize = 10;
	let totalPages = 1;

	// 데이터 로드
	const loadData = async (page = 1) => {
		loading = true;
		try {
			const token = localStorage.getItem('token') || '';
			const offset = (page - 1) * pageSize;
			const usage = await getPromptGroupUsage(token, groupId, selectedDays, pageSize, false, offset);

			traces = usage.traces;
			stats = usage.stats;
			currentPage = page;

			// Calculate total pages
			if (stats.total_count) {
				totalPages = Math.ceil(stats.total_count / pageSize);
			} else if (traces.length > 0) {
				// If we have traces but no total_count, assume at least one page
				totalPages = 1;
			} else {
				totalPages = 1;
			}
		} catch (error: any) {
			console.error('Error loading data:', error);
			if (error?.status === 503) {
				toast.info('모니터링 서비스를 사용할 수 없습니다.');
			} else {
				toast.error('데이터를 불러오는데 실패했습니다.');
			}
		} finally {
			loading = false;
		}
	};

	const goToPage = async (page) => {
		if (page < 1 || page > totalPages || page === currentPage) return;
		await loadData(page);
	};

	const changePageSize = async (newSize) => {
		pageSize = newSize;
		await loadData(1);
	};

	// Helper function to generate page numbers for pagination
	const getPageNumbers = () => {
		const pages = [];
		const maxVisible = 5;

		if (totalPages <= maxVisible) {
			// Show all pages
			for (let i = 1; i <= totalPages; i++) {
				pages.push(i);
			}
		} else {
			// Always show first page
			pages.push(1);

			// Calculate range around current page
			let start = Math.max(2, currentPage - 1);
			let end = Math.min(totalPages - 1, currentPage + 1);

			// Add ellipsis after first page if needed
			if (start > 2) {
				pages.push('...');
			}

			// Add pages around current
			for (let i = start; i <= end; i++) {
				pages.push(i);
			}

			// Add ellipsis before last page if needed
			if (end < totalPages - 1) {
				pages.push('...');
			}

			// Always show last page
			pages.push(totalPages);
		}

		return pages;
	};

	const formatDate = (isoString: string): string => {
		try {
			const date = new Date(isoString);
			const month = String(date.getMonth() + 1).padStart(2, '0');
			const day = String(date.getDate()).padStart(2, '0');
			const hours = String(date.getHours()).padStart(2, '0');
			const minutes = String(date.getMinutes()).padStart(2, '0');
			return `${month}-${day} ${hours}:${minutes}`;
		} catch {
			return isoString;
		}
	};

	const formatLatency = (ms: number | undefined): string => {
		if (ms === undefined || ms === null) return '-';
		if (ms < 1000) return `${ms}ms`;
		return `${(ms / 1000).toFixed(2)}s`;
	};

	onMount(() => {
		loadData(1);
	});

	// Reload when groupId changes
	$: if (groupId) {
		loadData(1);
	}

	// Reload when period changes
	$: if (selectedDays) {
		loadData(1);
	}
</script>

<div class="monitoring-dashboard flex flex-col gap-4">
	<!-- Header & Controls -->
	<div class="flex items-center justify-between">
		<div>
			<h3 class="text-lg font-semibold text-gray-900 dark:text-white">
				{groupName ? `${groupName} 모니터링` : '프롬프트 그룹 모니터링'}
			</h3>
			<p class="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
				프롬프트 그룹의 사용량 통계 및 최근 트레이스를 확인합니다.
				{#if stats.total_count}
					<span class="font-medium">
						(총 {stats.total_count.toLocaleString()}개)
					</span>
				{/if}
			</p>
		</div>
		<div class="flex items-center gap-2">
			<select
				bind:value={selectedDays}
				class="px-3 py-2 text-sm bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg outline-none focus:ring-2 focus:ring-blue-500"
			>
				<option value={7}>최근 7일</option>
				<option value={30}>최근 30일</option>
				<option value={90}>최근 90일</option>
			</select>
			<button
				on:click={() => loadData(1)}
				class="px-3 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-lg transition"
				disabled={loading}
				aria-label="새로고침"
			>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					fill="none"
					viewBox="0 0 24 24"
					stroke-width="1.5"
					stroke="currentColor"
					class="size-4"
					class:animate-spin={loading}
				>
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0 3.181 3.183a8.25 8.25 0 0 0 13.803-3.7M4.031 9.865a8.25 8.25 0 0 1 13.803-3.7l3.181 3.182m0-4.991v4.99"
					/>
				</svg>
			</button>
		</div>
	</div>

	{#if loading}
		<div class="flex items-center justify-center py-12">
			<Spinner className="size-8" />
		</div>
	{:else}
		<!-- Stats Grid -->
		<div class="stats-grid grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
			<StatCard
				title="총 호출 수"
				value={stats.total_count?.toLocaleString() || stats.total_calls.toLocaleString()}
			/>
			<StatCard title="평균 응답 시간" value={formatLatency(stats.avg_latency)} />
			<StatCard title="토큰 사용량" value={stats.total_tokens.toLocaleString()} />
			<StatCard title="사용자 수" value={stats.users.length} />
		</div>

		<!-- Traces Table -->
		<div class="traces-section">
			<div class="flex items-center justify-between mb-3">
				<h4 class="text-sm font-medium text-gray-900 dark:text-white">최근 트레이스</h4>
				{#if stats.total_count}
					<span class="text-xs text-gray-500 dark:text-gray-400">
						전체 {stats.total_count.toLocaleString()}개 중 {traces.length}개 표시
					</span>
				{/if}
			</div>

			{#if traces.length === 0}
				<div class="p-8 text-center border border-dashed border-gray-300 dark:border-gray-600 rounded-lg">
					<svg
						xmlns="http://www.w3.org/2000/svg"
						fill="none"
						viewBox="0 0 24 24"
						stroke-width="1.5"
						stroke="currentColor"
						class="size-12 mx-auto text-gray-300 dark:text-gray-600 mb-3"
					>
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							d="M3.75 3v11.25A2.25 2.25 0 0 0 6 16.5h2.25M3.75 3h-1.5m1.5 0h16.5m0 0h1.5m-1.5 0v11.25A2.25 2.25 0 0 1 18 16.5h-2.25m-7.5 0h7.5m-7.5 0-1 3m8.5-3 1 3m0 0 .5 1.5m-.5-1.5h-9.5m0 0-.5 1.5M9 11.25v1.5M12 9v3.75m3-6v6"
						/>
					</svg>
					<p class="text-gray-500 dark:text-gray-400 text-sm">
						선택한 기간에 트레이스가 없습니다.
					</p>
				</div>
			{:else}
				<div class="overflow-x-auto border border-gray-200 dark:border-gray-700 rounded-lg">
					<table class="w-full text-sm">
						<thead class="bg-gray-50 dark:bg-gray-800/50 border-b border-gray-200 dark:border-gray-700">
							<tr>
								<th class="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
									시간
								</th>
								<th class="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
									사용자
								</th>
								<th class="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
									모델
								</th>
								<th class="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
									챕터
								</th>
								<th class="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
									응답시간
								</th>
								<th class="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
									토큰
								</th>
								<th class="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
									비용
								</th>
								<th class="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
									상세
								</th>
							</tr>
						</thead>
						<tbody class="divide-y divide-gray-200 dark:divide-gray-700 bg-white dark:bg-gray-800">
							{#each traces as trace}
								<tr class="hover:bg-gray-50 dark:hover:bg-gray-800/50 transition">
									<td class="px-4 py-3 text-gray-700 dark:text-gray-300 whitespace-nowrap">
										{formatDate(trace.timestamp)}
									</td>
									<td class="px-4 py-3 text-gray-700 dark:text-gray-300">
										{#if trace.user}
											<div class="flex items-center gap-2">
												<span class="text-sm">{trace.user.name}</span>
												<span class="text-xs px-1.5 py-0.5 rounded {trace.user.role === 'admin' ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300' : 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300'}">
													{trace.user.role}
												</span>
											</div>
										{:else}
											<span class="font-mono text-xs text-gray-400">
												{trace.user_id ? `${trace.user_id.slice(0, 8)}...` : '-'}
											</span>
										{/if}
									</td>
									<td class="px-4 py-3 text-gray-700 dark:text-gray-300">
										<span class="text-xs font-mono">{trace.model || '-'}</span>
									</td>
									<td class="px-4 py-3 text-gray-700 dark:text-gray-300">
										{#if trace.chapter_id}
											<span class="text-xs px-2 py-1 rounded bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300 font-mono">
												{trace.chapter_id}
											</span>
										{:else}
											<span class="text-gray-400">-</span>
										{/if}
									</td>
									<td class="px-4 py-3 text-gray-700 dark:text-gray-300">
										{formatLatency(trace.latency)}
									</td>
									<td class="px-4 py-3 text-gray-700 dark:text-gray-300">
										{trace.tokens !== undefined ? trace.tokens.toLocaleString() : '-'}
									</td>
									<td class="px-4 py-3 text-gray-700 dark:text-gray-300">
										{#if trace.cost !== undefined && trace.cost > 0}
											<span class="text-green-600 dark:text-green-400 font-medium">
												${trace.cost.toFixed(4)}
											</span>
										{:else}
											<span class="text-gray-400">-</span>
										{/if}
									</td>
									<td class="px-4 py-3 text-gray-700 dark:text-gray-300">
										{#if trace.langfuse_url}
											<a
												href={trace.langfuse_url}
												target="_blank"
												rel="noopener noreferrer"
												class="text-blue-600 dark:text-blue-400 hover:underline text-xs"
											>
												Langfuse →
											</a>
										{:else}
											<span class="text-gray-400">-</span>
										{/if}
									</td>
								</tr>
							{/each}
						</tbody>
					</table>
				</div>

				<!-- Pagination -->
				{#if totalPages > 1}
					<div class="flex items-center justify-between mt-4 px-4">
						<!-- Page Size Selector -->
						<div class="flex items-center gap-2">
							<span class="text-sm text-gray-500 dark:text-gray-400">페이지당:</span>
							<select
								value={pageSize}
								on:change={(e) => changePageSize(Number(e.target.value))}
								disabled={loadingDetails}
								class="px-2 py-1 text-sm bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
							>
								<option value={10}>10</option>
								<option value={20}>20</option>
								<option value={50}>50</option>
							</select>
						</div>

						<!-- Page Navigation -->
						<div class="flex items-center gap-2">
							<!-- Previous Button -->
							<button
								on:click={() => goToPage(currentPage - 1)}
								disabled={currentPage === 1 || loadingDetails}
								class="px-3 py-1.5 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed rounded transition"
							>
								이전
							</button>

							<!-- Page Numbers -->
							{#each getPageNumbers() as page}
								{#if page === '...'}
									<span class="px-2 text-gray-400">...</span>
								{:else}
									<button
										on:click={() => goToPage(page)}
										disabled={loadingDetails}
										class="px-3 py-1.5 text-sm font-medium rounded transition disabled:opacity-50"
										class:bg-blue-600={page === currentPage}
										class:text-white={page === currentPage}
										class:hover:bg-blue-700={page === currentPage}
										class:bg-white={page !== currentPage}
										class:dark:bg-gray-800={page !== currentPage}
										class:text-gray-700={page !== currentPage}
										class:dark:text-gray-300={page !== currentPage}
										class:border={page !== currentPage}
										class:border-gray-300={page !== currentPage}
										class:dark:border-gray-600={page !== currentPage}
										class:hover:bg-gray-50={page !== currentPage}
										class:dark:hover:bg-gray-700={page !== currentPage}
									>
										{page}
									</button>
								{/if}
							{/each}

							<!-- Next Button -->
							<button
								on:click={() => goToPage(currentPage + 1)}
								disabled={currentPage === totalPages || loadingDetails}
								class="px-3 py-1.5 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed rounded transition"
							>
								다음
							</button>
						</div>

						<!-- Page Info -->
						<div class="text-sm text-gray-500 dark:text-gray-400">
							{currentPage} / {totalPages}
						</div>
					</div>
				{/if}
			{/if}
		</div>
	{/if}
</div>
