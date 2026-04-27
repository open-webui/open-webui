<script lang="ts">
	import type { ActionType } from '$lib/types/learning';

	export let actions: ActionType[] = ['hint', 'solve_myself', 'similar_problem', 'quiz', 'graph'];
	export let onAction: (type: ActionType) => void = () => {};

	const actionConfig: Record<ActionType, { icon: string; label: string }> = {
		hint: { icon: '💡', label: '한 단계 힌트' },
		solve_myself: { icon: '✏️', label: '내가 먼저 풀기' },
		similar_problem: { icon: '🔗', label: '비슷한 문제' },
		quiz: { icon: '📝', label: '퀴즈로 확인' },
		graph: { icon: '📈', label: '그래프로 보기' }
	};
</script>

<div class="flex flex-wrap gap-1.5 mt-2">
	{#each actions as action}
		<button
			class="flex items-center gap-1 px-3 py-1 rounded-full text-xs border border-gray-300 dark:border-gray-600
				text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700
				hover:border-gray-400 dark:hover:border-gray-500 transition"
			on:click={() => onAction(action)}
		>
			<span>{actionConfig[action].icon}</span>
			<span>{actionConfig[action].label}</span>
		</button>
	{/each}
</div>
