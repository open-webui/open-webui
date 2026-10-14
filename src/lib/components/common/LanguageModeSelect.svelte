<script lang="ts">
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import GlobeAlt from '$lib/components/icons/GlobeAlt.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import { getContext } from 'svelte';
	import availableLanguages from '$lib/i18n/locales/languages.json';

	const i18n = getContext<any>('i18n');

	export let value = '';
	export let languages: { code: string; title: string }[] = availableLanguages;
	export let translatedLocales: string[] = [];
	export let className = '';
	export let includeDefault = true;

	$: options = languages;

	const statusFor = (code: string) => (translatedLocales.includes(code) ? ' *' : '');
</script>

<Tooltip
	content={$i18n.t('Editing language')}
	className="relative inline-flex max-w-full shrink-0 rounded-lg bg-gray-50 text-gray-900 transition ring-1 ring-inset ring-gray-200 hover:bg-gray-100 dark:bg-gray-850 dark:text-gray-100 dark:ring-gray-800 dark:hover:bg-gray-800 {className ||
		'w-fit'}"
>
	<GlobeAlt className="pointer-events-none absolute start-2 top-1/2 size-3 -translate-y-1/2" />
	<select
		bind:value
		class="focus-ring min-w-0 max-w-full cursor-pointer appearance-none truncate rounded-lg bg-transparent py-1 ps-6 pe-6 text-xs font-normal outline-hidden ![background-image:none] [field-sizing:content]"
		aria-label={$i18n.t('Editing language')}
	>
		{#if includeDefault}<option value="">{$i18n.t('Default')}</option>{/if}
		{#each options as language}
			<option value={language.code}>{language.title}{statusFor(language.code)}</option>
		{/each}
	</select>
	<ChevronDown
		className="pointer-events-none absolute end-2 top-1/2 size-3 -translate-y-1/2"
		strokeWidth="2"
	/>
</Tooltip>
