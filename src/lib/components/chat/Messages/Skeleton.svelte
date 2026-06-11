<script lang="ts">
	export let size = 'md';
	export let legacy = false;
</script>

{#if legacy}
	<div class="w-full mt-2 mb-2">
		<div class="animate-pulse flex w-full">
			<div class="{size === 'md' ? 'space-y-2' : 'space-y-1.5'} w-full">
				<div
					class="{size === 'md' ? 'h-2' : 'h-1.5'} bg-gray-200 dark:bg-gray-600 rounded-sm mr-14"
				/>

				<div class="grid grid-cols-3 gap-4">
					<div
						class="{size === 'md'
							? 'h-2'
							: 'h-1.5'} bg-gray-200 dark:bg-gray-600 rounded-sm col-span-2"
					/>
					<div
						class="{size === 'md'
							? 'h-2'
							: 'h-1.5'} bg-gray-200 dark:bg-gray-600 rounded-sm col-span-1"
					/>
				</div>
				<div class="grid grid-cols-4 gap-4">
					<div
						class="{size === 'md'
							? 'h-2'
							: 'h-1.5'} bg-gray-200 dark:bg-gray-600 rounded-sm col-span-1"
					/>
					<div
						class="{size === 'md'
							? 'h-2'
							: 'h-1.5'} bg-gray-200 dark:bg-gray-600 rounded-sm col-span-2"
					/>
					<div
						class="{size === 'md'
							? 'h-2'
							: 'h-1.5'} bg-gray-200 dark:bg-gray-600 rounded-sm col-span-1 mr-4"
					/>
				</div>

				<div class="{size === 'md' ? 'h-2' : 'h-1.5'} bg-gray-200 dark:bg-gray-600 rounded-sm" />
			</div>
		</div>
	</div>
{:else}
	<span
		class="relative flex {size === 'md'
			? 'size-3 my-2'
			: size === 'xs'
				? 'size-1.5 my-1'
				: 'size-2 my-1'} mx-1"
	>
		<span
			class="absolute inline-flex h-full w-full animate-pulse rounded-full bg-gray-700 dark:bg-gray-200 opacity-75"
		></span>
		<span
			class="relative inline-flex {size === 'md'
				? 'size-3'
				: size === 'xs'
					? 'size-1.5'
					: 'size-2'} rounded-full bg-black dark:bg-white animate-size"
		></span>
	</span>
{/if}

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
