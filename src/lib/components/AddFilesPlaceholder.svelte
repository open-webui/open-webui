<script>
	import { getContext } from 'svelte';

	export let title = '';
	export let content = '';
	const i18n = getContext('i18n');
</script>

<div class="px-3">
	<div class="text-center text-6xl mb-3">📄</div>
	<div class="text-center dark:text-white text-xl font-semibold z-50">
		{#if title}
			{title}
		{:else}
			{$i18n.t('Add Files')}
		{/if}
	</div>

	<slot
		><div class="px-2 mt-2 text-center text-sm dark:text-gray-200 w-full">
			{#if content}
				{content}
			{:else}
				{$i18n.t('Drop any files here to upload')}
			{/if}
		</div>
	</slot>
</div>
