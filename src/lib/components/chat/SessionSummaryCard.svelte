<script lang="ts">
	export let concepts: string[] = ['라플라스 변환', '역변환'];
	export let hintCount: number = 0;
	export let nextRecommendation: string = '';
	export let onDismiss: () => void = () => {};

	let dismissed = false;

	function dismiss() {
		dismissed = true;
		onDismiss();
	}
</script>

{#if !dismissed}
	<div class="rounded-xl border border-blue-200 dark:border-blue-800/50 overflow-hidden mb-3">
		<div class="bg-blue-50 dark:bg-blue-950/30 px-4 py-2.5 flex items-center gap-2 border-b border-blue-100 dark:border-blue-800/40">
			<span>📚</span>
			<span class="text-sm font-semibold text-blue-900 dark:text-blue-200">오늘의 학습 요약</span>
			<button class="ml-auto text-xs text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition" on:click={dismiss}>닫기</button>
		</div>

		<div class="divide-y divide-blue-100 dark:divide-blue-800/30">
			<div class="px-4 py-3 bg-white dark:bg-gray-900/40 flex gap-2.5">
				<span class="text-blue-400 shrink-0">📖</span>
				<div>
					<p class="text-xs font-medium text-gray-500 dark:text-gray-400 mb-0.5">다룬 개념</p>
					<p class="text-sm text-gray-700 dark:text-gray-300">{concepts.join(', ')}</p>
				</div>
			</div>

			{#if hintCount > 0}
				<div class="px-4 py-3 bg-white dark:bg-gray-900/40 flex gap-2.5">
					<span class="text-amber-400 shrink-0">💡</span>
					<div>
						<p class="text-xs font-medium text-gray-500 dark:text-gray-400 mb-0.5">막힌 포인트</p>
						<p class="text-sm text-gray-700 dark:text-gray-300">힌트 {hintCount}회 사용</p>
					</div>
				</div>
			{/if}

			{#if nextRecommendation}
				<div class="px-4 py-3 bg-white dark:bg-gray-900/40 flex gap-2.5">
					<span class="text-green-400 shrink-0">🎯</span>
					<div>
						<p class="text-xs font-medium text-gray-500 dark:text-gray-400 mb-0.5">다음 추천 학습</p>
						<p class="text-sm text-gray-700 dark:text-gray-300">{nextRecommendation}</p>
					</div>
				</div>
			{/if}
		</div>
	</div>
{/if}
