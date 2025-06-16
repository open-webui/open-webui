<script lang="ts">
	import ArrowTurnDownRight from '$lib/components/icons/ArrowTurnDownRight.svelte';
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
			<!-- svelte-ignore a11y-no-static-element-interactions -->
			<!-- svelte-ignore a11y-click-events-have-key-events -->
			<div
				class=" mr-2 py-1.5 bg-transparent text-left text-sm flex items-center gap-2 px-1.5 text-gray-500 dark:text-gray-400 hover:text-black dark:hover:text-white transition cursor-pointer"
				on:click={() => onClick(followUp)}
				title={followUp}
				aria-label={followUp}
			>
				<ArrowTurnDownRight className="size-3.5" />

				<div class="line-clamp-1">
					{followUp}
				</div>
			</div>

			{#if idx < followUps.length - 1}
				<hr class="border-gray-100 dark:border-gray-850" />
			{/if}
		{/each}
	</div>
</div>
