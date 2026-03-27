<script lang="ts">
	import { collabState } from '$lib/stores/collab';

	$: edgeRange = $collabState.split?.edgeRange ?? 'L0-L15';
	$: cloudRange = $collabState.split?.cloudRange ?? 'L16-L31';
	$: currentLayer = $collabState.split?.currentLayer ?? 16;
	$: totalLayers = $collabState.split?.totalLayers ?? 32;
	$: splitPoint = totalLayers ? `L${currentLayer}` : '--';
	$: networkStatus = $collabState.network?.status ?? '稳定';
	$: ready = $collabState.phase === 'completed' || $collabState.overallProgress >= 100;
</script>

{#if $collabState.enabled}
	<div
		class="w-full rounded-2xl border border-emerald-200/70 dark:border-emerald-900/50 bg-emerald-50/70 dark:bg-emerald-950/20 px-4 py-2.5 shadow-sm"
	>
		<div class="flex flex-wrap items-center gap-x-5 gap-y-2 text-xs">
			<div class="flex items-center gap-2 text-emerald-800 dark:text-emerald-300 font-medium">
				<span class="inline-flex items-center justify-center w-2 h-2 rounded-full bg-emerald-500"></span>
				<span>协同摘要</span>
			</div>

			<div class="text-gray-600 dark:text-gray-300">
				<span class="text-gray-400 dark:text-gray-500">边端层：</span>
				<span class="font-medium text-sky-700 dark:text-sky-300">{edgeRange}</span>
			</div>

			<div class="text-gray-600 dark:text-gray-300">
				<span class="text-gray-400 dark:text-gray-500">云端层：</span>
				<span class="font-medium text-violet-700 dark:text-violet-300">{cloudRange}</span>
			</div>

			<div class="text-gray-600 dark:text-gray-300">
				<span class="text-gray-400 dark:text-gray-500">切分点：</span>
				<span class="font-medium">{splitPoint}</span>
			</div>

			<div class="text-gray-600 dark:text-gray-300">
				<span class="text-gray-400 dark:text-gray-500">链路：</span>
				<span class="font-medium">{networkStatus}</span>
			</div>

			<div
				class="ml-auto text-[11px] px-2 py-1 rounded-full border
				{ready
					? 'bg-emerald-100 text-emerald-700 border-emerald-200 dark:bg-emerald-900/30 dark:text-emerald-300 dark:border-emerald-800'
					: 'bg-amber-100 text-amber-700 border-amber-200 dark:bg-amber-900/30 dark:text-amber-300 dark:border-amber-800'}"
			>
				{#if ready}
					已就绪
				{:else}
					准备中 {$collabState.overallProgress}%
				{/if}
			</div>
		</div>
	</div>
{/if}