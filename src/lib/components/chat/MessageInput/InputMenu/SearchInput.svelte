<script lang="ts">
	import { getContext } from 'svelte';

	import Search from '$lib/components/icons/Search.svelte';

	const i18n = getContext('i18n');

	export let value = '';
	export let placeholder = $i18n.t('Search');
</script>

<div class="my-0.5 flex ml-2 mr-0.5 h-[1.6875rem] shrink-0 items-center gap-2">
	<Search className="size-3.5 shrink-0" strokeWidth="2" />

	<input
		bind:value
		class="w-full bg-transparent text-[13px] font-normal outline-hidden placeholder:text-gray-400 dark:placeholder:text-gray-500"
		{placeholder}
		autocomplete="off"
		aria-label={placeholder}
		on:click|stopPropagation
		on:keydown|stopPropagation
	/>
</div>
