<script lang="ts">
	import { learningSession } from '$lib/stores/learning';
	import AnswerRevealModal from './AnswerRevealModal.svelte';

	export let steps: { title: string; content: string }[] = [];
	export let answer: string = '';

	let expanded: boolean[] = [];
	let showAnswerModal = false;

	$: currentStep = $learningSession.currentHintStep;
	$: totalSteps = steps.length;

	// 이전 힌트는 열려있게 초기화
	$: {
		expanded = steps.map((_, i) => i <= currentStep);
	}

	function nextHint() {
		if (currentStep < totalSteps - 1) {
			learningSession.update((s) => ({ ...s, currentHintStep: s.currentHintStep + 1 }));
		}
	}

	function toggleExpand(i: number) {
		if (i <= currentStep) {
			expanded[i] = !expanded[i];
		}
	}

	function understood() {
		learningSession.update((s) => ({ ...s, mode: 'default' }));
	}

	function solveMyself() {
		learningSession.update((s) => ({ ...s, mode: 'solve' }));
	}
</script>

<div class="rounded-xl border border-amber-200 dark:border-amber-800/50 overflow-hidden mb-3">
	<!-- 헤더 -->
	<div class="bg-amber-50 dark:bg-amber-950/30 px-4 py-2.5 flex items-center gap-2 border-b border-amber-200 dark:border-amber-800/40">
		<span class="text-amber-500">💡</span>
		<span class="text-sm font-semibold text-amber-900 dark:text-amber-200">단계별 힌트</span>
		<span class="ml-auto text-xs text-amber-600 dark:text-amber-400">{currentStep + 1} / {totalSteps}</span>
	</div>

	<!-- 진행 바 -->
	<div class="h-1 bg-amber-100 dark:bg-amber-900/30">
		<div
			class="h-full bg-amber-400 dark:bg-amber-500 transition-all duration-500"
			style="width: {((currentStep + 1) / totalSteps) * 100}%"
		></div>
	</div>

	<!-- 힌트 목록 -->
	<div class="divide-y divide-amber-100 dark:divide-amber-800/30">
		{#each steps as step, i}
			<div class="bg-white dark:bg-gray-900/40">
				<!-- 힌트 행 헤더 -->
				<button
					class="w-full flex items-center gap-2 px-4 py-2.5 text-left
						{i <= currentStep ? 'cursor-pointer hover:bg-amber-50 dark:hover:bg-amber-950/20' : 'cursor-default opacity-40'}"
					on:click={() => toggleExpand(i)}
					disabled={i > currentStep}
				>
					{#if i < currentStep}
						<span class="text-green-500 text-xs">✅</span>
					{:else if i === currentStep}
						<span class="text-amber-500 text-xs">▶</span>
					{:else}
						<span class="text-gray-400 text-xs">🔒</span>
					{/if}
					<span class="text-sm font-medium text-gray-700 dark:text-gray-300">힌트 {i + 1}. {step.title}</span>
					{#if i <= currentStep}
						<span class="ml-auto text-gray-400 text-xs">{expanded[i] ? '▲' : '▼'}</span>
					{/if}
				</button>

				<!-- 힌트 내용 -->
				{#if i <= currentStep && expanded[i]}
					<div class="px-4 pb-3 pt-1">
						<p class="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">{step.content}</p>
					</div>
				{/if}
			</div>
		{/each}
	</div>

	<!-- 컨트롤 버튼 -->
	<div class="px-4 py-3 bg-amber-50 dark:bg-amber-950/20 border-t border-amber-100 dark:border-amber-800/30 flex flex-wrap gap-2">
		{#if currentStep < totalSteps - 1}
			<button
				class="px-3 py-1.5 rounded-lg text-xs font-medium bg-amber-500 hover:bg-amber-600 text-white transition"
				on:click={nextHint}
			>
				다음 힌트 →
			</button>
		{/if}
		<button
			class="px-3 py-1.5 rounded-lg text-xs font-medium border border-gray-300 dark:border-gray-600 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 transition"
			on:click={understood}
		>
			여기까지 이해했어요
		</button>
		<button
			class="px-3 py-1.5 rounded-lg text-xs font-medium border border-gray-300 dark:border-gray-600 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 transition"
			on:click={solveMyself}
		>
			내가 풀어볼게요
		</button>
		<button
			class="px-3 py-1.5 rounded-lg text-xs font-medium text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-400 transition ml-auto"
			on:click={() => (showAnswerModal = true)}
		>
			정답 보기
		</button>
	</div>
</div>

<AnswerRevealModal bind:show={showAnswerModal} {answer} />
