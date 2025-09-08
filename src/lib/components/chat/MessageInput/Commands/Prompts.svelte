<script lang="ts">
	import { prompts, settings, user } from '$lib/stores';
	import {
		extractCurlyBraceWords,
		getUserPosition,
		getFormattedDate,
		getFormattedTime,
		getCurrentDateTime,
		getUserTimezone,
		getWeekday
	} from '$lib/utils';
	import { tick, getContext, onMount, onDestroy } from 'svelte';
	import { toast } from 'svelte-sonner';

	const i18n = getContext('i18n');

	export let command = '';
	export let onSelect = (e) => {};

	let selectedPromptIdx = 0;
	let filteredPrompts = [];

	$: filteredPrompts = $prompts
		.filter((p) => p.command.toLowerCase().includes(command.toLowerCase()))
		.sort((a, b) => a.title.localeCompare(b.title));

	$: if (command) {
		selectedPromptIdx = 0;
	}

	export const selectUp = () => {
		selectedPromptIdx = Math.max(0, selectedPromptIdx - 1);
	};

	export const selectDown = () => {
		selectedPromptIdx = Math.min(selectedPromptIdx + 1, filteredPrompts.length - 1);
	};

	let container;
	let adjustHeightDebounce;

	const adjustHeight = () => {
		if (container) {
			if (adjustHeightDebounce) {
				clearTimeout(adjustHeightDebounce);
			}

			adjustHeightDebounce = setTimeout(() => {
				if (!container) return;

				// Ensure the container is visible before adjusting height
				const rect = container.getBoundingClientRect();
				container.style.maxHeight = Math.max(Math.min(240, rect.bottom - 80), 100) + 'px';
			}, 100);
		}
	};

	const confirmPrompt = async (command) => {
		onSelect({ type: 'prompt', data: command });
	};

	onMount(async () => {
		window.addEventListener('resize', adjustHeight);

		await tick();
		adjustHeight();
	});

	onDestroy(() => {
		window.removeEventListener('resize', adjustHeight);
	});
</script>

{#if filteredPrompts.length > 0}
	<div
		id="commands-container"
		class="px-2 mb-2 text-left w-full absolute bottom-0 left-0 right-0 z-10"
	>
		<div class="flex w-full rounded-xl border border-gray-100 dark:border-gray-850">
			<div class="flex flex-col w-full rounded-xl bg-white dark:bg-gray-900 dark:text-gray-100">
				<div
					class="m-1 overflow-y-auto p-1 space-y-0.5 scrollbar-hidden max-h-60"
					id="command-options-container"
					bind:this={container}
				>
					{#each filteredPrompts as promptItem, promptIdx}
						<button
							class=" px-3 py-1.5 rounded-xl w-full text-left {promptIdx === selectedPromptIdx
								? '  bg-gray-50 dark:bg-gray-850 selected-command-option-button'
								: ''}"
							type="button"
							on:click={() => {
								confirmPrompt(promptItem);
							}}
							on:mousemove={() => {
								selectedPromptIdx = promptIdx;
							}}
							on:focus={() => {}}
						>
							<div class=" font-medium text-black dark:text-gray-100">
								{promptItem.command}
							</div>

							<div class=" text-xs text-gray-600 dark:text-gray-100">
								{promptItem.title}
							</div>
						</button>
					{/each}
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
