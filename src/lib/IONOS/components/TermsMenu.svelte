<script lang="ts">
	import { DropdownMenu } from 'bits-ui';
	import type { Readable } from 'svelte/store';
	import type { I18Next } from '$lib/IONOS/i18next.d.ts';
	import { getContext } from 'svelte';
	import Link from '$lib/IONOS/components/common/Link.svelte';
	import { createEventDispatcher } from 'svelte';
	import { flyAndScale } from '$lib/utils/transitions';
	import ArrowUpRightFromSquare from '$lib/IONOS/components/icons/ArrowUpRightFromSquare.svelte';
	import { URLS } from '$lib/IONOS/urls';

	export let show: boolean;
	export let className: string = '';

	let dispatch = createEventDispatcher();

	const i18n = getContext<Readable<I18Next>>('i18n');

	let links: {label: string, url: string}[] = [
		{
			label: $i18n.t('modelLicenseLinkText', { ns: 'ionos' }),
			url: $i18n.t('modelLicenseLinkUrl', { ns: 'ionos' })
		},
		{
			label: $i18n.t('modelUsePolicyLinkText', { ns: 'ionos' }),
			url: $i18n.t('modelUsePolicyLinkUrl', { ns: 'ionos' })
		},
		{
			label: $i18n.t('Imprint', { ns: 'ionos' }),
			url: URLS.imprint
		},
		{
			label: $i18n.t('Privacy', { ns: 'ionos' }),
			url: URLS.privacy
		},
		{
			label: $i18n.t('Terms and conditions', { ns: 'ionos' }),
			url: URLS.terms
		}
	];
</script>

<DropdownMenu.Root
	bind:open={show}
>
	<DropdownMenu.Trigger>
		<slot />
	</DropdownMenu.Trigger>

	<DropdownMenu.Content
		class="rounded-2xl px-2 py-3 text-blue-800 text-xs font-semibold border-gray-300/30 dark:border-gray-700/50 z-50 bg-white dark:bg-gray-850 dark:text-white shadow"
		sideOffset={15}
		alignOffset={-8}
		side="top"
		align="start"
		transition={flyAndScale}
	>
		{#each links as link}
			<DropdownMenu.Item>
				<a href={link.url} target="_blank" rel="noopener noreferrer" class="flex gap-2.5 items-center px-3 py-2 text-sm font-medium cursor-pointer text-blue-800 hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl">
					<ArrowUpRightFromSquare />
					<div class="line-clamp-1">{$i18n.t(link.label)}</div>
				</a>
			</DropdownMenu.Item>
		{/each}
	</DropdownMenu.Content>
</DropdownMenu.Root>
