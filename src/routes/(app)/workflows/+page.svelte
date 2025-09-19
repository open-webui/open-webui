<script lang="ts">
	import { getContext } from 'svelte';
	import { get } from 'svelte/store';
	import { WEBUI_NAME } from '$lib/stores';

	const i18n = getContext('i18n');
</script>

<svelte:head>
	<title>
		{get(i18n).t('Workflows')} | {get(WEBUI_NAME)}
	</title>
</svelte:head>

<div class="flex h-full w-full items-center justify-center">
	<div class="text-center">
		<h1 class="text-2xl font-bold text-gray-900 dark:text-white mb-4">
			{get(i18n).t('Workflows')}
		</h1>
		<p class="text-gray-500 dark:text-gray-400">
			{get(i18n).t('Coming soon')}
		</p>
	</div>
</div>