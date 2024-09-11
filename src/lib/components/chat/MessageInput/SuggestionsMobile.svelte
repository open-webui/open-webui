<script lang="ts">
	import Bolt from '$lib/components/icons/Bolt.svelte';
	import { onMount } from 'svelte';

	export let submitPrompt: Function;
	export let suggestionPrompts = [];

	let prompts = [];

	let expanded = false;

	const iconList = ['sent-mail.gif','holidays.gif','approved.gif','task.gif','business-plan.gif']

	$: prompts = suggestionPrompts
		.reduce((acc, current) => [...acc, ...[current]], [])
		// .sort(() => Math.random() - 0.5);
	// suggestionPrompts.length <= 4
	// 	? suggestionPrompts
	// 	: suggestionPrompts.sort(() => Math.random() - 0.5).slice(0, 4);

	onMount(() => {
		// const containerElement = document.getElementById('suggestions-container');

		// if (containerElement) {
		// 	containerElement.addEventListener('wheel', function (event) {
		// 		if (event.deltaY !== 0) {
		// 			// If scrolling vertically, prevent default behavior
		// 			event.preventDefault();
		// 			// Adjust horizontal scroll position based on vertical scroll
		// 			containerElement.scrollLeft += event.deltaY;
		// 		}
		// 	});
		// }
	});
</script>

<!-- {#if prompts.length > 0}
	<div class="mb-2 flex gap-1 text-sm font-medium items-center text-gray-400 dark:text-gray-600">
		<Bolt />
		Suggested
	</div>
{/if} -->

	<div
		class="relative w-full px-4 flex flex-col items-center gap-4 snap-y snap-mandatory md:snap-none overflow-y-auto tabs mask"
		style="max-height: {!expanded ? '12vh':'36vh'};"
		id="suggestions-container"
		on:pointermove|preventDefault={() => {if (!expanded) { expanded = true }}}
	>
		{#each prompts as prompt, promptIdx}
			<div class="snap-center shrink-0 ">
				<button
					class="flex items-center h-16 px-4 bg-[#EEF9FD] rounded-2xl backdrop-blur group w-[80vw] notification {expanded ? 'expanded' : 'stacked'}"
					style={
						expanded ? '' :
						`transform: scaleX(${(prompts.length-promptIdx/2)/prompts.length}) translateY(${promptIdx/1.5}rem); z-index: ${prompts.length-promptIdx};
						opacity: ${(prompts.length-promptIdx/2)/prompts.length}
						`
					}
					on:click={() => {
						submitPrompt(prompt.content);
					}}
				>
					<img class="w-8 mr-2" src={`/icon/${iconList[promptIdx % 5]}`} alt="icon" />
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
								class=" self-center text-sm font-medium dark:text-gray-600 dark:group-hover:text-gray-800 transition line-clamp-2"
							>
								{prompt.content}
							</div>
						{/if}
					</div>
				</button>
			</div>
		{/each}
	</div>

<style>
	.notification {
		transition: transform 1.5s cubic-bezier(0.25, 0.8, 0.25, 1);
		box-shadow: 0px 4px 16px 0px rgba(0, 0, 0, 0.20);
	}

	.stacked {
		position: absolute;
		top: 2%;
		left: 5%;
		right: 0;
		/* opacity: 0.85; */
	}

	.expanded {
		position: relative;
		z-index: 0;
		opacity: 0.9;
		/* animation: expand 3s linear; */
	}
	@keyframes expand {
		0% {position: absolute;}
		100% {position: relative;}
	}
	.tabs::-webkit-scrollbar {
		display: none; /* for Chrome, Safari and Opera */
	}

	.tabs {
		-ms-overflow-style: none; /* IE and Edge */
		scrollbar-width: none; /* Firefox */
		padding-bottom: 3.5rem;
		transition: max-height 1.5s cubic-bezier(0.25, 0.8, 0.25, 1);
	}
	.mask {
		mask-image: linear-gradient(to top, rgba(0, 0, 0, 0) 0%, rgba(0, 0, 0, 1) 10%);
		-webkit-mask-image: linear-gradient(to top, rgba(0, 0, 0, 0) 0%, rgba(0, 0, 0, 1) 10%);
	}
</style>
