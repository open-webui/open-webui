<script lang="ts">
	import type { Readable } from 'svelte/store';
	import type { I18Next } from '$lib/IONOS/i18next.d.ts';
	import { getContext } from 'svelte';
	import Link from '$lib/IONOS/components/common/Link.svelte';
	import { URLS } from '$lib/IONOS/urls';

	const i18n = getContext<Readable<I18Next>>('i18n');

	$: [before, joiner1, joiner2, after] = $i18n.t('IONOS GPT is based on the [modelHubInfoLink], which provides the Llama model. By using it, you agree to the [modelLicenseLink] and [modelUsePolicyLink]', { ns: 'ionos' }).split(/\[[a-zA-Z]+\]/);

	export let extraClasses: string = '';
</script>

<div class="flex flex-col items-center">
	<p class="max-w-2xl text-gray-500 text-xs text-center">
		{before}
		<Link
			passive={true}
			href={$i18n.t('modelHubInfoLinkUrl', { ns: 'ionos' })}
		>
			{$i18n.t('modelHubInfoLinkText', { ns: 'ionos' })}
		</Link>
		{joiner1}
		<Link
			passive={true}
			href={$i18n.t('modelLicenseLinkUrl', { ns: 'ionos' })}
		>
			{$i18n.t('modelLicenseLinkText', { ns: 'ionos' })}
		</Link>
		{joiner2}
		<Link
			passive={true}
			href={$i18n.t('modelUsePolicyLinkUrl', { ns: 'ionos' })}
		>
			{$i18n.t('modelUsePolicyLinkText', { ns: 'ionos' })}
		</Link>
		{after}
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
