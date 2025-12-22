<script lang="ts">
	import Bars3BottomLeft from '$lib/components/icons/Bars3BottomLeft.svelte';
	import Grid from '$lib/components/icons/Grid.svelte';

	export let value: 'list' | 'grid' = 'list';
</script>

<div class="flex gap-0.5 bg-gray-50 dark:bg-gray-850 rounded-xl p-0.5">
	<button
		class="p-1.5 rounded-lg transition {value === 'list' ? 'bg-white dark:bg-gray-700 shadow-sm' : 'hover:bg-gray-100 dark:hover:bg-gray-800'}"
		on:click={() => value = 'list'}
		title="리스트 보기"
	>
		<Bars3BottomLeft className="size-4 text-gray-600 dark:text-gray-400" />
	</button>
	<button
		class="p-1.5 rounded-lg transition {value === 'grid' ? 'bg-white dark:bg-gray-700 shadow-sm' : 'hover:bg-gray-100 dark:hover:bg-gray-800'}"
		on:click={() => value = 'grid'}
		title="그리드 보기"
	>
		<Grid className="size-4 text-gray-600 dark:text-gray-400" />
	</button>
</div>
