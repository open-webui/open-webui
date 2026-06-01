<script lang="ts">
	import { getContext } from 'svelte';

	import Select from '$lib/components/common/Select.svelte';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	const i18n = getContext('i18n');

	export let align = 'center';
	export let className = '';

	export let value = '';
	export let placeholder = 'Select an option';
	export let items = [
		{ value: 'new', label: $i18n.t('New') },
		{ value: 'top', label: $i18n.t('Top') }
	];

	export let onChange: (value: string) => void = () => {};

	let selectComponent;
	let open = false;
</script>

<Select
	bind:this={selectComponent}
	bind:value
	bind:open
	{items}
	{placeholder}
	{align}
	triggerClass={className
		? className
		: 'flex shrink-0 items-center gap-2 bg-transparent px-0.5 text-sm placeholder-gray-400 outline-hidden focus:outline-hidden'}
	itemClass="flex w-full gap-2 items-center px-3 py-1.5 text-sm cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl"
	onChange={(v) => {
		onChange(v);
	}}
>
	<svelte:fragment slot="trigger" let:selectedLabel>
		{selectedLabel}
		<ChevronDown className=" size-3" strokeWidth="2.5" />
	</svelte:fragment>

	<svelte:fragment slot="item" let:item let:selected>
		<span class={selected ? '' : 'text-gray-500 dark:text-gray-400'}>{item.label}</span>
	</svelte:fragment>
</Select>
