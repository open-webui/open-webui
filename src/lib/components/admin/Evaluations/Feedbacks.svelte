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
	import FeedbackModal from './FeedbackModal.svelte';
	import EllipsisHorizontal from '$lib/components/icons/EllipsisHorizontal.svelte';

	import ChevronUp from '$lib/components/icons/ChevronUp.svelte';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import { WEBUI_BASE_URL } from '$lib/constants';
	import { config } from '$lib/stores';

	export let feedbacks = [];

	let page = 1;
	$: paginatedFeedbacks = sortedFeedbacks.slice((page - 1) * 10, page * 10);

	let orderBy: string = 'updated_at';
	let direction: 'asc' | 'desc' = 'desc';

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

	function setSortKey(key: string) {
		if (orderBy === key) {
			direction = direction === 'asc' ? 'desc' : 'asc';
		} else {
			orderBy = key;
			if (key === 'user' || key === 'model_id') {
				direction = 'asc';
			} else {
				direction = 'desc';
			}
		}
		page = 1;
	}

	$: sortedFeedbacks = [...feedbacks].sort((a, b) => {
		let aVal, bVal;

		switch (orderBy) {
			case 'user':
				aVal = a.user?.name || '';
				bVal = b.user?.name || '';
				return direction === 'asc' ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
			case 'model_id':
				aVal = a.data.model_id || '';
				bVal = b.data.model_id || '';
				return direction === 'asc' ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
			case 'rating':
				aVal = a.data.rating;
				bVal = b.data.rating;
				return direction === 'asc' ? aVal - bVal : bVal - aVal;
			case 'updated_at':
				aVal = a.updated_at;
				bVal = b.updated_at;
				return direction === 'asc' ? aVal - bVal : bVal - aVal;
			default:
				return 0;
		}
	});

	let showFeedbackModal = false;
	let selectedFeedback = null;

	const openFeedbackModal = (feedback) => {
		showFeedbackModal = true;
		selectedFeedback = feedback;
	};

	const closeFeedbackModal = () => {
		showFeedbackModal = false;
		selectedFeedback = null;
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

<FeedbackModal bind:show={showFeedbackModal} {selectedFeedback} onClose={closeFeedbackModal} />

<div class="mt-0.5 mb-2 gap-1 flex flex-row justify-between">
	<div class="flex md:self-center text-lg font-medium px-0.5">
		{$i18n.t('Feedback History')}

		<div class="flex self-center w-[1px] h-6 mx-2.5 bg-gray-50 dark:bg-gray-850" />

		<span class="text-lg font-medium text-gray-500 dark:text-gray-300">{feedbacks.length}</span>
	</div>

	{#if feedbacks.length > 0}
		<div>
			<Tooltip content={$i18n.t('Export')}>
				<button
					class=" p-2 rounded-xl hover:bg-gray-100 dark:bg-gray-900 dark:hover:bg-gray-850 transition font-medium text-sm flex items-center space-x-1"
					on:click={() => {
						exportHandler();
					}}
				>
					<ArrowDownTray className="size-3" />
				</button>
			</Tooltip>
		</div>
	{/if}
</div>

<div
	class="scrollbar-hidden relative whitespace-nowrap overflow-x-auto max-w-full rounded-sm pt-0.5"
>
	{#if (feedbacks ?? []).length === 0}
		<div class="text-center text-xs text-gray-500 dark:text-gray-400 py-1">
			{$i18n.t('No feedbacks found')}
		</div>
	{:else}
		<table
			class="w-full text-sm text-left text-gray-500 dark:text-gray-400 table-auto max-w-full rounded-sm"
		>
			<thead
				class="text-xs text-gray-700 uppercase bg-gray-50 dark:bg-gray-850 dark:text-gray-400 -translate-y-0.5"
			>
				<tr class="">
					<th
						scope="col"
						class="px-3 py-1.5 cursor-pointer select-none w-3"
						on:click={() => setSortKey('user')}
					>
						<div class="flex gap-1.5 items-center justify-end">
							{$i18n.t('User')}
							{#if orderBy === 'user'}
								<span class="font-normal">
									{#if direction === 'asc'}
										<ChevronUp className="size-2" />
									{:else}
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

					<th
						scope="col"
						class="px-3 pr-1.5 cursor-pointer select-none"
						on:click={() => setSortKey('model_id')}
					>
						<div class="flex gap-1.5 items-center">
							{$i18n.t('Models')}
							{#if orderBy === 'model_id'}
								<span class="font-normal">
									{#if direction === 'asc'}
										<ChevronUp className="size-2" />
									{:else}
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

					<th
						scope="col"
						class="px-3 py-1.5 text-right cursor-pointer select-none w-fit"
						on:click={() => setSortKey('rating')}
					>
						<div class="flex gap-1.5 items-center justify-end">
							{$i18n.t('Result')}
							{#if orderBy === 'rating'}
								<span class="font-normal">
									{#if direction === 'asc'}
										<ChevronUp className="size-2" />
									{:else}
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

					<th
						scope="col"
						class="px-3 py-1.5 text-right cursor-pointer select-none w-0"
						on:click={() => setSortKey('updated_at')}
					>
						<div class="flex gap-1.5 items-center justify-end">
							{$i18n.t('Updated At')}
							{#if orderBy === 'updated_at'}
								<span class="font-normal">
									{#if direction === 'asc'}
										<ChevronUp className="size-2" />
									{:else}
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

					<th scope="col" class="px-3 py-1.5 text-right cursor-pointer select-none w-0"> </th>
				</tr>
			</thead>
			<tbody class="">
				{#each paginatedFeedbacks as feedback (feedback.id)}
					<tr
						class="bg-white dark:bg-gray-900 dark:border-gray-850 text-xs cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-850/50 transition"
						on:click={() => openFeedbackModal(feedback)}
					>
						<td class=" py-0.5 text-right font-semibold">
							<div class="flex justify-center">
								<Tooltip content={feedback?.user?.name}>
									<div class="shrink-0">
										<img
											src={feedback?.user?.profile_image_url ?? `${WEBUI_BASE_URL}/user.png`}
											alt={feedback?.user?.name}
											class="size-5 rounded-full object-cover shrink-0"
										/>
									</div>
								</Tooltip>
							</div>
						</td>

						<td class=" py-1 pl-3 flex flex-col">
							<div class="flex flex-col items-start gap-0.5 h-full">
								<div class="flex flex-col h-full">
									{#if feedback.data?.sibling_model_ids}
										<div class="font-semibold text-gray-600 dark:text-gray-400 flex-1">
											{feedback.data?.model_id}
										</div>

										<Tooltip content={feedback.data.sibling_model_ids.join(', ')}>
											<div class=" text-[0.65rem] text-gray-600 dark:text-gray-400 line-clamp-1">
												{#if feedback.data.sibling_model_ids.length > 2}
													<!-- {$i18n.t('and {{COUNT}} more')} -->
													{feedback.data.sibling_model_ids.slice(0, 2).join(', ')}, {$i18n.t(
														'and {{COUNT}} more',
														{ COUNT: feedback.data.sibling_model_ids.length - 2 }
													)}
												{:else}
													{feedback.data.sibling_model_ids.join(', ')}
												{/if}
											</div>
										</Tooltip>
									{:else}
										<div
											class=" text-sm font-medium text-gray-600 dark:text-gray-400 flex-1 py-1.5"
										>
											{feedback.data?.model_id}
										</div>
									{/if}
								</div>
							</div>
						</td>

						{#if feedback?.data?.rating}
							<td class="px-3 py-1 text-right font-medium text-gray-900 dark:text-white w-max">
								<div class=" flex justify-end">
									{#if feedback?.data?.rating.toString() === '1'}
										<Badge type="info" content={$i18n.t('Won')} />
									{:else if feedback?.data?.rating.toString() === '0'}
										<Badge type="muted" content={$i18n.t('Draw')} />
									{:else if feedback?.data?.rating.toString() === '-1'}
										<Badge type="error" content={$i18n.t('Lost')} />
									{/if}
								</div>
							</td>
						{/if}

						<td class=" px-3 py-1 text-right font-medium">
							{dayjs(feedback.updated_at * 1000).fromNow()}
						</td>

						<td class=" px-3 py-1 text-right font-semibold" on:click={(e) => e.stopPropagation()}>
							<FeedbackMenu
								on:delete={(e) => {
									deleteFeedbackHandler(feedback.id);
								}}
							>
								<button
									class="self-center w-fit text-sm p-1.5 dark:text-gray-300 dark:hover:text-white hover:bg-black/5 dark:hover:bg-white/5 rounded-xl"
								>
									<EllipsisHorizontal />
								</button>
							</FeedbackMenu>
						</td>
					</tr>
				{/each}
			</tbody>
		</table>
	{/if}
</div>

{#if feedbacks.length > 0 && $config?.features?.enable_community_sharing}
	<div class=" flex flex-col justify-end w-full text-right gap-1">
		<div class="line-clamp-1 text-gray-500 text-xs">
			{$i18n.t('Help us create the best community leaderboard by sharing your feedback history!')}
		</div>

		<div class="flex space-x-1 ml-auto">
			<Tooltip
				content={$i18n.t(
					'To protect your privacy, only ratings, model IDs, tags, and metadata are shared from your feedback—your chat logs remain private and are not included.'
				)}
			>
				<button
					class="flex text-xs items-center px-3 py-1.5 rounded-xl bg-gray-50 hover:bg-gray-100 dark:bg-gray-850 dark:hover:bg-gray-800 dark:text-gray-200 transition"
					on:click={async () => {
						shareHandler();
					}}
				>
					<div class=" self-center mr-2 font-medium line-clamp-1">
						{$i18n.t('Share to Open WebUI Community')}
					</div>

					<div class=" self-center">
						<CloudArrowUp className="size-3" strokeWidth="3" />
					</div>
				</button>
			</Tooltip>
		</div>
	</div>
{/if}

{#if feedbacks.length > 10}
	<Pagination bind:page count={feedbacks.length} perPage={10} />
{/if}
