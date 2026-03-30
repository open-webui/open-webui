<script lang="ts">
	import { getContext } from 'svelte';

	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import Check from '$lib/components/icons/Check.svelte';
	import Select from '$lib/components/common/Select.svelte';

	const i18n = getContext('i18n');

	export let value = '';
	export let placeholder = $i18n.t('Select view');
	export let onChange: (value: string) => void = () => {};

	const items = [
		{ value: '', label: $i18n.t('All') },
		{ value: 'created', label: $i18n.t('Created by you') },
		{ value: 'shared', label: $i18n.t('Shared with you') }
	];
</script>

<Select
	bind:value
	{items}
	{placeholder}
	triggerClass="relative w-full flex items-center gap-0.5 px-2.5 py-1.5 bg-gray-50 dark:bg-gray-850 rounded-xl "
	labelClass="inline-flex h-input px-0.5 w-full outline-hidden bg-transparent truncate  placeholder-gray-400  focus:outline-hidden"
	onChange={() => onChange(value)}
>
	<svelte:fragment slot="trigger" let:selectedLabel>
		<span
			class="inline-flex h-input px-0.5 w-full outline-hidden bg-transparent truncate placeholder-gray-400 focus:outline-hidden"
		>
			{selectedLabel}
		</span>
		<ChevronDown className=" size-3.5" strokeWidth="2.5" />
	</svelte:fragment>

	<svelte:fragment slot="item" let:item let:selected>
		{item.label}
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
