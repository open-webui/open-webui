<script lang="ts">
	import { Select } from 'bits-ui';
	import { getContext } from 'svelte';

	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import Check from '$lib/components/icons/Check.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';

	const i18n = getContext('i18n');

	export let value = '';
	export let placeholder = $i18n.t('Tag');
	export let onChange: (value: string) => void = () => {};

	export let items = [];
</script>

<Select.Root
	selected={value ? items.find((item) => item.value === value) : null}
	{items}
	onSelectedChange={(selectedItem) => {
		value = selectedItem.value;
		onChange(value);
	}}
>
	<Select.Trigger
		class="relative w-full flex items-center gap-0.5 px-2.5 py-1.5 rounded-xl "
		aria-label={placeholder}
	>
		<Select.Value
			class="inline-flex h-input px-0.5 w-full outline-hidden bg-transparent truncate  placeholder-gray-400  focus:outline-hidden capitalize"
			{placeholder}
		/>

		{#if value}
			<button
				class="outline-none"
				on:click={() => {
					value = '';
					onChange(value);
				}}
			>
				<XMark className="size-3.5" />
			</button>
		{:else}
			<ChevronDown className=" size-3.5" strokeWidth="2.5" />
		{/if}
	</Select.Trigger>

	<Select.Content
		class="rounded-2xl min-w-[170px] p-1 border border-gray-100  dark:border-gray-800 z-50 bg-white dark:bg-gray-850 dark:text-white shadow-lg"
		sameWidth={false}
		align="start"
	>
		<slot>
			{#each items as item}
				<Select.Item
					class="flex  gap-2  items-center px-3 py-1.5 text-sm  cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl capitalize"
					value={item.value}
					label={item.label}
				>
					{item.label.length > 32 ? `${item.label.slice(0, 32)}...` : item.label}

					{#if value === item.value}
						<div class="ml-auto">
							<Check />
						</div>
					{/if}
				</Select.Item>
			{/each}
		</slot>
	</Select.Content>
</Select.Root>

<!-- <button
	class="min-w-fit outline-none p-1.5 {selectedTag === ''
		? ''
		: 'text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'} transition capitalize"
	on:click={() => {
		selectedTag = '';
	}}
>
	{$i18n.t('All')}
</button>

<button
	class="min-w-fit outline-none p-1.5 {selectedTag === ''
		? ''
		: 'text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'} transition capitalize"
	on:click={() => {
		selectedTag = '';
	}}
>
	{$i18n.t('Created by you')}
</button>

<button
	class="min-w-fit outline-none p-1.5 {selectedTag === ''
		? ''
		: 'text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'} transition capitalize"
	on:click={() => {
		selectedTag = '';
	}}
>
	{$i18n.t('Shared with you')}
</button> -->
