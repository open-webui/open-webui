<script lang="ts">
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import type { Readable } from 'svelte/store';
	import { onMount, tick, getContext } from 'svelte';

	type I18nStoreValue = {
		t: (key: string, vars?: Record<string, unknown>) => string;
	};

	const i18n = getContext<Readable<I18nStoreValue>>('i18n');

	export let followUps: string[] = [];
	export let onClick: (followUp: string) => void = () => {};

	const MAX_VISIBLE_FOLLOW_UPS = 3;

	$: visibleFollowUps = followUps.slice(0, MAX_VISIBLE_FOLLOW_UPS);
</script>

<div class="mt-3">
	<div class="text-xs font-semibold text-accent-500 dark:text-accent-400 mb-1.5">
		{$i18n.t('Follow up')}
	</div>

	<div class="flex flex-col text-left gap-1.5">
		{#each visibleFollowUps as followUp, idx (idx)}
			<!-- svelte-ignore a11y-no-static-element-interactions -->
			<!-- svelte-ignore a11y-click-events-have-key-events -->
			<Tooltip content={followUp} placement="top-start" className="line-clamp-1">
				<div
					class="py-2 px-3.5 bg-gray-100/50 dark:bg-gray-800/50 rounded-xl ring-1 ring-inset ring-gray-200/30 dark:ring-white/5 text-left text-[13px] flex items-center gap-2 text-gray-600 dark:text-gray-300 hover:bg-gray-200/70 dark:hover:bg-gray-700/70 hover:text-black dark:hover:text-white transition cursor-pointer"
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
