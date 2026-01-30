<script lang="ts">
	import { getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';

	const i18n = getContext<Writable<i18nType>>('i18n');
</script>

<p class="text-md text-gray-500 dark:text-gray-400 mt-2">
	{$i18n.t('Response generation stopped')}
</p>
