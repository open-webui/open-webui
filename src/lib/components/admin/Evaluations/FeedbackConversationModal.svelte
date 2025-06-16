<script lang="ts">
	import { toast } from 'svelte-sonner';
	import dayjs from 'dayjs';
	import { getContext, onMount } from 'svelte';

	import Modal from '$lib/components/common/Modal.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import ChevronLeft from '$lib/components/icons/ChevronLeft.svelte';

	const i18n = getContext('i18n');

	export let show = false;
	export let feedback = null;

	// Track if we're viewing the chat details
	let viewingChat = false;

	// Create a synthesized snapshot if one doesn't exist
	function ensureSnapshot(feedback) {
		if (!feedback) return feedback;

		if (!feedback.snapshot && feedback.meta?.chat_id) {
			// Create a minimal synthetic snapshot with just the chat_id
			feedback = {
				...feedback,
				snapshot: {
					chat: {
						id: feedback.meta.chat_id,
						title: feedback.data?.model_id ? `Feedback on ${feedback.data.model_id}` : 'Chat'
					}
				}
			};
		}

		return feedback;
	}

	// Extract chat information from feedback with better title extraction
	function extractChatInfo(feedback) {
		if (!feedback) return null;

		// Ensure we have a snapshot
		feedback = ensureSnapshot(feedback);

		try {
			let chatId = null;
			let chatTitle = 'Chat';
			let updatedAt = 0;

			// First try to use the meta.chat_id field which is most reliable
			if (feedback.meta?.chat_id) {
				chatId = feedback.meta.chat_id;
			}
			// Otherwise check snapshot data
			else if (feedback.snapshot?.chat) {
				if (feedback.snapshot.chat.id) {
					chatId = feedback.snapshot.chat.id;
				} else if (feedback.snapshot.chat.chat?.id) {
					chatId = feedback.snapshot.chat.chat.id;
				} else if (feedback.snapshot.chat.share_id) {
					chatId = feedback.snapshot.chat.share_id;
				}
			}

			// Get a meaningful title
			if (feedback.snapshot?.chat?.title) {
				chatTitle = feedback.snapshot.chat.title;
			} else if (feedback.snapshot?.chat?.chat?.title) {
				chatTitle = feedback.snapshot.chat.chat.title;
			} else if (feedback.data?.model_id) {
				// Fallback to using model ID as part of title
				chatTitle = `Feedback on ${feedback.data.model_id}`;
			}

			// Set updated time
			updatedAt = feedback.updated_at || feedback.created_at || Math.floor(Date.now() / 1000);

			// Ensure we have a valid chat ID (important)
			if (!chatId) {
				return null;
			}

			return {
				id: chatId,
				title: chatTitle,
				updated_at: updatedAt
			};
		} catch (error) {
			return null;
		}
	}

	// Extract messages from chat snapshot with improved handling of nested structures
	function extractConversation(feedback) {
		if (!feedback) return [];

		// Ensure we have a snapshot
		feedback = ensureSnapshot(feedback);

		try {
			// If there's no snapshot, try to extract minimal information from the feedback data
			if (!feedback.snapshot) {
				if (feedback.data && feedback.meta) {
					const messages = [];

					// Create a minimal conversation from the feedback data
					if (feedback.data.model_id) {
						// Add a user message
						const ratingText =
							feedback.data.rating === 1
								? 'positive'
								: feedback.data.rating === -1
									? 'negative'
									: 'neutral';

						messages.push({
							role: 'user',
							content: `Gave ${ratingText} feedback for ${feedback.data.model_id}`,
							timestamp: feedback.created_at || Math.floor(Date.now() / 1000) - 60
						});

						// Add the comment as an AI response if available
						if (feedback.data.comment) {
							messages.push({
								role: 'assistant',
								content: feedback.data.comment,
								timestamp: feedback.created_at || Math.floor(Date.now() / 1000)
							});
						}

						// Add the reason if available
						if (feedback.data.reason) {
							messages.push({
								role: 'user',
								content: `Reason: ${feedback.data.reason}`,
								timestamp: feedback.created_at || Math.floor(Date.now() / 1000) - 30
							});
						}

						return messages;
					}
				}

				return [];
			}

			if (!feedback.snapshot.chat) {
				return [];
			}

			// Try different paths to find messages

			// Option 1: chat.chat.messages array
			if (
				feedback.snapshot.chat.chat?.messages &&
				Array.isArray(feedback.snapshot.chat.chat.messages)
			) {
				return feedback.snapshot.chat.chat.messages.map((msg) => ({
					role: msg.role,
					content: msg.content || '',
					timestamp: msg.timestamp || 0
				}));
			}

			// Option 2: chat.chat.history.messages object
			if (feedback.snapshot.chat.chat?.history?.messages) {
				const messagesObj = feedback.snapshot.chat.chat.history.messages;
				return Object.values(messagesObj)
					.map((msg) => ({
						role: msg.role,
						content: msg.content || '',
						timestamp: msg.timestamp || 0
					}))
					.sort((a, b) => (a.timestamp || 0) - (b.timestamp || 0));
			}

			// If still no conversation but we have meta and data, create one from feedback data
			if (feedback.meta?.message_id && feedback.data) {
				const messages = [];

				// Create a minimal conversation from the feedback data
				if (feedback.data.model_id) {
					// Add a user message
					const ratingText =
						feedback.data.rating === 1
							? 'positive'
							: feedback.data.rating === -1
								? 'negative'
								: 'neutral';

					messages.push({
						role: 'user',
						content: `Gave ${ratingText} feedback for ${feedback.data.model_id}`,
						timestamp: feedback.created_at || Math.floor(Date.now() / 1000) - 60
					});

					// Add the message content if available
					if (feedback.meta.message_id) {
						messages.push({
							role: 'assistant',
							content: 'Response that received feedback',
							id: feedback.meta.message_id,
							timestamp: feedback.created_at || Math.floor(Date.now() / 1000)
						});
					}

					// Add the comment as additional context if available
					if (feedback.data.comment) {
						messages.push({
							role: 'user',
							content: `Comment: ${feedback.data.comment}`,
							timestamp: feedback.created_at || Math.floor(Date.now() / 1000) - 30
						});
					}

					return messages;
				}
			}

			return [];
		} catch (error) {
			return [];
		}
	}

	$: processedFeedback = feedback ? ensureSnapshot(feedback) : null;
	$: chat = processedFeedback ? extractChatInfo(processedFeedback) : null;
	$: userName = processedFeedback?.user?.name || $i18n.t('User');
	$: conversation = processedFeedback ? extractConversation(processedFeedback) : [];

	// Reset viewingChat when modal is closed or opened
	$: if (!show) {
		viewingChat = false;
	}
</script>

<Modal size="lg" bind:show>
	<div class="flex justify-between dark:text-gray-300 px-5 pt-4">
		<div class="text-lg font-medium self-center capitalize flex gap-1 items-center">
			{#if viewingChat}
				<button
					class="p-1 hover:bg-gray-100 dark:hover:bg-gray-850 rounded-lg"
					on:click={() => (viewingChat = false)}
				>
					<ChevronLeft className="size-4" />
				</button>
				<span>{chat?.title || $i18n.t('Chat')}</span>
			{:else}
				{$i18n.t("{{user}}'s Chat", { user: userName })}
			{/if}
		</div>

		<button
			class="self-center"
			on:click={() => {
				show = false;
			}}
		>
			<svg
				xmlns="http://www.w3.org/2000/svg"
				viewBox="0 0 20 20"
				fill="currentColor"
				class="w-5 h-5"
			>
				<path
					d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z"
				/>
			</svg>
		</button>
	</div>

	<div class="flex flex-col md:flex-row w-full px-5 pt-2 pb-4 md:space-x-4 dark:text-gray-200">
		<div class="flex flex-col w-full sm:flex-row sm:justify-center sm:space-x-6">
			{#if viewingChat}
				<!-- Chat conversation view when viewing chat details -->
				<div class="text-left text-sm w-full mb-4 max-h-[22rem] overflow-y-scroll">
					{#if conversation && conversation.length > 0}
						<div class="space-y-4 px-1">
							{#each conversation as message}
								<div
									class="border rounded-lg p-3 {message.role === 'user'
										? 'border-blue-100 dark:border-blue-900 bg-blue-50 dark:bg-blue-950/30'
										: 'border-green-100 dark:border-green-900 bg-green-50 dark:bg-green-950/30'}"
								>
									<div class="flex justify-between items-center mb-2">
										<div class="font-medium">
											{message.role === 'user' ? '👤 ' + $i18n.t('User') : '🤖 ' + $i18n.t('AI')}
										</div>
										{#if message.timestamp}
											<div class="text-xs text-gray-500">
												{dayjs(message.timestamp * 1000).format($i18n.t('MMM D, YYYY h:mm A'))}
											</div>
										{/if}
									</div>
									<div class="whitespace-pre-wrap text-sm">{message.content}</div>
								</div>
							{/each}
						</div>
					{:else}
						<div class="text-center py-4 text-gray-500">
							{$i18n.t('No messages found in conversation data')}
						</div>
					{/if}
				</div>
			{:else if chat}
				<!-- Normal chat link view -->
				<div class="text-left text-sm w-full mb-4 max-h-[22rem] overflow-y-scroll">
					<div class="relative overflow-x-auto">
						<table class="w-full text-sm text-left text-gray-600 dark:text-gray-400 table-auto">
							<thead
								class="text-xs text-gray-700 uppercase bg-transparent dark:text-gray-200 border-b-2 dark:border-gray-800"
							>
								<tr>
									<th scope="col" class="px-3 py-2 cursor-pointer select-none">
										{$i18n.t('Title')}
										<span class="invisible">▲</span>
									</th>
									<th
										scope="col"
										class="px-3 py-2 hidden md:flex cursor-pointer select-none justify-end"
									>
										{$i18n.t('Updated at')}
										<span class="invisible">▲</span>
									</th>
									<th scope="col" class="px-3 py-2 text-right" />
								</tr>
							</thead>
							<tbody>
								<tr class="bg-transparent border-b dark:bg-gray-900 dark:border-gray-850 text-xs">
									<td class="px-3 py-1">
										<!-- Allow both external link and internal view -->
										<div class="flex items-center gap-2">
											{#if conversation && conversation.length > 0}
												<button
													class="text-xs text-blue-500 hover:text-blue-700 dark:hover:text-blue-300"
													on:click={() => (viewingChat = true)}
												>
													{chat.title}
												</button>
											{/if}
										</div>
									</td>

									<td class="px-3 py-1 hidden md:flex h-[2.5rem] justify-end">
										<div class="my-auto shrink-0">
											{dayjs(chat.updated_at * 1000).format($i18n.t('MMMM DD, YYYY HH:mm'))}
										</div>
									</td>

									<td class="px-3 py-1 text-right">
										<div class="flex justify-end w-full">
											<!-- Empty cell to match UserChatsModal's layout -->
										</div>
									</td>
								</tr>
							</tbody>
						</table>
					</div>
				</div>
			{:else}
				<div class="text-left text-sm w-full mb-8 p-3">
					<div class="text-center py-4 text-gray-500">
						{#if feedback?.meta?.chat_id}
							<div>
								<a
									href="/s/{feedback.meta.chat_id}"
									target="_blank"
									class="underline text-blue-500 hover:text-blue-700 dark:text-blue-400"
								>
									{$i18n.t('Open Chat Directly')}
								</a>
							</div>
						{:else}
							{$i18n.t('No chat data available for this feedback.')}
						{/if}
					</div>
				</div>
			{/if}
		</div>
	</div>
</Modal>
