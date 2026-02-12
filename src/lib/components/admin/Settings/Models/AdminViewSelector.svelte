<script lang="ts">
	import { Select } from 'bits-ui';
	import { getContext } from 'svelte';

	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import Check from '$lib/components/icons/Check.svelte';

	const i18n = getContext('i18n');

	export let value = '';
	export let placeholder = $i18n.t('Select view');
	export let onChange: (value: string) => void = () => {};

	const items = [
		{ value: '', label: $i18n.t('All') },
		{ value: 'enabled', label: $i18n.t('Enabled') },
		{ value: 'disabled', label: $i18n.t('Disabled') },
		{ value: 'visible', label: $i18n.t('Visible') },
		{ value: 'hidden', label: $i18n.t('Hidden') }
	];
</script>

<Select.Root
	selected={items.find((item) => item.value === value)}
	{items}
	onSelectedChange={(selectedItem) => {
		value = selectedItem.value;
		onChange(value);
	}}
>
	<Select.Trigger
		class="relative w-full flex items-center gap-0.5 px-2.5 py-1.5 bg-gray-50 dark:bg-gray-850 rounded-xl"
		aria-label={placeholder}
	>
		<Select.Value
			class="inline-flex h-input px-0.5 w-full outline-hidden bg-transparent truncate placeholder-gray-400 focus:outline-hidden"
			{placeholder}
		/>
		<ChevronDown className="size-3.5" strokeWidth="2.5" />
	</Select.Trigger>

	<Select.Content
		class="rounded-2xl min-w-[170px] p-1 border border-gray-100 dark:border-gray-800 z-50 bg-white dark:bg-gray-850 dark:text-white shadow-lg"
		sameWidth={false}
		align="start"
	>
		{#each items as item}
			<Select.Item
				class="flex gap-2 items-center px-3 py-1.5 text-sm cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl"
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
		{/each}
	</Select.Content>
</Select.Root>
