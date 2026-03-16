<script lang="ts">
	import { getContext } from 'svelte';
	import { Select, DropdownMenu } from 'bits-ui';

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

	let open = false;
</script>

<DropdownMenu.Root bind:open>
	<DropdownMenu.Trigger>
		<div
			class={className
				? className
				: 'flex w-full items-center gap-2 truncate bg-transparent px-0.5 text-sm placeholder-gray-400 outline-hidden focus:outline-hidden'}
		>
			{items.find((item) => item.value === value)?.label ?? placeholder}
			<ChevronDown className=" size-3" strokeWidth="2.5" />
		</div>
	</DropdownMenu.Trigger>

	<DropdownMenu.Content {align}>
		<div
			class="dark:bg-gray-850 z-50 w-full rounded-2xl border border-gray-100 bg-white p-1 shadow-lg dark:border-gray-800 dark:text-white"
		>
			{#each items as item}
				<button
					class="flex w-full cursor-pointer items-center gap-2 rounded-xl px-3 py-1.5 text-sm hover:bg-gray-50 dark:hover:bg-gray-800 {value ===
					item.value
						? ' '
						: '  text-gray-500 dark:text-gray-400'}"
					type="button"
					on:click={() => {
						if (value === item.value) {
							value = null;
						} else {
							value = item.value;
						}

						open = false;
						onChange(value);
					}}
				>
					{item.label}
				</button>
			{/each}
		</div>
	</DropdownMenu.Content>
</DropdownMenu.Root>
