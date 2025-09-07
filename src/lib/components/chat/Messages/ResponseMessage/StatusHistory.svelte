<script>
	import { getContext } from 'svelte';
	const i18n = getContext('i18n');

	import Collapsible from '$lib/components/common/Collapsible.svelte';
	import StatusItem from './StatusHistory/StatusItem.svelte';
	export let statusHistory = [];

	let showHistory = false;
</script>

<!-- <Collapsible open={false} growDirection="up" className="w-full space-y-1" buttonClassName="w-full">
	<div
		class="flex items-center gap-2 text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 transition w-full"
	>
		
	</div>

	
</Collapsible> -->

{#if statusHistory}
	<div class="text-sm flex flex-col w-full">
		{#if showHistory}
			<div class="flex flex-row">
				{#if statusHistory.length > 1}
					<div class="w-1 border-r border-gray-50 dark:border-gray-800 mt-3 -mb-2.5" />

					<div class="w-full -translate-x-[7.5px]">
						{#each statusHistory as status, idx}
							{#if idx !== statusHistory.length - 1}
								<div class="flex items-start gap-2 mb-1">
									<div class="pt-3 px-1">
										<span class="relative flex size-2">
											<span
												class="relative inline-flex size-1.5 rounded-full bg-gray-200 dark:bg-gray-700"
											></span>
										</span>
									</div>
									<StatusItem {status} done={true} />
								</div>
							{/if}
						{/each}
					</div>
				{/if}
			</div>
		{/if}

		{#if statusHistory.length > 0}
			{@const status = statusHistory.at(-1)}
			<button
				class="w-full -translate-x-[3.5px]"
				on:click={() => {
					showHistory = !showHistory;
				}}
			>
				<div class="flex items-start gap-2 mb-1">
					<div class="pt-3 px-1">
						<span class="relative flex size-2">
							{#if status?.done === false}
								<span
									class="absolute inline-flex h-full w-full animate-ping rounded-full bg-gray-400 dark:bg-gray-700 opacity-75"
								></span>
							{/if}
							<span class="relative inline-flex size-1.5 rounded-full bg-gray-200 dark:bg-gray-700"
							></span>
						</span>
					</div>
					<StatusItem {status} />
				</div>
			</button>
		{/if}
	</div>
{/if}
