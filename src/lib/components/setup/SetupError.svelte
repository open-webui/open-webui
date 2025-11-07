<script lang="ts">
	export let error: string;
	export let onRetry: (() => void) | undefined = undefined;
	export let onCancel: (() => void) | undefined = undefined;
</script>

<div class="px-4 py-4 bg-red-50 dark:bg-red-900/20 border-l-4 border-red-500 rounded-r">
	<div class="flex items-start">
		<!-- Error Icon -->
		<div class="flex-shrink-0">
			<svg
				class="h-5 w-5 text-red-500"
				fill="none"
				stroke="currentColor"
				viewBox="0 0 24 24"
				xmlns="http://www.w3.org/2000/svg"
			>
				<path
					stroke-linecap="round"
					stroke-linejoin="round"
					stroke-width="2"
					d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
				></path>
			</svg>
		</div>

		<!-- Error Content -->
		<div class="ml-3 flex-1">
			<h3 class="text-sm font-medium text-red-800 dark:text-red-300">
				Setup Error
			</h3>
			<div class="mt-2 text-sm text-red-700 dark:text-red-400">
				<p>{error}</p>
			</div>

			<!-- Action Buttons -->
			{#if onRetry || onCancel}
				<div class="mt-4 flex gap-3">
					{#if onRetry}
						<button
							type="button"
							class="px-4 py-2 text-sm font-medium text-white bg-red-600 hover:bg-red-700 rounded-md transition-colors focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2"
							on:click={onRetry}
						>
							Retry
						</button>
					{/if}
					{#if onCancel}
						<button
							type="button"
							class="px-4 py-2 text-sm font-medium text-red-700 dark:text-red-300 bg-transparent hover:bg-red-100 dark:hover:bg-red-900/30 rounded-md transition-colors focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2"
							on:click={onCancel}
						>
							Cancel
						</button>
					{/if}
				</div>
			{/if}
		</div>
	</div>
</div>
