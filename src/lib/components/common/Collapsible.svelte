<script lang="ts">
	import { slide } from 'svelte/transition';
	import { quintOut } from 'svelte/easing';

	import ChevronUp from '../icons/ChevronUp.svelte';
	import ChevronDown from '../icons/ChevronDown.svelte';

	export let open = false;
	export let className = '';
	export let title = null;

	function handleClick(event) {
		if (!event.target.closest('.no-toggle')) {
			open = !open;
		}
	}
</script>

<div class={className}>
	{#if title !== null}
		<button class="w-full" on:click={handleClick}>
			<div class="w-full font-medium transition flex items-center justify-between gap-2">
				<div>
					{title}
				</div>

				<div>
					{#if open}
						<ChevronUp strokeWidth="3.5" className="size-3.5" />
					{:else}
						<ChevronDown strokeWidth="3.5" className="size-3.5" />
					{/if}
				</div>
			</div>
		</button>
	{:else}
		<button
			type="button"
			on:click={handleClick}
			class="flex w-full items-center gap-2 text-left text-gray-500 transition hover:text-gray-700 dark:hover:text-gray-300"
		>
			<slot />
		</button>
	{/if}

	{#if open}
		<div transition:slide={{ duration: 300, easing: quintOut, axis: 'y' }}>
			<slot name="content" />
		</div>
	{/if}
</div>
