<script lang="ts">
	import { DropdownMenu } from 'bits-ui';
	import { flyAndScale } from '$lib/utils/transitions';

	import emojiGroups from '$lib/emoji-groups.json';
	import emojiShortCodes from '$lib/emoji-shortcodes.json';
	import Tooltip from '$lib/components/common/Tooltip.svelte';

	export let onClose = () => {};
	export let side = 'top';
	export let align = 'start';

	export let user = null;
	let show = false;

	let emojis = emojiShortCodes;
	let search = '';

	$: if (search) {
		emojis = Object.keys(emojiShortCodes).reduce((acc, key) => {
			if (key.includes(search)) {
				acc[key] = emojiShortCodes[key];
			} else {
				if (Array.isArray(emojiShortCodes[key])) {
					const filtered = emojiShortCodes[key].filter((emoji) => emoji.includes(search));
					if (filtered.length) {
						acc[key] = filtered;
					}
				} else {
					if (emojiShortCodes[key].includes(search)) {
						acc[key] = emojiShortCodes[key];
					}
				}
			}

			return acc;
		}, {});
	} else {
		emojis = emojiShortCodes;
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

	<slot name="content">
		<DropdownMenu.Content
			class="max-w-full  w-80  bg-gray-50 dark:bg-gray-850 rounded-lg z-50 shadow-lg text-white"
			sideOffset={8}
			{side}
			{align}
			transition={flyAndScale}
		>
			<div class="mb-1 px-3 pt-2 pb-2">
				<input
					type="text"
					class="w-full text-sm bg-transparent outline-none"
					placeholder="Search all emojis"
					bind:value={search}
				/>
			</div>
			<div class=" w-full flex justify-start h-96 overflow-y-auto px-3 pb-3 text-sm">
				<div>
					{#if Object.keys(emojis).length === 0}
						<div class="text-center text-xs text-gray-500 dark:text-gray-400">No results</div>
					{:else}
						{#each Object.keys(emojiGroups) as group}
							{@const groupEmojis = emojiGroups[group].filter((emoji) => emojis[emoji])}
							{#if groupEmojis.length > 0}
								<div class="flex flex-col">
									<div class="text-xs font-medium mb-2 text-gray-500 dark:text-gray-400">
										{group}
									</div>

									<div class="flex mb-2 flex-wrap gap-1">
										{#each groupEmojis as emoji}
											<Tooltip
												content={(typeof emojiShortCodes[emoji] === 'string'
													? [emojiShortCodes[emoji]]
													: emojiShortCodes[emoji]
												)
													.map((code) => `:${code}:`)
													.join(', ')}
												placement="top"
											>
												<div
													class="p-1.5 rounded-lg cursor-pointer hover:bg-gray-200 dark:hover:bg-gray-700 transition"
												>
													<img
														src="/assets/emojis/{emoji.toLowerCase()}.svg"
														alt={emoji}
														class="size-5"
														loading="lazy"
													/>
												</div>
											</Tooltip>
										{/each}
									</div>
								</div>
							{/if}
						{/each}
					{/if}
				</div>
			</div>
		</DropdownMenu.Content>
	</slot>
</DropdownMenu.Root>
