<script lang="ts">
	import { createEventDispatcher, getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';

	const i18n: Writable<i18nType> = getContext('i18n');
	const dispatch = createEventDispatcher();

	interface KnowledgeGroup {
		id: string;
		name: string;
		itemCount: number;
	}

	export let selectedGroups: string[] = [];
	export let availableGroups: KnowledgeGroup[] = [];
	export let itemsPerPage: number = 5;

	let currentPage = 0;

	// Reset page when groups change
	$: if (availableGroups) {
		currentPage = 0;
	}

	$: totalPages = Math.ceil(availableGroups.length / itemsPerPage);
	$: paginatedGroups = availableGroups.slice(
		currentPage * itemsPerPage,
		(currentPage + 1) * itemsPerPage
	);

	// Generate visible page numbers with ellipsis
	$: visiblePages = getVisiblePages(currentPage, totalPages);

	function getVisiblePages(current: number, total: number): (number | 'ellipsis')[] {
		if (total <= 7) {
			return Array.from({ length: total }, (_, i) => i);
		}

		const pages: (number | 'ellipsis')[] = [];

		// Always show first page
		pages.push(0);

		if (current <= 2) {
			// Near start: 1 2 3 4 ... last
			pages.push(1, 2, 3, 'ellipsis', total - 1);
		} else if (current >= total - 3) {
			// Near end: 1 ... n-3 n-2 n-1 last
			pages.push('ellipsis', total - 4, total - 3, total - 2, total - 1);
		} else {
			// Middle: 1 ... current-1 current current+1 ... last
			pages.push('ellipsis', current - 1, current, current + 1, 'ellipsis', total - 1);
		}

		return pages;
	}

	const toggleGroup = (groupId: string) => {
		if (selectedGroups.includes(groupId)) {
			selectedGroups = selectedGroups.filter((id) => id !== groupId);
		} else {
			selectedGroups = [...selectedGroups, groupId];
		}
		dispatch('change', selectedGroups);
	};

	const goToPage = (page: number) => {
		if (page >= 0 && page < totalPages) {
			currentPage = page;
		}
	};

	const prevPage = () => {
		if (currentPage > 0) {
			currentPage--;
		}
	};

	const nextPage = () => {
		if (currentPage < totalPages - 1) {
			currentPage++;
		}
	};
</script>

<div class="border border-gray-200 dark:border-gray-700 rounded-xl overflow-hidden">
	{#if availableGroups.length === 0}
		<div class="px-4 py-3 text-sm text-gray-500 text-center">
			{$i18n.t('사용 가능한 지식 그룹이 없습니다')}
		</div>
	{:else}
		<!-- Group List -->
		<div>
			{#each paginatedGroups as group (group.id)}
				{@const isChecked = selectedGroups.includes(group.id)}
				<button
					type="button"
					class="w-full flex items-center gap-3 px-4 py-2.5 hover:bg-gray-50 dark:hover:bg-gray-800 transition border-b border-gray-100 dark:border-gray-800 last:border-b-0"
					on:click={() => toggleGroup(group.id)}
				>
					<!-- Checkbox -->
					<div
						class="size-5 shrink-0 rounded-md border-2 flex items-center justify-center transition {isChecked
							? 'bg-primary-500 border-primary-500'
							: 'border-gray-300 dark:border-gray-600'}"
					>
						{#if isChecked}
							<svg class="size-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="3"
									d="M5 13l4 4L19 7"
								/>
							</svg>
						{/if}
					</div>

					<!-- Group Info -->
					<div class="flex-1 text-left min-w-0">
						<div class="text-sm font-medium text-gray-900 dark:text-white truncate">
							{group.name}
						</div>
						<div class="text-xs text-gray-500">
							{group.itemCount} items
						</div>
					</div>
				</button>
			{/each}
		</div>

		<!-- Pagination Controls -->
		{#if totalPages > 1}
			<div
				class="flex items-center justify-center gap-1 px-3 py-2 bg-gray-50 dark:bg-gray-850 border-t border-gray-200 dark:border-gray-700"
			>
				<!-- Previous Button -->
				<button
					type="button"
					class="p-1.5 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-700 transition disabled:opacity-30 disabled:cursor-not-allowed text-gray-600 dark:text-gray-400"
					disabled={currentPage === 0}
					on:click={prevPage}
				>
					<svg class="size-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
						<path stroke-linecap="round" stroke-linejoin="round" d="M15 19l-7-7 7-7" />
					</svg>
				</button>

				<!-- Page Numbers -->
				<div class="flex items-center gap-0.5">
					{#each visiblePages as page}
						{#if page === 'ellipsis'}
							<span class="px-2 text-xs text-gray-400">...</span>
						{:else}
							<button
								type="button"
								class="min-w-[28px] h-7 px-1.5 text-xs font-medium rounded-lg transition {currentPage ===
								page
									? 'text-primary-600 dark:text-primary-400 bg-primary-50 dark:bg-primary-500/10 border-b-2 border-primary-500'
									: 'text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700'}"
								on:click={() => goToPage(page)}
							>
								{page + 1}
							</button>
						{/if}
					{/each}
				</div>

				<!-- Next Button -->
				<button
					type="button"
					class="p-1.5 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-700 transition disabled:opacity-30 disabled:cursor-not-allowed text-gray-600 dark:text-gray-400"
					disabled={currentPage >= totalPages - 1}
					on:click={nextPage}
				>
					<svg class="size-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
						<path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7" />
					</svg>
				</button>
			</div>
		{/if}
	{/if}

	<!-- Selection Count -->
	{#if selectedGroups.length > 0}
		<div
			class="px-4 py-2 bg-primary-50 dark:bg-primary-500/10 border-t border-gray-200 dark:border-gray-700"
		>
			<div class="text-xs text-primary-600 dark:text-primary-400 font-medium">
				{selectedGroups.length}{$i18n.t('개 선택됨')}
			</div>
		</div>
	{/if}
</div>
