<script lang="ts">
	import { getMessageSignature, type MessageSignature } from '$lib/apis/nearai';
	import type { Message } from '$lib/types';

	export let history: {
		messages: Record<string, Message>;
		currentId: string | null;
	};
	export let token: string;

	let signatures: Record<string, MessageSignature> = {};
	let loadingSignatures: Set<string> = new Set();
	let error: string | null = null;
	let selectedMessageId = '';
	let lastCurrentId = '';
	let containerElement: HTMLElement | undefined;

	// Get verifiable messages from history
	const getChatCompletions = (history: {
		messages: Record<string, Message>;
		currentId: string | null;
	}) => {
		if (!history?.messages) return [];
		return Object.values(history.messages).filter(
			(message) => message.role === 'assistant' && message.done === true
		);
	};

	// Reactive statement to calculate chatCompletions when history changes
	$: chatCompletions = history ? getChatCompletions(history) : [];

	// Set default selection to current message when component loads or history changes
	$: if (history?.currentId && history.messages[history.currentId]?.chatCompletionId) {
		// Auto-select only if this is a new message (currentId changed) or if no message is selected
		if (history.currentId !== lastCurrentId || !selectedMessageId) {
			selectedMessageId = history.messages[history.currentId].chatCompletionId!;
		}
		lastCurrentId = history.currentId;
	}

	// Scroll to selected message when selectedMessageId changes
	$: if (selectedMessageId && containerElement) {
		scrollToSelectedMessage();
	}

	// Function to fetch message signature
	const fetchMessageSignature = async (model: string, chatCompletionId: string) => {
		if (!chatCompletionId || !token || !model || loadingSignatures.has(chatCompletionId)) return;

		loadingSignatures.add(chatCompletionId);
		loadingSignatures = loadingSignatures; // Trigger reactivity

		try {
			const data = await getMessageSignature({ token, model, chatCompletionId });
			signatures = { ...signatures, [chatCompletionId]: data };
		} catch (err) {
			console.error('Error fetching message signature:', err);
			error = err instanceof Error ? err.message : 'Failed to fetch message signature';
		} finally {
			loadingSignatures.delete(chatCompletionId);
			loadingSignatures = loadingSignatures; // Trigger reactivity
		}
	};

	// Function to verify all message signatures
	const verifyAllMessageSignatures = async () => {
		for (const message of chatCompletions) {
			if (message.chatCompletionId && !signatures[message.chatCompletionId]) {
				await fetchMessageSignature(message.model, message.chatCompletionId);
			}
		}
	};

	// Function to scroll to selected message
	const scrollToSelectedMessage = () => {
		if (!containerElement || !selectedMessageId) return;

		// Use a longer delay to ensure DOM is fully updated and signatures are loaded
		setTimeout(() => {
			const selectedElement = containerElement?.querySelector(
				`[data-message-id="${selectedMessageId}"]`
			) as HTMLElement;
			if (selectedElement) {
				// Find the parent scroll container
				const scrollContainer = selectedElement.closest('.overflow-y-auto') as HTMLElement;
				if (scrollContainer) {
					// Calculate the scroll position to center the element
					const containerRect = scrollContainer.getBoundingClientRect();
					const elementRect = selectedElement.getBoundingClientRect();
					const scrollTop =
						selectedElement.offsetTop -
						scrollContainer.offsetTop -
						containerRect.height / 2 +
						elementRect.height / 2;

					scrollContainer.scrollTo({
						top: scrollTop,
						behavior: 'smooth'
					});
				} else {
					// Fallback to scrollIntoView
					selectedElement.scrollIntoView({
						behavior: 'smooth',
						block: 'center',
						inline: 'nearest'
					});
				}
			} else {
				console.log('Could not find element with data-message-id:', selectedMessageId);
			}
		}, 300); // Increased delay to ensure DOM is updated
	};

	// Auto-fetch signatures when chatCompletions change
	$: if (history && token && chatCompletions.length > 0) {
		chatCompletions.forEach((message: Message) => {
			if (message.chatCompletionId && !signatures[message.chatCompletionId]) {
				fetchMessageSignature(message.model, message.chatCompletionId);
			}
		});
	}
</script>

<div class="space-y-4 h-full overflow-y-auto pb-4 px-4" bind:this={containerElement}>
	{#if error}
		<!-- Error State -->
		<div
			class="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4"
		>
			<div class="flex items-center">
				<svg class="w-5 h-5 text-red-400 mr-2" fill="currentColor" viewBox="0 0 20 20">
					<path
						fill-rule="evenodd"
						d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
						clip-rule="evenodd"
					/>
				</svg>
				<span class="text-red-800 dark:text-red-200">{error}</span>
			</div>
		</div>
	{:else if chatCompletions.length > 0}
		<!-- Verifiable Messages Section -->
		<div class="space-y-4">
			<h3 class="text-sm mt-4 font-medium text-gray-900 dark:text-white">
				Verifiable Messages ({chatCompletions.length})
			</h3>

			{#each chatCompletions as message, index}
				<div
					class="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg my-2 p-2 relative cursor-pointer hover:bg-green-100 dark:hover:bg-green-900/30 transition-colors {selectedMessageId ===
					message.chatCompletionId
						? 'ring-1 ring-green-500'
						: ''}"
					on:click={() =>
						message.chatCompletionId && (selectedMessageId = message.chatCompletionId)}
					title="Click to view signature details"
					data-message-id={message.chatCompletionId}
				>
					<!-- TEE Verified Badge -->
					<div class="absolute top-3 right-3 flex items-center space-x-1">
						<svg class="w-4 h-4 text-green-500" fill="currentColor" viewBox="0 0 20 20">
							<path
								fill-rule="evenodd"
								d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
								clip-rule="evenodd"
							/>
						</svg>
						<span class="text-green-700 dark:text-green-300 text-xs font-medium">TEE Verified</span>
					</div>

					<!-- Message Content -->
					<div class="mb-3">
						<h4 class="text-sm font-medium text-gray-900 dark:text-white mb-2">
							Message {index + 1}
						</h4>
						<p class="text-sm text-gray-700 dark:text-gray-300 mb-2 line-clamp-2">
							{message.content}
						</p>
						<p class="text-xs text-gray-500 dark:text-gray-400">ID: {message.chatCompletionId}</p>
					</div>
				</div>
			{/each}

			<!-- Signature Details Section -->
			<div class="space-y-3">
				<div class="flex justify-between items-center">
					<h3 class="text-sm font-medium text-gray-900 dark:text-white mt-4">Signature Details</h3>
				</div>

				{#if selectedMessageId && signatures[selectedMessageId]}
					<!-- Verify on Etherscan Link -->
					{#if signatures[selectedMessageId].signature}
						<a class="mb-3" href="https://etherscan.io/verifiedSignatures" target="_blank">
							<button
								class="flex items-center text-blue-600 hover:text-blue-700 text-xs transition-colors"
							>
								<svg class="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path
										stroke-linecap="round"
										stroke-linejoin="round"
										stroke-width="2"
										d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
									/>
								</svg>
								Verify the signature on Etherscan
							</button>
						</a>
					{/if}

					<div class="border border-gray-200 dark:border-gray-700 rounded-lg p-3 min-h-[150px]">
						<!-- Signing Address -->
						<div class="mb-2">
							<label class="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1"
								>Signing Address:</label
							>
							<div
								class="px-2 py-1 bg-gray-100 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded text-xs font-mono break-all min-h-[24px] flex items-center"
							>
								{signatures[selectedMessageId].signing_address ?? ''}
							</div>
						</div>

						<!-- Message Hash -->
						<div class="mb-2">
							<label class="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1"
								>Message:</label
							>
							<div
								class="px-2 py-1 bg-gray-100 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded text-xs font-mono break-all min-h-[24px] flex items-center"
							>
								{signatures[selectedMessageId].text ?? ''}
							</div>
						</div>

						<!-- Signature -->
						<div class="mb-2">
							<label class="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1"
								>Signature:</label
							>
							<div
								class="px-2 py-1 bg-gray-100 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded text-xs font-mono break-all min-h-[24px] flex items-center"
							>
								{signatures[selectedMessageId].signature ?? ''}
							</div>
						</div>

						<!-- Algorithm -->
						<div>
							<label class="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1"
								>Algorithm:</label
							>
							<div
								class="px-2 py-1 bg-gray-100 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded text-xs min-h-[24px] flex items-center"
							>
								{signatures[selectedMessageId].signing_algo ?? ''}
							</div>
						</div>
					</div>
				{:else if selectedMessageId}
					<div
						class="border border-gray-200 dark:border-gray-700 rounded-lg p-3 min-h-[150px] flex items-center justify-center"
					>
						<div class="text-center py-2 text-gray-500 dark:text-gray-400">
							<p class="text-xs">No signature data available for selected message</p>
						</div>
					</div>
				{:else}
					<div
						class="border border-gray-200 dark:border-gray-700 rounded-lg p-3 min-h-[150px] flex items-center justify-center"
					>
						<div class="text-center py-2 text-gray-500 dark:text-gray-400">
							<p class="text-xs">Click on a message above to view signature details</p>
						</div>
					</div>
				{/if}
			</div>
		</div>
	{:else}
		<!-- No Data State -->
		<div class="text-center py-8 text-gray-500 dark:text-gray-400">
			<p class="text-sm">No verifiable messages found for this chat.</p>
		</div>
	{/if}

	<!-- Add bottom padding for better scrolling -->
	<div class="h-10"></div>
</div>
