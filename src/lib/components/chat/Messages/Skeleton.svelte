<script lang="ts">
	export let size = 'md';
</script>

<span
	class="relative flex {size === 'md'
		? 'size-3 my-2'
		: size === 'xs'
			? 'size-1.5 my-1'
			: 'size-2 my-1'} mx-1"
>
	<span
		class="absolute inline-flex h-full w-full animate-pulse rounded-full bg-base-700 dark:bg-base-200 opacity-75"
	></span>
	<span
		class="relative inline-flex {size === 'md'
			? 'size-3'
			: size === 'xs'
				? 'size-1.5'
				: 'size-2'} rounded-full bg-base-1000 dark:bg-base-0 animate-size"
	></span>
</span>

<style>
	@keyframes size {
		0%,
		100% {
			transform: scale(1);
		}
		50% {
			transform: scale(1.25);
		}
	}

	.animate-size {
		animation: size 1.5s ease-in-out infinite;
	}
</style>
