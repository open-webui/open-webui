<script lang="ts">
	export let chapters: { name: string; progress: number; status?: 'done' | 'active' | 'locked' }[] = [
		{ name: '10장. 벡터 적분법', progress: 60, status: 'active' },
		{ name: '11장. 푸리에 급수', progress: 30, status: 'active' },
		{ name: '12장. 편미분 방정식', progress: 0, status: 'locked' }
	];

	function statusColor(status: string | undefined, progress: number) {
		if (progress === 100) return 'bg-green-500';
		if (status === 'active') return 'bg-blue-500';
		return 'bg-gray-300 dark:bg-gray-600';
	}
</script>

<div class="flex flex-col gap-3">
	{#each chapters as ch}
		<div>
			<div class="flex justify-between items-center mb-1">
				<span class="text-sm text-gray-700 dark:text-gray-300 truncate">{ch.name}</span>
				<span class="text-xs text-gray-500 dark:text-gray-400 ml-2 shrink-0">{ch.progress}%</span>
			</div>
			<div class="h-2 rounded-full bg-gray-100 dark:bg-gray-700 overflow-hidden">
				<div
					class="h-full rounded-full transition-all duration-700 {statusColor(ch.status, ch.progress)}"
					style="width: {ch.progress}%"
				></div>
			</div>
		</div>
	{/each}
</div>
