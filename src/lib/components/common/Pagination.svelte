<script lang="ts">
	import { Pagination } from 'bits-ui';
	import { createEventDispatcher } from 'svelte';

	import ChevronLeft from '../icons/ChevronLeft.svelte';
	import ChevronRight from '../icons/ChevronRight.svelte';

	interface Props {
		page?: number;
		count?: number;
		perPage?: number;
	}

	let { page = $bindable(0), count = 0, perPage = 20 }: Props = $props();
</script>

<div class="flex justify-center">
	<Pagination.Root bind:page {count} {perPage} >
		{#snippet children({ pages })}
				<div class="my-2 flex items-center">
				<Pagination.PrevButton
					class="mr-[25px] inline-flex size-8 items-center justify-center rounded-[9px] bg-transparent hover:bg-gray-50 dark:hover:bg-gray-850 active:scale-98 disabled:cursor-not-allowed disabled:text-gray-400 dark:disabled:text-gray-700 hover:disabled:bg-transparent dark:hover:disabled:bg-transparent"
				>
					<ChevronLeft className="size-4" strokeWidth="2" />
				</Pagination.PrevButton>
				<div class="flex items-center gap-2.5">
					{#each pages as page (page.key)}
						{#if page.type === 'ellipsis'}
							<div class="text-sm font-medium text-foreground-alt">...</div>
						{:else}
							<Pagination.Page
								{page}
								class="inline-flex size-8 items-center justify-center rounded-[9px] bg-transparent hover:bg-gray-50 dark:hover:bg-gray-850 text-sm font-medium hover:bg-dark-10 active:scale-98 disabled:cursor-not-allowed disabled:opacity-50 hover:disabled:bg-transparent data-selected:bg-gray-50 data-selected:text-gray-700 data-selected:hover:bg-gray-100 dark:data-selected:bg-gray-850 dark:data-selected:text-gray-50 dark:data-selected:hover:bg-gray-800 transition"
							>
								{page.value}
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
					{/snippet}
		</Pagination.Root>
</div>
