<script lang="ts">
	import * as ort from 'onnxruntime-web';
	import { AutoModel, AutoTokenizer } from '@huggingface/transformers';

	import { onMount, getContext } from 'svelte';
	import { models } from '$lib/stores';

	import Spinner from '$lib/components/common/Spinner.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import MagnifyingGlass from '$lib/components/icons/MagnifyingGlass.svelte';

	const i18n = getContext('i18n');

	const EMBEDDING_MODEL = 'TaylorAI/bge-micro-v2';

	let tokenizer = null;
	let model = null;

	export let feedbacks = [];

	let rankedModels = [];

	let query = '';

	let tagEmbeddings = new Map();
	let loadingLeaderboard = true;
	let debounceTimer;

	type Feedback = {
		id: string;
		data: {
			rating: number;
			model_id: string;
			sibling_model_ids: string[] | null;
			reason: string;
			comment: string;
			tags: string[];
			details?: {
				rating: number;
			};
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
				const hasStats = stats && (stats.won > 0 || stats.lost > 0);
				const hasEloRating = stats && stats.rating !== 1000; // 1000 is the default starting rating

				return {
					...model,
					rating: hasEloRating ? Math.round(stats.rating) : hasStats ? 'N/A' : '-',
					stats: {
						count: hasStats ? stats.won + stats.lost : 0,
						won: hasStats ? stats.won.toString() : '-',
						lost: hasStats ? stats.lost.toString() : '-'
					}
				};
			})
			.sort((a, b) => {
				// Sort by rating first (numeric ratings come first)
				if (typeof a.rating === 'number' && typeof b.rating !== 'number') return -1;
				if (typeof b.rating === 'number' && typeof a.rating !== 'number') return 1;
				if (typeof a.rating === 'number' && typeof b.rating === 'number')
					return b.rating - a.rating;

				// Then by count (models with feedback come next)
				if (a.stats.count > 0 && b.stats.count === 0) return -1;
				if (b.stats.count > 0 && a.stats.count === 0) return 1;
				if (a.stats.count > 0 && b.stats.count > 0) return b.stats.count - a.stats.count;

				// Finally by name
				return a.name.localeCompare(b.name);
			});

		loadingLeaderboard = false;
	};

	function calculateModelStats(
		feedbacks: Feedback[],
		similarities: Map<string, number>
	): Map<string, ModelStats> {
		const stats = new Map<string, ModelStats>();
		const K_COMPETITIVE = 32; // Higher K-factor for competitive feedback
		const K_INDIVIDUAL = 16; // Lower K-factor for individual feedback
		const VIRTUAL_OPPONENT_RATING = 1000; // Baseline ELO for individual ratings

		function getOrDefaultStats(modelId: string): ModelStats {
			return stats.get(modelId) || { rating: 1000, won: 0, lost: 0 };
		}

		function getNormalizedRating(feedback: Feedback): number | null {
			// Check for detailed rating (1-10 scale) first
			if (feedback.data.details?.rating !== undefined && feedback.data.details?.rating !== null) {
				const detailedRating = parseInt(feedback.data.details.rating.toString());
				if (detailedRating >= 1 && detailedRating <= 10) {
					return detailedRating / 10; // Normalize to 0-1 scale
				}
			}

			// Fallback to binary rating system for backward compatibility
			switch (feedback.data.rating.toString()) {
				case '1':
					return 0.8; // Treat thumbs up as 8/10
				case '-1':
					return 0.3; // Treat thumbs down as 3/10
				default:
					return null; // Skip invalid ratings
			}
		}

		function updateStats(modelId: string, ratingChange: number, normalizedRating: number) {
			const currentStats = getOrDefaultStats(modelId);
			currentStats.rating += ratingChange;

			// Count wins/losses based on normalized rating
			if (normalizedRating >= 0.6)
				currentStats.won++; // 6+/10 = won
			else if (normalizedRating <= 0.5) currentStats.lost++; // 1-5/10 = lost
			// 5.1-5.9/10 range is neither won nor lost (neutral)

			stats.set(modelId, currentStats);
		}

		function calculateEloChange(
			ratingA: number,
			ratingB: number,
			outcome: number,
			kFactor: number,
			similarity: number = 1
		): number {
			const expectedScore = 1 / (1 + Math.pow(10, (ratingB - ratingA) / 400));
			return kFactor * (outcome - expectedScore) * similarity;
		}

		feedbacks.forEach((feedback) => {
			const modelA = feedback.data.model_id;
			const statsA = getOrDefaultStats(modelA);

			const normalizedRating = getNormalizedRating(feedback);
			if (normalizedRating === null) return; // Skip invalid ratings

			const similarity = query !== '' ? similarities.get(feedback.id) || 0 : 1;
			const opponents = feedback.data.sibling_model_ids || [];
			const outcome = normalizedRating >= 0.6 ? 1 : 0; // Convert to binary outcome for ELO

			if (opponents.length > 0) {
				// Traditional ELO for competing models (higher weight)
				opponents.forEach((modelB) => {
					const statsB = getOrDefaultStats(modelB);
					const changeA = calculateEloChange(
						statsA.rating,
						statsB.rating,
						outcome,
						K_COMPETITIVE,
						similarity
					);
					const changeB = calculateEloChange(
						statsB.rating,
						statsA.rating,
						1 - outcome,
						K_COMPETITIVE,
						similarity
					);

					updateStats(modelA, changeA, normalizedRating);
					updateStats(modelB, changeB, 1 - normalizedRating);
				});
			} else {
				// Virtual ELO against baseline for individual ratings (lower weight)
				const changeA = calculateEloChange(
					statsA.rating,
					VIRTUAL_OPPONENT_RATING,
					outcome,
					K_INDIVIDUAL,
					similarity
				);
				updateStats(modelA, changeA, normalizedRating);
			}
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

	const loadEmbeddingModel = async () => {
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
	};

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
		loadingLeaderboard = true;

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

	onMount(async () => {
		rankHandler();
	});
</script>

<div class="mt-0.5 mb-2 gap-1 flex flex-col md:flex-row justify-between">
	<div class="flex md:self-center text-lg font-medium px-0.5 shrink-0 items-center">
		<div class=" gap-1">
			{$i18n.t('Leaderboard')}
		</div>

		<div class="flex self-center w-[1px] h-6 mx-2.5 bg-gray-50 dark:bg-gray-850" />

		<span class="text-lg font-medium text-[#767676] dark:text-gray-300 mr-1.5"
			>{rankedModels.length}</span
		>
	</div>

	<div class=" flex space-x-2">
		<Tooltip content={$i18n.t('Re-rank models by topic similarity')}>
			<div class="flex flex-1">
				<label for="leaderboard-search" class="sr-only"
					>{$i18n.t('Search leaderboard by topic')}</label
				>
				<div class=" self-center ml-1 mr-3" aria-hidden="true">
					<MagnifyingGlass className="size-3" />
				</div>
				<input
					id="leaderboard-search"
					type="text"
					class=" w-full text-sm pr-4 py-1 rounded-r-xl outline-none bg-transparent focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
					bind:value={query}
					placeholder={$i18n.t('Search')}
					aria-describedby="leaderboard-search-help"
					on:focus={() => {
						loadEmbeddingModel();
					}}
				/>
			</div>
		</Tooltip>
		<div id="leaderboard-search-help" class="sr-only">
			{$i18n.t(
				'Search to re-rank models by topic similarity. This does not filter models but weights their ratings based on topic relevance.'
			)}
		</div>
	</div>
</div>

<div class="scrollbar-hidden relative whitespace-nowrap overflow-x-auto max-w-full rounded pt-0.5">
	{#if loadingLeaderboard}
		<div
			class=" absolute top-0 bottom-0 left-0 right-0 flex"
			aria-live="polite"
			aria-label="Loading leaderboard"
		>
			<div class="m-auto">
				<Spinner />
			</div>
		</div>
	{/if}
	{#if (rankedModels ?? []).length === 0}
		<div class="text-center text-xs text-[#767676] dark:text-gray-400 py-1">
			{$i18n.t('No models found')}
		</div>
	{:else}
		<table
			class="w-full text-sm text-left text-[#767676] dark:text-gray-400 table-auto max-w-full rounded {loadingLeaderboard
				? 'opacity-20'
				: ''}"
			aria-label="Model leaderboard rankings"
			aria-describedby={query ? 'leaderboard-search-help' : undefined}
		>
			<thead
				class="text-xs text-[#4a4a4a] uppercase bg-gray-50 dark:bg-gray-850 dark:text-gray-400 -translate-y-0.5"
			>
				<tr class="">
					<th scope="col" class="px-3 py-1.5 w-3">
						{$i18n.t('RK')}
					</th>
					<th scope="col" class="px-3 py-1.5">
						{$i18n.t('Model')}
					</th>
					<th scope="col" class="px-3 py-1.5 text-right w-fit">
						{$i18n.t('Rating')}
					</th>
					<th scope="col" class="px-3 py-1.5 text-right w-5">
						{$i18n.t('Won')}
					</th>
					<th scope="col" class="px-3 py-1.5 text-right w-5">
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

						<td class=" px-3 py-1.5 text-right font-semibold text-[#14873f] dark:text-green-400">
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

<div class=" text-[#767676] text-xs mt-1.5 w-full flex justify-end">
	<div class=" text-right" role="note" aria-label="Leaderboard methodology explanation">
		<div class="line-clamp-1">
			ⓘ {$i18n.t(
				'The evaluation leaderboard uses a hybrid rating system combining competitive ELO ratings with individual feedback analysis.'
			)}
		</div>
		{$i18n.t(
			'All feedback contributes to Won/Lost counts. Ratings 6-10 count as "Won", 1-5 as "Lost". Competitive feedback (comparing models) receives higher weighting than individual ratings.'
		)}
	</div>
</div>
