<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import type { Writable } from 'svelte/store';
	import { updateUserSettings } from '$lib/apis/users';
	import {
		DEFAULT_KEYBINDINGS,
		eventToChord,
		formatChord,
		isConfigurableShortcut,
		keybindings,
		resetKeybindings,
		Shortcut,
		shortcuts
	} from '$lib/shortcuts';
	import type { KeybindingsMap, ShortcutDefinition } from '$lib/shortcuts';
	import { settings } from '$lib/stores';
	import ShortcutItem from '../ShortcutItem.svelte';

	type ShortcutEntry = {
		id: Shortcut;
		shortcut: ShortcutDefinition;
	};
	type CategorizedShortcuts = {
		[category: string]: ShortcutEntry[];
	};
	type I18nStore = Writable<{
		t: (key: string, options?: Record<string, unknown>) => string;
	}>;

	const i18n: I18nStore = getContext('i18n');

	let categorizedShortcuts: CategorizedShortcuts = {};
	let isMac = false;
	let recordingShortcut: Shortcut | null = null;

	onMount(() => {
		isMac = /Mac/i.test(navigator.userAgent);
	});

	$: {
		const allShortcuts = Object.entries(shortcuts).filter(([, shortcut]) => {
			if (!shortcut.setting) {
				return true;
			}
			return ($settings as Record<string, unknown>)[shortcut.setting.id] === shortcut.setting.value;
		}) as [Shortcut, ShortcutDefinition][];

		categorizedShortcuts = allShortcuts.reduce<CategorizedShortcuts>((acc, [id, shortcut]) => {
			const category = shortcut.category;
			if (!acc[category]) {
				acc[category] = [];
			}
			acc[category].push({ id, shortcut });
			return acc;
		}, {});
	}

	const saveKeybindings = async (next: KeybindingsMap) => {
		keybindings.set(next);
		await updateUserSettings(localStorage.token, { keybindings: next });
	};

	const setBinding = async (id: Shortcut, chord: string) => {
		if (!isConfigurableShortcut(id)) return;
		await saveKeybindings({ ...$keybindings, [id]: chord });
	};

	const resetBindings = async () => {
		resetKeybindings();
		await updateUserSettings(localStorage.token, { keybindings: DEFAULT_KEYBINDINGS });
	};

	const getConflict = (id: Shortcut, chord: string): Shortcut | null => {
		if (!isConfigurableShortcut(id) || !chord) return null;
		for (const [otherId, otherChord] of Object.entries($keybindings)) {
			if (otherId !== id && otherChord === chord) return otherId as Shortcut;
		}
		return null;
	};

	const handleRecordingKeydown = async (event: KeyboardEvent) => {
		if (!recordingShortcut) return;
		event.preventDefault();
		event.stopPropagation();

		if (event.key === 'Escape') {
			recordingShortcut = null;
			return;
		}

		const chord = eventToChord(event);
		if (!chord) return;

		await setBinding(recordingShortcut, chord);
		recordingShortcut = null;
	};
</script>

<svelte:window on:keydown={handleRecordingKeydown} />

<div id="tab-shortcuts" class="flex h-full flex-col text-sm">
	<div class="mb-4 flex items-center justify-between">
		<h2 class="text-sm font-medium text-gray-900 dark:text-white">
			{$i18n.t('Keyboard')}
		</h2>

		<button
			class="text-[0.625rem] text-gray-400 transition hover:text-gray-600 dark:hover:text-gray-300"
			on:click={resetBindings}
		>
			{$i18n.t('Reset Defaults')}
		</button>
	</div>

	<div class="flex-1 min-h-0 overflow-y-auto scrollbar-hover pr-1.5">
		<div class="flex items-center gap-2 px-1 pb-1">
			<span class="flex-1 text-[0.625rem] font-medium text-gray-400 dark:text-gray-600">
				{$i18n.t('Command')}
			</span>
			<span
				class="w-[9.5rem] shrink-0 text-right text-[0.625rem] font-medium text-gray-400 dark:text-gray-600"
			>
				{$i18n.t('Key')}
			</span>
		</div>

		{#each Object.entries(categorizedShortcuts) as [category, items], categoryIndex}
			<div class={categoryIndex > 0 ? 'mt-3' : ''}>
				<div
					class="px-1 pb-0.5 pt-1 text-[0.625rem] font-medium uppercase tracking-wide text-gray-400 dark:text-gray-600"
				>
					{$i18n.t(category)}
				</div>
				<div class="divide-y divide-gray-100/70 dark:divide-white/[0.03]">
					<!-- {$i18n.t('Chat')} -->
					<!-- {$i18n.t('Global')} -->
					<!-- {$i18n.t('Input')} -->
					<!-- {$i18n.t('Message')} -->

					<!-- {$i18n.t('New Chat')} -->
					<!-- {$i18n.t('New Temporary Chat')} -->
					<!-- {$i18n.t('Delete Chat')} -->
					<!-- {$i18n.t('Open Model Selector')} -->
					<!-- {$i18n.t('Toggle Dictation')} -->
					<!-- {$i18n.t('Search')} -->
					<!-- {$i18n.t('Open Settings')} -->
					<!-- {$i18n.t('Show Shortcuts')} -->
					<!-- {$i18n.t('Toggle Sidebar')} -->
					<!-- {$i18n.t('Close Modal')} -->
					<!-- {$i18n.t('Focus Chat Input')} -->
					<!-- {$i18n.t('Accept Autocomplete Generation\nJump to Prompt Variable')} -->
					<!-- {$i18n.t('Prevent File Creation')} -->
					<!-- {$i18n.t('Attach File From Knowledge')} -->
					<!-- {$i18n.t('Add Custom Prompt')} -->
					<!-- {$i18n.t('Talk to Model')} -->
					<!-- {$i18n.t('Generate Message Pair')} -->
					<!-- {$i18n.t('Regenerate Response')} -->
					<!-- {$i18n.t('Stop Generating')} -->
					<!-- {$i18n.t('Edit Last Message')} -->
					<!-- {$i18n.t('Copy Last Response')} -->
					<!-- {$i18n.t('Copy Last Code Block')} -->

					<!-- {$i18n.t('Only active when "Paste Large Text as File" setting is toggled on.')} -->
					<!-- {$i18n.t('Only active when the chat input is in focus.')} -->
					<!-- {$i18n.t('Only active when the chat input is in focus and an LLM is generating a response.')} -->
					<!-- {$i18n.t('Only can be triggered when the chat input is in focus.')} -->

					<!-- {$i18n.t('Voice')} -->
					<!-- {$i18n.t('Toggle Mute')} -->
					<!-- {$i18n.t('Only active during Voice Mode.')} -->
					<!-- {$i18n.t('Reset Defaults')} -->
					<!-- {$i18n.t('Press keys...')} -->
					<!-- {$i18n.t('Unassigned')} -->
					<!-- {$i18n.t('Also bound to {{action}}')} -->
					{#each items as { id, shortcut }}
						{@const configurable = isConfigurableShortcut(id)}
						{@const chord = configurable ? $keybindings[id] : ''}
						{@const conflict = configurable ? getConflict(id, chord) : null}
						<div class="flex min-h-8 w-full items-center gap-3 px-1 py-1.5">
							<ShortcutItem {id} {shortcut} {isMac} compact />

							<div class="flex w-[9.5rem] shrink-0 items-center justify-end gap-1">
								{#if configurable}
									{#if recordingShortcut === id}
										<span
											class="inline-flex min-h-[1.125rem] items-center rounded-full bg-gray-100 px-[0.4375rem] py-0.5 text-[0.625rem] font-medium leading-none text-gray-500 dark:bg-white/6 dark:text-gray-400"
										>
											{$i18n.t('Press keys...')}
										</span>
									{:else if chord}
										<button
											class="inline-flex min-h-[1.125rem] items-center rounded-full bg-gray-100 px-[0.4375rem] py-0.5 text-center text-[0.625rem] font-medium leading-none text-gray-500 dark:bg-white/6 dark:text-gray-400"
											title={$i18n.t('Click to rebind')}
											on:click={() => (recordingShortcut = id)}
										>
											{formatChord(chord)}
										</button>
									{:else}
										<button
											class="text-[0.625rem] text-gray-500 transition hover:text-gray-400 dark:text-gray-600"
											on:click={() => (recordingShortcut = id)}
										>
											{$i18n.t('Unassigned')}
										</button>
									{/if}

									{#if conflict}
										<span
											class="text-[0.5625rem] text-amber-500"
											title={$i18n.t('Also bound to {{action}}', {
												action: $i18n.t(shortcuts[conflict]?.name ?? conflict)
											})}>!</span
										>
									{/if}
								{:else}
									<ShortcutItem {id} {shortcut} {isMac} keysOnly />
								{/if}
							</div>
						</div>
					{/each}
				</div>
			</div>
		{/each}
	</div>
</div>
