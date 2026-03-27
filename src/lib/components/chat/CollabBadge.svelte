<script lang="ts">
	import { collabState, toggleCollabRibbon } from '$lib/stores/collab';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';

	$: ready = $collabState.phase === 'completed' || $collabState.overallProgress >= 100;

	$: badgeText = ready ? '已就绪' : `准备中 ${$collabState.overallProgress}%`;
</script>

{#if $collabState.enabled}
	<button
		class="group inline-flex items-center gap-2.5 px-3.5 py-2 rounded-full border border-emerald-200/80 dark:border-emerald-900/50 bg-emerald-50/80 dark:bg-emerald-950/20 text-emerald-800 dark:text-emerald-300 shadow-sm transition hover:bg-emerald-100/80 dark:hover:bg-emerald-950/30"
		on:click={toggleCollabRibbon}
		aria-label="切换协同面板"
	>
		<span class="inline-flex items-center justify-center w-2.5 h-2.5 rounded-full bg-emerald-500"></span>

		<span class="text-sm font-semibold tracking-tight">边云协同</span>

		<span
			class="text-xs px-2 py-0.5 rounded-full border
			{ready
				? 'bg-emerald-100 text-emerald-700 border-emerald-200 dark:bg-emerald-900/30 dark:text-emerald-300 dark:border-emerald-800'
				: 'bg-amber-100 text-amber-700 border-amber-200 dark:bg-amber-900/30 dark:text-amber-300 dark:border-amber-800'}"
		>
			{badgeText}
		</span>

		<div
			class="transition-transform duration-200 ease-out {$collabState.ribbonExpanded
				? 'rotate-180'
				: 'rotate-0'}"
		>
			<ChevronDown className="size-3.5 opacity-80 group-hover:opacity-100" strokeWidth="2.5" />
		</div>
	</button>
{/if}