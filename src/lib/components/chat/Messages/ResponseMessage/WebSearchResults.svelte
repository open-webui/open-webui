<script lang="ts">
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import ChevronUp from '$lib/components/icons/ChevronUp.svelte';
	import MagnifyingGlass from '$lib/components/icons/MagnifyingGlass.svelte';
	import Collapsible from '$lib/components/common/Collapsible.svelte';
	import type { Snippet } from 'svelte';

	let {
		urls = $bindable([]),
		query = $bindable(''),
		children
	}: { urls: string[]; query: string; children: Snippet } = $props();
	let collapsedState = $state(false);
</script>

{#snippet content()}
	<div class="text-sm border border-gray-300/30 dark:border-gray-700/50 rounded-xl mb-1.5">
		{#if query}
			<a
				class="flex w-full items-center p-3 px-4 border-b border-gray-300/30 dark:border-gray-700/50 group/item justify-between font-normal text-gray-800 dark:text-gray-300 no-underline"
				href="https://www.google.com/search?q={query}"
				target="_blank"
			>
				<div class="flex gap-2 items-center">
					<MagnifyingGlass />

					<div class=" line-clamp-1">
						{query}
					</div>
				</div>

				<div
					class=" ml-1 text-white dark:text-gray-900 group-hover/item:text-gray-600 dark:group-hover/item:text-white transition"
				>
					<!--  -->
					<svg
						class="size-4"
						fill="currentColor"
						viewBox="0 0 16 16"
						xmlns="http://www.w3.org/2000/svg"
					>
						<path
							clip-rule="evenodd"
							d="M4.22 11.78a.75.75 0 0 1 0-1.06L9.44 5.5H5.75a.75.75 0 0 1 0-1.5h5.5a.75.75 0 0 1 .75.75v5.5a.75.75 0 0 1-1.5 0V6.56l-5.22 5.22a.75.75 0 0 1-1.06 0Z"
							fill-rule="evenodd"
						/>
					</svg>
				</div>
			</a>
		{/if}

		{#each urls as url, urlIdx}
			<a
				class="flex w-full items-center p-3 px-4 {urlIdx === urls.length - 1
					? ''
					: 'border-b border-gray-300/30 dark:border-gray-700/50'} group/item justify-between font-normal text-gray-800 dark:text-gray-300"
				href={url}
				target="_blank"
			>
				<div class=" line-clamp-1">
					{url}
				</div>

				<div
					class=" ml-1 text-white dark:text-gray-900 group-hover/item:text-gray-600 dark:group-hover/item:text-white transition"
				>
					<!--  -->
					<svg
						class="size-4"
						fill="currentColor"
						viewBox="0 0 16 16"
						xmlns="http://www.w3.org/2000/svg"
					>
						<path
							clip-rule="evenodd"
							d="M4.22 11.78a.75.75 0 0 1 0-1.06L9.44 5.5H5.75a.75.75 0 0 1 0-1.5h5.5a.75.75 0 0 1 .75.75v5.5a.75.75 0 0 1-1.5 0V6.56l-5.22 5.22a.75.75 0 0 1-1.06 0Z"
							fill-rule="evenodd"
						/>
					</svg>
				</div>
			</a>
		{/each}
	</div>
{/snippet}

<Collapsible className="w-full space-y-1" bind:open={collapsedState} {content}>
	<div
		class="flex items-center gap-2 text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 transition"
	>
		{@render children?.()}

		{#if collapsedState}
			<ChevronUp className="size-3.5 " strokeWidth="3.5" />
		{:else}
			<ChevronDown className="size-3.5 " strokeWidth="3.5" />
		{/if}
	</div>
</Collapsible>
