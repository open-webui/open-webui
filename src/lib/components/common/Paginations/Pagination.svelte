<script lang="ts">
	import type { DataHandler } from '@vincjo/datatables';
	export let dataHandler: DataHandler;
	const pageNumber = dataHandler.getPageNumber();
	const pageCount = dataHandler.getPageCount();
	const pages = dataHandler.getPages({ ellipsis: true });
</script>

<div class=" flex">
	<button
		type="button"
		class:disabled={$pageNumber === 1}
		on:click={() => dataHandler.setPage('previous')}
	>
		Previous
	</button>
	{#each $pages as page}
		<button
			type="button"
			class:active={$pageNumber === page}
			class:ellipse={page === null}
			on:click={() => dataHandler.setPage(page)}
		>
			{page ?? '...'}
		</button>
	{/each}
	<button
		type="button"
		class:disabled={$pageNumber === $pageCount}
		on:click={() => dataHandler.setPage('next')}
	>
		Next
	</button>
</div>

<style>
	button {
		background: inherit;
		height: 32px;
		width: 32px;
		color: #616161;
		cursor: pointer;
		font-size: 13px;
		margin: 0;
		padding: 0;
		transition: all, 0.2s;
		line-height: 32px;
		border: 1px solid #e0e0e0;
		border-right: none;
		outline: none;
	}
	button:first-child {
		border-radius: 4px 0 0 4px;
		width: auto;
		min-width: 72px;
	}
	button:last-child {
		border-right: 1px solid #e0e0e0;
		border-radius: 0 4px 4px 0;
		width: auto;
		min-width: 72px;
	}
	button:not(.active):hover {
		background: #eee;
	}
	button.ellipse:hover {
		background: inherit;
		cursor: default;
	}
	button.active {
		background: #eee;
		font-weight: bold;
		cursor: default;
	}
	button.disabled:hover {
		background: inherit;
		cursor: default;
	}
</style>
