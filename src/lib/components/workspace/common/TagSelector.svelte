<script lang="ts">
	import { getContext } from 'svelte';

	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import Check from '$lib/components/icons/Check.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import Select from '$lib/components/common/Select.svelte';

	const i18n = getContext('i18n');

	export let value = '';
	export let placeholder = $i18n.t('Tag');
	export let onChange: (value: string) => void = () => {};

	export let items = [];
</script>

<Select
	bind:value
	{items}
	{placeholder}
	triggerClass="relative w-full flex items-center gap-0.5 px-2.5 py-1.5 rounded-xl "
	itemClass="flex w-full gap-2 items-center px-3 py-1.5 text-sm cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl capitalize"
	onChange={() => onChange(value)}
>
	<svelte:fragment slot="trigger" let:selectedLabel>
		<div
			class="inline-flex h-input px-0.5 w-full outline-hidden bg-transparent truncate placeholder-gray-400 focus:outline-hidden capitalize"
		>
			{#if value}
				{value}
			{:else}
				{placeholder}
			{/if}
		</div>

		{#if value}
			<button
				class="outline-none"
				type="button"
				on:click|stopPropagation={() => {
					value = '';
					onChange(value);
				}}
			>
				<XMark className="size-3.5" />
			</button>
		{:else}
			<ChevronDown className=" size-3.5" strokeWidth="2.5" />
		{/if}
	</svelte:fragment>

	<svelte:fragment slot="item" let:item let:selected>
		{item.label.length > 32 ? `${item.label.slice(0, 32)}...` : item.label}
		<div class="ml-auto {selected ? '' : 'invisible'}">
			<Check />
		</div>
	</svelte:fragment>
</Select>

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
