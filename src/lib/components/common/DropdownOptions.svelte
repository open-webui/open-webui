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
		: 'flex h-8 shrink-0 items-center gap-1.5 rounded-xl bg-transparent px-1.5 text-[13px] font-normal text-gray-700 transition placeholder-gray-400 outline-hidden hover:text-gray-900 focus:outline-hidden dark:text-gray-200 dark:hover:text-gray-100'}
	itemClass="flex h-[1.6875rem] w-full cursor-pointer items-center gap-2 rounded-xl bg-transparent px-2 text-[13px] hover:bg-gray-50/40 hover:text-gray-900 dark:hover:bg-gray-800/40 dark:hover:text-gray-100"
	onChange={(v) => {
		onChange(v);
	}}
>
	<svelte:fragment slot="trigger" let:selectedLabel>
		<span class="min-w-0 truncate">{selectedLabel}</span>
		<ChevronDown className=" size-3" strokeWidth="2.5" />
	</svelte:fragment>

	<svelte:fragment slot="item" let:item let:selected>
		<span class={`min-w-0 truncate ${selected ? '' : 'text-gray-500 dark:text-gray-400'}`}
			>{item.label}</span
		>
	</svelte:fragment>
</Select>
