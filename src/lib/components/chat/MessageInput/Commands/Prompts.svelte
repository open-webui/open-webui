<script lang="ts">
	import { prompts, user } from '$lib/stores';
	import { getPrompts } from '$lib/apis/prompts';
	import {
		findWordIndices,
		getUserPosition,
		getFormattedDate,
		getFormattedTime,
		getCurrentDateTime,
		getUserTimezone,
		getWeekday
	} from '$lib/utils';
	import { tick, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';

	const i18n = getContext('i18n');

	export let files;

	export let prompt = '';
	export let command = '';

	let selectedPromptIdx = 0;
	let filteredPrompts = [];
	let loadedPrompts = [];
	let currentPage = 1;
	let isLoading = false;
	let hasMorePrompts = true;
	const pageSize = 20;

	// Debounced search for dynamic loading
	let searchTimeout;
	let lastCommand = '';
	let currentSearch = '';
	let isInitialized = false;

	// Load prompts dynamically based on search
	const loadPrompts = async (search = '', page = 1, append = false) => {
		if (isLoading) return;

		isLoading = true;

		// Update current search when starting a new search (not appending)
		if (!append) {
			currentSearch = search;
		}

		try {
			const newPrompts = await getPrompts(localStorage.token, {
				page,
				limit: pageSize,
				search: search || undefined
			});

			if (append) {
				loadedPrompts = [...loadedPrompts, ...newPrompts];
			} else {
				loadedPrompts = newPrompts;
				currentPage = 1; // Reset page counter for new search
			}

			hasMorePrompts = newPrompts.length === pageSize;
		} catch (error) {
			console.error('Error loading prompts:', error);
			// Fallback to global store on error
			loadedPrompts = $prompts.filter(
				(p) => !search || p.command.toLowerCase().includes(search.toLowerCase())
			);
			hasMorePrompts = false;
		} finally {
			isLoading = false;
		}
	};

	// Load more prompts when scrolling near bottom
	const loadMorePrompts = async () => {
		if (hasMorePrompts && !isLoading) {
			currentPage++;
			await loadPrompts(currentSearch, currentPage, true);
		}
	};

	// Reactive filtering with dynamic loading
	$: {
		// Clear timeout if exists
		if (searchTimeout) clearTimeout(searchTimeout);

		// Only trigger new search if command actually changed
		if (command !== lastCommand) {
			lastCommand = command;

			// Extract search term from command (remove the leading /)
			const searchTerm = command.startsWith('/') ? command.slice(1) : command;

			// Debounce search to avoid too many API calls
			searchTimeout = setTimeout(() => {
				loadPrompts(searchTerm, 1, false);
			}, 200);
		}

		// Update filtered prompts from loaded prompts
		filteredPrompts = loadedPrompts.sort((a, b) => a.title.localeCompare(b.title));
	}

	// Initial load when component mounts
	import { onMount } from 'svelte';
	onMount(() => {
		// Load initial prompts when component is shown
		if (!isInitialized) {
			isInitialized = true;
			loadPrompts('', 1, false);
		}
	});

	$: if (command) {
		selectedPromptIdx = 0;
	}

	export const selectUp = () => {
		selectedPromptIdx = Math.max(0, selectedPromptIdx - 1);
	};

	export const selectDown = () => {
		selectedPromptIdx = Math.min(selectedPromptIdx + 1, filteredPrompts.length - 1);
	};

	const confirmPrompt = async (command) => {
		let text = command.content;

		if (command.content.includes('{{CLIPBOARD}}')) {
			const clipboardText = await navigator.clipboard.readText().catch((err) => {
				toast.error($i18n.t('Failed to read clipboard contents'));
				return '{{CLIPBOARD}}';
			});

			const clipboardItems = await navigator.clipboard.read();

			let imageUrl = null;
			for (const item of clipboardItems) {
				// Check for known image types
				for (const type of item.types) {
					if (type.startsWith('image/')) {
						const blob = await item.getType(type);
						imageUrl = URL.createObjectURL(blob);
					}
				}
			}

			if (imageUrl) {
				files = [
					...files,
					{
						type: 'image',
						url: imageUrl
					}
				];
			}

			text = text.replaceAll('{{CLIPBOARD}}', clipboardText);
		}

		if (command.content.includes('{{USER_LOCATION}}')) {
			const location = await getUserPosition();
			text = text.replaceAll('{{USER_LOCATION}}', String(location));
		}

		if (command.content.includes('{{USER_NAME}}')) {
			const name = $user.name || 'User';
			text = text.replaceAll('{{USER_NAME}}', name);
		}

		if (command.content.includes('{{USER_LANGUAGE}}')) {
			const language = localStorage.getItem('locale') || 'en-US';
			text = text.replaceAll('{{USER_LANGUAGE}}', language);
		}

		if (command.content.includes('{{CURRENT_DATE}}')) {
			const date = getFormattedDate();
			text = text.replaceAll('{{CURRENT_DATE}}', date);
		}

		if (command.content.includes('{{CURRENT_TIME}}')) {
			const time = getFormattedTime();
			text = text.replaceAll('{{CURRENT_TIME}}', time);
		}

		if (command.content.includes('{{CURRENT_DATETIME}}')) {
			const dateTime = getCurrentDateTime();
			text = text.replaceAll('{{CURRENT_DATETIME}}', dateTime);
		}

		if (command.content.includes('{{CURRENT_TIMEZONE}}')) {
			const timezone = getUserTimezone();
			text = text.replaceAll('{{CURRENT_TIMEZONE}}', timezone);
		}

		if (command.content.includes('{{CURRENT_WEEKDAY}}')) {
			const weekday = getWeekday();
			text = text.replaceAll('{{CURRENT_WEEKDAY}}', weekday);
		}

		prompt = text;

		const chatInputContainerElement = document.getElementById('chat-input-container');
		const chatInputElement = document.getElementById('chat-input');

		await tick();
		if (chatInputContainerElement) {
			chatInputContainerElement.style.height = '';
			chatInputContainerElement.style.height =
				Math.min(chatInputContainerElement.scrollHeight, 200) + 'px';
		}

		await tick();
		if (chatInputElement) {
			chatInputElement.focus();
			chatInputElement.dispatchEvent(new Event('input'));
		}
	};
</script>

{#if filteredPrompts.length > 0}
	<div
		id="commands-container"
		class="px-2 mb-2 text-left w-full absolute bottom-0 left-0 right-0 z-10"
	>
		<div class="flex w-full rounded-xl border border-gray-50 dark:border-gray-850">
			<div
				class="max-h-60 flex flex-col w-full rounded-xl bg-white dark:bg-gray-900 dark:text-gray-100"
			>
				<div
					class="m-1 overflow-y-auto p-1 space-y-0.5 scrollbar-hidden"
					on:scroll={(e) => {
						const target = e.target;
						if (target) {
							const scrollPercentage =
								(target.scrollTop + target.clientHeight) / target.scrollHeight;

							// Load more when scrolled near the bottom (80% threshold for better UX)
							if (scrollPercentage >= 0.8) {
								loadMorePrompts();
							}
						}
					}}
				>
					{#each filteredPrompts as prompt, promptIdx}
						<button
							class=" px-3 py-1.5 rounded-xl w-full text-left {promptIdx === selectedPromptIdx
								? '  bg-gray-50 dark:bg-gray-850 selected-command-option-button'
								: ''}"
							type="button"
							on:click={() => {
								confirmPrompt(prompt);
							}}
							on:mousemove={() => {
								selectedPromptIdx = promptIdx;
							}}
							on:focus={() => {}}
						>
							<div class=" font-medium text-black dark:text-gray-100">
								{prompt.command}
							</div>

							<div class=" text-xs text-gray-600 dark:text-gray-100">
								{prompt.title}
							</div>
						</button>
					{/each}

					{#if isLoading}
						<div class="px-3 py-2 text-center text-xs text-gray-500 dark:text-gray-400">
							{$i18n.t('Loading more prompts...')}
						</div>
					{/if}
				</div>

				<div
					class=" px-2 pt-0.5 pb-1 text-xs text-gray-600 dark:text-gray-100 bg-white dark:bg-gray-900 rounded-b-xl flex items-center space-x-1"
				>
					<div>
						<svg
							xmlns="http://www.w3.org/2000/svg"
							fill="none"
							viewBox="0 0 24 24"
							stroke-width="1.5"
							stroke="currentColor"
							class="w-3 h-3"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								d="m11.25 11.25.041-.02a.75.75 0 0 1 1.063.852l-.708 2.836a.75.75 0 0 0 1.063.853l.041-.021M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9-3.75h.008v.008H12V8.25Z"
							/>
						</svg>
					</div>

					<div class="line-clamp-1">
						{$i18n.t(
							'Tip: Update multiple variable slots consecutively by pressing the tab key in the chat input after each replacement.'
						)}
					</div>
				</div>
			</div>
		</div>
	</div>
{/if}
