<script lang="ts">
	import { onMount } from 'svelte';
	import { formatChord, isConfigurableShortcut, keybindings, shortcuts } from '$lib/shortcuts';
	import type { Shortcut } from '$lib/shortcuts';

	export let name: string;
	export let className = '';

	let isMac = false;
	let mounted = false;
	let isVisible = true;

	onMount(() => {
		isMac = /Mac/i.test(navigator.userAgent);
		mounted = true;
	});

	function formatKey(key: string): string {
		const lowerKey = key.toLowerCase();

		if (lowerKey === 'mod') return isMac ? '⌘' : 'Ctrl';
		if (lowerKey === 'shift') return isMac ? '⇧' : 'Shift';
		if (lowerKey.startsWith('key')) return key.slice(-1);

		return key;
	}

	function displayKeys(): string {
		const id = name as Shortcut;
		if (isConfigurableShortcut(id)) {
			return formatChord($keybindings[id]);
		}
		const keys = shortcuts[id]?.keys ?? [];
		return keys.map(formatKey).join(isMac ? '' : '+');
	}
</script>

{#if mounted && isVisible}
	<div
		class="hidden md:flex items-center self-center whitespace-nowrap text-xs text-gray-400 dark:text-gray-600 {className}"
	>
		<span>{displayKeys()}</span>
	</div>
{/if}
