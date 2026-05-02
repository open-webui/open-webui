<script lang="ts">
	export let size = 'md';
</script>

<span
	class="relative inline-flex items-center mx-1 {size === 'md'
		? 'h-4 my-2'
		: size === 'xs'
			? 'h-2 my-1'
			: 'h-3 my-1'}"
>
	<span
		class="block {size === 'md'
			? 'w-[3px] h-4'
			: size === 'xs'
				? 'w-[2px] h-2'
				: 'w-[2px] h-3'} bg-gray-700 dark:bg-gray-200 rounded-[1px] animate-typewriter"
	></span>
</span>

<style>
	@keyframes typewriter {
		0%,
		100% {
			opacity: 0.85;
		}
		50% {
			opacity: 0.25;
		}
	}

	.animate-typewriter {
		animation: typewriter 1s cubic-bezier(0.4, 0, 0.6, 1) infinite;
	}
</style>
