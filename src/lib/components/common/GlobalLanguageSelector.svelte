<script lang="ts">
	import { getContext } from 'svelte';
	import Tooltip from './Tooltip.svelte';

	const i18n = getContext('i18n');

	async function toggleLanguage() {
		const newLocale = $i18n.language === 'en-GB' ? 'fr-CA' : 'en-GB';
		await $i18n.changeLanguage(newLocale);
	}

	$: currentLangDisplay = $i18n.language === 'en-GB' ? 'FR' : 'EN';
</script>

<Tooltip content={$i18n.language === 'en-GB' ? 'Français' : 'English'}>
	<button
		class="group flex cursor-pointer p-2 rounded-xl bg-white dark:bg-gray-900 transition hover:bg-gray-100 dark:hover:bg-gray-800"
		on:click={toggleLanguage}
	>
		<div
			class="m-auto self-center text-sm font-medium text-gray-900 dark:text-white rounded transition"
		>
			{currentLangDisplay}
		</div>
	</button>
</Tooltip>
