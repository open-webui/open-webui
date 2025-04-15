<script lang="ts">
	import { getAllTags } from '$lib/apis/chats';
	import { tags } from '$lib/stores';
	import { getContext, createEventDispatcher, onMount, onDestroy } from 'svelte';
	import { fade } from 'svelte/transition';

	const dispatch = createEventDispatcher();
	const i18n = getContext('i18n');

	export let placeholder = '';
	export let value = '';

	let selectedIdx = 0;

	let lastWord = '';
	$: lastWord = value ? value.split(' ').at(-1) : value;

	// Get the tag prefix based on locale from translations and add colon
	$: primaryTagPrefix = `${$i18n.t('tag')}:`;

	// Create reactive options based on current locale
	$: options = [
		{
			name: primaryTagPrefix,
			description: $i18n.t('search for tags')
		}
	];

	// Update tag prefixes based on current locale translations
	$: tagPrefixes =
		$i18n.language === 'fr-CA'
			? ['étiquette:', 'tag:'] // Keep both for backwards compatibility
			: ['tag:', 'étiquette:']; // Keep both for backwards compatibility

	// Watch for locale changes and update existing tag prefixes in the search value
	$: if (value && $i18n.language) {
		// Get the current primary prefix and old prefixes
		const oldPrefixes =
			$i18n.language === 'fr-CA'
				? ['tag:', 'étiquette:'] // If now in French, look for English prefixes
				: ['étiquette:', 'tag:']; // If now in English, look for French prefixes

		// Replace any old prefixes with the new primary prefix
		const words = value.split(' ');
		const updatedWords = words.map((word) => {
			if (oldPrefixes.some((prefix) => word.startsWith(prefix))) {
				// Extract the tag ID after the old prefix
				const tagId = word.slice(word.indexOf(':') + 1);
				// Replace with new prefix
				return `${primaryTagPrefix}${tagId}`;
			}
			return word;
		});
		value = updatedWords.join(' ');
	}

	let focused = false;
	let loading = false;

	let filteredOptions = options;
	$: filteredOptions = options.filter((option) => {
		return option.name.startsWith(lastWord);
	});

	// Update the filtering logic to check for any valid tag prefix
	$: filteredTags = tagPrefixes.some((prefix) => lastWord.startsWith(prefix))
		? [
				...$tags,
				{
					id: 'none',
					name: $i18n.t('Untagged')
				}
			].filter((tag) => {
				// Extract tag name after any of the valid prefixes
				const tagName = tagPrefixes.reduce((name, prefix) => {
					if (lastWord.startsWith(prefix)) {
						return lastWord.slice(prefix.length);
					}
					return name;
				}, '');

				if (tagName) {
					// Normalize the search tag ID
					const searchTagId = tagName.trim().replace(' ', '_').toLowerCase();
					// Compare with the actual tag ID
					if (tag.id !== searchTagId) {
						return tag.id.startsWith(searchTagId);
					}
					return false;
				}
				return true;
			})
		: [];

	const initTags = async () => {
		loading = true;
		await tags.set(await getAllTags(localStorage.token));
		loading = false;
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

	// Handle storage events for locale changes
	const handleStorageChange = (event) => {
		if (event?.detail?.locale || (event?.key === 'locale' && event?.newValue)) {
			// Force options and tagPrefixes to update by triggering reactivity
			options = [
				{
					name: primaryTagPrefix,
					description: $i18n.t('search for tags')
				}
			];
		}
	};

	onMount(() => {
		// Listen for both custom event and storage event
		window.addEventListener('storage', handleStorageChange);
		document.addEventListener('click', documentClickHandler);
	});

	onDestroy(() => {
		window.removeEventListener('storage', handleStorageChange);
		document.removeEventListener('click', documentClickHandler);
	});
</script>

<div class="px-1 mb-1 flex justify-center space-x-2 relative z-10" id="search-container">
	<div class="flex w-full rounded-xl" id="chat-search">
		<div class="self-center pl-3 py-2 rounded-l-xl bg-transparent">
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
			class="w-full rounded-r-xl py-1.5 pl-2.5 placeholder-[#5C6B8B] text-sm bg-transparent dark:text-gray-300 focus:outline-1 focus:outline-black dark:focus:outline-white"
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
						tagElement.click();
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

					if (filteredTags.length > 0) {
						selectedIdx = Math.min(selectedIdx + 1, filteredTags.length - 1);
					} else {
						selectedIdx = Math.min(selectedIdx + 1, filteredOptions.length - 1);
					}
				} else {
					// if the user types something, reset to the top selection.
					selectedIdx = 0;
				}
			}}
		/>
	</div>

	{#if focused && (filteredOptions.length > 0 || filteredTags.length > 0)}
		<!-- svelte-ignore a11y-no-static-element-interactions -->
		<div
			class="absolute top-0 mt-8 left-0 right-1 border dark:border-gray-900 bg-gray-50 dark:bg-gray-950 rounded-lg z-10 shadow-lg"
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
					<div class="px-1 font-medium dark:text-gray-300 text-gray-700 mb-1">
						{$i18n.t('Tags')}
					</div>

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
									words.push(`${primaryTagPrefix}${tag.id} `);

									value = words.join(' ');

									dispatch('input');
								}}
							>
								<div
									class="dark:text-gray-300 text-gray-700 font-medium line-clamp-1 flex-shrink-0"
								>
									{tag.name}
								</div>

								<div class=" text-gray-500 line-clamp-1">
									{tag.id}
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
									words.push(`${primaryTagPrefix}`);

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
