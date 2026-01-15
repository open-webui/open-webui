<script lang="ts">
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Info from '$lib/components/icons/Info.svelte';

	export let line: string;
	export let system: string | null = null;
	export let dpmo: number | null = null;
	export let totalUnits: number | null = null;
	export let changePercent: number = 0;
	export let isDark: boolean = false;
	export let onClick: (() => void) | null = null;
	export let dpmoHelpText: string | null = null;
	export let isEstimated: boolean = false;
	export let historicalDpmo: number | null = null;

	$: hasDpmo = dpmo !== null && dpmo !== undefined;
	$: hasUnits = totalUnits !== null && totalUnits !== undefined;
	$: hasHistorical = historicalDpmo !== null && historicalDpmo !== undefined;
	$: chipColor = changePercent > 0 ? 'red' : changePercent < 0 ? 'green' : 'neutral';
	$: chipValue = hasDpmo && changePercent !== 0 ? `${changePercent > 0 ? '+' : ''}${changePercent.toFixed(1)}%` : null;
	$: formattedDPMO = hasDpmo ? dpmo.toLocaleString(undefined, { maximumFractionDigits: 0 }) : 'N/A';
	$: formattedHistorical = hasHistorical ? historicalDpmo.toLocaleString(undefined, { maximumFractionDigits: 0 }) : null;
	$: formattedUnits = hasUnits
		? totalUnits >= 1000000
			? `${(totalUnits / 1000000).toFixed(1)}M`
			: totalUnits >= 1000
				? `${(totalUnits / 1000).toFixed(1)}K`
				: totalUnits.toString()
		: 'N/A';

	const chipColorClasses = {
		green: 'bg-[#5CC9D3] text-white',
		red: 'bg-red-500 text-white',
		neutral: 'bg-gray-500 text-white'
	};
</script>

<button
	class="w-full text-left rounded-lg border p-4 transition-all {isDark
		? 'bg-gray-800/50 border-gray-700/50 shadow-[0_0_15px_rgba(92,201,211,0.15)] hover:border-[#5CC9D3]/50'
		: 'bg-white border-gray-200 shadow-md hover:border-[#5CC9D3]'} {onClick ? 'cursor-pointer' : 'cursor-default'}"
	on:click={onClick}
	disabled={!onClick}
>
	<div class="flex flex-col gap-2">
		<div class="flex items-center justify-between">
			<span class="text-sm font-medium {isDark ? 'text-white' : 'text-gray-900'}">
				{line}
				{#if system}
					<span class="text-xs {isDark ? 'text-gray-400' : 'text-gray-500'}">({system})</span>
				{/if}
			</span>
			<div class="flex items-center gap-1">
				<span class="text-xs {isDark ? 'text-gray-400' : 'text-gray-500'}">DPMO</span>
				{#if dpmoHelpText}
					<Tooltip content={dpmoHelpText} placement="top">
						<span
							class="shrink-0 cursor-help {isDark
								? 'text-gray-500 hover:text-gray-300'
								: 'text-gray-400 hover:text-gray-600'}"
							aria-label="DPMO info"
						>
							<Info className="size-4" />
						</span>
					</Tooltip>
				{/if}
			</div>
		</div>

		<div class="flex items-end justify-between">
			<div class="flex flex-col gap-1">
				<div class="flex items-center gap-2">
					<span class="text-2xl font-bold {isDark ? 'text-white' : 'text-gray-900'}">
						{formattedDPMO}
					</span>
					{#if isEstimated && hasDpmo}
						<span class="text-xs px-2 py-0.5 rounded-full font-medium bg-amber-500 text-white">
							Est.
						</span>
					{/if}
					{#if chipValue}
						<span class="text-xs px-2 py-0.5 rounded-full font-medium {chipColorClasses[chipColor]}">
							{chipValue}
						</span>
					{/if}
				</div>
				{#if formattedHistorical}
					<span class="text-xs {isDark ? 'text-gray-500' : 'text-gray-400'}">
						vs {formattedHistorical} prev period
					</span>
				{/if}
			</div>
			<span class="text-xs {isDark ? 'text-gray-500' : 'text-gray-400'}">
				{formattedUnits} units
			</span>
		</div>
	</div>
</button>
