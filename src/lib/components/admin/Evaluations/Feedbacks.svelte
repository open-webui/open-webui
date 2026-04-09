<script lang="ts">
	import { toast } from 'svelte-sonner';
	import fileSaver from 'file-saver';
	const { saveAs } = fileSaver;

	import dayjs from 'dayjs';
	import relativeTime from 'dayjs/plugin/relativeTime';
	dayjs.extend(relativeTime);

	import { onMount, getContext } from 'svelte';
	const i18n = getContext('i18n');

	import {
		deleteFeedbackById,
		exportAllFeedbacks,
		getFeedbackItems,
		getFeedbackModelIds
	} from '$lib/apis/evaluations';

	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Download from '$lib/components/icons/Download.svelte';
	import Badge from '$lib/components/common/Badge.svelte';
	import CloudArrowUp from '$lib/components/icons/CloudArrowUp.svelte';
	import Pagination from '$lib/components/common/Pagination.svelte';
	import FeedbackMenu from './FeedbackMenu.svelte';
	import FeedbackModal from './FeedbackModal.svelte';
	import EllipsisHorizontal from '$lib/components/icons/EllipsisHorizontal.svelte';
	import Dropdown from '$lib/components/common/Dropdown.svelte';

	import ChevronUp from '$lib/components/icons/ChevronUp.svelte';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import { WEBUI_API_BASE_URL, WEBUI_BASE_URL } from '$lib/constants';
	import { config } from '$lib/stores';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Select from '$lib/components/common/Select.svelte';
	import Check from '$lib/components/icons/Check.svelte';

	let page = 1;
	let items = null;
	let total = null;

	let orderBy: string = 'updated_at';
	let direction: 'asc' | 'desc' = 'desc';

	let selectedModelId: string = '';
	let modelIds: string[] = [];

	const setSortKey = (key) => {
		if (orderBy === key) {
			direction = direction === 'asc' ? 'desc' : 'asc';
		} else {
			orderBy = key;
			direction = 'asc';
		}
	};

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

	const getFeedbacks = async () => {
		try {
			const res = await getFeedbackItems(
				localStorage.token,
				orderBy,
				direction,
				page,
				selectedModelId
			).catch((error) => {
				toast.error(`${error}`);
				return null;
			});

			if (res) {
				items = res.items;
				total = res.total;
			}
		} catch (err) {
			console.error(err);
		}
	};

	$: if (orderBy && direction && page !== undefined) {
		getFeedbacks();
	}

	const loadModelIds = async () => {
		try {
			const res = await getFeedbackModelIds(localStorage.token);
			if (res) {
				modelIds = res;
			}
		} catch (err) {
			console.error(err);
		}
	};

	const deleteFeedbackHandler = async (feedbackId: string) => {
		const response = await deleteFeedbackById(localStorage.token, feedbackId).catch((err) => {
			toast.error(err);
			return null;
		});
		if (response) {
			toast.success($i18n.t('Feedback deleted successfully'));
			page = 1;
			getFeedbacks();
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

	const feedbacksToCsv = (feedbacks) => {
		const rows = feedbacks.map((f) => {
			const { data, ...rest } = f;
			return {
				id: rest.id,
				user_id: rest.user_id,
				chat_id: data?.chat_id ?? '',
				model_id: data?.model_id ?? '',
				sibling_model_ids: (data?.sibling_model_ids ?? []).join(';'),
				rating: data?.rating ?? '',
				reason: data?.reason ?? '',
				comment: data?.comment ?? '',
				created_at: rest.created_at,
				updated_at: rest.updated_at
			};
		});

		if (rows.length === 0) return '';

		const headers = Object.keys(rows[0]);
		const escape = (val) => {
			const s = String(val ?? '');
			return s.includes(',') || s.includes('"') || s.includes('\n')
				? `"${s.replace(/"/g, '""')}"`
				: s;
		};

		return [headers.join(','), ...rows.map((r) => headers.map((h) => escape(r[h])).join(','))].join(
			'\n'
		);
	};

	const exportHandler = async (format: 'json' | 'csv' = 'json') => {
		const _feedbacks = await exportAllFeedbacks(localStorage.token, selectedModelId).catch(
			(err) => {
				toast.error(err);
				return null;
			}
		);

		if (_feedbacks) {
			if (format === 'csv') {
				const csv = feedbacksToCsv(_feedbacks);
				let blob = new Blob([csv], { type: 'text/csv' });
				saveAs(blob, `feedback-history-export-${Date.now()}.csv`);
			} else {
				let blob = new Blob([JSON.stringify(_feedbacks)], {
					type: 'application/json'
				});
				saveAs(blob, `feedback-history-export-${Date.now()}.json`);
			}
		}
	};

	onMount(() => {
		loadModelIds();
	});
</script>

<FeedbackModal bind:show={showFeedbackModal} {selectedFeedback} onClose={closeFeedbackModal} />

{#if items === null || total === null}
	<div class="my-10">
		<Spinner className="size-5" />
	</div>
{:else}
	<div class="flex flex-col gap-1 mt-0.5 mb-3">
		<div class="flex justify-between items-center">
			<div class="flex items-center md:self-center text-xl font-medium px-0.5 gap-2 shrink-0">
				<div>
					{$i18n.t('Feedback History')}
				</div>

				<div class="text-lg font-medium text-gray-500 dark:text-gray-500">
					{total}
				</div>
			</div>

			<div class="flex w-full justify-end gap-1.5">
				{#if total > 0}
					<Dropdown align="end">
						<button
							class="flex text-xs items-center space-x-1 px-3 py-1.5 rounded-xl bg-gray-50 hover:bg-gray-100 dark:bg-gray-850 dark:hover:bg-gray-800 dark:text-gray-200 transition"
						>
							<div class="self-center font-medium line-clamp-1">
								{$i18n.t('Export')}
							</div>
							<ChevronDown className="size-3" strokeWidth="2.5" />
						</button>

						<div slot="content">
							<div
								class="w-[170px] rounded-2xl p-1 border border-gray-100 dark:border-gray-800 z-50 bg-white dark:bg-gray-850 dark:text-white shadow-lg"
							>
								<button
									class="select-none flex w-full gap-2 items-center px-3 py-1.5 text-sm cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl"
									type="button"
									on:click={() => exportHandler('json')}
								>
									{$i18n.t('Export as JSON')}
								</button>

								<button
									class="select-none flex w-full gap-2 items-center px-3 py-1.5 text-sm cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl"
									type="button"
									on:click={() => exportHandler('csv')}
								>
									{$i18n.t('Export as CSV')}
								</button>
							</div>
						</div>
					</Dropdown>
				{/if}
			</div>
		</div>
	</div>

	<div
		class="py-2 bg-white dark:bg-gray-900 rounded-3xl border border-gray-100/30 dark:border-gray-850/30"
	>
		{#if modelIds.length > 0}
			<div
				class="px-2.5 flex w-full bg-transparent overflow-x-auto scrollbar-none mb-1"
				on:wheel={(e) => {
					if (e.deltaY !== 0) {
						e.preventDefault();
						e.currentTarget.scrollLeft += e.deltaY;
					}
				}}
			>
				<div
					class="flex gap-0.5 w-fit text-center text-sm rounded-full bg-transparent whitespace-nowrap"
				>
					<Select
						bind:value={selectedModelId}
						items={[
							{ value: '', label: $i18n.t('All') },
							...modelIds.map((mid) => ({ value: mid, label: mid }))
						]}
						placeholder={$i18n.t('All')}
						triggerClass="relative w-full flex items-center gap-0.5 px-2.5 py-1.5 bg-gray-50 dark:bg-gray-850 rounded-xl"
						onChange={() => {
							page = 1;
							getFeedbacks();
						}}
					>
						<svelte:fragment slot="trigger" let:selectedLabel>
							<span
								class="inline-flex h-input px-0.5 w-full outline-hidden bg-transparent truncate placeholder-gray-400 focus:outline-hidden"
							>
								{selectedLabel}
							</span>
							<ChevronDown className="size-3.5" strokeWidth="2.5" />
						</svelte:fragment>

						<svelte:fragment slot="item" let:item let:selected>
							{item.label}
							<div class="ml-auto {selected ? '' : 'invisible'}">
								<Check />
							</div>
						</svelte:fragment>
					</Select>
				</div>
			</div>
		{/if}

		<div class="scrollbar-hidden relative whitespace-nowrap overflow-x-auto max-w-full px-2">
			{#if (items ?? []).length === 0}
				<div class="w-full h-full flex flex-col justify-center items-center my-16 mb-24">
					<div class="max-w-md text-center">
						<div class="text-3xl mb-3">😕</div>
						<div class="text-lg font-medium mb-1">{$i18n.t('No feedback found')}</div>
						<div class="text-gray-500 text-center text-xs">
							{$i18n.t('Try adjusting your search or filter to find what you are looking for.')}
						</div>
					</div>
				</div>
			{:else}
				<table
					class="w-full text-sm text-left text-gray-500 dark:text-gray-400 table-auto max-w-full px-2"
				>
					<thead class="text-xs text-gray-800 uppercase bg-transparent dark:text-gray-200">
						<tr class=" border-b-[1.5px] border-gray-50 dark:border-gray-850/30">
							<th
								scope="col"
								class="px-2.5 py-2 cursor-pointer select-none w-3"
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
								class="px-2.5 py-2 cursor-pointer select-none"
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
								class="px-2.5 py-2 text-right cursor-pointer select-none w-fit"
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
								class="px-2.5 py-2 text-right cursor-pointer select-none w-0"
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

							<th scope="col" class="px-2.5 py-2 text-right cursor-pointer select-none w-0"> </th>
						</tr>
					</thead>
					<tbody class="">
						{#each items as feedback (feedback.id)}
							<tr
								class="bg-white dark:bg-gray-900 dark:border-gray-850 text-xs cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-850/50 transition rounded-xl"
								on:click={() => openFeedbackModal(feedback)}
							>
								<td class=" py-0.5 text-right font-medium">
									<div class="flex justify-center">
										<Tooltip content={feedback?.user?.name}>
											<div class="shrink-0">
												<img
													src={`${WEBUI_API_BASE_URL}/users/${feedback.user.id}/profile/image`}
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
												<Tooltip content={feedback.data?.model_id} placement="top-start">
													<div
														class="font-medium text-gray-600 dark:text-gray-400 flex-1 line-clamp-1"
													>
														{feedback.data?.model_id}
													</div>
												</Tooltip>

												<Tooltip content={feedback.data.sibling_model_ids.join(', ')}>
													<div
														class=" text-[0.65rem] text-gray-600 dark:text-gray-400 line-clamp-1"
													>
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
												<Tooltip content={feedback.data?.model_id} placement="top-start">
													<div
														class="text-sm font-medium text-gray-600 dark:text-gray-400 flex-1 py-1.5 line-clamp-1"
													>
														{feedback.data?.model_id}
													</div>
												</Tooltip>
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

								<td class=" px-3 py-1 text-right font-medium" on:click={(e) => e.stopPropagation()}>
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

		{#if total > 30}
			<Pagination bind:page count={total} perPage={30} />
		{/if}
	</div>
{/if}
