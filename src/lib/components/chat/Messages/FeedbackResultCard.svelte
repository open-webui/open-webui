<script lang="ts">
	import ActionBar from './ResponseMessage/ActionBar.svelte';
	import { learningSession } from '$lib/stores/learning';

	export let correctParts: string = '라플라스 변환의 정의를 올바르게 적용했습니다.';
	export let errorStep: string | undefined = '3단계: 역변환 적용';
	export let errorTags: string[] = ['계산 오류', '부호 실수'];

	const tagColors: Record<string, string> = {
		'개념 오류': 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 border-red-300 dark:border-red-700',
		'계산 오류': 'bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300 border-amber-300 dark:border-amber-700',
		'식 전개 오류': 'bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-300 border-orange-300 dark:border-orange-700',
		'부호 실수': 'bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300 border-purple-300 dark:border-purple-700'
	};

	const defaultTagColor = 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 border-gray-300 dark:border-gray-600';
</script>

<div class="rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden mb-3">
	<!-- 헤더 -->
	<div class="px-4 py-2.5 bg-gray-50 dark:bg-gray-800/60 border-b border-gray-200 dark:border-gray-700 flex items-center gap-2">
		<span>📋</span>
		<span class="text-sm font-semibold text-gray-800 dark:text-gray-200">풀이 피드백</span>
	</div>

	<div class="divide-y divide-gray-100 dark:divide-gray-700/50">
		<!-- 맞게 접근한 부분 -->
		<div class="px-4 py-3 bg-white dark:bg-gray-900/40 flex gap-2.5">
			<span class="text-green-500 mt-0.5 shrink-0">✅</span>
			<div>
				<p class="text-xs font-medium text-green-600 dark:text-green-400 mb-0.5">맞게 접근한 부분</p>
				<p class="text-sm text-gray-700 dark:text-gray-300">{correctParts}</p>
			</div>
		</div>

		<!-- 의심되는 오류 단계 -->
		{#if errorStep}
			<div class="px-4 py-3 bg-white dark:bg-gray-900/40 flex gap-2.5">
				<span class="text-amber-500 mt-0.5 shrink-0">⚠️</span>
				<div>
					<p class="text-xs font-medium text-amber-600 dark:text-amber-400 mb-0.5">의심되는 오류 단계</p>
					<p class="text-sm text-gray-700 dark:text-gray-300">{errorStep}</p>
				</div>
			</div>
		{/if}

		<!-- 오류 유형 태그 -->
		{#if errorTags.length > 0}
			<div class="px-4 py-3 bg-white dark:bg-gray-900/40">
				<p class="text-xs font-medium text-gray-500 dark:text-gray-400 mb-2">오류 유형</p>
				<div class="flex flex-wrap gap-1.5">
					{#each errorTags as tag}
						<span class="px-2.5 py-0.5 rounded-full text-xs border {tagColors[tag] ?? defaultTagColor}">
							{tag}
						</span>
					{/each}
				</div>
			</div>
		{/if}
	</div>

	<!-- 재학습 액션 -->
	<div class="px-4 pb-3 pt-1 bg-gray-50 dark:bg-gray-800/40 border-t border-gray-100 dark:border-gray-700/50">
		<p class="text-xs text-gray-400 dark:text-gray-500 mb-1.5">다음으로</p>
		<ActionBar
			actions={['hint', 'similar_problem', 'solve_myself']}
			onAction={(type) => {
				if (type === 'hint') learningSession.update((s) => ({ ...s, mode: 'hint', currentHintStep: 0 }));
				else if (type === 'solve_myself') learningSession.update((s) => ({ ...s, mode: 'solve' }));
				else if (type === 'similar_problem') learningSession.update((s) => ({ ...s, mode: 'default' }));
			}}
		/>
	</div>
</div>
