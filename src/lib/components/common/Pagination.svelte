<script lang="ts">
	import { Pagination } from 'bits-ui';
	import { createEventDispatcher, getContext } from 'svelte';

	import ChevronLeft from '../icons/ChevronLeft.svelte';
	import ChevronRight from '../icons/ChevronRight.svelte';

	export let page = 0;
	export let count = 0;
	export let perPage = 20;

	const i18n = getContext('i18n');
</script>

<div class="flex justify-center">
	<Pagination.Root bind:page {count} {perPage}>
		{#snippet children({ pages, currentPage })}
			<div class="my-2 flex items-center">
				<Pagination.PrevButton
					aria-label={$i18n.t('Previous page')}
					class="mr-[1.5625rem] inline-flex size-8 items-center justify-center rounded-[0.5625rem] bg-transparent hover:bg-gray-50 dark:hover:bg-gray-850 active:scale-98 disabled:cursor-not-allowed disabled:text-gray-400 dark:disabled:text-gray-700 hover:disabled:bg-transparent dark:hover:disabled:bg-transparent"
				>
					<ChevronLeft className="size-4" strokeWidth="2" />
				</Pagination.PrevButton>
				<div class="flex items-center gap-2.5">
					{#each pages as page (page.key)}
						{#if page.type === 'ellipsis'}
							<div class="text-sm font-normal text-foreground-alt">...</div>
						{:else}
							<Pagination.Page
								{page}
								aria-current={page.value === currentPage ? 'page' : undefined}
								class="inline-flex size-8 items-center justify-center rounded-[0.5625rem] bg-transparent hover:bg-gray-50 dark:hover:bg-gray-850 text-sm font-normal hover:bg-dark-10 active:scale-98 disabled:cursor-not-allowed disabled:opacity-50 hover:disabled:bg-transparent data-selected:bg-gray-50 data-selected:text-gray-700 data-selected:hover:bg-gray-100 dark:data-selected:bg-gray-850 dark:data-selected:text-gray-50 dark:data-selected:hover:bg-gray-800 transition"
							>
								{page.value}
							</Pagination.Page>
						{/if}
					{/each}
				</div>
				<Pagination.NextButton
					aria-label={$i18n.t('Next page')}
					class="ml-[1.5625rem]  inline-flex size-8 items-center justify-center rounded-[0.5625rem] bg-transparent hover:bg-gray-50 dark:hover:bg-gray-850 active:scale-98 disabled:cursor-not-allowed disabled:text-gray-400 dark:disabled:text-gray-700 hover:disabled:bg-transparent dark:hover:disabled:bg-transparent"
				>
					<ChevronRight className="size-4" strokeWidth="2" />
				</Pagination.NextButton>
			</div>
		{/snippet}
	</Pagination.Root>
</div>
