<script lang="ts">
	import { toast } from 'svelte-sonner';
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
	import MagnifyingGlass from '$lib/components/icons/MagnifyingGlass.svelte';

	export let feedbacks: any[] = [];
	export let totalFeedbackCount: number = 0;
	export let feedbacksPage: number = 1;
	export let feedbacksPerPage: number = 10;
	export let loadFeedbacks: (page: number, search: string) => Promise<void>;
	export let loadFeedbacksCount: (search: string) => Promise<void>;
	export let page: number = 1;

	let searchQuery = '';
	let searchTimeout: NodeJS.Timeout;
	let debouncedSearchQuery = '';

	// Debounced search - wait 500ms after user stops typing
	$: {
		if (searchTimeout) {
			clearTimeout(searchTimeout);
		}

		searchTimeout = setTimeout(() => {
			debouncedSearchQuery = searchQuery;
		}, 500);
	}

	// Handle search query changes
	$: if (debouncedSearchQuery !== undefined) {
		page = 1;
		handleSearch();
	}

	// Handle page changes
	$: if (page && loadFeedbacks) {
		loadFeedbacks(page, debouncedSearchQuery);
	}

	const handleSearch = async () => {
		if (loadFeedbacksCount && loadFeedbacks) {
			await loadFeedbacksCount(debouncedSearchQuery);
			await loadFeedbacks(1, debouncedSearchQuery);
		}
	};

	// Calculate total pages
	$: totalPages = Math.ceil(totalFeedbackCount / feedbacksPerPage);

	// Use the feedbacks directly from props (no more client-side filtering/pagination)
	$: displayFeedbacks = feedbacks;

	let selectedFeedback: any = null;
	let showConversationModal = false;

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
			// Reload current page and update count
			await loadFeedbacksCount(debouncedSearchQuery);
			await loadFeedbacks(page, debouncedSearchQuery);
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
	function extractConversation(feedback: any) {
		// No feedback = no conversation
		if (!feedback) return [];

		try {
			// Extract conversation from snapshot if available
			if (feedback.snapshot?.chat) {
				const chatData = feedback.snapshot.chat.chat || feedback.snapshot.chat;

				// Check for array-style messages (flat structure)
				if (Array.isArray(chatData.messages)) {
					return chatData.messages.map((msg: any) => ({
						role: msg.role,
						content: msg.content || '',
						timestamp: msg.timestamp || 0
					}));
				}

				// Check for history-based messages (tree structure)
				if (chatData.history?.messages) {
					const messagesObj = chatData.history.messages;
					return Object.values(messagesObj)
						.map((msg: any) => ({
							role: msg.role,
							content: msg.content || '',
							timestamp: msg.timestamp || 0
						}))
						.sort((a: any, b: any) => (a.timestamp || 0) - (b.timestamp || 0));
				}

				// Check for direct object-style messages
				if (chatData.messages && typeof chatData.messages === 'object') {
					return Object.values(chatData.messages)
						.map((msg: any) => ({
							role: msg.role,
							content: msg.content || '',
							timestamp: msg.timestamp || 0
						}))
						.sort((a: any, b: any) => (a.timestamp || 0) - (b.timestamp || 0));
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

	// Sorting functionality (currently client-side, could be moved to server-side)
	let sortKey: string | null = null;
	let sortOrder: 'asc' | 'desc' | null = null;

	function setSortKey(key: string) {
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

	// Apply client-side sorting to display feedbacks (for now)
	$: sortedDisplayFeedbacks =
		sortKey && sortOrder
			? [...displayFeedbacks].sort((a: any, b: any) => {
					// Helper function to safely navigate nested properties
					const getValue = (obj: any, path: string) => {
						const properties = path.split('.');
						return properties.reduce(
							(prev: any, curr: string) => (prev && prev[curr] !== undefined ? prev[curr] : null),
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
				})
			: displayFeedbacks;

	// ...existing code...
</script>

<div class="mt-0.5 mb-2 gap-1 flex flex-row justify-between">
	<div class="flex md:self-center text-lg font-medium px-0.5">
		{$i18n.t('Feedback History')}

		<div class="flex self-center w-[1px] h-6 mx-2.5 bg-gray-50 dark:bg-gray-850" />

		<span class="text-lg font-medium text-[#767676] dark:text-gray-300">{feedbacks.length}</span>
	</div>

	<div>
		<Tooltip content={$i18n.t('Export')}>
			<button
				type="button"
				class="p-2 rounded-xl hover:bg-gray-100 dark:bg-gray-900 dark:hover:bg-gray-850 transition font-medium text-sm flex items-center focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
				on:click={exportHandler}
				aria-label="Export"
			>
				<ArrowDownTray className="size-3" />
			</button>
		</Tooltip>
	</div>
</div>

<!-- Search bar added here -->
<div class="mb-4">
	<label
		for="feedback-search"
		class="block text-sm font-medium text-[#4a4a4a] dark:text-gray-300 mb-2"
	>
		{$i18n.t('Search Feedbacks')}
	</label>
	<div class="relative">
		<div
			class="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none"
			aria-hidden="true"
		>
			<MagnifyingGlass className="w-4 h-4 text-gray-400 dark:text-gray-500" />
		</div>
		<input
			id="feedback-search"
			type="text"
			bind:value={searchQuery}
			placeholder={$i18n.t('Search by model ID, user name, reason, comment, or tags')}
			class="block w-full pl-10 pr-12 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 focus:outline-none dark:bg-gray-800 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white dark:focus:ring-blue-500 dark:focus:border-blue-500"
			aria-describedby={searchQuery ? 'search-results-count' : undefined}
		/>
		{#if searchQuery}
			<div class="absolute inset-y-0 right-0 flex items-center pr-3">
				<button
					type="button"
					on:click={() => (searchQuery = '')}
					class="text-[#757575] hover:text-gray-600 dark:hover:text-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 rounded p-1"
					aria-label="Clear search"
				>
					<span aria-hidden="true">✕</span>
				</button>
			</div>
		{/if}
	</div>
	{#if searchQuery}
		<div
			id="search-results-count"
			class="mt-2 text-sm text-[#767676] dark:text-gray-400"
			role="status"
			aria-live="polite"
		>
			{$i18n.t('Showing')}: {displayFeedbacks.length} / {totalFeedbackCount} total
		</div>
	{/if}
</div>

<div class="relative pt-0.5 w-full">
	{#if (feedbacks ?? []).length === 0}
		<div class="text-center text-xs text-[#767676] dark:text-gray-400 py-1">
			{$i18n.t('No feedbacks found')}
		</div>
	{:else}
		<table
			class="w-full text-sm text-left text-[#767676] dark:text-gray-400 table-fixed"
			aria-label="Feedback history table"
			aria-describedby={searchQuery ? 'search-results-count' : undefined}
		>
			<thead
				class="text-xs text-[#4a4a4a] uppercase bg-gray-50 dark:bg-gray-850 dark:text-gray-400 -translate-y-0.5"
			>
				<tr>
					<!-- User column - wider to accommodate French translation -->
					<th
						scope="col"
						class="px-2 py-1.5 w-16 text-center cursor-pointer"
						on:click={() => setSortKey('user.name')}
						on:keydown={(e) => e.key === 'Enter' && setSortKey('user.name')}
						tabindex="0"
						aria-sort={sortKey === 'user.name'
							? sortOrder === 'asc'
								? 'ascending'
								: sortOrder === 'desc'
									? 'descending'
									: 'none'
							: 'none'}
						aria-label="Sort by user name"
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
						on:keydown={(e) => e.key === 'Enter' && setSortKey('data.model_id')}
						tabindex="0"
						role="columnheader"
						aria-sort={sortKey === 'data.model_id'
							? sortOrder === 'asc'
								? 'ascending'
								: sortOrder === 'desc'
									? 'descending'
									: 'none'
							: 'none'}
						aria-label="Sort by model"
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
						on:keydown={(e) => e.key === 'Enter' && setSortKey('data.rating')}
						tabindex="0"
						role="columnheader"
						aria-sort={sortKey === 'data.rating'
							? sortOrder === 'asc'
								? 'ascending'
								: sortOrder === 'desc'
									? 'descending'
									: 'none'
							: 'none'}
						aria-label="Sort by result"
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
						on:keydown={(e) => e.key === 'Enter' && setSortKey('data.details.rating')}
						tabindex="0"
						role="columnheader"
						aria-sort={sortKey === 'data.details.rating'
							? sortOrder === 'asc'
								? 'ascending'
								: sortOrder === 'desc'
									? 'descending'
									: 'none'
							: 'none'}
						aria-label="Sort by rating"
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
						on:keydown={(e) => e.key === 'Enter' && setSortKey('data.reason')}
						tabindex="0"
						role="columnheader"
						aria-sort={sortKey === 'data.reason'
							? sortOrder === 'asc'
								? 'ascending'
								: sortOrder === 'desc'
									? 'descending'
									: 'none'
							: 'none'}
						aria-label="Sort by reason"
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
						on:keydown={(e) => e.key === 'Enter' && setSortKey('data.comment')}
						tabindex="0"
						role="columnheader"
						aria-sort={sortKey === 'data.comment'
							? sortOrder === 'asc'
								? 'ascending'
								: sortOrder === 'desc'
									? 'descending'
									: 'none'
							: 'none'}
						aria-label="Sort by comment"
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
					<th scope="col" class="px-3 py-1.5 w-[13%]">
						<span class="whitespace-nowrap">{$i18n.t('Tags')}</span>
					</th>

					<!-- Updated At column - better width -->
					<th
						scope="col"
						class="px-3 py-1.5 w-[13%] text-right cursor-pointer select-none"
						on:click={() => setSortKey('updated_at')}
						on:keydown={(e) => e.key === 'Enter' && setSortKey('updated_at')}
						tabindex="0"
						role="columnheader"
						aria-sort={sortKey === 'updated_at'
							? sortOrder === 'asc'
								? 'ascending'
								: sortOrder === 'desc'
									? 'descending'
									: 'none'
							: 'none'}
						aria-label="Sort by updated date"
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
					<th scope="col" class="px-2 py-1.5 w-10 text-right">
						<span class="sr-only">{$i18n.t('Actions')}</span>
					</th>
				</tr>
			</thead>

			<tbody>
				{#each sortedDisplayFeedbacks as feedback (feedback.id)}
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
									class="font-medium text-[#767676] dark:text-gray-400 whitespace-nowrap overflow-hidden text-ellipsis"
								>
									{feedback.data?.model_id || '-'}
								</div>
								{#if feedback.data?.sibling_model_ids?.length}
									<Tooltip content={feedback.data.sibling_model_ids.join(', ')}>
										<div class="text-[0.65rem] text-[#767676] dark:text-gray-400 line-clamp-1">
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
											type="button"
											class="w-fit text-sm px-1 py-1 hover:bg-black/5 dark:hover:bg-white/5 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
											on:click={() => {
												selectedFeedback = feedback;
												showConversationModal = true;
											}}
											aria-label="View chat conversation for this feedback"
										>
											<ChatBubbles />
										</button>
									</Tooltip>
								{:else}
									<span class="text-[#757575] italic text-xs" aria-label="No chat available">-</span
									>
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
										class="inline-flex items-center justify-center px-1.5 py-0.5 rounded-full bg-gray-100 dark:bg-gray-800 text-[#6a6a6a] dark:text-gray-300"
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
							<time datetime={new Date(feedback.updated_at * 1000).toISOString()}>
								{dayjs(feedback.updated_at * 1000).fromNow()}
							</time>
						</td>

						<!-- Actions cell - ensure right alignment to match header -->
						<td class="px-2 py-1.5 text-right">
							<div class="flex justify-end items-center">
								<FeedbackMenu
									on:delete={() => {
										deleteFeedbackHandler(feedback.id);
									}}
								>
									<div
										class="inline-flex text-sm p-1 dark:text-gray-300 dark:hover:text-white hover:bg-black/5 dark:hover:bg-white/5 rounded-xl cursor-pointer"
										aria-label="Open feedback actions menu"
									>
										<EllipsisHorizontal />
									</div>
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

{#if totalFeedbackCount > feedbacksPerPage}
	<Pagination bind:page count={totalFeedbackCount} perPage={feedbacksPerPage} />
{/if}
