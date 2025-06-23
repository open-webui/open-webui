<script lang="ts">
	import type { Readable } from 'svelte/store';
	import type { I18Next } from '$lib/IONOS/i18next.d.ts';
	import { getContext } from 'svelte';
	import Link from '$lib/IONOS/components/common/Link.svelte';

	const i18n = getContext<Readable<I18Next>>('i18n');

	export let className: string = '';

	$: [before, joiner1, joiner2, joiner3, after] = $i18n.t('IONOS GPT is based on the IONOS AI Model Hub. By using it, you agree to the [modelLicenseLink], the [modelUsePolicyLink], the [bflTermsLinkUrl] and the [bflUsePolicyLinkUrl].', { ns: 'ionos' }).split(/\[[a-zA-Z]+\]/);
</script>

<div class="flex flex-col text-left shadow-lg rounded-2xl bg-white w-full {className}">
	<p class="max-w-2xl text-gray-400 text-sm break-keep p-5">
		{before}
		<Link
			passive={true}
			href={$i18n.t('modelLicenseLinkUrl', { ns: 'ionos' })}
		>
			{$i18n.t('modelLicenseLinkText', { ns: 'ionos' })}
		</Link>
		{joiner1}
		<Link
			passive={true}
			href={$i18n.t('modelUsePolicyLinkUrl', { ns: 'ionos' })}
		>
			{$i18n.t('modelUsePolicyLinkText', { ns: 'ionos' })}
		</Link>
		{joiner2}
		<Link
			passive={true}
			href={$i18n.t('bflTermsLinkUrl', { ns: 'ionos' })}
		>
			{$i18n.t('bflTermsLinkText', { ns: 'ionos' })}
		</Link>
		{joiner3}
		<Link
			passive={true}
			href={$i18n.t('bflUsePolicyLinkUrl', { ns: 'ionos' })}
		>
			{$i18n.t('bflUsePolicyLinkText', { ns: 'ionos' })}
		</Link>
		{after}
	</p>
</div>
