<script lang="ts">
	export let isCorrect: boolean;
	export let explanation: string;
	export let correctIndex: number;
	export let selectedChoice: number | null;
	export let choices: string[] = [];
	export let onNext: () => void = () => {};
	export let onExit: () => void = () => {};
	export let isLast: boolean = false;
</script>

<div>
	<!-- 정오답 표시 -->
	<div class="flex items-center gap-2 mb-3">
		{#if isCorrect}
			<span class="text-2xl">✅</span>
			<p class="text-base font-semibold text-green-600 dark:text-green-400">정답입니다!</p>
		{:else}
			<span class="text-2xl">❌</span>
			<p class="text-base font-semibold text-red-500 dark:text-red-400">오답입니다.</p>
		{/if}
	</div>

	<!-- 정답 표시 (오답일 때) -->
	{#if !isCorrect && choices.length > 0}
		<div class="mb-3 text-sm text-gray-600 dark:text-gray-400">
			정답: <span class="font-semibold text-green-600 dark:text-green-400">{['①', '②', '③', '④'][correctIndex]} {choices[correctIndex]}</span>
		</div>
	{/if}

	<!-- 해설 -->
	<div class="bg-gray-50 dark:bg-gray-800/60 rounded-lg px-3 py-2.5 mb-4 border border-gray-200 dark:border-gray-700">
		<p class="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">해설</p>
		<p class="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">{explanation}</p>
	</div>

	<!-- 액션 버튼 -->
	<div class="flex gap-2 flex-wrap">
		{#if !isLast}
			<button
				class="px-4 py-1.5 rounded-lg text-sm font-medium bg-purple-600 hover:bg-purple-700 text-white transition"
				on:click={onNext}
			>
				다음 문제 →
			</button>
		{:else}
			<button
				class="px-4 py-1.5 rounded-lg text-sm font-medium bg-purple-600 hover:bg-purple-700 text-white transition"
				on:click={onExit}
			>
				퀴즈 완료 🎉
			</button>
		{/if}
		<button
			class="px-4 py-1.5 rounded-lg text-sm font-medium border border-gray-300 dark:border-gray-600 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 transition"
			on:click={onExit}
		>
			퀴즈 종료
		</button>
	</div>
</div>
