<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import dayjs from 'dayjs';
	import relativeTime from 'dayjs/plugin/relativeTime';
	dayjs.extend(relativeTime);

	import * as ort from 'onnxruntime-web';
	import { AutoModel, AutoTokenizer } from '@huggingface/transformers';

	const EMBEDDING_MODEL = 'TaylorAI/bge-micro-v2';
	let tokenizer = null;
	let model = null;

	import { models } from '$lib/stores';
	import { deleteFeedbackById, getAllFeedbacks } from '$lib/apis/evaluations';

	import FeedbackMenu from './Evaluations/FeedbackMenu.svelte';
	import EllipsisHorizontal from '../icons/EllipsisHorizontal.svelte';
	import Tooltip from '../common/Tooltip.svelte';
	import Badge from '../common/Badge.svelte';
	import Pagination from '../common/Pagination.svelte';
	import MagnifyingGlass from '../icons/MagnifyingGlass.svelte';
	import Share from '../icons/Share.svelte';
	import CloudArrowUp from '../icons/CloudArrowUp.svelte';
	import { toast } from 'svelte-sonner';

	const i18n = getContext('i18n');

	let rankedModels = [];
	let feedbacks = [];

	let query = '';
	let page = 1;

	let tagEmbeddings = new Map();

	let loaded = false;
	let debounceTimer;

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
	// Rank models by Elo rating
	//
	//////////////////////

	const rankHandler = async (similarities: Map<string, number> = new Map()) => {
		const modelStats = calculateModelStats(feedbacks, similarities);

		rankedModels = $models
			.filter((m) => m?.owned_by !== 'arena' && (m?.info?.meta?.hidden ?? false) !== true)
			.map((model) => {
				const stats = modelStats.get(model.id);
				return {
					...model,
					rating: stats ? Math.round(stats.rating) : '-',
					stats: {
						count: stats ? stats.won + stats.lost : 0,
						won: stats ? stats.won.toString() : '-',
						lost: stats ? stats.lost.toString() : '-'
					}
				};
			})
			.sort((a, b) => {
				if (a.rating === '-' && b.rating !== '-') return 1;
				if (b.rating === '-' && a.rating !== '-') return -1;
				if (a.rating !== '-' && b.rating !== '-') return b.rating - a.rating;
				return a.name.localeCompare(b.name);
			});
	};

	function calculateModelStats(
		feedbacks: Feedback[],
		similarities: Map<string, number>
	): Map<string, ModelStats> {
		const stats = new Map<string, ModelStats>();
		const K = 32;

		function getOrDefaultStats(modelId: string): ModelStats {
			return stats.get(modelId) || { rating: 1000, won: 0, lost: 0 };
		}

		function updateStats(modelId: string, ratingChange: number, outcome: number) {
			const currentStats = getOrDefaultStats(modelId);
			currentStats.rating += ratingChange;
			if (outcome === 1) currentStats.won++;
			else if (outcome === 0) currentStats.lost++;
			stats.set(modelId, currentStats);
		}

		function calculateEloChange(
			ratingA: number,
			ratingB: number,
			outcome: number,
			similarity: number
		): number {
			const expectedScore = 1 / (1 + Math.pow(10, (ratingB - ratingA) / 400));
			return K * (outcome - expectedScore) * similarity;
		}

		feedbacks.forEach((feedback) => {
			const modelA = feedback.data.model_id;
			const statsA = getOrDefaultStats(modelA);
			let outcome: number;

			switch (feedback.data.rating.toString()) {
				case '1':
					outcome = 1;
					break;
				case '-1':
					outcome = 0;
					break;
				default:
					return; // Skip invalid ratings
			}

			// If the query is empty, set similarity to 1, else get the similarity from the map
			const similarity = query !== '' ? similarities.get(feedback.id) || 0 : 1;
			const opponents = feedback.data.sibling_model_ids || [];

			opponents.forEach((modelB) => {
				const statsB = getOrDefaultStats(modelB);
				const changeA = calculateEloChange(statsA.rating, statsB.rating, outcome, similarity);
				const changeB = calculateEloChange(statsB.rating, statsA.rating, 1 - outcome, similarity);

				updateStats(modelA, changeA, outcome);
				updateStats(modelB, changeB, 1 - outcome);
			});
		});

		return stats;
	}

	//////////////////////
	//
	// Calculate cosine similarity
	//
	//////////////////////

	const cosineSimilarity = (vecA, vecB) => {
		// Ensure the lengths of the vectors are the same
		if (vecA.length !== vecB.length) {
			throw new Error('Vectors must be the same length');
		}

		// Calculate the dot product
		let dotProduct = 0;
		let normA = 0;
		let normB = 0;

		for (let i = 0; i < vecA.length; i++) {
			dotProduct += vecA[i] * vecB[i];
			normA += vecA[i] ** 2;
			normB += vecB[i] ** 2;
		}

		// Calculate the magnitudes
		normA = Math.sqrt(normA);
		normB = Math.sqrt(normB);

		// Avoid division by zero
		if (normA === 0 || normB === 0) {
			return 0;
		}

		// Return the cosine similarity
		return dotProduct / (normA * normB);
	};

	const calculateMaxSimilarity = (queryEmbedding, tagEmbeddings: Map<string, number[]>) => {
		let maxSimilarity = 0;
		for (const tagEmbedding of tagEmbeddings.values()) {
			const similarity = cosineSimilarity(queryEmbedding, tagEmbedding);
			maxSimilarity = Math.max(maxSimilarity, similarity);
		}
		return maxSimilarity;
	};

	//////////////////////
	//
	// Embedding functions
	//
	//////////////////////

	const getEmbeddings = async (text: string) => {
		const tokens = await tokenizer(text);
		const output = await model(tokens);

		// Perform mean pooling on the last hidden states
		const embeddings = output.last_hidden_state.mean(1);
		return embeddings.ort_tensor.data;
	};

	const getTagEmbeddings = async (tags: string[]) => {
		const embeddings = new Map();
		for (const tag of tags) {
			if (!tagEmbeddings.has(tag)) {
				tagEmbeddings.set(tag, await getEmbeddings(tag));
			}
			embeddings.set(tag, tagEmbeddings.get(tag));
		}
		return embeddings;
	};

	const debouncedQueryHandler = async () => {
		if (query.trim() === '') {
			rankHandler();
			return;
		}

		clearTimeout(debounceTimer);

		debounceTimer = setTimeout(async () => {
			const queryEmbedding = await getEmbeddings(query);
			const similarities = new Map<string, number>();

			for (const feedback of feedbacks) {
				const feedbackTags = feedback.data.tags || [];
				const tagEmbeddings = await getTagEmbeddings(feedbackTags);
				const maxSimilarity = calculateMaxSimilarity(queryEmbedding, tagEmbeddings);
				similarities.set(feedback.id, maxSimilarity);
			}

			rankHandler(similarities);
		}, 1500); // Debounce for 1.5 seconds
	};

	$: query, debouncedQueryHandler();

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
		toast.success($i18n.t('Redirecting you to OpenWebUI Community'));

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

	onMount(async () => {
		feedbacks = await getAllFeedbacks(localStorage.token);
		loaded = true;

		// Check if the tokenizer and model are already loaded and stored in the window object
		if (!window.tokenizer) {
			window.tokenizer = await AutoTokenizer.from_pretrained(EMBEDDING_MODEL);
		}

		if (!window.model) {
			window.model = await AutoModel.from_pretrained(EMBEDDING_MODEL);
		}

		// Use the tokenizer and model from the window object
		tokenizer = window.tokenizer;
		model = window.model;

		// Pre-compute embeddings for all unique tags
		const allTags = new Set(feedbacks.flatMap((feedback) => feedback.data.tags || []));
		await getTagEmbeddings(Array.from(allTags));

		rankHandler();
	});
</script>

{#if loaded}
	<div class="mt-0.5 mb-2 gap-1 flex flex-col md:flex-row justify-between">
		<div class="flex md:self-center text-lg font-medium px-0.5 shrink-0 items-center">
			<div class=" gap-1">
				{$i18n.t('Leaderboard')}
			</div>

			<div class="flex self-center w-[1px] h-6 mx-2.5 bg-gray-50 dark:bg-gray-850" />

			<span class="text-lg font-medium text-gray-500 dark:text-gray-300 mr-1.5"
				>{rankedModels.length}</span
			>
		</div>

		<div class=" flex space-x-2">
			<Tooltip content={$i18n.t('Re-rank models by topic similarity')}>
				<div class="flex flex-1">
					<div class=" self-center ml-1 mr-3">
						<MagnifyingGlass className="size-3" />
					</div>
					<input
						class=" w-full text-sm pr-4 py-1 rounded-r-xl outline-none bg-transparent"
						bind:value={query}
						placeholder={$i18n.t('Search')}
					/>
				</div>
			</Tooltip>
		</div>
	</div>

	<div
		class="scrollbar-hidden relative whitespace-nowrap overflow-x-auto max-w-full rounded pt-0.5"
	>
		{#if (rankedModels ?? []).length === 0}
			<div class="text-center text-xs text-gray-500 dark:text-gray-400 py-1">
				{$i18n.t('No models found')}
			</div>
		{:else}
			<table
				class="w-full text-sm text-left text-gray-500 dark:text-gray-400 table-auto max-w-full rounded"
			>
				<thead
					class="text-xs text-gray-700 uppercase bg-gray-50 dark:bg-gray-850 dark:text-gray-400 -translate-y-0.5"
				>
					<tr class="">
						<th scope="col" class="px-3 py-1.5 cursor-pointer select-none w-3">
							{$i18n.t('RK')}
						</th>
						<th scope="col" class="px-3 py-1.5 cursor-pointer select-none">
							{$i18n.t('Model')}
						</th>
						<th scope="col" class="px-3 py-1.5 text-right cursor-pointer select-none w-fit">
							{$i18n.t('Rating')}
						</th>
						<th scope="col" class="px-3 py-1.5 text-right cursor-pointer select-none w-5">
							{$i18n.t('Won')}
						</th>
						<th scope="col" class="px-3 py-1.5 text-right cursor-pointer select-none w-5">
							{$i18n.t('Lost')}
						</th>
					</tr>
				</thead>
				<tbody class="">
					{#each rankedModels as model, modelIdx (model.id)}
						<tr class="bg-white dark:bg-gray-900 dark:border-gray-850 text-xs group">
							<td class="px-3 py-1.5 text-left font-medium text-gray-900 dark:text-white w-fit">
								<div class=" line-clamp-1">
									{model?.rating !== '-' ? modelIdx + 1 : '-'}
								</div>
							</td>
							<td class="px-3 py-1.5 flex flex-col justify-center">
								<div class="flex items-center gap-2">
									<div class="flex-shrink-0">
										<img
											src={model?.info?.meta?.profile_image_url ?? '/favicon.png'}
											alt={model.name}
											class="size-5 rounded-full object-cover shrink-0"
										/>
									</div>

									<div class="font-medium text-gray-800 dark:text-gray-200 pr-4">
										{model.name}
									</div>
								</div>
							</td>
							<td class="px-3 py-1.5 text-right font-medium text-gray-900 dark:text-white w-max">
								{model.rating}
							</td>

							<td class=" px-3 py-1.5 text-right font-semibold text-green-500">
								<div class=" w-10">
									{#if model.stats.won === '-'}
										-
									{:else}
										<span class="hidden group-hover:inline"
											>{((model.stats.won / model.stats.count) * 100).toFixed(1)}%</span
										>
										<span class=" group-hover:hidden">{model.stats.won}</span>
									{/if}
								</div>
							</td>

							<td class="px-3 py-1.5 text-right font-semibold text-red-500">
								<div class=" w-10">
									{#if model.stats.lost === '-'}
										-
									{:else}
										<span class="hidden group-hover:inline"
											>{((model.stats.lost / model.stats.count) * 100).toFixed(1)}%</span
										>
										<span class=" group-hover:hidden">{model.stats.lost}</span>
									{/if}
								</div>
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		{/if}
	</div>

	<div class=" text-gray-500 text-xs mt-1.5 w-full flex justify-end">
		<div class=" text-right">
			<div class="line-clamp-1">
				ⓘ {$i18n.t(
					'The evaluation leaderboard is based on the Elo rating system and is updated in real-time.'
				)}
			</div>
			{$i18n.t(
				'The leaderboard is currently in beta, and we may adjust the rating calculations as we refine the algorithm.'
			)}
		</div>
	</div>

	<div class="pb-4"></div>

	<div class="mt-0.5 mb-2 gap-1 flex flex-col md:flex-row justify-between">
		<div class="flex md:self-center text-lg font-medium px-0.5">
			{$i18n.t('Feedback History')}

			<div class="flex self-center w-[1px] h-6 mx-2.5 bg-gray-50 dark:bg-gray-850" />

			<span class="text-lg font-medium text-gray-500 dark:text-gray-300">{feedbacks.length}</span>
		</div>
	</div>

	<div
		class="scrollbar-hidden relative whitespace-nowrap overflow-x-auto max-w-full rounded pt-0.5"
	>
		{#if (feedbacks ?? []).length === 0}
			<div class="text-center text-xs text-gray-500 dark:text-gray-400 py-1">
				{$i18n.t('No feedbacks found')}
			</div>
		{:else}
			<table
				class="w-full text-sm text-left text-gray-500 dark:text-gray-400 table-auto max-w-full rounded"
			>
				<thead
					class="text-xs text-gray-700 uppercase bg-gray-50 dark:bg-gray-850 dark:text-gray-400 -translate-y-0.5"
				>
					<tr class="">
						<th scope="col" class="px-3 text-right cursor-pointer select-none w-0">
							{$i18n.t('User')}
						</th>

						<th scope="col" class="px-3 pr-1.5 cursor-pointer select-none">
							{$i18n.t('Models')}
						</th>

						<th scope="col" class="px-3 py-1.5 text-right cursor-pointer select-none w-fit">
							{$i18n.t('Result')}
						</th>

						<th scope="col" class="px-3 py-1.5 text-right cursor-pointer select-none w-0">
							{$i18n.t('Updated At')}
						</th>

						<th scope="col" class="px-3 py-1.5 text-right cursor-pointer select-none w-0"> </th>
					</tr>
				</thead>
				<tbody class="">
					{#each paginatedFeedbacks as feedback (feedback.id)}
						<tr class="bg-white dark:bg-gray-900 dark:border-gray-850 text-xs">
							<td class=" py-0.5 text-right font-semibold">
								<div class="flex justify-center">
									<Tooltip content={feedback?.user?.name}>
										<div class="flex-shrink-0">
											<img
												src={feedback?.user?.profile_image_url ?? '/user.png'}
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
							<td class="px-3 py-1 text-right font-medium text-gray-900 dark:text-white w-max">
								<div class=" flex justify-end">
									{#if feedback.data.rating.toString() === '1'}
										<Badge type="info" content={$i18n.t('Won')} />
									{:else if feedback.data.rating.toString() === '0'}
										<Badge type="muted" content={$i18n.t('Draw')} />
									{:else if feedback.data.rating.toString() === '-1'}
										<Badge type="error" content={$i18n.t('Lost')} />
									{/if}
								</div>
							</td>

							<td class=" px-3 py-1 text-right font-medium">
								{dayjs(feedback.updated_at * 1000).fromNow()}
							</td>

							<td class=" px-3 py-1 text-right font-semibold">
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

	{#if feedbacks.length > 0}
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
							{$i18n.t('Share to OpenWebUI Community')}
						</div>

						<div class=" self-center">
							<svg
								xmlns="http://www.w3.org/2000/svg"
								viewBox="0 0 16 16"
								fill="currentColor"
								class="w-3.5 h-3.5"
							>
								<path
									fill-rule="evenodd"
									d="M4 2a1.5 1.5 0 0 0-1.5 1.5v9A1.5 1.5 0 0 0 4 14h8a1.5 1.5 0 0 0 1.5-1.5V6.621a1.5 1.5 0 0 0-.44-1.06L9.94 2.439A1.5 1.5 0 0 0 8.878 2H4Zm4 9.5a.75.75 0 0 1-.75-.75V8.06l-.72.72a.75.75 0 0 1-1.06-1.06l2-2a.75.75 0 0 1 1.06 0l2 2a.75.75 0 1 1-1.06 1.06l-.72-.72v2.69a.75.75 0 0 1-.75.75Z"
									clip-rule="evenodd"
								/>
							</svg>
						</div>
					</button>
				</Tooltip>
			</div>
		</div>
	{/if}

	{#if feedbacks.length > 10}
		<Pagination bind:page count={feedbacks.length} perPage={10} />
	{/if}

	<div class="pb-12"></div>
{/if}
