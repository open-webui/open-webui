<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import type { Writable } from 'svelte/store';
	import { shortcuts } from '$lib/shortcuts';
	import { settings } from '$lib/stores';
	import ShortcutItem from '../ShortcutItem.svelte';

	type ShortcutDefinition = NonNullable<(typeof shortcuts)[keyof typeof shortcuts]>;
	type CategorizedShortcuts = {
		[category: string]: ShortcutDefinition[];
	};

	const i18n: Writable<any> = getContext('i18n');

	let categorizedShortcuts: CategorizedShortcuts = {};
	let isMac = false;

	onMount(() => {
		isMac = /Mac/i.test(navigator.userAgent);
	});

	$: {
		const allShortcuts = Object.values(shortcuts).filter((shortcut) => {
			if (!shortcut.setting) {
				return true;
			}
			return ($settings as Record<string, any>)[shortcut.setting.id] === shortcut.setting.value;
		});

		categorizedShortcuts = allShortcuts.reduce<CategorizedShortcuts>((acc, shortcut) => {
			const category = shortcut.category;
			if (!acc[category]) {
				acc[category] = [];
			}
			acc[category].push(shortcut);
			return acc;
		}, {});
	}
</script>

<div id="tab-shortcuts" class="flex h-full flex-col text-sm">
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
					{#each items as shortcut}
						<ShortcutItem {shortcut} {isMac} />
					{/each}
				</div>
			</div>
		{/each}
	</div>
</div>
