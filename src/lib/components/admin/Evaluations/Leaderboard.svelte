<script lang="ts">
	import * as ort from 'onnxruntime-web';
	import { env, AutoModel, AutoTokenizer } from '@huggingface/transformers';

	env.backends.onnx.wasm.wasmPaths = '/wasm/';

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

		loadingLeaderboard = false;
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

<div class="mb-5 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
	<div class="flex items-center gap-3">
		<h2 class="text-2xl font-semibold text-gray-900 dark:text-white">
			{$i18n.t('Leaderboard')}
		</h2>
		<span class="text-sm text-gray-500 dark:text-gray-400">
			{rankedModels.length} {rankedModels.length === 1 ? 'model' : 'models'}
		</span>
	</div>

	<Tooltip content={$i18n.t('Re-rank models by topic similarity')}>
		<div class="relative md:w-64">
			<div class="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none">
				<MagnifyingGlass className="size-4 text-gray-400" />
			</div>
			<input
				class="w-full pl-10 pr-4 py-2 text-sm rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400 focus:border-transparent outline-none transition-all"
				bind:value={query}
				placeholder={$i18n.t('Search by topic...')}
				on:focus={() => {
					loadEmbeddingModel();
				}}
			/>
		</div>
	</Tooltip>
</div>

<div class="overflow-hidden rounded-lg border border-gray-200 dark:border-gray-700 shadow-sm bg-white dark:bg-gray-900 relative">
	{#if loadingLeaderboard}
		<div class="absolute inset-0 flex items-center justify-center bg-white/80 dark:bg-gray-900/80 z-10">
			<Spinner />
		</div>
	{/if}

	{#if (rankedModels ?? []).length === 0}
		<div class="text-center text-sm text-gray-500 dark:text-gray-400 py-12">
			{$i18n.t('No models found')}
		</div>
	{:else}
		<div class="overflow-x-auto">
			<table class="w-full">
				<thead class="bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
					<tr>
						<th scope="col" class="px-4 py-3 text-left text-xs font-semibold text-gray-600 dark:text-gray-300 uppercase tracking-wider w-16">
							{$i18n.t('RK')}
						</th>
						<th scope="col" class="px-4 py-3 text-left text-xs font-semibold text-gray-600 dark:text-gray-300 uppercase tracking-wider">
							{$i18n.t('Model')}
						</th>
						<th scope="col" class="px-4 py-3 text-right text-xs font-semibold text-gray-600 dark:text-gray-300 uppercase tracking-wider w-24">
							{$i18n.t('Rating')}
						</th>
						<th scope="col" class="px-4 py-3 text-right text-xs font-semibold text-gray-600 dark:text-gray-300 uppercase tracking-wider w-20">
							{$i18n.t('Won')}
						</th>
						<th scope="col" class="px-4 py-3 text-right text-xs font-semibold text-gray-600 dark:text-gray-300 uppercase tracking-wider w-20">
							{$i18n.t('Lost')}
						</th>
					</tr>
				</thead>
				<tbody class="divide-y divide-gray-200 dark:divide-gray-700">
					{#each rankedModels as model, modelIdx (model.id)}
						<tr class="hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors group">
							<td class="px-4 py-3 text-sm font-medium text-gray-900 dark:text-white">
								{model?.rating !== '-' ? modelIdx + 1 : '-'}
							</td>
							<td class="px-4 py-3">
								<div class="flex items-center gap-3">
									<img
										src={model?.info?.meta?.profile_image_url ?? '/favicon.png'}
										alt={model.name}
										class="w-8 h-8 rounded-full object-cover ring-2 ring-gray-100 dark:ring-gray-800"
									/>
									<span class="text-sm font-medium text-gray-900 dark:text-white">
										{model.name}
									</span>
								</div>
							</td>
							<td class="px-4 py-3 text-right text-sm font-semibold text-gray-900 dark:text-white">
								{model.rating}
							</td>
							<td class="px-4 py-3 text-right text-sm font-semibold text-green-600 dark:text-green-400">
								{#if model.stats.won === '-'}
									-
								{:else}
									<span class="hidden group-hover:inline">
										{((model.stats.won / model.stats.count) * 100).toFixed(1)}%
									</span>
									<span class="group-hover:hidden">{model.stats.won}</span>
								{/if}
							</td>
							<td class="px-4 py-3 text-right text-sm font-semibold text-red-600 dark:text-red-400">
								{#if model.stats.lost === '-'}
									-
								{:else}
									<span class="hidden group-hover:inline">
										{((model.stats.lost / model.stats.count) * 100).toFixed(1)}%
									</span>
									<span class="group-hover:hidden">{model.stats.lost}</span>
								{/if}
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
	{/if}
</div>

<div class="mt-3 flex items-start gap-2 text-xs text-gray-500 dark:text-gray-400">
	<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-4 h-4 flex-shrink-0 mt-0.5">
		<path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a.75.75 0 000 1.5h.253a.25.25 0 01.244.304l-.459 2.066A1.75 1.75 0 0010.747 15H11a.75.75 0 000-1.5h-.253a.25.25 0 01-.244-.304l.459-2.066A1.75 1.75 0 009.253 9H9z" clip-rule="evenodd" />
	</svg>
	<div>
		<div>
			{$i18n.t(
				'The evaluation leaderboard is based on the Elo rating system and is updated in real-time.'
			)}
		</div>
		<div class="mt-1">
			{$i18n.t(
				'The leaderboard is currently in beta, and we may adjust the rating calculations as we refine the algorithm.'
			)}
		</div>
	</div>
</div>