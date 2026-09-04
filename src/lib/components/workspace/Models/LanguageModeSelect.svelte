<script lang="ts">
	import SettingsSelect from '$lib/components/common/SettingsSelect.svelte';
	import GlobeAlt from '$lib/components/icons/GlobeAlt.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import { getContext } from 'svelte';

	const i18n = getContext<any>('i18n');

	export let value = '';
	export let languages: { code: string; title: string }[] = [];
	export let translatedLocales: string[] = [];
	export let className = '';

	$: options = languages.filter((language) => language.code !== 'en-US');

	const statusFor = (code: string) => (translatedLocales.includes(code) ? ' *' : '');
</script>

<Tooltip
	content={$i18n.t('Editing language')}
	className="relative {className || 'w-full sm:w-fit'}"
>
	<GlobeAlt
		className="pointer-events-none absolute start-2.5 top-1/2 z-10 size-3.5 -translate-y-1/2 text-gray-400 dark:text-gray-500"
	/>
	<SettingsSelect
		bind:value
		className="w-full"
		selectClassName="min-w-[8.5rem] !ps-8"
		ariaLabel={$i18n.t('Editing language')}
	>
		<option value="">{$i18n.t('Default')}</option>
		{#each options as language}
			<option value={language.code}>{language.title}{statusFor(language.code)}</option>
		{/each}
	</SettingsSelect>
</Tooltip>
