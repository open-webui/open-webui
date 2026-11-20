<script>
	import { getContext } from 'svelte';

	export let title = '';
	export let content = '';
	const i18n = getContext('i18n');
</script>

<div class="px-3">
	<div class="text-center dark:text-white text-2xl font-normal z-50" role="heading" aria-level="2">
		{#if title}
			{title}
		{:else}
			{$i18n.t('Add Files')}
		{/if}
	</div>

	<slot
		><div class="px-2 mt-2 text-center text-base-700 dark:text-base-200 w-full">
			{#if content}
				{content}
			{:else}
				{$i18n.t('Drop any files here to upload')}
			{/if}
		</div>
	</slot>
</div>
