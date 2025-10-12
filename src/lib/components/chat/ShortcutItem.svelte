<script lang="ts">
	import { getContext } from 'svelte';
	import Tooltip from '../common/Tooltip.svelte';
	import type { Shortcut } from '$lib/shortcuts';

	export let shortcut: Shortcut;
	export let isMac: boolean;

	const i18n = getContext('i18n');

	function formatKey(key: string): string {
		const lowerKey = key.toLowerCase();

		if (lowerKey === 'mod') return isMac ? '⌘' : 'Ctrl/⌘';
		if (lowerKey === 'shift') return isMac ? '⇧' : 'Shift';
		if (lowerKey === 'backspace') return '⌫/Delete';
		if (lowerKey === 'escape') return 'Esc';
		if (lowerKey === 'enter') return 'Enter';
		if (lowerKey === 'tab') return 'Tab';
		if (lowerKey === 'arrowup') return '↑';
		if (lowerKey === 'arrowdown') return '↓';

		// For keys like 'KeyK', 'KeyO', etc., we just want the last character.
		if (lowerKey.startsWith('key')) return key.slice(-1);
		// For keys like 'Digit2', 'Digit3', etc.
		if (lowerKey.startsWith('digit')) return key.slice(-1);
		// For other special keys
		if (lowerKey === 'quote') return "'";
		if (lowerKey === 'period') return '.';
		if (lowerKey === 'slash') return '/';
		if (lowerKey === 'semicolon') return ';';

		return key.toUpperCase();
	}
</script>

<div class="w-full flex justify-between items-center">
	<div class="text-sm whitespace-pre-line">
		{#if shortcut.tooltip}
			<Tooltip content={$i18n.t(shortcut.tooltip)}>
				<span class="whitespace-nowrap">
					{$i18n.t(shortcut.name)}<span class="text-xs">&nbsp;*</span>
				</span>
			</Tooltip>
		{:else}
			{$i18n.t(shortcut.name)}
		{/if}
	</div>
	<div class="flex-shrink-0 flex items-center self-center space-x-1 text-xs">
		{#each shortcut.keys as key}
			<div
				class="h-fit py-1 px-2 flex items-center justify-center rounded-sm border border-black/10 capitalize text-gray-600 dark:border-white/10 dark:text-gray-300"
			>
				{formatKey(key)}
			</div>
		{/each}
	</div>
</div>