<script lang="ts">
	import { getContext } from 'svelte';
	import Tooltip from '../common/Tooltip.svelte';
	import type { Shortcut } from '$lib/shortcuts';

	export let shortcut: Shortcut;
	export let isMac: boolean;

	const i18n = getContext('i18n');

	function formatKey(key: string): string {
		const lowerKey = key.toLowerCase();

		switch (lowerKey) {
			case 'mod':
				return isMac ? '⌘' : 'Ctrl';
			case 'shift':
				return isMac ? '⇧' : 'Shift';
			case 'alt':
				return isMac ? '⌥' : 'Alt';
			case 'backspace':
			case 'delete':
				return isMac ? '⌫' : 'Delete';
			case 'escape':
				return 'Esc';
			case 'enter':
				return isMac ? '↩' : 'Enter';
			case 'tab':
				return isMac ? '⇥' : 'Tab';
			case 'arrowup':
				return '↑';
			case 'arrowdown':
				return '↓';
			case 'quote':
				return "'";
			case 'period':
				return '.';
			case 'slash':
				return '/';
			case 'semicolon':
				return ';';
			default:
				if (lowerKey.startsWith('key')) return key.slice(-1);
				if (lowerKey.startsWith('digit')) return key.slice(-1);
				return key.toUpperCase();
		}
	}
</script>

<div class="w-full flex justify-between">
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
	<div class="flex-shrink-0 flex justify-end self-start h-full space-x-1 text-xs">
		{#each shortcut.keys.filter((key) => !(key.toLowerCase() === 'delete' && shortcut.keys.includes('Backspace'))) as key}
			<div
				class="h-fit px-1 py-0.5 flex items-start justify-center rounded-sm border border-black/10 capitalize text-gray-600 dark:border-white/10 dark:text-gray-300"
			>
				{formatKey(key)}
			</div>
		{/each}
	</div>
</div>
