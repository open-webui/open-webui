<script lang="ts">
	import type { Readable } from 'svelte/store';
	import type { I18Next } from '$lib/IONOS/i18next.d.ts';
	import { getContext } from 'svelte';
	import Shield from '$lib/IONOS/components/icons/Shield.svelte';

	const i18n = getContext<Readable<I18Next>>('i18n');
</script>

<div class="flex flex-row mx-10 items-center">
	<Shield className={"h-6 w-6 inline-block mr-2 fill-ai-main-500"} />

	<span class="text-ai-main-500">
		{$i18n.t('Privacy by Design!', { ns: 'ionos' })}
	</span>
</div>
