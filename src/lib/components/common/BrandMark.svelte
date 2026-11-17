<script lang="ts">
	import { onMount } from 'svelte';
	import { theme } from '$lib/stores';
	import { brandLockupUrl, brandMarkUrl, documentIsDark } from '$lib/branding';

	export let variant: 'mark' | 'lockup' = 'mark';
	export let markSize: 32 | 48 | 64 = 32;
	/** When set, ignores UI theme (e.g. onboarding hero on a dark background). */
	export let preferDark: boolean | undefined = undefined;
	export let alt = '';
	export let className = '';

	let dark = documentIsDark();

	function syncTheme() {
		if (preferDark !== undefined) {
			dark = preferDark;
			return;
		}
		if ($theme === 'dark' || $theme === 'oled-dark') {
			dark = true;
		} else if ($theme === 'light' || $theme === 'her') {
			dark = false;
		} else {
			dark = documentIsDark();
		}
	}

	$: syncTheme();

	onMount(() => {
		syncTheme();
		const observer = new MutationObserver(() => {
			if ($theme === 'system') syncTheme();
		});
		observer.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });
		return () => observer.disconnect();
	});

	$: src = variant === 'lockup' ? brandLockupUrl(dark) : brandMarkUrl(dark, markSize);
</script>

<img {src} {alt} class={className} loading="eager" decoding="async" />