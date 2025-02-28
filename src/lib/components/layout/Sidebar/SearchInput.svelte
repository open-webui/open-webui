<script lang="ts">
	import { run, stopPropagation } from 'svelte/legacy';

	import { getAllTags } from '$lib/apis/chats';
	import { tags } from '$lib/stores';
	import { getContext, createEventDispatcher, onMount, onDestroy, tick } from 'svelte';
	import { fade } from 'svelte/transition';

	const dispatch = createEventDispatcher();
	const i18n = getContext('i18n');

	interface Props {
		placeholder?: string;
		value?: string;
	}

	let { placeholder = '', value = $bindable('') }: Props = $props();

	let selectedIdx = $state(0);

	let lastWord = $state('');
	run(() => {
		lastWord = value ? value.split(' ').at(-1) : value;
	});

	const options = [
		{
			name: 'tag:',
			description: $i18n.t('search for tags')
		}
	];
	let focused = $state(false);
	let loading = false;

	let filteredOptions = $state(options);
	run(() => {
		filteredOptions = options.filter((option) => {
			return option.name.startsWith(lastWord);
		});
	});

	let filteredTags = $state([]);
	run(() => {
		filteredTags = lastWord.startsWith('tag:')
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
	});

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

	onMount(() => {
		document.addEventListener('click', documentClickHandler);
	});

	onDestroy(() => {
		document.removeEventListener('click', documentClickHandler);
	});
</script>

<div id="search-container" class="px-1 mb-1 flex justify-center space-x-2 relative z-10">
	<div id="chat-search" class="flex w-full rounded-xl">
		<div class="self-center pl-3 py-2 rounded-l-xl bg-transparent">
			<svg
				class="w-4 h-4"
				fill="currentColor"
				viewBox="0 0 20 20"
				xmlns="http://www.w3.org/2000/svg"
			>
				<path
					clip-rule="evenodd"
					d="M9 3.5a5.5 5.5 0 100 11 5.5 5.5 0 000-11zM2 9a7 7 0 1112.452 4.391l3.328 3.329a.75.75 0 11-1.06 1.06l-3.329-3.328A7 7 0 012 9z"
					fill-rule="evenodd"
				/>
			</svg>
		</div>

		<input
			class="w-full rounded-r-xl py-1.5 pl-2.5 pr-4 text-sm bg-transparent dark:text-gray-300 outline-hidden"
			onfocus={() => {
				focused = true;
				initTags();
			}}
			oninput={() => {
				dispatch('input');
			}}
			onkeydown={(e) => {
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
			placeholder={placeholder ? placeholder : $i18n.t('Search')}
			bind:value
		/>
	</div>

	{#if focused && (filteredOptions.length > 0 || filteredTags.length > 0)}
		<!-- svelte-ignore a11y_no_static_element_interactions -->
		<div
			class="absolute top-0 mt-8 left-0 right-1 border dark:border-gray-900 bg-gray-50 dark:bg-gray-950 rounded-lg z-10 shadow-lg"
			onmouseenter={() => {
				selectedIdx = null;
			}}
			onmouseleave={() => {
				selectedIdx = 0;
			}}
			in:fade={{ duration: 50 }}
		>
			<div class="px-2 py-2 text-xs group">
				{#if filteredTags.length > 0}
					<div class="px-1 font-medium dark:text-gray-300 text-gray-700 mb-1">Tags</div>

					<div class="max-h-60 overflow-auto">
						{#each filteredTags as tag, tagIdx}
							<button
								id="search-tag-{tagIdx}"
								class=" px-1.5 py-0.5 flex gap-1 hover:bg-gray-100 dark:hover:bg-gray-900 w-full rounded {selectedIdx ===
								tagIdx
									? 'bg-gray-100 dark:bg-gray-900'
									: ''}"
								onclick={stopPropagation(async () => {
									const words = value.split(' ');

									words.pop();
									words.push(`tag:${tag.id} `);

									value = words.join(' ');

									dispatch('input');
								})}
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
				{:else if filteredOptions.length > 0}
					<div class="px-1 font-medium dark:text-gray-300 text-gray-700 mb-1">
						{$i18n.t('Search options')}
					</div>

					<div class=" max-h-60 overflow-auto">
						{#each filteredOptions as option, optionIdx}
							<button
								id="search-option-{optionIdx}"
								class=" px-1.5 py-0.5 flex gap-1 hover:bg-gray-100 dark:hover:bg-gray-900 w-full rounded {selectedIdx ===
								optionIdx
									? 'bg-gray-100 dark:bg-gray-900'
									: ''}"
								onclick={stopPropagation(async () => {
									const words = value.split(' ');

									words.pop();
									words.push('tag:');

									value = words.join(' ');

									dispatch('input');
								})}
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
