<script lang="ts">
	import { getContext } from 'svelte';
	
	const i18n = getContext('i18n');
</script>

<div class="flex items-center justify-center h-full min-h-[400px]">
	<div class="text-center">
		<div class="text-6xl mb-4">🚀</div>
		<h1 class="text-2xl font-bold mb-2 text-gray-900 dark:text-white">
			{$i18n.t('Analytics')}
		</h1>
		<p class="text-lg text-gray-600 dark:text-gray-400">
			{$i18n.t('Coming Soon')}
	</div>
</div>