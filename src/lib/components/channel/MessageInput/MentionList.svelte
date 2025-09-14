<script lang="ts">
	import { getContext } from 'svelte';
	const i18n = getContext('i18n');

	import { models } from '$lib/stores';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	export let query = '';

	export let command: (payload: { id: string; label: string }) => void;
	export let selectedIndex = 0;

	let items = [];

	$: filteredItems = $models.filter((u) => u.name.toLowerCase().includes(query.toLowerCase()));

	const select = (index: number) => {
		const item = filteredItems[index];
		if (item) command({ id: item.id, label: item.name });
	};

	const onKeyDown = (event: KeyboardEvent) => {
		if (!['ArrowUp', 'ArrowDown', 'Enter', 'Tab', 'Escape'].includes(event.key)) return false;

		if (event.key === 'ArrowUp') {
			selectedIndex = (selectedIndex + filteredItems.length - 1) % filteredItems.length;
			const item = document.querySelector(`[data-selected="true"]`);
			item?.scrollIntoView({ block: 'center', inline: 'nearest', behavior: 'instant' });
			return true;
		}
		if (event.key === 'ArrowDown') {
			selectedIndex = (selectedIndex + 1) % filteredItems.length;
			const item = document.querySelector(`[data-selected="true"]`);
			item?.scrollIntoView({ block: 'center', inline: 'nearest', behavior: 'instant' });
			return true;
		}
		if (event.key === 'Enter' || event.key === 'Tab') {
			select(selectedIndex);
			return true;
		}
		if (event.key === 'Escape') {
			// tell tiptap we handled it (it will close)
			return true;
		}
		return false;
	};

	// This method will be called from the suggestion renderer
	// @ts-ignore
	export function _onKeyDown(event: KeyboardEvent) {
		return onKeyDown(event);
	}
</script>

{#if filteredItems.length}
	<div
		class="mention-list text-black dark:text-white rounded-2xl shadow-lg border border-gray-200 dark:border-gray-800 flex flex-col bg-white dark:bg-gray-850 w-60 p-1"
		id="suggestions-container"
	>
		<div class="overflow-y-auto scrollbar-thin max-h-60">
			<div class="px-2 text-xs text-gray-500 py-1">
				{$i18n.t('Models')}
			</div>
			{#each filteredItems as item, i}
				<Tooltip content={item?.id} placement="top-start">
					<button
						type="button"
						on:click={() => select(i)}
						on:mousemove={() => {
							selectedIndex = i;
						}}
						class="px-2.5 py-1.5 rounded-xl w-full text-left {i === selectedIndex
							? 'bg-gray-50 dark:bg-gray-800 selected-command-option-button'
							: ''}"
						data-selected={i === selectedIndex}
					>
						<div class="truncate">
							@{item.name}
						</div>
					</button>
				</Tooltip>
			{/each}
		</div>
	</div>
{/if}
