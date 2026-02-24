<script lang="ts">
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import { onMount, tick, getContext } from 'svelte';

	const i18n = getContext('i18n');

	export let followUps: string[] = [];
	export let onClick: (followUp: string) => void = () => {};
</script>

<div class="mt-4">
	<div class="text-sm font-medium text-accent-500 dark:text-accent-400 mb-2">
		{$i18n.t('Follow up')}
	</div>

	<div class="flex flex-col text-left gap-2">
		{#each followUps as followUp, idx (idx)}
			<!-- svelte-ignore a11y-no-static-element-interactions -->
			<!-- svelte-ignore a11y-click-events-have-key-events -->
			<Tooltip content={followUp} placement="top-start" className="line-clamp-1">
				<div
					class="py-2.5 px-4 bg-gray-100/50 dark:bg-gray-800/50 rounded-xl ring-1 ring-inset ring-gray-200/30 dark:ring-white/5 text-left text-sm flex items-center gap-2 text-gray-600 dark:text-gray-300 hover:bg-gray-200/70 dark:hover:bg-gray-700/70 hover:text-black dark:hover:text-white transition cursor-pointer"
					on:click={() => onClick(followUp)}
					aria-label={followUp}
				>
					<div class="line-clamp-1">
						{followUp}
					</div>
				</div>
			</Tooltip>
		{/each}
	</div>
</div>
