<script lang="ts">
	import { getOllamaVersion } from '$lib/apis/ollama';
	import { onMount, getContext } from 'svelte';
	import BuildVersion from '$lib/components/common/BuildVersion.svelte';
	import UserSettingSection from './UserSettingSection.svelte';
	const i18n: any = getContext('i18n');
	let ollamaVersion = '';
	onMount(async () => {
		ollamaVersion = await getOllamaVersion(localStorage.token).catch(() => '');
	});
</script>

<div id="tab-about" class="flex flex-col h-full text-sm">
	<h2 class="text-sm font-medium text-gray-900 dark:text-white mb-4">GCAT</h2>
	<div class="flex-1 min-h-0 overflow-y-auto scrollbar-hover pr-1.5">
		<UserSettingSection title="GCAT" first>
			<img src="/static/gcat.svg" alt="GCAT logo" class="size-10 rounded-xl bg-gray-900 p-2" />
			<BuildVersion />
		</UserSettingSection>
		{#if ollamaVersion}
			<UserSettingSection title={$i18n.t('settings.personal.about.sections.ollamaVersion.title')}>
				<div class="text-xs text-gray-600 dark:text-gray-400">{ollamaVersion}</div>
			</UserSettingSection>
		{/if}
		<UserSettingSection title={$i18n.t('License')}>
			<div class="text-xs text-gray-400 dark:text-gray-500">
				<a
					href="/static/THIRD_PARTY_LICENSE.txt"
					target="_blank"
					rel="noopener noreferrer"
					class="underline">{$i18n.t('License')}</a
				>
			</div>
			<div class="text-xs text-gray-400 dark:text-gray-500">
				{$i18n.t('Emoji graphics provided by')}
				<a href="https://github.com/jdecked/twemoji" target="_blank" rel="noopener noreferrer"
					>Twemoji</a
				>,
				{$i18n.t('licensed under')}
				<a
					href="https://creativecommons.org/licenses/by/4.0/"
					target="_blank"
					rel="noopener noreferrer">CC-BY 4.0</a
				>.
			</div>
			<div class="text-xs text-gray-400 dark:text-gray-500">
				Original project created by Tim J. Baek.
			</div>
		</UserSettingSection>
	</div>
</div>
