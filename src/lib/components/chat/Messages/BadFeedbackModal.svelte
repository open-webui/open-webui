<script lang="ts">
	import { getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	import Modal from '$lib/components/common/Modal.svelte';

	const i18n = getContext<Writable<i18nType>>('i18n');

	export let show = false;

	const reasons = [
		'설명이 너무 어려워요',
		'틀린 내용이 있어요',
		'질문을 잘못 이해했어요',
		'기타'
	];

	let selectedReason: string | null = null;

	const handleSubmit = () => {
		if (!selectedReason) {
			toast.error('사유를 선택해 주세요.');
			return;
		}
		console.log('[BadFeedback]', { reason: selectedReason });
		toast.success('소중한 의견 감사합니다!');
		selectedReason = null;
		show = false;
	};

	const handleClose = () => {
		selectedReason = null;
		show = false;
	};
</script>

<Modal bind:show size="sm" className="bg-white dark:bg-gray-800 rounded-2xl p-0">
	<div class="px-6 pt-6 pb-5 flex flex-col gap-5">
		<!-- Header -->
		<div class="flex items-center justify-between">
			<div class="flex items-center gap-2">
				<span class="text-lg">😕</span>
				<h2 class="text-base font-semibold text-gray-900 dark:text-white">
					이 답변이 왜 별로였나요?
				</h2>
			</div>
			<button
				class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 transition"
				on:click={handleClose}
			>
				<svg xmlns="http://www.w3.org/2000/svg" class="size-5" viewBox="0 0 20 20" fill="currentColor">
					<path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd" />
				</svg>
			</button>
		</div>

		<!-- Radio Options -->
		<div class="flex flex-col gap-2">
			{#each reasons as reason}
				<label
					class="flex items-center gap-3 px-4 py-3 rounded-xl cursor-pointer transition
						{selectedReason === reason
							? 'bg-blue-50 dark:bg-blue-900/30 border border-blue-400 dark:border-blue-500'
							: 'bg-gray-50 dark:bg-gray-700/50 border border-transparent hover:border-gray-300 dark:hover:border-gray-500'}"
				>
					<input
						type="radio"
						name="bad-reason"
						value={reason}
						bind:group={selectedReason}
						class="accent-blue-500 size-4 shrink-0"
					/>
					<span class="text-sm text-gray-800 dark:text-gray-100">{reason}</span>
				</label>
			{/each}
		</div>

		<!-- Submit Button -->
		<button
			class="w-full py-2.5 rounded-xl text-sm font-medium transition
				{selectedReason
					? 'bg-blue-600 hover:bg-blue-700 text-white'
					: 'bg-gray-200 dark:bg-gray-700 text-gray-400 dark:text-gray-500 cursor-not-allowed'}"
			on:click={handleSubmit}
			disabled={!selectedReason}
		>
			전송하기
		</button>
	</div>
</Modal>
