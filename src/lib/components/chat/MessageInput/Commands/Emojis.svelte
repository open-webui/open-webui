<script lang="ts">
	import { getContext } from 'svelte';

	import { WEBUI_BASE_URL } from '$lib/constants';
	import emojiShortCodes from '$lib/emoji-shortcodes.json';
	import Tooltip from '$lib/components/common/Tooltip.svelte';

	const i18n = getContext('i18n');

	export let query = '';
	export let onSelect = (e) => {};

	let selectedIdx = 0;
	export let filteredItems = [];

	// Build a flat list of { name, shortCodes } for searching
	const allEmojis = Object.entries(emojiShortCodes).map(([key, value]) => ({
		name: key,
		shortCodes: typeof value === 'string' ? [value] : (value as string[])
	}));

	$: {
		if (query && query.length >= 2) {
			const q = query.toLowerCase();
			filteredItems = allEmojis
				.filter(
					(emoji) =>
						emoji.name.toLowerCase().includes(q) ||
						emoji.shortCodes.some((code) => code.toLowerCase().includes(q))
				)
				.sort((a, b) => {
					// Score: 0 = exact match, 1 = prefix match, 2 = substring match
					const score = (emoji) => {
						if (emoji.shortCodes.some((c) => c.toLowerCase() === q)) return 0;
						if (emoji.shortCodes.some((c) => c.toLowerCase().startsWith(q))) return 1;
						return 2;
					};
					return score(a) - score(b);
				})
				.slice(0, 50);
		} else {
			filteredItems = [];
		}
	}

	$: if (query) {
		selectedIdx = 0;
	}

	export const selectUp = () => {
		selectedIdx = Math.max(0, selectedIdx - 1);
	};

	export const selectDown = () => {
		selectedIdx = Math.min(selectedIdx + 1, filteredItems.length - 1);
	};

	export const select = async () => {
		const emoji = filteredItems[selectedIdx];
		if (emoji) {
			onSelect({ type: 'emoji', data: emoji });
		}
	};
</script>

{#if filteredItems.length > 0}
	<div class="px-2 text-xs text-gray-500 py-1">
		{$i18n.t('Emojis')}
	</div>

	{#each filteredItems as emoji, emojiIdx}
		<button
			class="px-2.5 py-1.5 rounded-xl w-full text-left {emojiIdx === selectedIdx
				? 'bg-gray-50 dark:bg-gray-800 selected-command-option-button'
				: ''}"
			type="button"
			on:click={() => {
				onSelect({ type: 'emoji', data: emoji });
			}}
			on:mousemove={() => {
				selectedIdx = emojiIdx;
			}}
			on:focus={() => {}}
			data-selected={emojiIdx === selectedIdx}
		>
			<div class="flex items-center gap-2 text-black dark:text-gray-100">
				<img
					src="{WEBUI_BASE_URL}/assets/emojis/{emoji.name.toLowerCase()}.svg"
					alt={emoji.name}
					class="size-5 flex-shrink-0"
					loading="lazy"
				/>
				<div class="truncate text-sm">
					:{emoji.shortCodes[0]}:
				</div>
			</div>
		</button>
	{/each}
{/if}
