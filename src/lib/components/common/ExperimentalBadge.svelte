<script lang="ts">
	import { getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import Tooltip from './Tooltip.svelte';

	type I18nStore = Writable<{
		t: (key: string, options?: Record<string, unknown>) => string;
	}>;

	const i18n: I18nStore = getContext('i18n');

	$: label = $i18n.t('Experimental');
	$: content = $i18n.t(
		'This is an experimental feature, it may not function as expected and is subject to change at any time.'
	);
</script>

<Tooltip {content} className="inline-flex">
	<span class="text-[0.625rem] font-normal uppercase leading-none text-gray-400 dark:text-gray-600">
		{label}
	</span>
</Tooltip>
