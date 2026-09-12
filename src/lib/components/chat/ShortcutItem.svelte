<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import type { Writable } from 'svelte/store';
	import Tooltip from '../common/Tooltip.svelte';
	import { formatChord, isConfigurableShortcut, keybindings, shortcuts } from '$lib/shortcuts';
	import type { Shortcut } from '$lib/shortcuts';

	type ShortcutDefinition = NonNullable<(typeof shortcuts)[keyof typeof shortcuts]>;
	type I18nStore = Writable<{
		t: (key: string, options?: Record<string, unknown>) => string;
	}>;

	export let id: Shortcut | undefined = undefined;
	export let shortcut: ShortcutDefinition;
	export let isMac: boolean;
	export let compact = false;
	export let keysOnly = false;

	const i18n: I18nStore = getContext('i18n');
	let keyboardLayoutMap: Map<string, string> | undefined;

	onMount(async () => {
		const nav = navigator as Navigator & {
			keyboard?: { getLayoutMap?: () => Promise<Map<string, string>> };
		};

		if (nav.keyboard?.getLayoutMap) {
			try {
				keyboardLayoutMap = await nav.keyboard.getLayoutMap();
			} catch (error) {
				console.error('Failed to get keyboard layout map:', error);
			}
		}
	});

	function formatKey(key: string): string {
		// First, handle special modifier keys which are defined in lowercase
		switch (key) {
			case 'mod':
				return isMac ? '⌘' : 'Ctrl';
			case 'shift':
				return isMac ? '⇧' : 'Shift';
			case 'alt':
				return isMac ? '⌥' : 'Alt';
		}

		// Next, try to use the layout map with the raw KeyboardEvent.code (e.g., "Slash")
		if (keyboardLayoutMap && keyboardLayoutMap.has(key)) {
			const mappedKey = keyboardLayoutMap.get(key) ?? key;
			// For single characters, make them uppercase. For others (like 'CapsLock'), leave as is.
			return mappedKey.length === 1 ? mappedKey.toUpperCase() : mappedKey;
		}

		// Finally, provide a fallback for browsers without getLayoutMap or for keys not in the map
		const lowerKey = key.toLowerCase();
		switch (lowerKey) {
			case 'backspace':
			case 'delete':
				return isMac ? '⌫' : 'Delete';
			case 'escape':
				return 'Esc';
			case 'enter':
				return isMac ? '↩\uFE0E' : 'Enter';
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
				// For 'KeyA', 'Digit1', etc., extract the last character.
				if (lowerKey.startsWith('key') || lowerKey.startsWith('digit')) {
					return key.slice(-1).toUpperCase();
				}
				// For anything else, just uppercase it.
				return key.toUpperCase();
		}
	}

	function visibleKeys(keys: string[]): string[] {
		return keys.filter((key) => !(key.toLowerCase() === 'delete' && keys.includes('Backspace')));
	}

	function formatKeys(keys: string[]): string {
		return visibleKeys(keys)
			.map(formatKey)
			.join(isMac ? '' : ' + ');
	}

	function displayKeys(): string {
		if (id && isConfigurableShortcut(id)) {
			return formatChord($keybindings[id]) || $i18n.t('Unassigned');
		}
		return formatKeys(shortcut.keys);
	}
</script>

{#if keysOnly}
	<span
		class="inline-flex min-h-[1.125rem] max-w-[9.5rem] shrink-0 items-center justify-center rounded-full bg-gray-100 px-[0.4375rem] py-0.5 text-center text-[0.625rem] font-medium leading-none text-gray-500 dark:bg-white/6 dark:text-gray-400"
	>
		{displayKeys()}
	</span>
{:else}
	<div
		class={compact
			? 'min-w-0 flex-1 text-[0.71875rem] leading-tight text-gray-700 dark:text-gray-300'
			: 'flex min-h-8 w-full items-center gap-3 px-1 py-1.5'}
	>
		<div
			class={compact
				? ''
				: 'min-w-0 flex-1 text-[0.71875rem] leading-tight text-gray-700 dark:text-gray-300'}
		>
			{#if shortcut.tooltip}
				<Tooltip content={$i18n.t(shortcut.tooltip)}>
					<span class="inline-flex max-w-full items-baseline gap-1">
						<span class="truncate whitespace-pre-line">{$i18n.t(shortcut.name)}</span>
						<span class="text-[0.625rem] text-gray-400 dark:text-gray-600">*</span>
					</span>
				</Tooltip>
			{:else}
				<span class="whitespace-pre-line">{$i18n.t(shortcut.name)}</span>
			{/if}
		</div>
		{#if !compact}
			<span
				class="inline-flex min-h-[1.125rem] max-w-[9.5rem] shrink-0 items-center justify-center rounded-full bg-gray-100 px-[0.4375rem] py-0.5 text-center text-[0.625rem] font-medium leading-none text-gray-500 dark:bg-white/6 dark:text-gray-400"
			>
				{displayKeys()}
			</span>
		{/if}
	</div>
{/if}
