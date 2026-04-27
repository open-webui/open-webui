<script lang="ts">
	import type { ActionType } from '$lib/types/learning';

	export let summary: string = '';
	export let checkQuestion: string | undefined = undefined;
	export let choices: string[] = [];
	export let onChoiceSelect: (index: number) => void = () => {};

	let selectedChoice: number | null = null;

	function handleChoice(index: number) {
		selectedChoice = index;
		onChoiceSelect(index);
	}
</script>

<div class="rounded-xl border border-blue-200 dark:border-blue-800/50 overflow-hidden mb-3">
	<!-- 핵심 요약 블록 -->
	<div class="bg-blue-50 dark:bg-blue-950/40 px-4 py-3 flex gap-2.5 items-start">
		<span class="text-blue-500 mt-0.5 shrink-0">📌</span>
		<p class="text-sm text-blue-900 dark:text-blue-100 leading-relaxed font-medium">{summary}</p>
	</div>

	<!-- 확인 질문 (있을 때) -->
	{#if checkQuestion}
		<div class="border-t border-blue-100 dark:border-blue-800/40 px-4 py-3 bg-white dark:bg-gray-900/50 flex gap-2.5 items-start">
			<span class="text-amber-500 mt-0.5 shrink-0">❓</span>
			<p class="text-sm text-gray-800 dark:text-gray-200">{checkQuestion}</p>
		</div>
	{/if}

	<!-- 객관식 보기 (있을 때) -->
	{#if choices.length > 0}
		<div class="border-t border-blue-100 dark:border-blue-800/40 px-4 py-3 bg-white dark:bg-gray-900/50 flex flex-col gap-2">
			{#each choices as choice, i}
				<button
					class="text-left text-sm px-3 py-2 rounded-lg border transition
						{selectedChoice === i
							? 'bg-blue-600 border-blue-600 text-white'
							: 'border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800'}"
					on:click={() => handleChoice(i)}
				>
					<span class="font-medium mr-1.5">{['①', '②', '③', '④', '⑤'][i]}</span>{choice}
				</button>
			{/each}
		</div>
	{/if}
</div>
