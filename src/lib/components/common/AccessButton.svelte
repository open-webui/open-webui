<script lang="ts">
	import { getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';

	import LockClosed from '$lib/components/icons/LockClosed.svelte';

	const i18n = getContext<Writable<i18nType>>('i18n');

	export let className = '';
	export let disabled = false;
	export let label = '';
</script>

<button
	type="button"
	class="focus-ring flex shrink-0 items-center gap-1 rounded-lg bg-gray-50 px-2 py-1 text-xs font-normal text-gray-900 transition ring-1 ring-gray-200 hover:bg-gray-100 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-gray-850 dark:text-gray-100 dark:ring-gray-800 dark:hover:bg-gray-800 {className}"
	{disabled}
	on:click
>
	<LockClosed strokeWidth="2.5" className="size-3 shrink-0" />
	<span class="shrink-0">{label || $i18n.t('Access')}</span>
</button>
