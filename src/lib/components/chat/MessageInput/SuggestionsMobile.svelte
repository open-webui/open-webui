<script lang="ts">
	import Bolt from '$lib/components/icons/Bolt.svelte';
	import { onMount } from 'svelte';

	export let submitPrompt: Function;
	export let suggestionPrompts = [];

	let prompts = [];

	const iconList = ['sent-mail.gif','holidays.gif','approved.gif','task.gif','business-plan.gif']

	$: prompts = suggestionPrompts
		.reduce((acc, current) => [...acc, ...[current]], [])
		// .sort(() => Math.random() - 0.5);
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

<!-- {#if prompts.length > 0}
	<div class="mb-2 flex gap-1 text-sm font-medium items-center text-gray-400 dark:text-gray-600">
		<Bolt />
		Suggested
	</div>
{/if} -->

<div class="w-full px-4">
	<div
		class="relative w-full flex gap-2 snap-x snap-mandatory md:snap-none overflow-x-auto tabs"
		id="suggestions-container"
	>
		{#each prompts as prompt, promptIdx}
			<div class="snap-center shrink-0">
				<button
					class="flex flex-col flex-1 shrink-0 justify-between p-4 px-6 bg-[#E3F3FF] rounded-3xl transition group h-20 max-w-60"
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
								class=" self-center text-base font-medium dark:text-gray-600 dark:group-hover:text-gray-800 transition line-clamp-2"
							>
								{prompt.content}
							</div>
						{/if}
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
	.mask {
		padding-right: 6rem;
		mask-image: linear-gradient(to left, rgba(0, 0, 0, 0) 0%, rgba(0, 0, 0, 1) 10%);
		-webkit-mask-image: linear-gradient(to left, rgba(0, 0, 0, 0) 0%, rgba(0, 0, 0, 1) 10%);
	}
</style>
