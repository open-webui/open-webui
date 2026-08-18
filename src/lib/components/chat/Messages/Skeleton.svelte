<script lang="ts">
	export let size = 'md';
</script>

<div class="flex items-center space-x-1 p-1">
	<span
		class="inline-block {size === 'md' ? 'size-2' : size === 'xs' ? 'size-1' : 'size-1.5'} rounded-full bg-gray-700 dark:bg-gray-300 animate-bounce1"
	></span>
	<span
		class="inline-block {size === 'md' ? 'size-2' : size === 'xs' ? 'size-1' : 'size-1.5'} rounded-full bg-gray-700 dark:bg-gray-300 animate-bounce2"
	></span>
	<span
		class="inline-block {size === 'md' ? 'size-2' : size === 'xs' ? 'size-1' : 'size-1.5'} rounded-full bg-gray-700 dark:bg-gray-300 animate-bounce3"
	></span>
</div>

<style>
	@keyframes bounce {
		0%, 100% {
			transform: translateY(0);
			opacity: 0.5;
		}
		50% {
			transform: translateY(-4px);
			opacity: 1;
		}
	}

	.animate-bounce1 {
		animation: bounce 1.2s infinite ease-in-out;
		animation-delay: 0s;
	}
	.animate-bounce2 {
		animation: bounce 1.2s infinite ease-in-out;
		animation-delay: 0.15s;
	}
	.animate-bounce3 {
		animation: bounce 1.2s infinite ease-in-out;
		animation-delay: 0.3s;
	}
</style>
