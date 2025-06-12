<script lang="ts">
	import type { Readable } from 'svelte/store';
	import type { I18Next } from '$lib/IONOS/i18next.d.ts';
	import { getContext } from 'svelte';
	import Shield from '$lib/IONOS/components/icons/Shield.svelte';

	const i18n = getContext<Readable<I18Next>>('i18n');
</script>

<div class="flex flex-row mx-10 items-center">
	<a
		href="https://www.ionos.de/ionos-gpt-datenschutz-manifest#digitale-loesungen"
		target="_blank"

	>
		<Shield className={"h-6 w-6 inline-block mr-2 fill-purple-700"} />

		<span class="text-purple-700">
			{$i18n.t('Privacy by Design!', { ns: 'ionos' })}
		</span>
	</a>
</div>
