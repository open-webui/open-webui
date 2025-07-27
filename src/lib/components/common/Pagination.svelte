<script lang="ts">
	import { Pagination } from 'bits-ui';
	import { createEventDispatcher } from 'svelte';

	import ChevronLeft from '../icons/ChevronLeft.svelte';
	import ChevronRight from '../icons/ChevronRight.svelte';

	export let page = 0;
	export let count = 0;
	export let perPage = 20;

	$: totalPages = Math.ceil(count / perPage);

	function getDisplayPages(currentPage: number, total: number) {
		const pagesToDisplay = [];
		if (total <= 3) {
			for (let i = 1; i <= total; i++) {
				pagesToDisplay.push({ type: 'page', value: i, key: i });
			}
		} else {
			if (currentPage === 1) {
				pagesToDisplay.push(
					{ type: 'page', value: 1, key: 1 },
					{ type: 'page', value: 2, key: 2 },
					{ type: 'page', value: 3, key: 3 }
				);
			} else if (currentPage === total) {
				pagesToDisplay.push(
					{ type: 'page', value: total - 2, key: total - 2 },
					{ type: 'page', value: total - 1, key: total - 1 },
					{ type: 'page', value: total, key: total }
				);
			} else {
				pagesToDisplay.push(
					{ type: 'page', value: currentPage - 1, key: currentPage - 1 },
					{ type: 'page', value: currentPage, key: currentPage },
					{ type: 'page', value: currentPage + 1, key: currentPage + 1 }
				);
			}
		}
		return pagesToDisplay;
	}

	$: displayPages = getDisplayPages(page, totalPages);
</script>

<style>
	.selected-page-button {
		transform: scale(1.25);
		font-weight: bold;
		transition: transform 0.2s ease-out;
		z-index: 10;
		position: relative;
	}
</style>

<div class="flex justify-center">
	<Pagination.Root bind:page {count} {perPage} let:pages>
		<div class="my-2 flex items-center">
			<Pagination.PrevButton
				class="mr-[25px] inline-flex size-8 items-center justify-center rounded-[9px] bg-transparent hover:bg-gray-50 dark:hover:bg-gray-850 active:scale-98 disabled:cursor-not-allowed disabled:text-gray-400 dark:disabled:text-gray-700 hover:disabled:bg-transparent dark:hover:disabled:bg-transparent"
			>
				<ChevronLeft className="size-4" strokeWidth="2" />
			</Pagination.PrevButton>
			<div class="flex items-center gap-2.5">
				{#each displayPages as p (p.key)}
					{#if p.type === 'ellipsis'}
						<div class="text-sm font-medium text-foreground-alt">...</div>
					{:else}
						<Pagination.Page
							page={p}
							class="inline-flex size-8 items-center justify-center rounded-[9px] bg-transparent hover:bg-gray-50 dark:hover:bg-gray-850 text-sm font-medium hover:bg-dark-10 active:scale-98 disabled:cursor-not-allowed disabled:opacity-50 hover:disabled:bg-transparent data-selected:bg-gray-50 data-selected:text-gray-700 data-selected:hover:bg-gray-100 dark:data-selected:bg-gray-850 dark:data-selected:text-gray-50 dark:data-selected:hover:bg-gray-800 transition {p.value === page ? 'selected-page-button' : ''}"
						>
							{p.value}
						</Pagination.Page>
					{/if}
				{/each}
			</div>
			<Pagination.NextButton
				class="ml-[25px]  inline-flex size-8 items-center justify-center rounded-[9px] bg-transparent hover:bg-gray-50 dark:hover:bg-gray-850 active:scale-98 disabled:cursor-not-allowed disabled:text-gray-400 dark:disabled:text-gray-700 hover:disabled:bg-transparent dark:hover:disabled:bg-transparent"
			>
				<ChevronRight className="size-4" strokeWidth="2" />
			</Pagination.NextButton>
		</div>
	</Pagination.Root>
</div>