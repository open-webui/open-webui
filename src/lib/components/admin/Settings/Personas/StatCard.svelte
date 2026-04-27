<script lang="ts">
	export let title: string;
	export let value: string | number;
	export let icon: string | undefined = undefined;
	export let status: 'ok' | 'warn' | 'critical' | undefined = undefined;
	export let delta: { value: number; direction: 'up' | 'down'; isGood: boolean } | undefined = undefined;
	export let hint: string | undefined = undefined;

	$: borderClass =
		status === 'critical'
			? 'border-l-4 border-l-red-500'
			: status === 'warn'
				? 'border-l-4 border-l-yellow-500'
				: status === 'ok'
					? 'border-l-4 border-l-green-500'
					: '';
	$: dotClass =
		status === 'critical'
			? 'bg-red-500'
			: status === 'warn'
				? 'bg-yellow-500'
				: status === 'ok'
					? 'bg-green-500'
					: '';
	$: deltaColor = delta
		? delta.isGood
			? 'text-green-600 dark:text-green-400'
			: 'text-red-600 dark:text-red-400'
		: '';
	$: deltaArrow = delta ? (delta.direction === 'up' ? '↑' : '↓') : '';
</script>

<div
	class="stat-card p-4 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 shadow-sm {borderClass}"
>
	<div class="flex items-start justify-between">
		<div class="flex-1 min-w-0">
			<h3 class="text-sm text-gray-500 dark:text-gray-400 truncate">
				{title}
			</h3>
			<p class="text-2xl font-bold text-gray-900 dark:text-white mt-2">
				{value}
			</p>
			{#if delta}
				<p class="text-xs mt-1 {deltaColor} font-medium">
					{deltaArrow} {Math.abs(delta.value).toFixed(1)}% vs 이전
				</p>
			{:else if hint}
				<p class="text-xs mt-1 text-gray-400 dark:text-gray-500">{hint}</p>
			{/if}
		</div>
		<div class="flex flex-col items-end gap-2">
			{#if status}
				<span class="inline-block w-2 h-2 rounded-full {dotClass}" aria-hidden="true"></span>
			{/if}
			{#if icon}
				<div class="text-gray-400 dark:text-gray-500">
					{@html icon}
				</div>
			{/if}
		</div>
	</div>
</div>
