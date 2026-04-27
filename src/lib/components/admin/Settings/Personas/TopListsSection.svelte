<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import type {
		TopTokenUser,
		TopExpensiveCall,
		TopSlowCall
	} from '$lib/apis/analytics';

	export let topTokenUsers: TopTokenUser[] = [];
	export let topExpensive: TopExpensiveCall[] = [];
	export let topSlow: TopSlowCall[] = [];

	const dispatch = createEventDispatcher<{ select: { traceId: string } }>();

	const formatTime = (iso: string): string => {
		try {
			const d = new Date(iso);
			const mm = String(d.getMonth() + 1).padStart(2, '0');
			const dd = String(d.getDate()).padStart(2, '0');
			const hh = String(d.getHours()).padStart(2, '0');
			const mi = String(d.getMinutes()).padStart(2, '0');
			return `${mm}-${dd} ${hh}:${mi}`;
		} catch {
			return iso;
		}
	};

	const formatLatency = (ms: number): string =>
		ms < 1000 ? `${Math.round(ms)}ms` : `${(ms / 1000).toFixed(2)}s`;

	const onSelect = (traceId: string) => dispatch('select', { traceId });

	$: hasAny =
		(topTokenUsers && topTokenUsers.length > 0) ||
		(topExpensive && topExpensive.length > 0) ||
		(topSlow && topSlow.length > 0);
</script>

{#if hasAny}
	<div class="top-lists border border-gray-200 dark:border-gray-700 rounded-lg p-4 bg-white dark:bg-gray-800">
		<h4 class="text-sm font-semibold text-gray-900 dark:text-white mb-3">Top 운영 지표</h4>
		<div class="grid grid-cols-1 md:grid-cols-3 gap-4">
			<!-- Top Token Users -->
			<div>
				<h5 class="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-2">
					Top 토큰 사용자
				</h5>
				{#if topTokenUsers && topTokenUsers.length > 0}
					<ul class="divide-y divide-gray-100 dark:divide-gray-700">
						{#each topTokenUsers as u, i}
							<li class="py-2 flex items-center gap-2">
								<span class="w-5 text-xs text-gray-400 font-mono">#{i + 1}</span>
								<div class="flex-1 min-w-0">
									<p class="text-sm text-gray-900 dark:text-white truncate">
										{u.name || u.user_id.slice(0, 8)}
									</p>
									<p class="text-xs text-gray-500 dark:text-gray-400">
										{u.tokens.toLocaleString()} tokens · {u.calls} calls
									</p>
								</div>
							</li>
						{/each}
					</ul>
				{:else}
					<p class="text-xs text-gray-400 py-2">데이터 없음</p>
				{/if}
			</div>

			<!-- Top Expensive Calls -->
			<div>
				<h5 class="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-2">
					Top 비싼 호출
				</h5>
				{#if topExpensive && topExpensive.length > 0}
					<ul class="divide-y divide-gray-100 dark:divide-gray-700">
						{#each topExpensive as c, i}
							<li class="py-2 flex items-center gap-2">
								<span class="w-5 text-xs text-gray-400 font-mono">#{i + 1}</span>
								<button
									type="button"
									class="flex-1 min-w-0 text-left hover:bg-gray-50 dark:hover:bg-gray-700/50 rounded px-1 -mx-1 py-0.5 transition"
									on:click={() => onSelect(c.trace_id)}
								>
									<p class="text-sm text-green-600 dark:text-green-400 font-medium">
										${c.cost_usd.toFixed(4)}
									</p>
									<p class="text-xs text-gray-500 dark:text-gray-400 truncate font-mono">
										{formatTime(c.timestamp)} · {c.model || '-'}
									</p>
								</button>
							</li>
						{/each}
					</ul>
				{:else}
					<p class="text-xs text-gray-400 py-2">데이터 없음</p>
				{/if}
			</div>

			<!-- Top Slow Calls -->
			<div>
				<h5 class="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-2">
					Top 느린 호출
				</h5>
				{#if topSlow && topSlow.length > 0}
					<ul class="divide-y divide-gray-100 dark:divide-gray-700">
						{#each topSlow as s, i}
							<li class="py-2 flex items-center gap-2">
								<span class="w-5 text-xs text-gray-400 font-mono">#{i + 1}</span>
								<button
									type="button"
									class="flex-1 min-w-0 text-left hover:bg-gray-50 dark:hover:bg-gray-700/50 rounded px-1 -mx-1 py-0.5 transition"
									on:click={() => onSelect(s.trace_id)}
								>
									<p class="text-sm text-orange-600 dark:text-orange-400 font-medium">
										{formatLatency(s.latency_ms)}
									</p>
									<p class="text-xs text-gray-500 dark:text-gray-400 truncate font-mono">
										{formatTime(s.timestamp)} · {s.model || '-'}
									</p>
								</button>
							</li>
						{/each}
					</ul>
				{:else}
					<p class="text-xs text-gray-400 py-2">데이터 없음</p>
				{/if}
			</div>
		</div>
	</div>
{/if}
