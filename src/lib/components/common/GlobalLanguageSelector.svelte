<script lang="ts">
	import { getContext } from 'svelte';
	import { locale } from '$lib/stores/locale';
	import Tooltip from './Tooltip.svelte';

	const i18n = getContext('i18n');

	async function toggleLanguage() {
		const newLocale = $locale === 'en-GB' ? 'fr-CA' : 'en-GB';
		// Update store and localStorage
		locale.set(newLocale);
		localStorage.locale = newLocale; // This triggers the storage event
		await $i18n.changeLanguage(newLocale);

		// Dispatch a custom event for immediate reactivity
		window.dispatchEvent(
			new CustomEvent('storage', {
				detail: { locale: newLocale }
			})
		);
	}

	$: currentLangDisplay = $locale === 'en-GB' ? 'FR' : 'EN';
</script>

<Tooltip content={$locale === 'en-GB' ? 'Français' : 'English'}>
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
