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
	import CloudArrowUp from '$lib/components/icons/CloudArrowUp.svelte';
	import Pagination from '$lib/components/common/Pagination.svelte';
	import FeedbackMenu from './FeedbackMenu.svelte';
	import EllipsisHorizontal from '$lib/components/icons/EllipsisHorizontal.svelte';

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

	const shareHandler = async () => {
		toast.success($i18n.t('Redirecting you to Open WebUI Community'));

		// remove snapshot from feedbacks
		const feedbacksToShare = feedbacks.map((f) => {
			const { snapshot, user, ...rest } = f;
			return rest;
		});
		console.log(feedbacksToShare);

		const url = 'https://openwebui.com';
		const tab = await window.open(`${url}/leaderboard`, '_blank');

		// Define the event handler function
		const messageHandler = (event) => {
			if (event.origin !== url) return;
			if (event.data === 'loaded') {
				tab.postMessage(JSON.stringify(feedbacksToShare), '*');

				// Remove the event listener after handling the message
				window.removeEventListener('message', messageHandler);
			}
		};

		window.addEventListener('message', messageHandler, false);
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
</script>

<!-- Header Section with improved spacing and alignment -->
<div class="mb-3 sm:mb-6">
	<div class="flex flex-col sm:flex-row items-start sm:items-center sm:justify-between gap-2 sm:gap-4">
		<div class="flex items-center gap-2 sm:gap-3 min-w-0">
			<h2 class="text-lg sm:text-xl font-semibold text-gray-900 dark:text-gray-100 truncate">
				{$i18n.t('Feedback History')}
			</h2>
			<div class="h-6 w-px bg-gray-200 dark:bg-gray-700 flex-shrink-0" />
			<span class="inline-flex items-center justify-center h-6 px-2 text-xs sm:text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-800 rounded-full flex-shrink-0">
				{feedbacks.length}
			</span>
		</div>

		{#if feedbacks.length > 0}
			<Tooltip content={$i18n.t('Export')}>
				<button
					class="inline-flex items-center justify-center p-2 sm:p-2.5 rounded-lg bg-gray-50 hover:bg-gray-100 dark:bg-gray-800 dark:hover:bg-gray-750 transition-colors duration-200 flex-shrink-0"
					on:click={() => {
						exportHandler();
					}}
					aria-label="Export feedbacks"
				>
					<ArrowDownTray className="size-3.5 sm:size-4 text-gray-700 dark:text-gray-300" />
				</button>
			</Tooltip>
		{/if}
	</div>
</div>

<!-- Table Section with improved styling -->
<div class="rounded-lg border border-gray-200 dark:border-gray-800 overflow-hidden bg-white dark:bg-gray-900">
	{#if (feedbacks ?? []).length === 0}
		<div class="flex flex-col items-center justify-center py-16 px-4">
			<div class="w-16 h-16 mb-4 rounded-full bg-gray-100 dark:bg-gray-800 flex items-center justify-center">
				<svg class="w-8 h-8 text-gray-400 dark:text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
				</svg>
			</div>
			<p class="text-sm font-medium text-gray-900 dark:text-gray-100 mb-1">
				{$i18n.t('No feedbacks found')}
			</p>
			<p class="text-xs text-gray-500 dark:text-gray-400">
				Your feedback history will appear here
			</p>
		</div>
	{:else}
		<div class="overflow-x-auto">
			<table class="w-full text-xs sm:text-sm">
				<thead class="bg-gray-50 dark:bg-gray-850 border-b border-gray-200 dark:border-gray-800">
					<tr>
						<th scope="col" class="px-3 sm:px-6 py-2.5 sm:py-3.5 text-left text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider whitespace-nowrap">
							{$i18n.t('User')}
						</th>

						<th scope="col" class="px-3 sm:px-6 py-2.5 sm:py-3.5 text-left text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider whitespace-nowrap">
							{$i18n.t('Models')}
						</th>

						<th scope="col" class="px-3 sm:px-6 py-2.5 sm:py-3.5 text-center text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider whitespace-nowrap">
							{$i18n.t('Result')}
						</th>

						<th scope="col" class="px-3 sm:px-6 py-2.5 sm:py-3.5 text-right text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider whitespace-nowrap">
							{$i18n.t('Updated At')}
						</th>

						<th scope="col" class="px-3 sm:px-6 py-2.5 sm:py-3.5 w-10 sm:w-12">
							<span class="sr-only">Actions</span>
						</th>
					</tr>
				</thead>
				<tbody class="divide-y divide-gray-200 dark:divide-gray-800">
					{#each paginatedFeedbacks as feedback (feedback.id)}
						<tr class="hover:bg-gray-50 dark:hover:bg-gray-850 transition-colors duration-150">
							<td class="px-3 sm:px-6 py-2.5 sm:py-4 whitespace-nowrap">
								<Tooltip content={feedback?.user?.name}>
									<div class="flex items-center">
										<div class="shrink-0">
											<img
												src={feedback?.user?.profile_image_url ?? '/user.png'}
												alt={feedback?.user?.name}
												class="size-7 sm:size-8 rounded-full object-cover ring-2 ring-gray-100 dark:ring-gray-800"
											/>
										</div>
									</div>
								</Tooltip>
							</td>

							<td class="px-3 sm:px-6 py-2.5 sm:py-4">
								<div class="flex flex-col gap-1 min-w-0">
									{#if feedback.data?.sibling_model_ids}
										<div class="font-medium text-gray-900 dark:text-gray-100 truncate text-xs sm:text-sm">
											{feedback.data?.model_id}
										</div>

										<Tooltip content={feedback.data.sibling_model_ids.join(', ')}>
											<div class="text-xs text-gray-500 dark:text-gray-400 line-clamp-1">
												{#if feedback.data.sibling_model_ids.length > 2}
													{feedback.data.sibling_model_ids.slice(0, 2).join(', ')}, 
													<span class="font-medium">
														{$i18n.t('and {{COUNT}} more', { COUNT: feedback.data.sibling_model_ids.length - 2 })}
													</span>
												{:else}
													{feedback.data.sibling_model_ids.join(', ')}
												{/if}
											</div>
										</Tooltip>
									{:else}
										<div class="font-medium text-gray-900 dark:text-gray-100 truncate text-xs sm:text-sm">
											{feedback.data?.model_id}
										</div>
									{/if}
								</div>
							</td>

							<td class="px-3 sm:px-6 py-2.5 sm:py-4 whitespace-nowrap text-center">
								{#if feedback.data.rating.toString() === '1'}
									<Badge type="info" content={$i18n.t('Won')} />
								{:else if feedback.data.rating.toString() === '0'}
									<Badge type="muted" content={$i18n.t('Draw')} />
								{:else if feedback.data.rating.toString() === '-1'}
									<Badge type="error" content={$i18n.t('Lost')} />
								{/if}
							</td>

							<td class="px-3 sm:px-6 py-2.5 sm:py-4 whitespace-nowrap text-right text-xs sm:text-sm text-gray-600 dark:text-gray-400">
								{dayjs(feedback.updated_at * 1000).fromNow()}
							</td>

							<td class="px-3 sm:px-6 py-2.5 sm:py-4 whitespace-nowrap text-right">
								<FeedbackMenu
									on:delete={(e) => {
										deleteFeedbackHandler(feedback.id);
									}}
								>
									<button
										class="inline-flex items-center justify-center p-1 sm:p-1.5 rounded-lg text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 hover:text-gray-900 dark:hover:text-gray-100 transition-colors duration-200"
										aria-label="Open menu"
									>
										<EllipsisHorizontal className="size-4 sm:size-5" />
									</button>
								</FeedbackMenu>
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
	{/if}
</div>

<!-- Community Share Section with improved layout -->
{#if feedbacks.length > 0}
	<div class="mt-3 sm:mt-6 p-3 sm:p-4 rounded-lg bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-gray-850 dark:to-gray-800 border border-blue-100 dark:border-gray-700">
		<div class="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 sm:gap-3">
			<div class="flex-1 min-w-0">
				<p class="text-xs sm:text-sm font-medium text-gray-900 dark:text-gray-100 mb-1">
					Share with the Community
				</p>
				<p class="text-xs text-gray-600 dark:text-gray-400">
					{$i18n.t('Help us create the best community leaderboard by sharing your feedback history!')}
				</p>
			</div>

			<Tooltip
				content={$i18n.t(
					'To protect your privacy, only ratings, model IDs, tags, and metadata are shared from your feedback—your chat logs remain private and are not included.'
				)}
			>
				<button
					class="inline-flex items-center gap-2 px-3 sm:px-4 py-2 sm:py-2.5 rounded-lg bg-white dark:bg-gray-900 hover:bg-gray-50 dark:hover:bg-gray-850 border border-gray-200 dark:border-gray-700 text-xs sm:text-sm font-medium text-gray-700 dark:text-gray-300 transition-all duration-200 hover:shadow-sm whitespace-nowrap flex-shrink-0"
					on:click={async () => {
						shareHandler();
					}}
				>
					<span>{$i18n.t('Share to Open WebUI Community')}</span>
					<CloudArrowUp className="size-3.5 sm:size-4" strokeWidth="2.5" />
				</button>
			</Tooltip>
		</div>
	</div>
{/if}

<!-- Pagination with improved spacing -->
{#if feedbacks.length > 10}
	<div class="mt-3 sm:mt-6">
		<Pagination bind:page count={feedbacks.length} perPage={10} />
	</div>
{/if}