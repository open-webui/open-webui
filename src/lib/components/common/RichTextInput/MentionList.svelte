<script lang="ts">
	export let query = '';

	export let command: (payload: { id: string; label: string }) => void;
	export let selectedIndex = 0;

	let ITEMS = [
		{ id: '1', label: 'alice' },
		{ id: '2', label: 'alex' },
		{ id: '3', label: 'bob' },
		{ id: '4', label: 'charlie' },
		{ id: '5', label: 'diana' },
		{ id: '6', label: 'eve' },
		{ id: '7', label: 'frank' },
		{ id: '8', label: 'grace' },
		{ id: '9', label: 'heidi' },
		{ id: '10', label: 'ivan' },
		{ id: '11', label: 'judy' },
		{ id: '12', label: 'mallory' },
		{ id: '13', label: 'oscar' },
		{ id: '14', label: 'peggy' },
		{ id: '15', label: 'trent' },
		{ id: '16', label: 'victor' },
		{ id: '17', label: 'walter' }
	];

	let items = ITEMS;

	$: items = ITEMS.filter((u) => u.label.toLowerCase().includes(query.toLowerCase())).slice(0, 5);

	const select = (index: number) => {
		const item = items[index];
		if (item) command(item);
	};

	const onKeyDown = (event: KeyboardEvent) => {
		if (!['ArrowUp', 'ArrowDown', 'Enter', 'Tab', 'Escape'].includes(event.key)) return false;

		if (event.key === 'ArrowUp') {
			selectedIndex = (selectedIndex + items.length - 1) % items.length;
			return true;
		}
		if (event.key === 'ArrowDown') {
			selectedIndex = (selectedIndex + 1) % items.length;
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

<div
	class="mention-list text-black dark:text-white rounded-2xl shadow-lg border border-gray-200 dark:border-gray-800 flex flex-col bg-white dark:bg-gray-850 overflow-y-auto scrollbar-thin max-h-60 w-52"
	id="suggestions-container"
>
	{#if items.length === 0}
		<div class=" p-4 text-gray-400">No results</div>
	{:else}
		{#each items as item, i}
			<button
				type="button"
				on:click={() => select(i)}
				class=" text-left w-full hover:bg-gray-50 dark:hover:bg-gray-800 transition px-3 py-1 {i ===
				selectedIndex
					? 'bg-gray-50 dark:bg-gray-800 font-medium'
					: ''}"
			>
				@{item.label}
			</button>
		{/each}
	{/if}
</div>
