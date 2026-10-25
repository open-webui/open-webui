<script lang="ts">
	import { getContext } from 'svelte';
	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import DropdownMenu from '$lib/components/common/DropdownMenu.svelte';
	import Hashtag from '$lib/components/icons/Hashtag.svelte';
	import LockClosed from '$lib/components/icons/LockClosed.svelte';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import Check from '$lib/components/icons/Check.svelte';

	const i18n = getContext<typeof import('$lib/i18n').default>('i18n');

	export let onChange: (value: string) => void = () => {};
	export let state = 'private';

	$: options = [
		{ value: 'private', label: $i18n.t('Private') },
		{ value: 'public', label: $i18n.t('Public') }
	];
</script>

<div class="-mx-1 rounded-xl bg-gray-50/60 px-3 py-2 dark:bg-white/[0.03]">
	<Dropdown closeOnSelect>
		<button
			type="button"
			class="flex h-6 items-center gap-2 rounded-md text-[0.8125rem] font-medium text-gray-800 transition hover:text-gray-950 dark:text-gray-200 dark:hover:text-white"
		>
			{#if state === 'private'}
				<LockClosed className="size-3.5 text-gray-500 dark:text-gray-400" />
			{:else}
				<Hashtag className="size-3.5 text-gray-500 dark:text-gray-400" />
			{/if}
			<span class="sr-only">{$i18n.t('Visibility')}</span>
			<span>{state === 'private' ? $i18n.t('Private') : $i18n.t('Public')}</span>
			<ChevronDown className="size-3 text-gray-400 dark:text-gray-500" strokeWidth="2" />
		</button>
		<div slot="content">
			<DropdownMenu className="min-w-40">
				{#each options as option}
					<button
						type="button"
						role="menuitemradio"
						aria-checked={state === option.value}
						on:click={() => {
							if (state !== option.value) {
								state = option.value;
								onChange(state);
							}
						}}
					>
						{#if option.value === 'private'}
							<LockClosed className="size-3.5" />
						{:else}
							<Hashtag className="size-3.5" />
						{/if}
						<span class="flex-1 text-left">{option.label}</span>
						{#if state === option.value}<Check className="size-3.5 text-blue-500" />{/if}
					</button>
				{/each}
			</DropdownMenu>
		</div>
	</Dropdown>
	<p class="mt-0.5 text-xs leading-5 text-gray-500 dark:text-gray-400">
		{#if state === 'private'}
			{$i18n.t('Only invited users can access')}
		{:else}
			{$i18n.t('Visible to all users')}
		{/if}
	</p>
</div>
