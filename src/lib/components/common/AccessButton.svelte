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
	class="focus-ring flex shrink-0 items-center gap-1 rounded-lg bg-base-50 px-2 py-1 text-xs font-normal text-base-900 transition ring-1 ring-inset ring-base-200 hover:bg-base-100 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-base-850 dark:text-base-100 dark:ring-base-800 dark:hover:bg-base-800 {className}"
	{disabled}
	on:click
>
	<LockClosed strokeWidth="2.5" className="size-3 shrink-0" />
	<span class="shrink-0">{label || $i18n.t('Access')}</span>
</button>
