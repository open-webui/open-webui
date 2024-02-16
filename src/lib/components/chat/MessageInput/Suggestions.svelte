<script lang="ts">
	export let submitPrompt: Function;
	export let suggestionPrompts = [];

	let prompts = [];

	$: prompts =
		suggestionPrompts.length <= 4
			? suggestionPrompts
			: suggestionPrompts.sort(() => Math.random() - 0.5).slice(0, 4);
</script>

<div class=" flex flex-wrap-reverse mb-3 md:p-1 text-left w-full">
	{#each prompts as prompt, promptIdx}
		<div
			class="{promptIdx > 1 ? 'hidden sm:inline-flex' : ''} basis-full sm:basis-1/2 p-[5px] px-2"
		>
			<button
				class=" flex-1 flex justify-between w-full h-full px-4 py-2.5 bg-white hover:bg-gray-50 dark:bg-gray-900 dark:hover:bg-gray-700 outline outline-1 outline-gray-200 dark:outline-gray-800 rounded-lg transition group"
				on:click={() => {
					submitPrompt(prompt.content);
				}}
			>
				<div class="flex flex-col text-left self-center">
					{#if prompt.title && prompt.title[0] !== ''}
						<div class="text-sm font-medium dark:text-gray-300">{prompt.title[0]}</div>
						<div class="text-sm text-gray-500 line-clamp-1">{prompt.title[1]}</div>
					{:else}
						<div class=" self-center text-sm font-medium dark:text-gray-300 line-clamp-2">
							{prompt.content}
						</div>
					{/if}
				</div>

				<div
					class="self-center p-1 rounded-lg text-white group-hover:bg-gray-100 group-hover:text-gray-800 dark:group-hover:bg-gray-800 dark:group-hover:text-gray-100 dark:text-gray-900 transition"
				>
					<svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 16 16"
						fill="currentColor"
						class="w-4 h-4"
					>
						<path
							fill-rule="evenodd"
							d="M8 14a.75.75 0 0 1-.75-.75V4.56L4.03 7.78a.75.75 0 0 1-1.06-1.06l4.5-4.5a.75.75 0 0 1 1.06 0l4.5 4.5a.75.75 0 0 1-1.06 1.06L8.75 4.56v8.69A.75.75 0 0 1 8 14Z"
							clip-rule="evenodd"
						/>
					</svg>
				</div>
			</button>
		</div>
	{/each}
</div>
