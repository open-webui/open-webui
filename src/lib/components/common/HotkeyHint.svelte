<script lang="ts">
	import KeyPill from './KeyPill.svelte';
	import { onMount } from 'svelte';
	import { formatChord, isConfigurableShortcut, keybindings, shortcuts } from '$lib/shortcuts';
	import type { Shortcut } from '$lib/shortcuts';
	import { settings } from '$lib/stores';

	export let name: string;
	export let className = '';

	let isMac = false;
	let mounted = false;

	$: isVisible = $settings?.keyboardShortcuts !== false;

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

	$: id = name as Shortcut;
	$: text = isConfigurableShortcut(id)
		? formatChord($keybindings[id])
		: (shortcuts[id]?.keys ?? []).map(formatKey).join(isMac ? '' : '+');
</script>

{#if mounted && isVisible && text}
	<span class="hidden md:inline-flex items-center self-center {className}">
		<KeyPill {text} />
	</span>
{/if}
