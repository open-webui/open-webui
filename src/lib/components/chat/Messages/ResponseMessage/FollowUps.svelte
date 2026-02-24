<script lang="ts">
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import { onMount, tick, getContext } from 'svelte';

	const i18n = getContext('i18n');

	export let followUps: string[] = [];
	export let onClick: (followUp: string) => void = () => {};
</script>

<div class="mt-4">
	<div class="text-sm font-medium">
		{$i18n.t('Follow up')}
	</div>

	<div class="flex flex-col text-left gap-1 mt-1.5">
		{#each followUps as followUp, idx (idx)}
			<Tooltip content={followUp} placement="top-start" className="line-clamp-1">
				<button
					class=" py-1.5 bg-transparent text-left text-sm flex items-center gap-2 text-gray-500 dark:text-gray-400 hover:text-black dark:hover:text-white transition cursor-pointer w-full"
					on:click={() => onClick(followUp)}
					aria-label={$i18n.t('Follow up: {{question}}', { question: followUp })}
				>
					<div class="line-clamp-1">
						{followUp}
					</div>
				</button>
			</Tooltip>

			{#if idx < followUps.length - 1}
				<hr class="border-gray-50 dark:border-gray-850/30" />
			{/if}
		{/each}
	</div>
</div>
