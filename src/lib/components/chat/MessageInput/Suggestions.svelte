<script lang="ts">
	import Bolt from '$lib/components/icons/Bolt.svelte';
	import { onMount, getContext } from 'svelte';

	const i18n = getContext('i18n');

	export let submitPrompt: Function;
	export let suggestionPrompts = [];

	let prompts = [];

	$: prompts = suggestionPrompts
		.reduce((acc, current) => [...acc, ...[current]], [])
		.sort(() => Math.random() - 0.5);
	// suggestionPrompts.length <= 4
	// 	? suggestionPrompts
	// 	: suggestionPrompts.sort(() => Math.random() - 0.5).slice(0, 4);

	onMount(() => {
		const containerElement = document.getElementById('suggestions-container');

		if (containerElement) {
			containerElement.addEventListener('wheel', function (event) {
				if (event.deltaY !== 0) {
					// If scrolling vertically, prevent default behavior
					event.preventDefault();
					// Adjust horizontal scroll position based on vertical scroll
					containerElement.scrollLeft += event.deltaY;
				}
			});
		}
	});
</script>

{#if prompts.length > 0}
	<div class="mb-2 flex gap-1 text-sm font-medium items-center text-gray-400 dark:text-gray-600">
		<Bolt />
		{$i18n.t('Suggested')}
	</div>
{/if}

<div class="w-full">
	<div
		class="relative w-full flex gap-2 snap-x snap-mandatory md:snap-none overflow-x-auto tabs"
		id="suggestions-container"
	>
		{#each prompts as prompt, promptIdx}
			<div class="snap-center shrink-0">
				<button
					class="flex flex-col flex-1 shrink-0 w-64 justify-between h-36 p-5 px-6 bg-gray-50 hover:bg-gray-100 dark:bg-gray-850 dark:hover:bg-gray-800 rounded-3xl transition group"
					on:click={() => {
						submitPrompt(prompt.content);
					}}
				>
					<div class="flex flex-col text-left">
						{#if prompt.title && prompt.title[0] !== ''}
							<div
								class="  font-medium dark:text-gray-300 dark:group-hover:text-gray-200 transition"
							>
								{prompt.title[0]}
							</div>
							<div class="text-sm text-gray-600 font-normal line-clamp-2">{prompt.title[1]}</div>
						{:else}
							<div
								class=" self-center text-sm font-medium dark:text-gray-300 dark:group-hover:text-gray-100 transition line-clamp-2"
							>
								{prompt.content}
							</div>
						{/if}
					</div>

					<div class="w-full flex justify-between">
						<div
							class="text-xs text-gray-400 group-hover:text-gray-500 dark:text-gray-600 dark:group-hover:text-gray-500 transition self-center"
						>
							{$i18n.t('Prompt')}
						</div>

						<div
							class="self-end p-1 rounded-lg text-gray-300 group-hover:text-gray-800 dark:text-gray-700 dark:group-hover:text-gray-100 transition"
						>
							<svg
								xmlns="http://www.w3.org/2000/svg"
								viewBox="0 0 16 16"
								fill="currentColor"
								class="size-4"
							>
								<path
									fill-rule="evenodd"
									d="M8 14a.75.75 0 0 1-.75-.75V4.56L4.03 7.78a.75.75 0 0 1-1.06-1.06l4.5-4.5a.75.75 0 0 1 1.06 0l4.5 4.5a.75.75 0 0 1-1.06 1.06L8.75 4.56v8.69A.75.75 0 0 1 8 14Z"
									clip-rule="evenodd"
								/>
							</svg>
						</div>
					</div>
				</button>
			</div>
		{/each}

		<!-- <div class="snap-center shrink-0">
		<img
			class="shrink-0 w-80 h-40 rounded-lg shadow-xl bg-white"
			src="https://images.unsplash.com/photo-1604999565976-8913ad2ddb7c?ixlib=rb-1.2.1&amp;ixid=MnwxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8&amp;auto=format&amp;fit=crop&amp;w=320&amp;h=160&amp;q=80"
		/>
	</div> -->
	</div>
</div>

<style>
	.tabs::-webkit-scrollbar {
		display: none; /* for Chrome, Safari and Opera */
	}

	.tabs {
		-ms-overflow-style: none; /* IE and Edge */
		scrollbar-width: none; /* Firefox */
	}
</style>
