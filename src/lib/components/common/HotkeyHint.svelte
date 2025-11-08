<script lang="ts">
	import { onMount } from 'svelte';
	import { shortcuts } from '$lib/shortcuts';
	import { settings } from '$lib/stores';

	export let name: string;
	export let className = '';

	let isMac = false;
	let mounted = false;
	let keys: string[] = [];
	let isVisible = true;

	onMount(() => {
		isMac = /Mac/i.test(navigator.userAgent);
		keys = shortcuts[name]?.keys ?? [];
		mounted = true;
	});

	function formatKey(key: string): string {
		const lowerKey = key.toLowerCase();

		if (lowerKey === 'mod') return isMac ? '⌘' : 'Ctrl';
		if (lowerKey === 'shift') return isMac ? '⇧' : 'Shift';
		if (lowerKey.startsWith('key')) return key.slice(-1);

		return key;
	}
</script>

{#if mounted && isVisible}
	<div
		class="hidden md:flex items-center self-center text-xs text-gray-400 dark:text-gray-600 {className}"
	>
		<span>{keys.map(formatKey).join(isMac ? '' : '+')}</span>
	</div>
{/if}
