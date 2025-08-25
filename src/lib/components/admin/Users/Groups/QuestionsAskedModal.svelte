<script lang="ts">
	import { getContext } from 'svelte';
	import Modal from '$lib/components/common/Modal.svelte';
	import Cross from '$lib/components/icons/Cross.svelte';

	const i18n = getContext('i18n');

	export let show = false;
	export let member = null;

	// Generate placeholder questions based on member data
	const generateQuestions = (questionsAsked) => {
		if (!questionsAsked) return [];

		const questionCount = questionsAsked.length || 5;
		return Array.from({ length: questionCount }, (_, index) => ({
			id: index + 1,
			question: questionsAsked[index] || `Sample question ${index + 1}`,
			timestamp: new Date(Date.now() - Math.random() * 7 * 24 * 60 * 60 * 1000).toLocaleString(),
		}));
	};

	let questions = [];

	// Update questions when member changes
	$: if (member && show) {
		questions = generateQuestions(member.questionsAsked);
	}

	// Close modal function
	const closeModal = () => {
		show = false;
	};
</script>

<Modal
	bind:show
	size="sm"
	containerClassName="p-4 flex justify-start items-center"
	className="bg-white dark:bg-gray-900 rounded-lg ml-4 h-[90vh] overflow-hidden flex flex-col"
>
	<!-- Header -->
	<div class="flex justify-between items-center p-6 border-b border-gray-200 dark:border-gray-700">
		<div class="flex flex-col">
			{#if member}
				<div class="text-sm text-gray-500 dark:text-gray-400 mt-1">
					<span class="font-medium">Questions by</span>
					<span class="font-bold">{member.name}</span>
					<span class="font-medium">in</span>
					<span
						class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-800 dark:text-blue-100"
					>
						{member.model}
					</span>
				</div>
			{/if}
		</div>
		<button
			class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 transition"
			on:click={closeModal}
			aria-label="Close modal"
		>
			<Cross className="size-4.5" />
		</button>
	</div>

	<!-- Questions List -->
	<div class="flex-1 overflow-hidden flex flex-col">
		{#if member}
			<!-- Questions List -->
			<div
				class="flex-1 overflow-y-auto p-4 space-y-3"
				role="list"
				aria-label="List of questions asked"
			>
				{#each questions as question, index}
					<article
						class=" p-3 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
					>
						<div class="flex items-start gap-3 mb-2">
							<!-- Question Number -->
							<div class="flex-shrink-0 text-gray-800 dark:text-gray-200 text-xs font-bold">
								{index + 1}
							</div>
							<!-- Question Content - Height Adaptive -->
							<div
								class="flex-1 text-sm font-medium text-gray-900 dark:text-gray-100 leading-relaxed"
							>
								{question.question}
							</div>
						</div>
						<div class="flex justify-between items-start">
							<!-- Timestamp -->
							<div class="flex-shrink-0 text-xs text-gray-500 dark:text-gray-400">
								{question.timestamp}
							</div>
							<!-- Time Taken -->
							<div class="text-xs text-gray-500 dark:text-gray-400">
								In: {question.timeTaken || `${Math.floor(Math.random() * 5) + 1}min`}
							</div>
						</div>
					</article>
				{/each}

				{#if questions.length === 0}
					<div class="text-center py-8 text-gray-500 dark:text-gray-400">No questions found</div>
				{/if}
			</div>
		{:else}
			<div class="flex-1 flex items-center justify-center text-gray-500 dark:text-gray-400">
				No member selected
			</div>
		{/if}
	</div>

	<!-- Footer -->
	<div class="p-4 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800">
		<div class="flex justify-between items-center">
			<div class="text-xs text-gray-500 dark:text-gray-400">
				Press <kbd class="px-2 py-1 bg-gray-200 dark:bg-gray-700 rounded text-xs">Esc</kbd> to close
			</div>
			<button
				class="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-xs font-medium rounded-md transition"
				on:click={closeModal}
			>
				Close
			</button>
		</div>
	</div>
</Modal>
