<script lang="ts">
	import { getContext } from 'svelte';

	const i18n = getContext('i18n');
</script>

<div class="flex w-full items-center gap-3 my-3 text-xs text-gray-400 dark:text-gray-500">
	<div class="flex-1 border-t-2 border-dotted border-gray-200 dark:border-gray-800"></div>
	<div class="shrink-0">{$i18n.t('Context compacted')}</div>
	<div class="flex-1 border-t-2 border-dotted border-gray-200 dark:border-gray-800"></div>
</div>
