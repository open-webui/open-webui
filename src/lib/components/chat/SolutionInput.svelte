<script lang="ts">
	import { learningSession } from '$lib/stores/learning';
	import { createEventDispatcher } from 'svelte';

	const dispatch = createEventDispatcher();

	let solutionText = '';
	let submitted = false;

	function submit() {
		if (!solutionText.trim()) return;
		submitted = true;
		dispatch('submit', { solution: solutionText });
	}

	function cancel() {
		solutionText = '';
		submitted = false;
		learningSession.update((s) => ({ ...s, mode: 'default' }));
	}
</script>

<div class="rounded-xl border border-green-200 dark:border-green-800/50 overflow-hidden mb-3">
	<!-- 헤더 -->
	<div class="bg-green-50 dark:bg-green-950/30 px-4 py-2.5 flex items-center gap-2 border-b border-green-200 dark:border-green-800/40">
		<span class="text-green-600">✏️</span>
		<span class="text-sm font-semibold text-green-900 dark:text-green-200">내 풀이 작성</span>
		<button
			class="ml-auto text-xs text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition"
			on:click={cancel}
		>
			취소
		</button>
	</div>

	<div class="p-4 bg-white dark:bg-gray-900/50">
		<textarea
			class="w-full min-h-[120px] text-sm bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700
				rounded-lg px-3 py-2.5 text-gray-800 dark:text-gray-200 resize-none focus:outline-none
				focus:ring-2 focus:ring-green-400 dark:focus:ring-green-600 placeholder-gray-400 dark:placeholder-gray-600"
			placeholder="여기에 풀이 과정을 입력하세요..."
			bind:value={solutionText}
			disabled={submitted}
		></textarea>

		<div class="flex justify-end mt-2">
			<button
				class="px-4 py-2 rounded-lg text-sm font-medium transition
					{solutionText.trim()
						? 'bg-green-600 hover:bg-green-700 text-white'
						: 'bg-gray-200 dark:bg-gray-700 text-gray-400 cursor-not-allowed'}"
				disabled={!solutionText.trim() || submitted}
				on:click={submit}
			>
				{submitted ? '제출 완료 ✓' : '제출하기'}
			</button>
		</div>
	</div>
</div>
