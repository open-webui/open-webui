<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { onMount } from 'svelte';
	import Modal from './Modal.svelte';

	export let show = false;

	const categories = ['버그', 'UI 오류', '기능 제안'];
	let selectedCategory: string | null = null;
	let description = '';
	let currentPath = '';

	onMount(() => {
		currentPath = window.location.pathname;
	});

	$: if (show) {
		currentPath = typeof window !== 'undefined' ? window.location.pathname : '';
	}

	const handleSubmit = () => {
		if (!description.trim()) {
			toast.error('내용을 입력해 주세요.');
			return;
		}
		console.log('[BugReport]', { category: selectedCategory, description, path: currentPath });
		toast.success('신고가 접수됐어요. 감사합니다!');
		description = '';
		selectedCategory = null;
		show = false;
	};
</script>

<Modal bind:show size="sm" className="bg-white dark:bg-gray-800 rounded-2xl p-0">
	<div class="px-6 pt-6 pb-5 flex flex-col gap-4">
		<!-- Header -->
		<div class="flex items-center justify-between">
			<h2 class="text-base font-semibold text-gray-900 dark:text-white">불편한 점을 알려주세요</h2>
			<button
				class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 transition"
				on:click={() => (show = false)}
			>
				<svg xmlns="http://www.w3.org/2000/svg" class="size-5" viewBox="0 0 20 20" fill="currentColor">
					<path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd" />
				</svg>
			</button>
		</div>

		<!-- Auto-fill badge -->
		<div class="flex items-center gap-2 px-3 py-2 rounded-lg bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800">
			<svg xmlns="http://www.w3.org/2000/svg" class="size-4 text-green-600 dark:text-green-400 shrink-0" viewBox="0 0 20 20" fill="currentColor">
				<path d="M10 12a2 2 0 100-4 2 2 0 000 4z"/>
				<path fill-rule="evenodd" d="M.458 10C1.732 5.943 5.522 3 10 3s8.268 2.943 9.542 7c-1.274 4.057-5.064 7-9.542 7S1.732 14.057.458 10zM14 10a4 4 0 11-8 0 4 4 0 018 0z" clip-rule="evenodd"/>
			</svg>
			<span class="text-xs text-green-700 dark:text-green-300">← 현재 화면 자동 첨부됨</span>
			<span class="text-xs text-green-600 dark:text-green-400 font-mono ml-auto truncate max-w-[12rem]">{currentPath}</span>
		</div>

		<!-- Textarea -->
		<textarea
			bind:value={description}
			placeholder="어떤 문제가 발생했나요?"
			rows="4"
			class="w-full px-4 py-3 rounded-xl text-sm resize-none outline-none border transition
				bg-gray-50 dark:bg-gray-700 border-gray-200 dark:border-gray-600
				text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500
				focus:border-amber-400 dark:focus:border-amber-500"
		></textarea>

		<!-- Category chips -->
		<div class="flex gap-2">
			{#each categories as cat}
				<button
					class="px-4 py-1.5 rounded-full text-sm font-medium transition
						{selectedCategory === cat
							? 'bg-amber-500 text-white'
							: 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'}"
					on:click={() => (selectedCategory = selectedCategory === cat ? null : cat)}
				>
					{cat}
				</button>
			{/each}
		</div>

		<!-- Submit -->
		<button
			class="w-full py-2.5 rounded-xl text-sm font-semibold transition
				bg-amber-500 hover:bg-amber-600 text-white"
			on:click={handleSubmit}
		>
			신고 전송하기
		</button>
	</div>
</Modal>
