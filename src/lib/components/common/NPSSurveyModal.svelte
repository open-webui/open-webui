<script lang="ts">
	import { toast } from 'svelte-sonner';
	import Modal from './Modal.svelte';

	export let show = false;

	let selectedScore: number | null = null;
	let comment = '';

	const handleSubmit = () => {
		if (selectedScore === null) {
			toast.error('점수를 선택해 주세요.');
			return;
		}
		console.log('[NPS]', { score: selectedScore, comment });
		toast.success('소중한 의견 감사합니다! 더 나은 서비스로 보답할게요.');
		selectedScore = null;
		comment = '';
		show = false;
	};

	const handleLater = () => {
		selectedScore = null;
		comment = '';
		show = false;
	};
</script>

<Modal bind:show size="sm" className="bg-white dark:bg-gray-800 rounded-2xl p-0">
	<div class="px-6 pt-6 pb-5 flex flex-col gap-5">
		<!-- Header -->
		<div class="flex items-center justify-between">
			<h2 class="text-base font-semibold text-gray-900 dark:text-white">
				이 서비스를 친구에게 추천하시겠어요?
			</h2>
			<button
				class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 transition"
				on:click={handleLater}
			>
				<svg xmlns="http://www.w3.org/2000/svg" class="size-5" viewBox="0 0 20 20" fill="currentColor">
					<path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd" />
				</svg>
			</button>
		</div>

		<!-- Score selector -->
		<div class="flex flex-col gap-2">
			<div class="flex gap-1.5">
				{#each Array.from({ length: 11 }, (_, i) => i) as score}
					<button
						class="flex-1 aspect-square flex items-center justify-center rounded-full text-sm font-medium transition
							{selectedScore === score
								? 'bg-blue-600 text-white shadow-md'
								: 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'}"
						on:click={() => (selectedScore = score)}
					>
						{score}
					</button>
				{/each}
			</div>
			<div class="flex justify-between text-xs text-gray-400 dark:text-gray-500 px-0.5">
				<span>전혀 아니요</span>
				<span>강력 추천</span>
			</div>
		</div>

		<!-- Low score additional question -->
		{#if selectedScore !== null && selectedScore <= 6}
			<div class="flex flex-col gap-2">
				<textarea
					bind:value={comment}
					placeholder="어떤 점이 불편하셨나요? (선택)"
					rows="3"
					class="w-full px-4 py-3 rounded-xl text-sm resize-none outline-none border transition
						bg-gray-50 dark:bg-gray-700 border-gray-200 dark:border-gray-600
						text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500
						focus:border-blue-400 dark:focus:border-blue-500"
				></textarea>
			</div>
		{/if}

		<!-- Buttons -->
		<div class="flex flex-col gap-2">
			<button
				class="w-full py-2.5 rounded-xl text-sm font-semibold transition
					{selectedScore !== null
						? 'bg-blue-600 hover:bg-blue-700 text-white'
						: 'bg-gray-200 dark:bg-gray-700 text-gray-400 dark:text-gray-500 cursor-not-allowed'}"
				on:click={handleSubmit}
				disabled={selectedScore === null}
			>
				제출하기
			</button>
			<button
				class="text-xs text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300 transition text-center"
				on:click={handleLater}
			>
				나중에 하기
			</button>
		</div>
	</div>
</Modal>
