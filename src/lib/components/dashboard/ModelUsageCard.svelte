<script lang="ts">
	import { getContext } from 'svelte';

	const i18n = getContext('i18n');

	export let modelStats: { model: string; tokens: number; requests: number }[] = [];
	export let totalUsed = 0;

	const modelLabels: Record<string, string> = {
		'claude-haiku-4-5': 'Claude Haiku 4.5',
		'claude-haiku-4-5-20251001': 'Claude Haiku 4.5',
		'claude-sonnet-4-6': 'Claude Sonnet 4.6',
		'claude-opus-4-7': 'Claude Opus 4.7',
		'mistral-medium': 'Mistral Medium 3'
	};

	const barColors = ['#0D5C3F', '#E07020', '#2a8f62', '#c45e15', '#6b9e85'];

	function label(model: string) {
		return modelLabels[model] ?? model;
	}

	function pct(tokens: number) {
		if (!totalUsed) return 0;
		return Math.min(Math.round((tokens / totalUsed) * 100), 100);
	}

	function fmt(n: number) {
		if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + 'M';
		if (n >= 1_000) return (n / 1_000).toFixed(1) + 'K';
		return n.toString();
	}
</script>

<div class="rounded-2xl p-6 border bg-white dark:bg-gray-800 border-black/[.07] dark:border-white/[.07]">
	<div class="flex items-center justify-between mb-5">
		<p class="text-[10px] font-semibold uppercase tracking-[.12em] text-gray-400 dark:text-white/40">
			{$i18n.t('Usage by model')}
		</p>
		{#if modelStats.length > 0}
			<span class="text-[10px] font-mono text-gray-300 dark:text-gray-600">
				{modelStats.reduce((s, m) => s + m.requests, 0)} {$i18n.t('total requests')}
			</span>
		{/if}
	</div>

	{#if modelStats.length === 0}
		<div class="flex items-center gap-6 py-2">
			<div class="flex-1 space-y-3">
				{#each ['Claude Haiku 4.5', 'Claude Sonnet 4.6'] as name}
					<div>
						<div class="flex justify-between mb-1.5">
							<span class="text-xs text-gray-300 dark:text-gray-600">{name}</span>
						</div>
						<div class="w-full h-1.5 rounded-full bg-gray-100 dark:bg-gray-700" />
					</div>
				{/each}
			</div>
			<p class="text-xs text-gray-300 dark:text-gray-600 max-w-[180px] text-right shrink-0">
				{$i18n.t('Stats appear after your first conversations')}
			</p>
		</div>
	{:else}
		<div class="space-y-3.5">
			{#each modelStats as stat, i}
				<div>
					<div class="flex items-center justify-between mb-1.5">
						<span class="text-sm text-gray-700 dark:text-gray-300">{label(stat.model)}</span>
						<div class="flex items-center gap-4">
							<span class="text-xs text-gray-400 dark:text-gray-500 font-mono">{stat.requests} req</span>
							<span class="text-xs font-mono font-semibold w-12 text-right tabular-nums text-gray-700 dark:text-gray-300">
								{fmt(stat.tokens)}
							</span>
							<span class="text-[10px] font-mono w-8 text-right tabular-nums text-gray-300 dark:text-gray-600">
								{pct(stat.tokens)}%
							</span>
						</div>
					</div>
					<div class="w-full h-1.5 rounded-full bg-gray-100 dark:bg-gray-700 overflow-hidden">
						<div
							class="h-full rounded-full"
							style="width:{pct(stat.tokens)}%;background:{barColors[i % barColors.length]};transition:width 1s cubic-bezier(.4,0,.2,1)"
						/>
					</div>
				</div>
			{/each}
		</div>
	{/if}
</div>
