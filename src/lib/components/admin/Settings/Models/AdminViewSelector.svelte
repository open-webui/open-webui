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
		{ value: 'enabled', label: $i18n.t('Enabled') },
		{ value: 'disabled', label: $i18n.t('Disabled') },
		{ value: 'visible', label: $i18n.t('Visible') },
		{ value: 'hidden', label: $i18n.t('Hidden') },
		{ value: 'public', label: $i18n.t('Public') },
		{ value: 'private', label: $i18n.t('Private') }
	];
</script>

<Select
	bind:value
	{items}
	{placeholder}
	triggerClass="relative w-full flex items-center gap-0.5 px-2.5 py-1.5 bg-gray-50 dark:bg-gray-850 rounded-xl"
	labelClass="inline-flex h-input px-0.5 w-full outline-hidden bg-transparent truncate placeholder-gray-400 focus:outline-hidden"
	onChange={() => onChange(value)}
>
	<svelte:fragment slot="trigger" let:selectedLabel>
		<span
			class="inline-flex h-input px-0.5 w-full outline-hidden bg-transparent truncate placeholder-gray-400 focus:outline-hidden"
		>
			{selectedLabel}
		</span>
		<ChevronDown className="size-3.5" strokeWidth="2.5" />
	</svelte:fragment>

	<svelte:fragment slot="item" let:item let:selected>
		{item.label}
		<div class="ml-auto {selected ? '' : 'invisible'}">
			<Check />
		</div>
	</svelte:fragment>
</Select>
