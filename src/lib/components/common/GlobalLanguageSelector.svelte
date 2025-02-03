<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { getLanguages } from '$lib/i18n';
	import Tooltip from '../common/Tooltip.svelte';

	const i18n = getContext('i18n');
	let languages: Awaited<ReturnType<typeof getLanguages>> = [];
	let currentLang = $i18n.language;

	const toggleLanguage = () => {
		const newLang = currentLang === 'en-GB' ? 'fr-CA' : 'en-GB';
		$i18n.changeLanguage(newLang);
		currentLang = newLang;
	};

	onMount(async () => {
		languages = await getLanguages();
	});

	$: currentLanguage = languages.find((lang) => lang.code === currentLang);
</script>

<button
	class="flex items-center rounded-xl py-2.5 px-2.5 w-full hover:bg-gray-100 dark:hover:bg-gray-900 transition"
	on:click|stopPropagation={toggleLanguage}
>
	<div class="self-center mr-3">
		<svg
			xmlns="http://www.w3.org/2000/svg"
			width="28"
			height="28"
			viewBox="0 0 24 24"
			fill="none"
			stroke="currentColor"
			stroke-width="2"
			stroke-linecap="round"
			stroke-linejoin="round"
			class="tabler-icon tabler-icon-info-square-rounded"
		>
			<path d="M12 9h.01"></path>
			<path d="M11 12h1v4h1"></path>
			<path d="M12 3c7.2 0 9 1.8 9 9s-1.8 9 -9 9s-9 -1.8 -9 -9s1.8 -9 9 -9z"></path>
		</svg>
	</div>
	<div class="self-center font-medium">
		{#if currentLanguage}
			{currentLanguage.title}
		{/if}
	</div>
</button>
