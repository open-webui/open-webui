<script lang="ts">
	export let tags: { label: string; count: number }[] = [
		{ label: '라플라스 역변환', count: 5 },
		{ label: '벡터 내적', count: 4 },
		{ label: '푸리에 계수', count: 3 },
		{ label: '편미분', count: 2 },
		{ label: '그린의 정리', count: 2 }
	];

	$: maxCount = Math.max(...tags.map((t) => t.count), 1);

	function sizeClass(count: number) {
		const ratio = count / maxCount;
		if (ratio > 0.8) return 'text-base font-semibold';
		if (ratio > 0.5) return 'text-sm font-medium';
		return 'text-xs';
	}

	function colorClass(count: number) {
		const ratio = count / maxCount;
		if (ratio > 0.8) return 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 border-red-200 dark:border-red-700';
		if (ratio > 0.5) return 'bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300 border-amber-200 dark:border-amber-700';
		return 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 border-gray-200 dark:border-gray-700';
	}
</script>

<div class="flex flex-wrap gap-2">
	{#each tags as tag}
		<span class="px-2.5 py-1 rounded-full border {sizeClass(tag.count)} {colorClass(tag.count)}">
			{tag.label}
			<span class="ml-1 opacity-60">×{tag.count}</span>
		</span>
	{/each}
</div>
