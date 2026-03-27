<script lang="ts">
	import { collabState } from '$lib/stores/collab';
	import { slide } from 'svelte/transition';

	$: edgeRange = $collabState.split?.edgeRange ?? 'L0-L15';
	$: cloudRange = $collabState.split?.cloudRange ?? 'L16-L31';
	$: currentLayer = $collabState.split?.currentLayer ?? 16;
	$: totalLayers = $collabState.split?.totalLayers ?? 32;
	$: splitPoint = totalLayers ? `L${currentLayer}` : '--';

	$: networkStatus = $collabState.network?.status ?? '稳定';
	$: rtt = $collabState.network?.rtt ?? 28;
	$: bandwidth = $collabState.network?.bandwidth ?? 84;

	$: overall = $collabState.overallProgress ?? 0;
	$: edgeProgress = $collabState.edge?.progress ?? 0;
	$: cloudProgress = $collabState.cloud?.progress ?? 0;

	$: layerMarks = Array.from({ length: 32 }, (_, i) => i);

	$: phaseLabel =
		$collabState.phase === 'completed'
			? '协同就绪'
			: $collabState.phase === 'cloud_loading'
				? '云端加载中'
				: $collabState.phase === 'edge_loading'
					? '边端加载中'
					: $collabState.phase === 'split_ready'
						? '切分完成'
						: '协同准备中';
</script>

{#if $collabState.enabled && $collabState.ribbonExpanded}
	<div
		transition:slide={{ duration: 180 }}
		class="w-full rounded-[22px] border border-gray-200/80 dark:border-gray-800 bg-white/95 dark:bg-gray-900/95 shadow-[0_10px_30px_rgba(0,0,0,0.06)] px-4 py-4"
	>
		<div class="flex flex-col gap-4">
			<div class="flex items-center justify-between gap-3">
				<div class="flex items-center gap-2.5">
					<span class="inline-flex items-center justify-center w-2.5 h-2.5 rounded-full bg-emerald-500"></span>
					<div class="flex flex-col">
						<div class="text-sm font-semibold text-gray-900 dark:text-gray-100">边云协同准备中</div>
						<div class="text-[11px] text-gray-500 dark:text-gray-400">
							边端与云端正在建立联合推理上下文
						</div>
					</div>
				</div>

				<div class="text-xs px-2.5 py-1 rounded-full bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-300 border border-gray-200 dark:border-gray-700">
					{phaseLabel}
				</div>
			</div>

			<div class="rounded-2xl border border-gray-200/70 dark:border-gray-800 bg-gray-50/70 dark:bg-gray-850/70 px-4 py-3">
				<div class="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400 mb-2">
					<span>整体进度</span>
					<span class="font-medium text-gray-700 dark:text-gray-200">{overall}%</span>
				</div>

				<div class="w-full h-6 rounded-full bg-gray-200 dark:bg-gray-800 overflow-hidden">
					<div
						class="h-full rounded-full bg-linear-to-r from-sky-400 via-sky-500 to-cyan-500 transition-all duration-300"
						style="width: {overall}%"
					></div>
				</div>

			</div>

			<div class="grid grid-cols-1 lg:grid-cols-2 gap-3">
				<div class="rounded-[20px] border border-sky-200/70 dark:border-sky-900/60 bg-sky-50/70 dark:bg-sky-950/20 px-4 py-4">
					<div class="flex items-start justify-between gap-3 mb-3">
						<div>
							<div class="text-sm font-semibold text-sky-900 dark:text-sky-200">边端执行</div>
							<div class="text-xs text-sky-800/80 dark:text-sky-300/80 mt-1">
								Qwen2.5-0.5B · Local Device
							</div>
						</div>

						<div class="text-[11px] px-2.5 py-1 rounded-full bg-white/80 dark:bg-gray-900/60 text-sky-700 dark:text-sky-300 border border-sky-200/60 dark:border-sky-900/50">
							{$collabState.edge?.status ?? '准备中'}
						</div>
					</div>

					<div class="flex items-center justify-between text-[11px] text-sky-900/80 dark:text-sky-200/80 mb-2">
						<span>层范围 {edgeRange}</span>
						<span>{edgeProgress}%</span>
					</div>

					<div class="w-full h-6 rounded-full bg-sky-100 dark:bg-sky-950/40 overflow-hidden mb-3">
						<div
							class="h-full rounded-full bg-linear-to-r from-sky-400 via-blue-500 to-cyan-500 transition-all duration-300"
							style="width: {edgeProgress}%"
						></div>
					</div>

					<div class="grid grid-cols-2 gap-2 text-[11px] text-sky-900/75 dark:text-sky-200/75">
						<div class="rounded-xl bg-white/60 dark:bg-gray-900/30 px-2.5 py-2">状态：边端预热</div>
						<div class="rounded-xl bg-white/60 dark:bg-gray-900/30 px-2.5 py-2">缓存：KV Ready</div>
					</div>
				</div>

				<div class="rounded-[20px] border border-violet-200/70 dark:border-violet-900/60 bg-violet-50/70 dark:bg-violet-950/20 px-4 py-4">
					<div class="flex items-start justify-between gap-3 mb-3">
						<div>
							<div class="text-sm font-semibold text-violet-900 dark:text-violet-200">云端执行</div>
							<div class="text-xs text-violet-800/80 dark:text-violet-300/80 mt-1">
								Qwen2.5-0.5B · Remote Node
							</div>
						</div>

						<div class="text-[11px] px-2.5 py-1 rounded-full bg-white/80 dark:bg-gray-900/60 text-violet-700 dark:text-violet-300 border border-violet-200/60 dark:border-violet-900/50">
							{$collabState.cloud?.status ?? '准备中'}
						</div>
					</div>

					<div class="flex items-center justify-between text-[11px] text-violet-900/80 dark:text-violet-200/80 mb-2">
						<span>层范围 {cloudRange}</span>
						<span>{cloudProgress}%</span>
					</div>

					<div class="w-full h-4 rounded-full bg-amber-100 dark:bg-amber-950/30 overflow-hidden mb-3">
						<div
							class="h-full rounded-full bg-linear-to-r from-amber-300 via-orange-400 to-yellow-400 transition-all duration-300"
							style="width: {cloudProgress}%"
						></div>
					</div>

					<div class="grid grid-cols-2 gap-2 text-[11px] text-violet-900/75 dark:text-violet-200/75">
						<div class="rounded-xl bg-white/60 dark:bg-gray-900/30 px-2.5 py-2">状态：云端装载</div>
						<div class="rounded-xl bg-white/60 dark:bg-gray-900/30 px-2.5 py-2">队列：已分配</div>
					</div>
				</div>
			</div>

			<div class="rounded-[20px] border border-gray-200/70 dark:border-gray-800 bg-gray-50/80 dark:bg-gray-850/80 px-4 py-4">
	<div class="flex items-center justify-between gap-3 mb-3">
		<div>
			<div class="text-sm font-semibold text-gray-900 dark:text-gray-100">模型切分</div>
			<div class="text-[11px] text-gray-500 dark:text-gray-400 mt-1">
				静态分层策略 · 切分点 {splitPoint}
			</div>
		</div>

		<div class="text-[11px] px-2.5 py-1 rounded-full bg-white/80 dark:bg-gray-900/60 border border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-300">
			{edgeRange} / {cloudRange}
		</div>
	</div>

	<div class="w-full h-5 rounded-full bg-gray-200 dark:bg-gray-800 overflow-hidden flex mb-2 shadow-inner relative">
		<div
			class="h-full bg-linear-to-r from-sky-400 via-blue-500 to-cyan-500 flex items-center justify-center text-[10px] text-white font-medium"
			style="width: 50%"
		>
			边端
		</div>
		<div
			class="h-full bg-linear-to-r from-amber-300 via-orange-400 to-yellow-400 flex items-center justify-center text-[10px] text-white font-medium"
			style="width: 50%"
		>
			云端
		</div>
	</div>

	<div class="relative mb-3 px-[2px]">
		<div class="grid grid-cols-32 gap-0 text-[9px] text-gray-500 dark:text-gray-400">
			{#each layerMarks as layer}
				<div class="flex flex-col items-center min-w-0">
					<div
						class="w-px h-2 {layer === currentLayer
							? 'bg-red-500'
							: 'bg-gray-300 dark:bg-gray-600'}"
					></div>
					<div
						class="mt-1 leading-none {layer === currentLayer
							? 'text-red-500 font-semibold'
							: ''}"
					>
						{layer}
					</div>
				</div>
			{/each}
		</div>
	</div>

	<div class="grid grid-cols-1 md:grid-cols-3 gap-2 text-xs text-gray-600 dark:text-gray-300">
		<div class="rounded-xl bg-white/70 dark:bg-gray-900/30 px-3 py-2">边端层：{edgeRange}</div>
		<div class="rounded-xl bg-white/70 dark:bg-gray-900/30 px-3 py-2">云端层：{cloudRange}</div>
		<div class="rounded-xl bg-white/70 dark:bg-gray-900/30 px-3 py-2">切分点：{splitPoint}</div>
	</div>
</div>
			<div class="rounded-[20px] border border-gray-200/70 dark:border-gray-800 bg-gray-50/80 dark:bg-gray-850/80 px-4 py-4">
				<div class="flex items-center justify-between gap-3 mb-3">
					<div class="text-sm font-semibold text-gray-900 dark:text-gray-100">链路状态</div>

					<div class="text-[11px] px-2.5 py-1 rounded-full bg-emerald-100 text-emerald-700 border border-emerald-200 dark:bg-emerald-900/30 dark:text-emerald-300 dark:border-emerald-800">
						{networkStatus}
					</div>
				</div>

				<div class="grid grid-cols-1 md:grid-cols-3 gap-2 text-xs text-gray-600 dark:text-gray-300">
					<div class="rounded-xl bg-white/70 dark:bg-gray-900/30 px-3 py-2">RTT：{rtt} ms</div>
					<div class="rounded-xl bg-white/70 dark:bg-gray-900/30 px-3 py-2">带宽：{bandwidth} Mbps</div>
					<div class="rounded-xl bg-white/70 dark:bg-gray-900/30 px-3 py-2">链路：稳定连接</div>
				</div>
			</div>

			{#if $collabState.error}
				<div class="rounded-[20px] border border-red-200 dark:border-red-900 bg-red-50 dark:bg-red-950/20 px-4 py-3 text-xs text-red-700 dark:text-red-300">
					错误：{$collabState.error?.message ?? '未知错误'}
				</div>
			{/if}
		</div>
	</div>
{/if}