<script lang="ts">
	import { DropdownMenu } from 'bits-ui';
	import VirtualList from '@sveltejs/svelte-virtual-list';

	import { getContext } from 'svelte';

	import { flyAndScale } from '$lib/utils/transitions';
	import { WEBUI_BASE_URL } from '$lib/constants';

	import Tooltip from '$lib/components/common/Tooltip.svelte';

	import emojiGroups from '$lib/emoji-groups.json';
	import emojiShortCodes from '$lib/emoji-shortcodes.json';

	const i18n = getContext('i18n');

	export let onClose = () => {};
	export let onSubmit = (name) => {};
	export let side = 'top';
	export let align = 'start';
	export let user = null;

	let show = false;
	let emojis = emojiShortCodes;
	let search = '';
	let flattenedEmojis = [];
	let emojiRows = [];

	// Reactive statement to filter the emojis based on search query
	$: {
		if (search) {
			emojis = Object.keys(emojiShortCodes).reduce((acc, key) => {
				if (key.includes(search.toLowerCase())) {
					acc[key] = emojiShortCodes[key];
				} else {
					if (Array.isArray(emojiShortCodes[key])) {
						const filtered = emojiShortCodes[key].filter((emoji) =>
							emoji.includes(search.toLowerCase())
						);
						if (filtered.length) {
							acc[key] = filtered;
						}
					} else {
						if (emojiShortCodes[key].includes(search.toLowerCase())) {
							acc[key] = emojiShortCodes[key];
						}
					}
				}
				return acc;
			}, {});
		} else {
			emojis = emojiShortCodes;
		}
	}
	// Flatten emoji groups and group them into rows of 8 for virtual scrolling
	$: {
		flattenedEmojis = [];
		Object.keys(emojiGroups).forEach((group) => {
			const groupEmojis = emojiGroups[group].filter((emoji) => emojis[emoji]);
			if (groupEmojis.length > 0) {
				flattenedEmojis.push({ type: 'group', label: group });
				flattenedEmojis.push(
					...groupEmojis.map((emoji) => ({
						type: 'emoji',
						name: emoji,
						shortCodes:
							typeof emojiShortCodes[emoji] === 'string'
								? [emojiShortCodes[emoji]]
								: emojiShortCodes[emoji]
					}))
				);
			}
		});
		// Group emojis into rows of 8
		emojiRows = [];
		let currentRow = [];
		flattenedEmojis.forEach((item) => {
			if (item.type === 'emoji') {
				currentRow.push(item);
				if (currentRow.length === 8) {
					emojiRows.push(currentRow);
					currentRow = [];
				}
			} else if (item.type === 'group') {
				if (currentRow.length > 0) {
					emojiRows.push(currentRow); // Push the remaining row
					currentRow = [];
				}
				emojiRows.push([item]); // Add the group label as a separate row
			}
		});
		if (currentRow.length > 0) {
			emojiRows.push(currentRow); // Push the final row
		}
	}
	const ROW_HEIGHT = 48; // Approximate height for a row with multiple emojis
	// Handle emoji selection
	function selectEmoji(emoji) {
		const selectedCode = emoji.shortCodes[0];
		onSubmit(selectedCode);
		show = false;
	}
</script>

<DropdownMenu.Root
	bind:open={show}
	closeFocus={false}
	onOpenChange={(state) => {
		if (!state) {
			search = '';
			onClose();
		}
	}}
	typeahead={false}
>
	<DropdownMenu.Trigger>
		<slot />
	</DropdownMenu.Trigger>
	<DropdownMenu.Content
		class="max-w-full w-80 bg-gray-50 dark:bg-gray-850 rounded-lg z-9999 shadow-lg dark:text-white"
		sideOffset={8}
		{side}
		{align}
		transition={flyAndScale}
	>
		<div class="mb-1 px-3 pt-2 pb-2">
			<input
				type="text"
				class="w-full text-sm bg-transparent outline-hidden"
				placeholder={$i18n.t('Search all emojis')}
				bind:value={search}
			/>
		</div>
		<!-- Virtualized Emoji List -->
		<div class="w-full flex justify-start h-96 overflow-y-auto px-3 pb-3 text-sm">
			{#if emojiRows.length === 0}
				<div class="text-center text-xs text-gray-500 dark:text-gray-400">
					{$i18n.t('No results')}
				</div>
			{:else}
				<div class="w-full flex ml-0.5">
					<VirtualList rowHeight={ROW_HEIGHT} items={emojiRows} height={384} let:item>
						<div class="w-full">
							{#if item.length === 1 && item[0].type === 'group'}
								<!-- Render group header -->
								<div class="text-xs font-medium mb-2 text-gray-500 dark:text-gray-400">
									{item[0].label}
								</div>
							{:else}
								<!-- Render emojis in a row -->
								<div class="flex items-center gap-1.5 w-full">
									{#each item as emojiItem}
										<Tooltip
											content={emojiItem.shortCodes.map((code) => `:${code}:`).join(', ')}
											placement="top"
										>
											<button
												class="p-1.5 rounded-lg cursor-pointer hover:bg-gray-200 dark:hover:bg-gray-700 transition"
												on:click={() => selectEmoji(emojiItem)}
											>
												<img
													src="{WEBUI_BASE_URL}/assets/emojis/{emojiItem.name.toLowerCase()}.svg"
													alt={emojiItem.name}
													class="size-5"
													loading="lazy"
												/>
											</button>
										</Tooltip>
									{/each}
								</div>
							{/if}
						</div>
					</VirtualList>
				</div>
			{/if}
		</div>
	</DropdownMenu.Content>
</DropdownMenu.Root>
