<script lang="ts">
	import { toast } from 'svelte-sonner';
	import Modal from '$lib/components/common/Modal.svelte';

	export let show = false;
	export let messageContent = '';

	const emojis = [
		{ value: 'bad',     label: '별로',   icon: '😤' },
		{ value: 'a-bit',   label: '조금',   icon: '😐' },
		{ value: 'good',    label: '좋아요',  icon: '😊' },
		{ value: 'perfect', label: '완벽',   icon: '😄' }
	];

	const levels = ['입문', '기초', '이해', '심화'];

	let selectedEmoji: string | null = null;
	let selectedLevel: string | null = null;

	const preview = messageContent ? messageContent.replace(/[#*`]/g, '').slice(0, 80) + (messageContent.length > 80 ? '…' : '') : '';

	const handleSave = () => {
		console.log('[Understanding]', { emoji: selectedEmoji, level: selectedLevel });
		toast.success('자가 평가가 저장됐어요!');
		selectedEmoji = null;
		selectedLevel = null;
		show = false;
	};
</script>

<Modal bind:show size="sm" className="bg-white dark:bg-gray-800 rounded-2xl p-0">
	<div class="px-6 pt-6 pb-5 flex flex-col gap-5">
		<!-- Header -->
		<div class="flex items-center justify-between">
			<h2 class="text-base font-semibold text-gray-900 dark:text-white">이해도 자가 평가</h2>
			<button
				class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 transition"
				on:click={() => (show = false)}
			>
				<svg xmlns="http://www.w3.org/2000/svg" class="size-5" viewBox="0 0 20 20" fill="currentColor">
					<path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd" />
				</svg>
			</button>
		</div>

		<!-- Message Preview -->
		{#if preview}
			<div class="text-xs text-gray-500 dark:text-gray-400 bg-gray-100 dark:bg-gray-700/60 rounded-xl px-4 py-3 leading-relaxed">
				{preview}
			</div>
		{/if}

		<!-- Emoji Rating -->
		<div class="flex flex-col gap-2">
			<p class="text-sm font-medium text-gray-700 dark:text-gray-300">이 설명이 도움이 됐나요?</p>
			<div class="grid grid-cols-4 gap-2">
				{#each emojis as e}
					<button
						class="flex flex-col items-center gap-1 py-3 rounded-xl transition
							{selectedEmoji === e.value
								? 'bg-blue-600 scale-105'
								: 'bg-gray-100 dark:bg-gray-700/50 hover:bg-gray-200 dark:hover:bg-gray-700'}"
						on:click={() => (selectedEmoji = selectedEmoji === e.value ? null : e.value)}
					>
						<span class="text-xl">{e.icon}</span>
						<span class="text-xs {selectedEmoji === e.value ? 'text-white font-medium' : 'text-gray-600 dark:text-gray-400'}">{e.label}</span>
					</button>
				{/each}
			</div>
		</div>

		<!-- Understanding Level -->
		<div class="flex flex-col gap-2">
			<p class="text-sm font-medium text-gray-700 dark:text-gray-300">이해도 레벨</p>
			<div class="flex gap-2">
				{#each levels as level}
					<button
						class="flex-1 py-2 text-sm rounded-full border transition
							{selectedLevel === level
								? 'bg-green-500 border-green-500 text-white font-medium'
								: 'border-gray-300 dark:border-gray-600 text-gray-600 dark:text-gray-400 hover:border-gray-400 dark:hover:border-gray-400'}"
						on:click={() => (selectedLevel = selectedLevel === level ? null : level)}
					>
						{level}
					</button>
				{/each}
			</div>
		</div>

		<!-- Save Button -->
		<button
			class="w-full py-2.5 rounded-xl text-sm font-medium transition
				{selectedEmoji || selectedLevel
					? 'bg-green-500 hover:bg-green-600 text-white'
					: 'bg-gray-200 dark:bg-gray-700 text-gray-400 dark:text-gray-500 cursor-not-allowed'}"
			on:click={handleSave}
			disabled={!selectedEmoji && !selectedLevel}
		>
			저장하기
		</button>
	</div>
</Modal>
