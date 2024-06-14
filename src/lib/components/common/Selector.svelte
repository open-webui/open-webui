<script lang="ts">
	import { Select } from 'bits-ui';

	import { flyAndScale } from '$lib/utils/transitions';

	import { createEventDispatcher } from 'svelte';
	import ChevronDown from '../icons/ChevronDown.svelte';
	import Check from '../icons/Check.svelte';
	import Search from '../icons/Search.svelte';

	const dispatch = createEventDispatcher();

	export let value = '';
	export let placeholder = 'Select a model';
	export let searchEnabled = true;
	export let searchPlaceholder = 'Search a model';

	export let items = [
		{ value: 'mango', label: 'Mango' },
		{ value: 'watermelon', label: 'Watermelon' },
		{ value: 'apple', label: 'Apple' },
		{ value: 'pineapple', label: 'Pineapple' },
		{ value: 'orange', label: 'Orange' }
	];

	let searchValue = '';

	$: filteredItems = searchValue
		? items.filter((item) => item.value.toLowerCase().includes(searchValue.toLowerCase()))
		: items;
</script>

<Select.Root
	{items}
	onOpenChange={() => {
		searchValue = '';
	}}
	selected={items.find((item) => item.value === value)}
	onSelectedChange={(selectedItem) => {
		value = selectedItem.value;
	}}
>
	<Select.Trigger class="relative w-full" aria-label={placeholder}>
		<Select.Value
			class="inline-flex h-input px-0.5 w-full outline-none bg-transparent truncate text-lg font-semibold placeholder-gray-400  focus:outline-none"
			{placeholder}
		/>
		<ChevronDown className="absolute end-2 top-1/2 -translate-y-[45%] size-3.5" strokeWidth="2.5" />
	</Select.Trigger>
	<Select.Content
		class="w-full rounded-lg  bg-white dark:bg-gray-900 dark:text-white shadow-lg border border-gray-300/30 dark:border-gray-850/50  outline-none"
		transition={flyAndScale}
		sideOffset={4}
	>
		<slot>
			{#if searchEnabled}
				<div class="flex items-center gap-2.5 px-5 mt-3.5 mb-3">
					<Search className="size-4" strokeWidth="2.5" />

					<input
						bind:value={searchValue}
						class="w-full text-sm bg-transparent outline-none"
						placeholder={searchPlaceholder}
					/>
				</div>

				<hr class="border-gray-100 dark:border-gray-800" />
			{/if}

			<div class="px-3 my-2 max-h-80 overflow-y-auto">
				{#each filteredItems as item}
					<Select.Item
						class="flex w-full font-medium line-clamp-1 select-none items-center rounded-button py-2 pl-3 pr-1.5 text-sm  text-gray-700 dark:text-gray-100  outline-none transition-all duration-75 hover:bg-gray-100 dark:hover:bg-gray-850 rounded-lg cursor-pointer data-[highlighted]:bg-muted"
						value={item.value}
						label={item.label}
					>
						{item.label}

						{#if value === item.value}
							<div class="ml-auto">
								<Check />
							</div>
						{/if}
					</Select.Item>
				{:else}
					<div>
						<div class="block px-5 py-2 text-sm text-gray-700 dark:text-gray-100">
							No results found
						</div>
					</div>
				{/each}
			</div>
		</slot>
	</Select.Content>
</Select.Root>
