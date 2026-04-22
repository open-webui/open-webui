<script lang="ts">
	import ChevronDown from '../icons/ChevronDown.svelte';
	import Check from '../icons/Check.svelte';
	import Search from '../icons/Search.svelte';
	import Select from './Select.svelte';

	export let value = '';
	export let placeholder = $i18n.t('Select a model');
	export let searchEnabled = true;
	export let searchPlaceholder = $i18n.t('Search a model');

	export let items = [
		{ value: 'mango', label: 'Mango' },
		{ value: 'watermelon', label: 'Watermelon' },
		{ value: 'apple', label: 'Apple' },
		{ value: 'pineapple', label: 'Pineapple' },
		{ value: 'orange', label: 'Orange' }
	];

	let searchValue = '';
	let selectRef;

	$: filteredItems = searchValue
		? items.filter((item) => item.value.toLowerCase().includes(searchValue.toLowerCase()))
		: items;
</script>

<Select
	bind:value
	bind:this={selectRef}
	{items}
	{placeholder}
	triggerClass="relative w-full"
	contentClass="w-full rounded-lg bg-white dark:bg-gray-900 dark:text-white shadow-lg border border-gray-300/30 dark:border-gray-700/40 outline-hidden"
	onClose={() => {
		searchValue = '';
	}}
>
	<svelte:fragment slot="trigger" let:selectedLabel>
		<span
			class="inline-flex h-input px-0.5 w-full outline-hidden bg-transparent truncate text-lg font-semibold placeholder-gray-400 focus:outline-hidden"
		>
			{selectedLabel}
		</span>
		<ChevronDown className="absolute end-2 top-1/2 -translate-y-[45%] size-3.5" strokeWidth="2.5" />
	</svelte:fragment>

	<svelte:fragment let:selectItem>
		<slot>
			{#if searchEnabled}
				<div class="flex items-center gap-2.5 px-5 mt-3.5 mb-3">
					<Search className="size-4" strokeWidth="2.5" />

					<input
						bind:value={searchValue}
						class="w-full text-sm bg-transparent outline-hidden"
						placeholder={searchPlaceholder}
						on:click|stopPropagation
					/>
				</div>

				<hr class="border-gray-100/30 dark:border-gray-850/30" />
			{/if}

			<div class="px-3 my-2 max-h-80 overflow-y-auto">
				{#each filteredItems as item}
					<button
						class="flex w-full font-medium line-clamp-1 select-none items-center rounded-button py-2 pl-3 pr-1.5 text-sm text-gray-700 dark:text-gray-100 outline-hidden transition-all duration-75 hover:bg-gray-100 dark:hover:bg-gray-850 rounded-lg cursor-pointer"
						type="button"
						on:click={() => selectItem(item)}
					>
						{item.label}

						{#if value === item.value}
							<div class="ml-auto">
								<Check />
							</div>
						{/if}
					</button>
				{:else}
					<div>
						<div class="block px-5 py-2 text-sm text-gray-700 dark:text-gray-100">
							{$i18n.t('No results found')}
						</div>
					</div>
				{/each}
			</div>
		</slot>
	</svelte:fragment>
</Select>
