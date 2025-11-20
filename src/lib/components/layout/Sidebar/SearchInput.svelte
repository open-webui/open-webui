<script lang="ts">
	import { getAllTags } from '$lib/apis/chats';
	import { folders, tags } from '$lib/stores';
	import { getContext, createEventDispatcher, onMount, onDestroy, tick } from 'svelte';
	import { fade } from 'svelte/transition';
	import Search from '$lib/components/icons/Search.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';

	const dispatch = createEventDispatcher();
	const i18n = getContext('i18n');

	export let placeholder = '';
	export let value = '';
	export let showClearButton = false;

	export let onFocus = () => {};
	export let onKeydown = (e) => {};

	let selectedIdx = 0;
	let selectedOption = null;

	let lastWord = '';
	$: lastWord = value ? value.split(' ').at(-1) : value;

	let options = [
		{
			name: 'tag:',
			description: $i18n.t('search for tags')
		},
		{
			name: 'folder:',
			description: $i18n.t('search for folders')
		},
		{
			name: 'pinned:',
			description: $i18n.t('search for pinned chats')
		},
		{
			name: 'shared:',
			description: $i18n.t('search for shared chats')
		},
		{
			name: 'archived:',
			description: $i18n.t('search for archived chats')
		}
	];
	let focused = false;
	let loading = false;

	let hovering = false;

	let filteredOptions = options;
	$: filteredOptions = options.filter((option) => {
		return option.name.startsWith(lastWord);
	});

	let filteredItems = [];

	$: if (lastWord && lastWord !== null) {
		initItems();
	}

	const initItems = async () => {
		console.log('initItems', lastWord);
		loading = true;
		await tick();

		if (lastWord.startsWith('tag:')) {
			filteredItems = [
				...$tags,
				{
					id: 'none',
					name: $i18n.t('Untagged')
				}
			]
				.filter((tag) => {
					const tagName = lastWord.slice(4);
					if (tagName) {
						const tagId = tagName.replaceAll(' ', '_').toLowerCase();

						if (tag.id !== tagId) {
							return tag.id.startsWith(tagId);
						} else {
							return false;
						}
					} else {
						return true;
					}
				})
				.map((tag) => {
					return {
						id: tag.id,
						name: tag.name,
						type: 'tag'
					};
				});
		} else if (lastWord.startsWith('folder:')) {
			filteredItems = [...$folders]
				.filter((folder) => {
					const folderName = lastWord.slice(7);
					if (folderName) {
						const id = folder.name.replaceAll(' ', '_').toLowerCase();
						const folderId = folderName.replaceAll(' ', '_').toLowerCase();

						if (id !== folderId) {
							return id.startsWith(folderId);
						} else {
							return false;
						}
					} else {
						return true;
					}
				})
				.map((folder) => {
					return {
						id: folder.name.replaceAll(' ', '_').toLowerCase(),
						name: folder.name,
						type: 'folder'
					};
				});
		} else if (lastWord.startsWith('pinned:')) {
			filteredItems = [
				{
					id: 'true',
					name: 'true',
					type: 'pinned'
				},
				{
					id: 'false',
					name: 'false',
					type: 'pinned'
				}
			].filter((item) => {
				const pinnedValue = lastWord.slice(7);
				if (pinnedValue) {
					return item.id.startsWith(pinnedValue) && item.id !== pinnedValue;
				} else {
					return true;
				}
			});
		} else if (lastWord.startsWith('shared:')) {
			filteredItems = [
				{
					id: 'true',
					name: 'true',
					type: 'shared'
				},
				{
					id: 'false',
					name: 'false',
					type: 'shared'
				}
			].filter((item) => {
				const sharedValue = lastWord.slice(7);
				if (sharedValue) {
					return item.id.startsWith(sharedValue) && item.id !== sharedValue;
				} else {
					return true;
				}
			});
		} else if (lastWord.startsWith('archived:')) {
			filteredItems = [
				{
					id: 'true',
					name: 'true',
					type: 'archived'
				},
				{
					id: 'false',
					name: 'false',
					type: 'archived'
				}
			].filter((item) => {
				const archivedValue = lastWord.slice(9);
				if (archivedValue) {
					return item.id.startsWith(archivedValue) && item.id !== archivedValue;
				} else {
					return true;
				}
			});
		} else {
			filteredItems = [];
		}

		loading = false;
	};

	const initTags = async () => {
		loading = true;

		await tags.set(await getAllTags(localStorage.token));
		loading = false;
	};

	const clearSearchInput = () => {
		value = '';
		dispatch('input');
	};
</script>

<div class="px-1 mb-1 flex justify-center space-x-2 relative z-10" id="search-container">
	<div class="flex w-full rounded-xl" id="chat-search">
		<div class="self-center py-2 rounded-l-xl bg-transparent dark:text-gray-300">
			<Search />
		</div>

		<input
			id="search-input"
			class="w-full rounded-r-xl py-1.5 pl-2.5 text-sm bg-transparent dark:text-gray-300 outline-hidden"
			placeholder={placeholder ? placeholder : $i18n.t('Search')}
			autocomplete="off"
			bind:value
			on:input={() => {
				dispatch('input');
			}}
			on:click={() => {
				if (!focused) {
					onFocus();
					hovering = false;

					focused = true;
					initTags();
				}
			}}
			on:blur={() => {
				if (!hovering) {
					focused = false;
				}
			}}
			on:keydown={(e) => {
				if (e.key === 'Enter') {
					if (filteredItems.length > 0) {
						const itemElement = document.getElementById(`search-item-${selectedIdx}`);
						itemElement.click();
						return;
					}

					if (filteredOptions.length > 0) {
						const optionElement = document.getElementById(`search-option-${selectedIdx}`);
						optionElement.click();
						return;
					}
				}

				if (e.key === 'ArrowUp') {
					e.preventDefault();
					selectedIdx = Math.max(0, selectedIdx - 1);
				} else if (e.key === 'ArrowDown') {
					e.preventDefault();

					if (filteredItems.length > 0) {
						if (selectedIdx === filteredItems.length - 1) {
							focused = false;
						} else {
							selectedIdx = Math.min(selectedIdx + 1, filteredItems.length - 1);
						}
					} else {
						if (selectedIdx === filteredOptions.length - 1) {
							focused = false;
						} else {
							selectedIdx = Math.min(selectedIdx + 1, filteredOptions.length - 1);
						}
					}
				} else {
					// if the user types something, reset to the top selection.
					if (!focused) {
						onFocus();
						hovering = false;

						focused = true;
						initTags();
					}

					selectedIdx = 0;
				}

				const item = document.querySelector(`[data-selected="true"]`);
				item?.scrollIntoView({ block: 'center', inline: 'nearest', behavior: 'instant' });

				if (!document.getElementById('search-options-container')) {
					onKeydown(e);
				}
			}}
		/>

		{#if showClearButton && value}
			<div class="self-center pl-1.5 translate-y-[0.5px] rounded-l-xl bg-transparent">
				<button
					class="p-0.5 rounded-full hover:bg-gray-100 dark:hover:bg-gray-900 transition"
					on:click={clearSearchInput}
				>
					<XMark className="size-3" strokeWidth="2" />
				</button>
			</div>
		{/if}
	</div>

	{#if focused && (filteredOptions.length > 0 || filteredItems.length > 0)}
		<!-- svelte-ignore a11y-no-static-element-interactions -->
		<div
			class="absolute top-0 mt-8 left-0 right-1 border border-gray-100 dark:border-gray-900 bg-gray-50 dark:bg-gray-950 rounded-2xl z-10 shadow-lg"
			id="search-options-container"
			in:fade={{ duration: 50 }}
			on:mouseenter={() => {
				hovering = true;
				selectedIdx = null;
			}}
			on:mouseleave={() => {
				hovering = false;
				selectedIdx = 0;
			}}
		>
			<div class="px-3 py-2.5 text-xs group">
				{#if filteredItems.length > 0}
					<div class="px-1 font-medium dark:text-gray-300 text-gray-700 mb-1 capitalize">
						{selectedOption}
					</div>

					<div class="max-h-60 overflow-auto">
						{#each filteredItems as item, itemIdx}
							<button
								class=" px-1.5 py-0.5 flex gap-1 hover:bg-gray-100 dark:hover:bg-gray-900 w-full rounded {selectedIdx ===
								itemIdx
									? 'bg-gray-100 dark:bg-gray-900'
									: ''}"
								data-selected={selectedIdx === itemIdx}
								id="search-item-{itemIdx}"
								on:click|stopPropagation={async () => {
									const words = value.split(' ');

									words.pop();
									words.push(`${item.type}:${item.id} `);

									value = words.join(' ');

									filteredItems = [];
									dispatch('input');
								}}
							>
								<div class="dark:text-gray-300 text-gray-700 font-medium line-clamp-1 shrink-0">
									{item.name}
								</div>

								<div class=" text-gray-500 line-clamp-1">
									{item.id}
								</div>
							</button>
						{/each}
					</div>
				{:else if filteredOptions.length > 0}
					<div class="px-1 font-medium dark:text-gray-300 text-gray-700 mb-1">
						{$i18n.t('Search options')}
					</div>

					<div class=" max-h-60 overflow-auto">
						{#each filteredOptions as option, optionIdx}
							<button
								class=" px-1.5 py-0.5 flex gap-1 hover:bg-gray-100 dark:hover:bg-gray-900 w-full rounded {selectedIdx ===
								optionIdx
									? 'bg-gray-100 dark:bg-gray-900'
									: ''}"
								id="search-option-{optionIdx}"
								on:click|stopPropagation={async () => {
									const words = value.split(' ');

									words.pop();
									words.push(`${option.name}`);

									selectedOption = option.name.replace(':', '');

									value = words.join(' ');

									dispatch('input');
								}}
							>
								<div class="dark:text-gray-300 text-gray-700 font-medium">{option.name}</div>

								<div class=" text-gray-500 line-clamp-1">
									{option.description}
								</div>
							</button>
						{/each}
					</div>
				{/if}
			</div>
		</div>
	{/if}
</div>
