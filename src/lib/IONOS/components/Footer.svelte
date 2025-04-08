<script lang="ts">
	import type { Readable } from 'svelte/store';
	import type { I18Next } from '$lib/IONOS/i18next.d.ts';
	import { getContext } from 'svelte';
	import Link from '$lib/IONOS/components/common/Link.svelte';
	import { URLS } from '$lib/IONOS/urls';

	const i18n = getContext<Readable<I18Next>>('i18n');

	export let extraClasses: string = '';
</script>

<div class="flex flex-col items-center">
	<p class="max-w-2xl text-gray-500 text-xs text-center">
		{$i18n.t('By sending messages to IONOS GPT, you agree to our terms and conditions and confirm that you\'ve read our privacy policy.', { ns: 'ionos' })}
	</p>

	<div
		class="flex-1 flex flex-row justify-end mt-5 mb-7 gap-3 text-sm justify-center {extraClasses}"
	>
		<span>
			{$i18n.t('© 2025 IONOS SE', { ns: 'ionos' })}
		</span>
		·
		<Link href={URLS.imprint}>
			{$i18n.t('Imprint', { ns: 'ionos' })}
		</Link>
		·
		<Link href={URLS.privacy}>
			{$i18n.t('Privacy', { ns: 'ionos' })}
		</Link>
		·
		<Link href={URLS.terms}>
			{$i18n.t('Terms and conditions', { ns: 'ionos' })}
		</Link>
	</div>
</div>
