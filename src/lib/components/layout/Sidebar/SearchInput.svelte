<script lang="ts">
	import { getAllTags } from '$lib/apis/chats';
	import { tags } from '$lib/stores';
	import { getContext, createEventDispatcher, onMount, onDestroy, tick } from 'svelte';
	import { fade } from 'svelte/transition';
	import XMark from '$lib/components/icons/XMark.svelte';

	const dispatch = createEventDispatcher();
	const i18n = getContext('i18n');

	export let placeholder = '';
	export let value = '';
	export let showClearButton = false;
	export let onKeydown = (e) => {};

	let selectedIdx = 0;

	let lastWord = '';
	$: lastWord = value ? value.split(' ').at(-1) : value;

	let options = [
		{
			name: 'tag:',
			description: $i18n.t('search for tags')
		},
		{
			name: 'before:',
			description: $i18n.t('Search for chats updated before a date (YYYY-MM-DD)')
		},
		{
			name: 'after:',
			description: $i18n.t('Search for chats updated after a date (YYYY-MM-DD)')
		}
	];
	let focused = false;
	let loading = false;

	let filteredOptions = options;
	$: filteredOptions = lastWord.includes(':')
		? []
		: options.filter((option) => {
				return option.name.startsWith(lastWord);
			});

	let filteredTags = [];
	$: filteredTags = lastWord.startsWith('tag:')
		? [
				...$tags,
				{
					id: 'none',
					name: $i18n.t('Untagged')
				}
			].filter((tag) => {
				const tagName = lastWord.slice(4);
				if (tagName) {
					const tagId = tagName.replace(' ', '_').toLowerCase();

					if (tag.id !== tagId) {
						return tag.id.startsWith(tagId);
					} else {
						return false;
					}
				} else {
					return true;
				}
			})
		: [];

	let filteredDateSuggestions = [];
	$: {
		if (lastWord.startsWith('before:') || lastWord.startsWith('after:')) {
			const dateQuery = lastWord.split(':')[1];
			if (dateQuery === '' || /^\d{4}(-\d{0,2}(-\d{0,2})?)?$/.test(dateQuery)) {
				filteredDateSuggestions = [
					{ id: 'format', name: 'YYYY-MM-DD', description: $i18n.t('Enter date as YYYY-MM-DD') }
				];
			} else {
				filteredDateSuggestions = [];
			}
		} else {
			filteredDateSuggestions = [];
		}
	}

	const initTags = async () => {
		loading = true;
		await tags.set(await getAllTags(localStorage.token));
		loading = false;
	};

	const clearSearchInput = () => {
		value = '';
		dispatch('input');
	};

	const documentClickHandler = (e) => {
		const searchContainer = document.getElementById('search-container');
		const chatSearch = document.getElementById('chat-search');

		if (!searchContainer.contains(e.target) && !chatSearch.contains(e.target)) {
			if (e.target.id.startsWith('search-tag-') || e.target.id.startsWith('search-option-')) {
				return;
			}
			focused = false;
		}
	};

	onMount(() => {
		document.addEventListener('click', documentClickHandler);
	});

	onDestroy(() => {
		document.removeEventListener('click', documentClickHandler);
	});
</script>

<div class="px-1 mb-1 flex justify-center space-x-2 relative z-10" id="search-container">
	<div class="flex w-full rounded-xl" id="chat-search">
		<div class="self-center py-2 rounded-l-xl bg-transparent dark:text-gray-300">
			<svg
				xmlns="http://www.w3.org/2000/svg"
				viewBox="0 0 20 20"
				fill="currentColor"
				class="w-4 h-4"
			>
				<path
					fill-rule="evenodd"
					d="M9 3.5a5.5 5.5 0 100 11 5.5 5.5 0 000-11zM2 9a7 7 0 1112.452 4.391l3.328 3.329a.75.75 0 11-1.06 1.06l-3.329-3.328A7 7 0 012 9z"
					clip-rule="evenodd"
				/>
			</svg>
		</div>

		<input
			class="w-full rounded-r-xl py-1.5 pl-2.5 text-sm bg-transparent dark:text-gray-300 outline-hidden"
			placeholder={placeholder ? placeholder : $i18n.t('Search')}
			bind:value
			on:input={() => {
				dispatch('input');
			}}
			on:focus={() => {
				focused = true;
				initTags();
			}}
			on:keydown={(e) => {
				if (e.key === 'Enter') {
					if (filteredTags.length > 0) {
						const tagElement = document.getElementById(`search-tag-${selectedIdx}`);
				tagElement?.click();
						return;
			} else if (filteredDateSuggestions.length > 0 && selectedIdx < filteredDateSuggestions.length) {
				const dateSuggestionElement = document.getElementById(`search-date-${selectedIdx}`);
				dateSuggestionElement?.click();
				return;
			} else if (filteredOptions.length > 0) {
				const optionElement = document.getElementById(
					`search-option-${selectedIdx - filteredDateSuggestions.length}`
				);
				optionElement?.click();
						return;
					}
				}

				if (e.key === 'ArrowUp') {
					e.preventDefault();
					selectedIdx = Math.max(0, selectedIdx - 1);
				} else if (e.key === 'ArrowDown') {
					e.preventDefault();
			const totalSuggestions =
				filteredOptions.length + filteredTags.length + filteredDateSuggestions.length;
			selectedIdx = Math.min(selectedIdx + 1, totalSuggestions - 1);
				} else {
					// if the user types something, reset to the top selection.
					selectedIdx = 0;
				}

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

	{#if focused && (filteredOptions.length > 0 || filteredTags.length > 0 || filteredDateSuggestions.length > 0)}
		<!-- svelte-ignore a11y-no-static-element-interactions -->
		<div
			class="absolute top-0 mt-8 left-0 right-1 border border-gray-100 dark:border-gray-900 bg-gray-50 dark:bg-gray-950 rounded-lg z-10 shadow-lg"
			id="search-options-container"
			in:fade={{ duration: 50 }}
			on:mouseenter={() => {
				selectedIdx = null;
			}}
			on:mouseleave={() => {
				selectedIdx = 0;
			}}
		>
			<div class="px-2 py-2 text-xs group">
				{#if filteredTags.length > 0}
					<div class="px-1 font-medium dark:text-gray-300 text-gray-700 mb-1">Tags</div>
					<div class="max-h-60 overflow-auto">
						{#each filteredTags as tag, tagIdx}
							<button
								class=" px-1.5 py-0.5 flex gap-1 hover:bg-gray-100 dark:hover:bg-gray-900 w-full rounded {selectedIdx ===
								tagIdx
									? 'bg-gray-100 dark:bg-gray-900'
									: ''}"
								id="search-tag-{tagIdx}"
								on:click|stopPropagation={async () => {
									const words = value.split(' ');
									words.pop();
									words.push(`tag:${tag.id} `);
									value = words.join(' ');
									dispatch('input');
									await tick();
									focused = false;
								}}
							>
								<div class="dark:text-gray-300 text-gray-700 font-medium line-clamp-1 shrink-0">
									{tag.name}
								</div>
								<div class=" text-gray-500 line-clamp-1">
									{tag.id}
								</div>
							</button>
						{/each}
					</div>
				{:else if filteredDateSuggestions.length > 0}
					<div class="px-1 font-medium dark:text-gray-300 text-gray-700 mb-1">
						{$i18n.t('Date Format')}
					</div>
					<div class="max-h-60 overflow-auto">
						{#each filteredDateSuggestions as suggestion, dateIdx}
							<button
								class=" px-1.5 py-0.5 flex gap-1 hover:bg-gray-100 dark:hover:bg-gray-900 w-full rounded {selectedIdx ===
								dateIdx
									? 'bg-gray-100 dark:bg-gray-900'
									: ''}"
								id="search-date-{dateIdx}"
								on:click|stopPropagation={async () => {
									const words = value.split(' ');
									let currentParam = words.pop();
									// Ensure the parameter itself (e.g., "before:") is fully present and add a space
									if (!currentParam.endsWith(':')) {
										currentParam += ':';
									}
									words.push(`${currentParam} `);
									value = words.join(' ');
									dispatch('input');
									await tick();
									// Keep focus to allow user to type the date
									const inputElement = document.querySelector<HTMLInputElement>('#chat-search input');
									inputElement?.focus();
									// focused = true; // Re-ensure focused state if needed
								}}
							>
								<div class="dark:text-gray-300 text-gray-700 font-medium">
									{suggestion.name}
								</div>
								<div class=" text-gray-500 line-clamp-1">
									{suggestion.description}
								</div>
							</button>
						{/each}
					</div>
				{:else if filteredOptions.length > 0}
					<div class="px-1 font-medium dark:text-gray-300 text-gray-700 mb-1">
						{$i18n.t('Search options')}
					</div>
					<div class="max-h-60 overflow-auto">
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
									words.push(option.name); // Keep the colon, e.g., "after:"
									value = words.join(' ');
									dispatch('input');
									await tick();
									// Ensure input remains focused to trigger next suggestions if applicable
									const inputElement = document.querySelector<HTMLInputElement>('#chat-search input');
									inputElement?.focus();
									focused = true;
								}}
							>
								<div class="dark:text-gray-300 text-gray-700 font-medium">
									{option.name}
								</div>
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
