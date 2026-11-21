<script lang="ts">
	import { getContext } from 'svelte';

	import Select from '$lib/components/common/Select.svelte';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	const i18n = getContext<typeof import('$lib/i18n').default>('i18n');

	export let align = 'center';
	export let className = '';

	export let value = '';
	export let placeholder: string | undefined = undefined;
	export let items: { value: string; label: string }[] | undefined = undefined;
	export let onChange: (value: string) => void = () => {};

	let selectComponent;
	let open = false;
</script>

<Select
	bind:this={selectComponent}
	bind:value
	bind:open
	items={items ?? [
		{ value: 'new', label: $i18n.t('New') },
		{ value: 'top', label: $i18n.t('Top') }
	]}
	placeholder={placeholder ?? $i18n.t('Select an option')}
	{align}
	triggerClass={className
		? className
		: 'flex h-8 shrink-0 items-center gap-1.5 rounded-xl bg-transparent px-1.5 text-[0.8125rem] font-normal text-base-700 transition placeholder-base-400 outline-hidden hover:text-base-900 focus:outline-hidden dark:text-base-200 dark:hover:text-base-100'}
	itemClass="flex h-[1.6875rem] w-full cursor-pointer items-center gap-2 rounded-xl bg-transparent px-2 text-[0.8125rem] hover:bg-base-50/40 hover:text-base-900 dark:hover:bg-base-800/40 dark:hover:text-base-100"
	onChange={(v) => {
		onChange(v);
	}}
>
	<svelte:fragment slot="trigger" let:selectedLabel>
		<span class="min-w-0 truncate">{selectedLabel}</span>
		<ChevronDown className=" size-3" strokeWidth="2.5" />
	</svelte:fragment>

	<svelte:fragment slot="item" let:item let:selected>
		<span class={`min-w-0 truncate ${selected ? '' : 'text-base-500 dark:text-base-400'}`}
			>{item.label}</span
		>
	</svelte:fragment>
</Select>
