<script lang="ts">
	import { getContext } from 'svelte';

	import Merge from '$lib/components/icons/Merge.svelte';
	import GraphModal from '$lib/components/common/GraphModal.svelte';

	const i18n = getContext('i18n');

	export let url = '';

	let show = false;
</script>

<GraphModal bind:show {url} />

<div class="py-1 -mx-0.5 w-full flex gap-1 items-center flex-wrap">
	<button
		class="text-xs font-normal text-gray-600 dark:text-gray-300 px-3.5 h-8 rounded-full hover:bg-gray-100 dark:hover:bg-gray-800 transition flex items-center gap-1.5 border border-gray-50 dark:border-gray-850/30"
		aria-label={$i18n.t('View record graph')}
		on:click={() => {
			show = true;
		}}
	>
		<Merge className="size-3.5" />
		<div>{$i18n.t('View Graph')}</div>
	</button>
</div>
