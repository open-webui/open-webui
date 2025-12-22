<script lang="ts">
	import { Select } from 'bits-ui';
	import { getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import Check from '$lib/components/icons/Check.svelte';

	const i18n: Writable<i18nType> = getContext('i18n');

	export let value: string = 'name-asc';

	const items = [
		{ value: 'name-asc', label: $i18n.t('이름 (A-Z)') },
		{ value: 'name-desc', label: $i18n.t('이름 (Z-A)') },
		{ value: 'date-desc', label: $i18n.t('최신순') },
		{ value: 'date-asc', label: $i18n.t('오래된순') },
		{ value: 'size-desc', label: $i18n.t('크기 (큰순)') },
		{ value: 'size-asc', label: $i18n.t('크기 (작은순)') }
	];
</script>

<Select.Root
	selected={items.find((item) => item.value === value)}
	{items}
	onSelectedChange={(selectedItem) => {
		if (selectedItem) value = selectedItem.value;
	}}
>
	<Select.Trigger
		class="relative flex items-center gap-1 px-2.5 py-1.5 bg-gray-50 dark:bg-gray-850 rounded-xl text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 transition"
		aria-label={$i18n.t('정렬')}
	>
		<Select.Value
			class="inline-flex px-0.5 outline-hidden bg-transparent truncate placeholder-gray-400 focus:outline-hidden"
			placeholder={$i18n.t('정렬')}
		/>
		<ChevronDown className="size-3.5" strokeWidth="2.5" />
	</Select.Trigger>

	<Select.Content
		class="rounded-2xl min-w-[140px] p-1 border border-gray-100 dark:border-gray-800 z-50 bg-white dark:bg-gray-850 dark:text-white shadow-lg"
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
