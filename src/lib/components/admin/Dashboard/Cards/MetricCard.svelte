<script lang="ts">
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Info from '$lib/components/icons/Info.svelte';

	export let label: string;
	export let value: number | string;
	export let chipValue: string | null = null;
	export let chipColor: 'green' | 'red' | 'neutral' = 'neutral';
	export let isDark: boolean = false;
	export let subtitle: string | null = null;
	export let helpText: string | null = null;

	$: formattedValue =
		typeof value === 'number'
			? value >= 1000000
				? `${(value / 1000000).toFixed(1)}M`
				: value >= 1000
					? `${(value / 1000).toFixed(1)}K`
					: value.toLocaleString()
			: value;

	const chipColorClasses = {
		green: 'bg-[#5CC9D3] text-white',
		red: 'bg-red-500 text-white',
		neutral: 'bg-gray-500 text-white'
	};
</script>

<div
	class="rounded-lg border p-3 transition-all {isDark
		? 'bg-gray-800/50 border-gray-700/50'
		: 'bg-white border-gray-200 shadow-sm'}"
>
	<div class="flex flex-col gap-1">
		<div class="flex items-start justify-between gap-2">
			<span class="text-xs font-medium {isDark ? 'text-gray-400' : 'text-gray-500'}">
				{label}
			</span>
			{#if helpText}
				<Tooltip content={helpText} placement="top">
					<span
						class="shrink-0 cursor-help {isDark
							? 'text-gray-500 hover:text-gray-300'
							: 'text-gray-400 hover:text-gray-600'}"
						aria-label="Metric info"
					>
						<Info className="size-4" />
					</span>
				</Tooltip>
			{/if}
		</div>
		<div class="flex items-center gap-2">
			<span class="text-xl font-bold {isDark ? 'text-white' : 'text-gray-900'}">
				{formattedValue}
			</span>
			{#if chipValue}
				<span class="text-xs px-1.5 py-0.5 rounded-full font-medium {chipColorClasses[chipColor]}">
					{chipValue}
				</span>
			{/if}
		</div>
		{#if subtitle}
			<span class="text-xs {isDark ? 'text-gray-500' : 'text-gray-400'}">
				{subtitle}
			</span>
		{/if}
	</div>
</div>
