<script lang="ts">
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import ChevronUp from '$lib/components/icons/ChevronUp.svelte';
	import Search from '$lib/components/icons/Search.svelte';
	import Collapsible from '$lib/components/common/Collapsible.svelte';

	export let status = { urls: [], query: '' };
	let state = false;
</script>

<Collapsible grow={true} className="w-full" buttonClassName="w-full" bind:open={state}>
	<div class="flex items-center gap-2 text-gray-500 transition">
		<slot />
		{#if state}
			<ChevronUp strokeWidth="2.5" className="size-3.5 " />
		{:else}
			<ChevronDown strokeWidth="2.5" className="size-3.5 " />
		{/if}
	</div>

	<div
		class="text-sm border border-gray-50 dark:border-gray-850 rounded-xl my-1.5 p-2 w-full"
		slot="content"
	>
		{#if status?.query}
			<a
				href="https://www.google.com/search?q={status.query}"
				target="_blank"
				class="flex w-full items-center p-1 px-3 group/item justify-between text-gray-800 dark:text-gray-300 font-normal! no-underline!"
			>
				<div class="flex gap-2 items-center">
					<Search />

					<div class=" line-clamp-1">
						{status.query}
					</div>
				</div>

				<div
					class=" ml-1 text-white dark:text-gray-900 group-hover/item:text-gray-600 dark:group-hover/item:text-white transition"
				>
					<!--  -->
					<svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 16 16"
						fill="currentColor"
						class="size-4"
					>
						<path
							fill-rule="evenodd"
							d="M4.22 11.78a.75.75 0 0 1 0-1.06L9.44 5.5H5.75a.75.75 0 0 1 0-1.5h5.5a.75.75 0 0 1 .75.75v5.5a.75.75 0 0 1-1.5 0V6.56l-5.22 5.22a.75.75 0 0 1-1.06 0Z"
							clip-rule="evenodd"
						/>
					</svg>
				</div>
			</a>
		{/if}

		{#if status?.items}
			{#each status.items as item, itemIdx}
				<a
					href={item.link}
					target="_blank"
					class="flex w-full items-center p-1 px-3 group/item justify-between text-gray-800 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-850 rounded-lg font-normal! no-underline! mb-1"
				>
					<div class=" flex justify-center items-center gap-3">
						<div class="w-fit">
							<img
								src="https://www.google.com/s2/favicons?sz=32&domain={item.link}"
								alt="favicon"
								class="size-3.5"
							/>
						</div>

						<div class="w-full text-sm line-clamp-1">
							{item?.title ?? item.link}
						</div>
					</div>

					<div
						class=" ml-1 text-white dark:text-gray-900 group-hover/item:text-gray-600 dark:group-hover/item:text-white transition"
					>
						<!--  -->
						<svg
							xmlns="http://www.w3.org/2000/svg"
							viewBox="0 0 16 16"
							fill="currentColor"
							class="size-4"
						>
							<path
								fill-rule="evenodd"
								d="M4.22 11.78a.75.75 0 0 1 0-1.06L9.44 5.5H5.75a.75.75 0 0 1 0-1.5h5.5a.75.75 0 0 1 .75.75v5.5a.75.75 0 0 1-1.5 0V6.56l-5.22 5.22a.75.75 0 0 1-1.06 0Z"
								clip-rule="evenodd"
							/>
						</svg>
					</div>
				</a>
			{/each}
		{:else if status?.urls}
			{#each status.urls as url, urlIdx}
				<a
					href={url}
					target="_blank"
					class="flex w-full items-center p-1 px-3 group/item justify-between text-gray-800 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-850 rounded-lg no-underline mb-1"
				>
					<div class=" flex justify-center items-center gap-3">
						<div class="w-fit">
							<img
								src="https://www.google.com/s2/favicons?sz=32&domain={url}"
								alt="favicon"
								class="size-3.5"
							/>
						</div>

						<div class="w-full text-sm line-clamp-1">
							{url}
						</div>
					</div>

					<div
						class=" ml-1 text-white dark:text-gray-900 group-hover/item:text-gray-600 dark:group-hover/item:text-white transition"
					>
						<!--  -->
						<svg
							xmlns="http://www.w3.org/2000/svg"
							viewBox="0 0 16 16"
							fill="currentColor"
							class="size-4"
						>
							<path
								fill-rule="evenodd"
								d="M4.22 11.78a.75.75 0 0 1 0-1.06L9.44 5.5H5.75a.75.75 0 0 1 0-1.5h5.5a.75.75 0 0 1 .75.75v5.5a.75.75 0 0 1-1.5 0V6.56l-5.22 5.22a.75.75 0 0 1-1.06 0Z"
								clip-rule="evenodd"
							/>
						</svg>
					</div>
				</a>
			{/each}
		{/if}
	</div>
</Collapsible>
