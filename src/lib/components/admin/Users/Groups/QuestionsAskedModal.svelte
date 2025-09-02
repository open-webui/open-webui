<script lang="ts">
	import { getContext } from 'svelte';
	import Modal from '$lib/components/common/Modal.svelte';
	import Cross from '$lib/components/icons/Cross.svelte';

	const i18n = getContext('i18n');

	export let show = false;
	export let member = null;

	// Generate structured questions from the questions array
	const generateQuestions = (questionsArray) => {
		if (!Array.isArray(questionsArray) || questionsArray.length === 0) {
			return [];
		}

		return questionsArray.map((questionText, index) => ({
			id: index + 1,
			question: questionText || `Question ${index + 1}`,
			timestamp: new Date(Date.now() - Math.random() * 7 * 24 * 60 * 60 * 1000).toLocaleString(),
			timeTaken: `${Math.floor(Math.random() * 5) + 1}min`,
		}));
	};

	let questions = [];
	let isGrouped = false;

	// Update questions when member changes
	$: if (member && show) {
		// Check if this is a grouped member (has multiple chats)
		isGrouped = member.chatCount > 1;

		// Use member.questions (array) instead of member.questionsAsked (count)
		questions = generateQuestions(member.questions || []);

		console.log('QuestionsAskedModal - Member data:', {
			name: member.name,
			model: member.model,
			isGrouped,
			chatCount: member.chatCount,
			questionsAsked: member.questionsAsked, // This is the count
			questionsArray: member.questions, // This is the actual questions
			questionsLength: member.questions?.length || 0,
		});
	}

	// Close modal function
	const closeModal = () => {
		show = false;
	};
</script>

<Modal
	bind:show
	size="lg"
	containerClassName="p-4 flex justify-start items-center"
	className="bg-white dark:bg-gray-900 rounded-lg ml-4 h-[90vh] overflow-hidden flex flex-col"
>
	<!-- Header -->
	<div class="flex justify-between items-center p-6 border-b border-gray-200 dark:border-gray-700">
		<div class="flex flex-col">
			{#if member}
				<h2 class="text-lg font-semibold text-gray-900 dark:text-gray-100">
					Questions by {member.name}
				</h2>
				<div class="text-sm text-gray-500 dark:text-gray-400 mt-1 flex flex-wrap items-center gap-2">
					<span class="font-medium">Model:</span>
					<span
						class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-100"
					>
						{member.model}
					</span>

					{#if isGrouped}
						<span class="text-gray-400">•</span>
						<span class="font-medium">
							{member.questionsAsked} total questions
						</span>
					{:else}
						<span class="text-gray-400">•</span>
						<span class="font-medium">
							{member.questionsAsked} questions
						</span>
					{/if}
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
						class="border border-gray-200 dark:border-gray-700 p-4 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
					>
						<div class="flex items-start gap-3 mb-3">
							<!-- Question Number -->
							<div class="flex-shrink-0 w-8 h-8 bg-gray-100 dark:bg-gray-900 text-gray-800 dark:text-gray-200 rounded-full flex items-center justify-center text-sm font-bold">
								{index + 1}
							</div>
							<!-- Question Content -->
							<div class="flex-1">
								<div class="text-sm font-medium text-gray-900 dark:text-gray-100 leading-relaxed mb-2">
									{question.question}
								</div>
								<div class="flex justify-between items-center text-xs text-gray-500 dark:text-gray-400">
									<span class="font-medium">Asked on: {question.timestamp}</span>
									<span class="bg-gray-100 dark:bg-gray-700 px-2 py-1 rounded">
										⏱️ {question.timeTaken}
									</span>
								</div>
							</div>
						</div>
					</article>
				{/each}

				{#if questions.length === 0}
					<div class="text-center py-12">
						<div class="text-gray-400 text-lg mb-2">🤔</div>
						<div class="text-gray-500 dark:text-gray-400 font-medium">No questions found</div>
						<div class="text-sm text-gray-400 dark:text-gray-500 mt-1">
							{#if isGrouped}
								No questions were recorded in any of the {member.chatCount} conversations
							{:else}
								No questions were recorded in this conversation
							{/if}
						</div>
					</div>
				{/if}
			</div>
		{:else}
			<div class="flex-1 flex items-center justify-center text-gray-500 dark:text-gray-400">
				<div class="text-center">
					<div class="text-gray-400 text-2xl mb-2">💬</div>
					<div class="font-medium">No member selected</div>
					<div class="text-sm mt-1">Select a conversation to view questions</div>
				</div>
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
				class="px-4 py-2 bg-gray-600 hover:bg-gray-700 text-white text-sm font-medium rounded-md transition"
				on:click={closeModal}
			>
				Close
			</button>
		</div>
	</div>
</Modal>
