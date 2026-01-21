<script lang="ts">
	import { slide } from 'svelte/transition';
	import { quintOut } from 'svelte/easing';
	import ChevronDown from '../icons/ChevronDown.svelte';

	export let title: string = '';
	export let open: boolean = true;
	export let className: string = '';
</script>

<div class="border border-gray-100 dark:border-gray-850 rounded-xl {className}">
	<button
		type="button"
		class="w-full flex items-center justify-between px-4 py-3 text-sm font-medium text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-850 rounded-xl transition-colors"
		on:click={() => (open = !open)}
	>
		<span>{title}</span>
		<div class="transform transition-transform duration-200 {open ? 'rotate-180' : ''}">
			<ChevronDown className="size-4" />
		</div>
	</button>

	{#if open}
		<div transition:slide={{ duration: 200, easing: quintOut }} class="px-4 pb-4">
			<slot />
		</div>
	{/if}
</div>
