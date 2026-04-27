<script lang="ts">
	import Modal from '$lib/components/common/Modal.svelte';

	export let show = false;
	export let answer: string = '';
</script>

<Modal bind:show size="sm">
	<div class="p-5">
		<h3 class="text-base font-semibold text-gray-900 dark:text-white mb-1">정답 해설</h3>
		<p class="text-xs text-gray-500 dark:text-gray-400 mb-4">스스로 풀어본 후 확인하세요.</p>

		<div class="rounded-lg bg-green-50 dark:bg-green-950/30 border border-green-200 dark:border-green-800/40 px-4 py-3">
			<p class="text-sm text-gray-800 dark:text-gray-200 leading-relaxed whitespace-pre-wrap">{answer || '(정답 정보가 없습니다)'}</p>
		</div>

		<button
			class="mt-4 w-full py-2 rounded-lg text-sm font-medium bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 transition"
			on:click={() => (show = false)}
		>
			닫기
		</button>
	</div>
</Modal>
