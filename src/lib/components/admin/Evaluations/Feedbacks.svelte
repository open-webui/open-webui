<script lang="ts">
	import { toast } from '$lib/utils/toast';
	import fileSaver from 'file-saver';
	const { saveAs } = fileSaver;

	import dayjs from 'dayjs';
	import relativeTime from 'dayjs/plugin/relativeTime';
	dayjs.extend(relativeTime);

	import { onMount, getContext } from 'svelte';
	const i18n = getContext('i18n');

	import { deleteFeedbackById, exportAllFeedbacks, getAllFeedbacks } from '$lib/apis/evaluations';

	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import ArrowDownTray from '$lib/components/icons/ArrowDownTray.svelte';
	import Badge from '$lib/components/common/Badge.svelte';
	import Pagination from '$lib/components/common/Pagination.svelte';
	import FeedbackMenu from './FeedbackMenu.svelte';
	import EllipsisHorizontal from '$lib/components/icons/EllipsisHorizontal.svelte';
	import ChatBubbles from '$lib/components/icons/ChatBubbles.svelte';
	import FeedbackConversationModal from './FeedbackConversationModal.svelte';
	import ChevronUp from '$lib/components/icons/ChevronUp.svelte';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';

	export let feedbacks = [];

	let page = 1;
	$: paginatedFeedbacks = feedbacks.slice((page - 1) * 10, page * 10);

	type Feedback = {
		id: string;
		data: {
			rating: number;
			model_id: string;
			sibling_model_ids: string[] | null;
			reason: string;
			comment: string;
			tags: string[];
		};
		user: {
			name: string;
			profile_image_url: string;
		};
		updated_at: number;
	};

	type ModelStats = {
		rating: number;
		won: number;
		lost: number;
	};

	//////////////////////
	//
	// CRUD operations
	//
	//////////////////////

	const deleteFeedbackHandler = async (feedbackId: string) => {
		const response = await deleteFeedbackById(localStorage.token, feedbackId).catch((err) => {
			toast.error(err);
			return null;
		});
		if (response) {
			feedbacks = feedbacks.filter((f) => f.id !== feedbackId);
		}
	};

	const exportHandler = async () => {
		const _feedbacks = await exportAllFeedbacks(localStorage.token).catch((err) => {
			toast.error(err);
			return null;
		});

		if (_feedbacks) {
			let blob = new Blob([JSON.stringify(_feedbacks)], {
				type: 'application/json'
			});
			saveAs(blob, `feedback-history-export-${Date.now()}.json`);
		}
	};

	// Simplified conversation extraction function
	function extractConversation(feedback) {
		// No feedback = no conversation
		if (!feedback) return [];

		try {
			// Extract conversation from snapshot if available
			if (feedback.snapshot?.chat) {
				const chatData = feedback.snapshot.chat.chat || feedback.snapshot.chat;

				// Check for array-style messages (flat structure)
				if (Array.isArray(chatData.messages)) {
					return chatData.messages.map((msg) => ({
						role: msg.role,
						content: msg.content || '',
						timestamp: msg.timestamp || 0
					}));
				}

				// Check for history-based messages (tree structure)
				if (chatData.history?.messages) {
					const messagesObj = chatData.history.messages;
					return Object.values(messagesObj)
						.map((msg) => ({
							role: msg.role,
							content: msg.content || '',
							timestamp: msg.timestamp || 0
						}))
						.sort((a, b) => (a.timestamp || 0) - (b.timestamp || 0));
				}

				// Check for direct object-style messages
				if (chatData.messages && typeof chatData.messages === 'object') {
					return Object.values(chatData.messages)
						.map((msg) => ({
							role: msg.role,
							content: msg.content || '',
							timestamp: msg.timestamp || 0
						}))
						.sort((a, b) => (a.timestamp || 0) - (b.timestamp || 0));
				}
			}

			// Fallback to using available feedback data
			const messages = [];

			if (feedback.data) {
				// Create placeholder messages from feedback data
				if (feedback.data.model_id || feedback.data.reason || feedback.data.comment) {
					const ratingText =
						feedback.data.rating === 1
							? 'Positive'
							: feedback.data.rating === -1
								? 'Negative'
								: 'Neutral';

					messages.push({
						role: 'user',
						content: `[${ratingText} feedback for ${feedback.data.model_id || 'unknown model'}]`,
						timestamp: feedback.created_at ? feedback.created_at - 1 : 0
					});

					if (feedback.data.comment) {
						messages.push({
							role: 'assistant',
							content: feedback.data.comment,
							timestamp: feedback.created_at || 0
						});
					}
				}
			}

			return messages;
		} catch (error) {
			// Return empty array on error
			return [];
		}
	}

	// Sorting functionality
	let sortKey = null; // Set initial sort to null instead of 'updated_at'
	let sortOrder = null; // Set initial order to null instead of 'desc'

	function setSortKey(key) {
		if (sortKey === key) {
			// Cycle through: asc -> desc -> null (default/no sorting)
			if (sortOrder === 'asc') {
				sortOrder = 'desc';
			} else if (sortOrder === 'desc') {
				sortOrder = null; // Add null state for no sorting
			} else {
				sortOrder = 'asc';
			}
		} else {
			sortKey = key;
			sortOrder = 'asc';
		}
	}

	// Apply sorting to feedbacks before pagination
	$: sortedFeedbacks = [...feedbacks].sort((a, b) => {
		// If no sort order is specified, sort by updated_at desc (default behavior)
		if (sortOrder === null || sortKey === null) {
			return b.updated_at - a.updated_at; // Default sort by updated_at desc
		}

		// Helper function to safely navigate nested properties
		const getValue = (obj, path) => {
			const properties = path.split('.');
			return properties.reduce(
				(prev, curr) => (prev && prev[curr] !== undefined ? prev[curr] : null),
				obj
			);
		};

		let valA = getValue(a, sortKey);
		let valB = getValue(b, sortKey);

		// Special handling for different data types
		if (typeof valA === 'string' && typeof valB === 'string') {
			return sortOrder === 'asc' ? valA.localeCompare(valB) : valB.localeCompare(valA);
		}

		// Ensure we have values to compare
		if (valA === null || valA === undefined) return sortOrder === 'asc' ? -1 : 1;
		if (valB === null || valB === undefined) return sortOrder === 'asc' ? 1 : -1;

		return sortOrder === 'asc' ? valA - valB : valB - valA;
	});

	// Update paginated feedbacks to use sorted result
	$: paginatedFeedbacks = sortedFeedbacks.slice((page - 1) * 10, page * 10);

	let selectedFeedback = null;
	let showConversationModal = false;
</script>

<div class="mt-0.5 mb-2 gap-1 flex flex-row justify-between">
	<div class="flex md:self-center text-lg font-medium px-0.5">
		{$i18n.t('Feedback History')}

		<div class="flex self-center w-[1px] h-6 mx-2.5 bg-gray-50 dark:bg-gray-850" />

		<span class="text-lg font-medium text-gray-500 dark:text-gray-300">{feedbacks.length}</span>
	</div>

	<div>
		<Tooltip content={$i18n.t('Export')}>
			<button
				class="p-2 rounded-xl hover:bg-gray-100 dark:bg-gray-900 dark:hover:bg-gray-850 transition font-medium text-sm flex items-center"
				on:click={exportHandler}
			>
				<ArrowDownTray className="size-3" />
			</button>
		</Tooltip>
	</div>
</div>

<div class="relative pt-0.5 w-full">
	{#if (feedbacks ?? []).length === 0}
		<div class="text-center text-xs text-gray-500 dark:text-gray-400 py-1">
			{$i18n.t('No feedbacks found')}
		</div>
	{:else}
		<table class="w-full text-sm text-left text-gray-500 dark:text-gray-400 table-fixed">
			<thead
				class="text-xs text-gray-700 uppercase bg-gray-50 dark:bg-gray-850 dark:text-gray-400 -translate-y-0.5"
			>
				<tr>
					<!-- User column - wider to accommodate French translation -->
					<th
						scope="col"
						class="px-2 py-1.5 w-16 text-center"
						on:click={() => setSortKey('user.name')}
					>
						<div class="flex items-center justify-center">
							<span class="whitespace-nowrap mx-auto">{$i18n.t('User')}</span>
							{#if sortKey === 'user.name'}
								<span class="font-normal ml-1">
									{#if sortOrder === 'asc'}
										<ChevronUp className="size-2" />
									{:else if sortOrder === 'desc'}
										<ChevronDown className="size-2" />
									{/if}
								</span>
							{/if}
						</div>
					</th>

					<!-- Model column - compact -->
					<th
						scope="col"
						class="px-3 py-1.5 w-[12%] cursor-pointer select-none"
						on:click={() => setSortKey('data.model_id')}
					>
						<div class="flex gap-1 items-center">
							{$i18n.t('Models')}
							{#if sortKey === 'data.model_id'}
								<span class="font-normal">
									{#if sortOrder === 'asc'}
										<ChevronUp className="size-2" />
									{:else if sortOrder === 'desc'}
										<ChevronDown className="size-2" />
									{/if}
								</span>
							{:else}
								<span class="invisible">
									<ChevronUp className="size-2" />
								</span>
							{/if}
						</div>
					</th>

					<!-- Chat column - fixed width, explicitly centered -->
					<th scope="col" class="px-1 py-1.5 w-12 text-center">
						<span class="whitespace-nowrap mx-auto">{$i18n.t('Chat')}</span>
					</th>

					<!-- Result column - left aligned like other columns -->
					<th
						scope="col"
						class="px-1 py-1.5 w-16 cursor-pointer select-none"
						on:click={() => setSortKey('data.rating')}
					>
						<div class="flex gap-1 items-center">
							<span class="whitespace-nowrap">{$i18n.t('Result')}</span>
							{#if sortKey === 'data.rating'}
								<span class="font-normal">
									{#if sortOrder === 'asc'}
										<ChevronUp className="size-2" />
									{:else if sortOrder === 'desc'}
										<ChevronDown className="size-2" />
									{/if}
								</span>
							{:else}
								<span class="invisible">
									<ChevronUp className="size-2" />
								</span>
							{/if}
						</div>
					</th>

					<!-- Rating column - left aligned like other columns -->
					<th
						scope="col"
						class="px-1 py-1.5 w-16 cursor-pointer select-none"
						on:click={() => setSortKey('data.details.rating')}
					>
						<div class="flex gap-1 items-center">
							<span class="whitespace-nowrap">{$i18n.t('Rating')}</span>
							{#if sortKey === 'data.details.rating'}
								<span class="font-normal">
									{#if sortOrder === 'asc'}
										<ChevronUp className="size-2" />
									{:else if sortOrder === 'desc'}
										<ChevronDown className="size-2" />
									{/if}
								</span>
							{:else}
								<span class="invisible">
									<ChevronUp className="size-2" />
								</span>
							{/if}
						</div>
					</th>

					<!-- Reason column - reduced width -->
					<th
						scope="col"
						class="px-3 py-1.5 w-[13%] cursor-pointer select-none"
						on:click={() => setSortKey('data.reason')}
					>
						<div class="flex gap-1 items-center whitespace-nowrap">
							{$i18n.t('Reason')}
							{#if sortKey === 'data.reason'}
								<span class="font-normal">
									{#if sortOrder === 'asc'}
										<ChevronUp className="size-2" />
									{:else if sortOrder === 'desc'}
										<ChevronDown className="size-2" />
									{/if}
								</span>
							{:else}
								<span class="invisible">
									<ChevronUp className="size-2" />
								</span>
							{/if}
						</div>
					</th>

					<!-- Comment column - reduced width -->
					<th
						scope="col"
						class="px-3 py-1.5 w-[15%] cursor-pointer select-none"
						on:click={() => setSortKey('data.comment')}
					>
						<div class="flex gap-1 items-center">
							{$i18n.t('Comment')}
							{#if sortKey === 'data.comment'}
								<span class="font-normal">
									{#if sortOrder === 'asc'}
										<ChevronUp className="size-2" />
									{:else if sortOrder === 'desc'}
										<ChevronDown className="size-2" />
									{/if}
								</span>
							{:else}
								<span class="invisible">
									<ChevronUp className="size-2" />
								</span>
							{/if}
						</div>
					</th>

					<!-- Tags column - reduced width -->
					<th scope="col" class="px-3 py-1.5 w-[13%] cursor-pointer select-none">
						<span class="whitespace-nowrap">{$i18n.t('Tags')}</span>
					</th>

					<!-- Updated At column - better width -->
					<th
						scope="col"
						class="px-3 py-1.5 w-[13%] text-right cursor-pointer select-none"
						on:click={() => setSortKey('updated_at')}
					>
						<div class="flex gap-1 items-center justify-end whitespace-nowrap">
							{$i18n.t('Updated At')}
							{#if sortKey === 'updated_at'}
								<span class="font-normal">
									{#if sortOrder === 'asc'}
										<ChevronUp className="size-2" />
									{:else if sortOrder === 'desc'}
										<ChevronDown className="size-2" />
									{/if}
								</span>
							{/if}
						</div>
					</th>

					<!-- Actions column - minimal width -->
					<th scope="col" class="px-2 py-1.5 w-10 text-right"></th>
				</tr>
			</thead>

			<tbody>
				{#each paginatedFeedbacks as feedback (feedback.id)}
					{@const conversation = extractConversation(feedback)}
					<tr
						class="bg-white dark:bg-gray-900 dark:border-gray-850 text-xs hover:bg-gray-50 dark:hover:bg-gray-850"
					>
						<!-- User cell - explicitly centered to match header -->
						<td class="px-2 py-1.5 text-center">
							<div class="flex items-center justify-center">
								<Tooltip content={feedback?.user?.name}>
									<div class="flex-shrink-0">
										<img
											src={feedback?.user?.profile_image_url ?? '/user.png'}
											alt={feedback?.user?.name}
											class="size-5 rounded-full object-cover shrink-0 mx-auto"
										/>
									</div>
								</Tooltip>
							</div>
						</td>

						<!-- Model cell - ensure left alignment to match header -->
						<td class="px-3 py-1.5">
							<div class="flex flex-col overflow-hidden">
								<div
									class="font-medium text-gray-600 dark:text-gray-400 whitespace-nowrap overflow-hidden text-ellipsis"
								>
									{feedback.data?.model_id || '-'}
								</div>
								{#if feedback.data?.sibling_model_ids?.length}
									<Tooltip content={feedback.data.sibling_model_ids.join(', ')}>
										<div class="text-[0.65rem] text-gray-600 dark:text-gray-400 line-clamp-1">
											{#if feedback.data.sibling_model_ids.length > 2}
												{feedback.data.sibling_model_ids.slice(0, 2).join(', ')}, {$i18n.t(
													'and {{COUNT}} more',
													{ COUNT: feedback.data.sibling_model_ids.length - 2 }
												)}
											{:else}
												{feedback.data.sibling_model_ids.join(', ')}
											{/if}
										</div>
									</Tooltip>
								{/if}
							</div>
						</td>

						<!-- Chat cell - explicitly centered to match header -->
						<td class="px-1 py-1.5 text-center">
							<div class="flex justify-center">
								{#if conversation && conversation.length > 0}
									<Tooltip content={$i18n.t('Chat')}>
										<button
											class="w-fit text-sm px-1 py-1 hover:bg-black/5 dark:hover:bg-white/5 rounded-xl"
											on:click={() => {
												selectedFeedback = feedback;
												showConversationModal = true;
											}}
										>
											<ChatBubbles />
										</button>
									</Tooltip>
								{:else}
									<span class="text-gray-400 italic text-xs">-</span>
								{/if}
							</div>
						</td>

						<!-- Result cell - left aligned to match header -->
						<td class="px-1 py-1.5">
							<div class="w-full flex">
								{#if feedback.data.rating.toString() === '1'}
									<Badge type="info" content={$i18n.t('Won')} />
								{:else if feedback.data.rating.toString() === '0'}
									<Badge type="muted" content={$i18n.t('Draw')} />
								{:else if feedback.data.rating.toString() === '-1'}
									<Badge type="error" content={$i18n.t('Lost')} />
								{/if}
							</div>
						</td>

						<!-- Rating cell - left aligned to match header -->
						<td class="px-1 py-1.5">
							<div class="w-full flex">
								{#if feedback.data.details?.rating}
									<div
										class="inline-flex items-center justify-center px-1.5 py-0.5 rounded-full bg-gray-100 dark:bg-gray-800"
									>
										{feedback.data.details.rating}/10
									</div>
								{:else}
									<span>-</span>
								{/if}
							</div>
						</td>

						<!-- Reason cell - ensure left alignment to match header -->
						<td class="px-3 py-1.5 min-w-0">
							{#if feedback.data.reason}
								<Tooltip content={feedback.data.reason}>
									<div class="line-clamp-1 overflow-hidden text-ellipsis">
										{#if feedback.data.reason === 'accurate_information'}
											{$i18n.t('Accurate information')}
										{:else if feedback.data.reason === 'followed_instructions_perfectly'}
											{$i18n.t('Followed instructions perfectly')}
										{:else if feedback.data.reason === 'showcased_creativity'}
											{$i18n.t('Showcased creativity')}
										{:else if feedback.data.reason === 'positive_attitude'}
											{$i18n.t('Positive attitude')}
										{:else if feedback.data.reason === 'attention_to_detail'}
											{$i18n.t('Attention to detail')}
										{:else if feedback.data.reason === 'thorough_explanation'}
											{$i18n.t('Thorough explanation')}
										{:else if feedback.data.reason === 'dont_like_the_style'}
											{$i18n.t("Don't like the style")}
										{:else if feedback.data.reason === 'too_verbose'}
											{$i18n.t('Too verbose')}
										{:else if feedback.data.reason === 'not_helpful'}
											{$i18n.t('Not helpful')}
										{:else if feedback.data.reason === 'not_factually_correct'}
											{$i18n.t('Not factually correct')}
										{:else if feedback.data.reason === 'didnt_fully_follow_instructions'}
											{$i18n.t("Didn't fully follow instructions")}
										{:else if feedback.data.reason === 'refused_when_it_shouldnt_have'}
											{$i18n.t("Refused when it shouldn't have")}
										{:else if feedback.data.reason === 'being_lazy'}
											{$i18n.t('Being lazy')}
										{:else if feedback.data.reason === 'other'}
											{$i18n.t('Other')}
										{:else}
											{feedback.data.reason}
										{/if}
									</div>
								</Tooltip>
							{:else}
								<div class="text-center sm:text-left">-</div>
							{/if}
						</td>

						<!-- Comment cell - ensure left alignment to match header -->
						<td class="px-3 py-1.5 min-w-0">
							{#if feedback.data.comment}
								<Tooltip content={feedback.data.comment}>
									<div class="line-clamp-1 overflow-hidden text-ellipsis">
										{feedback.data.comment}
									</div>
								</Tooltip>
							{:else}
								<div class="text-center sm:text-left">-</div>
							{/if}
						</td>

						<!-- Tags cell - ensure left alignment to match header -->
						<td class="px-3 py-1.5">
							{#if feedback.data.tags?.length > 0}
								<div class="flex flex-wrap gap-1">
									{#each feedback.data.tags.slice(0, 2) as tag}
										<Badge type="muted" content={tag} />
									{/each}
									{#if feedback.data.tags.length > 2}
										<Tooltip content={feedback.data.tags.slice(2).join(', ')}>
											<Badge type="muted" content={`+${feedback.data.tags.length - 2}`} />
										</Tooltip>
									{/if}
								</div>
							{:else}
								<div class="text-center sm:text-left">-</div>
							{/if}
						</td>

						<td class="px-3 py-1.5 text-right text-xs" style="min-width: 90px;">
							{dayjs(feedback.updated_at * 1000).fromNow()}
						</td>

						<!-- Actions cell - ensure right alignment to match header -->
						<td class="px-2 py-1.5 text-right">
							<div class="flex justify-end items-center">
								<FeedbackMenu
									on:delete={() => {
										deleteFeedbackHandler(feedback.id);
									}}
								>
									<button
										class="inline-flex text-sm p-1 dark:text-gray-300 dark:hover:text-white hover:bg-black/5 dark:hover:bg-white/5 rounded-xl"
									>
										<EllipsisHorizontal />
									</button>
								</FeedbackMenu>
							</div>
						</td>
					</tr>
				{/each}
			</tbody>
		</table>
	{/if}
</div>

<FeedbackConversationModal bind:show={showConversationModal} feedback={selectedFeedback} />

{#if feedbacks.length > 10}
	<Pagination bind:page count={feedbacks.length} perPage={10} />
{/if}
