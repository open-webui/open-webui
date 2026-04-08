<script lang="ts">
	import { toast } from 'svelte-sonner';
	import Modal from './Modal.svelte';

	export let show = false;

	const statusConfig = {
		'개발 예정': { color: 'bg-orange-100 dark:bg-orange-900/30 text-orange-600 dark:text-orange-400' },
		'검토 중':   { color: 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-600 dark:text-yellow-400' },
		'완료':      { color: 'bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400' }
	};

	let ideas = [
		{ id: 1, title: '수식 직접 입력 기능 추가', votes: 23, status: '개발 예정', voted: false },
		{ id: 2, title: '다크 / 라이트 모드 토글',  votes: 18, status: '검토 중',   voted: false },
		{ id: 3, title: 'PDF 내보내기 기능',         votes: 12, status: '완료',      voted: false },
		{ id: 4, title: '수업 녹음 연동 기능',       votes: 8,  status: '검토 중',   voted: false }
	];

	let showSuggestForm = false;
	let newIdeaText = '';

	const handleVote = (id: number) => {
		ideas = ideas.map(i =>
			i.id === id ? { ...i, votes: i.voted ? i.votes - 1 : i.votes + 1, voted: !i.voted } : i
		);
	};

	const handleSuggest = () => {
		if (!newIdeaText.trim()) return;
		ideas = [
			{ id: Date.now(), title: newIdeaText.trim(), votes: 1, status: '검토 중', voted: true },
			...ideas
		];
		toast.success('아이디어가 제안됐어요!');
		newIdeaText = '';
		showSuggestForm = false;
	};
</script>

<Modal bind:show size="md" className="bg-white dark:bg-gray-800 rounded-2xl p-0">
	<div class="px-6 pt-6 pb-5 flex flex-col gap-4">
		<!-- Header -->
		<div class="flex items-center justify-between">
			<div class="flex items-center gap-2">
				<span>💡</span>
				<h2 class="text-base font-semibold text-gray-900 dark:text-white">기능 개선 아이디어</h2>
			</div>
			<div class="flex items-center gap-2">
				<button
					class="px-3 py-1.5 rounded-full text-xs font-medium bg-blue-600 hover:bg-blue-700 text-white transition"
					on:click={() => (showSuggestForm = !showSuggestForm)}
				>
					+ 제안하기
				</button>
				<button
					class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 transition"
					on:click={() => (show = false)}
				>
					<svg xmlns="http://www.w3.org/2000/svg" class="size-5" viewBox="0 0 20 20" fill="currentColor">
						<path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd" />
					</svg>
				</button>
			</div>
		</div>

		<!-- Suggest form (inline) -->
		{#if showSuggestForm}
			<div class="flex gap-2">
				<input
					type="text"
					bind:value={newIdeaText}
					placeholder="아이디어를 입력해 주세요"
					class="flex-1 px-4 py-2.5 rounded-xl text-sm outline-none border
						bg-gray-50 dark:bg-gray-700 border-gray-200 dark:border-gray-600
						text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500
						focus:border-blue-400 dark:focus:border-blue-500"
					on:keydown={(e) => e.key === 'Enter' && handleSuggest()}
				/>
				<button
					class="px-4 py-2.5 rounded-xl text-sm font-medium bg-blue-600 hover:bg-blue-700 text-white transition shrink-0"
					on:click={handleSuggest}
				>
					제출
				</button>
			</div>
		{/if}

		<!-- Ideas list -->
		<div class="flex flex-col gap-2">
			{#each ideas as idea (idea.id)}
				<div class="flex items-center gap-3 px-4 py-3 rounded-xl bg-gray-50 dark:bg-gray-700/50 border border-gray-100 dark:border-gray-700">
					<!-- Vote button -->
					<button
						class="flex flex-col items-center gap-0.5 shrink-0 transition
							{idea.voted ? 'text-blue-500' : 'text-gray-400 dark:text-gray-500 hover:text-blue-400'}"
						on:click={() => handleVote(idea.id)}
					>
						<svg xmlns="http://www.w3.org/2000/svg" class="size-4" viewBox="0 0 20 20" fill="currentColor">
							<path fill-rule="evenodd" d="M14.707 12.707a1 1 0 01-1.414 0L10 9.414l-3.293 3.293a1 1 0 01-1.414-1.414l4-4a1 1 0 011.414 0l4 4a1 1 0 010 1.414z" clip-rule="evenodd"/>
						</svg>
						<span class="text-xs font-bold {idea.voted ? 'text-blue-500' : 'text-gray-500 dark:text-gray-400'}">{idea.votes}</span>
					</button>

					<!-- Title -->
					<span class="flex-1 text-sm text-gray-800 dark:text-gray-100">{idea.title}</span>

					<!-- Status badge -->
					<span class="text-xs px-2.5 py-1 rounded-full font-medium shrink-0 {statusConfig[idea.status]?.color ?? ''}">
						{idea.status === '완료' ? '✓ ' : ''}{idea.status}
					</span>
				</div>
			{/each}
		</div>

	</div>
</Modal>
