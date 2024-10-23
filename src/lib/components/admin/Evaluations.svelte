<script lang="ts">
	import { onMount, getContext } from 'svelte';

	import dayjs from 'dayjs';
	import relativeTime from 'dayjs/plugin/relativeTime';
	dayjs.extend(relativeTime);

	import { models } from '$lib/stores';
	import { getAllFeedbacks } from '$lib/apis/evaluations';

	import FeedbackMenu from './Evaluations/FeedbackMenu.svelte';
	import EllipsisHorizontal from '../icons/EllipsisHorizontal.svelte';
	import Tooltip from '../common/Tooltip.svelte';
	import Badge from '../common/Badge.svelte';

	const i18n = getContext('i18n');

	let rankedModels = [];
	let feedbacks = [];

	type Feedback = {
		model_id: string;
		sibling_model_ids?: string[];
		rating: number;
	};

	type ModelStats = {
		rating: number;
		won: number;
		draw: number;
		lost: number;
	};

	function calculateModelStats(feedbacks: Feedback[]): Map<string, ModelStats> {
		const stats = new Map<string, ModelStats>();
		const K = 32;

		function getOrDefaultStats(modelId: string): ModelStats {
			return stats.get(modelId) || { rating: 1000, won: 0, draw: 0, lost: 0 };
		}

		function updateStats(modelId: string, ratingChange: number, outcome: number) {
			const currentStats = getOrDefaultStats(modelId);
			currentStats.rating += ratingChange;
			if (outcome === 1) currentStats.won++;
			else if (outcome === 0.5) currentStats.draw++;
			else if (outcome === 0) currentStats.lost++;
			stats.set(modelId, currentStats);
		}

		function calculateEloChange(ratingA: number, ratingB: number, outcome: number): number {
			const expectedScore = 1 / (1 + Math.pow(10, (ratingB - ratingA) / 400));
			return K * (outcome - expectedScore);
		}

		feedbacks.forEach((feedback) => {
			const modelA = feedback.data.model_id;
			const statsA = getOrDefaultStats(modelA);
			let outcome: number;

			switch (feedback.data.rating.toString()) {
				case '1':
					outcome = 1;
					break;
				case '0':
					outcome = 0.5;
					break;
				case '-1':
					outcome = 0;
					break;
				default:
					return; // Skip invalid ratings
			}

			const opponents = feedback.data.sibling_model_ids || [];
			opponents.forEach((modelB) => {
				const statsB = getOrDefaultStats(modelB);
				const changeA = calculateEloChange(statsA.rating, statsB.rating, outcome);
				const changeB = calculateEloChange(statsB.rating, statsA.rating, 1 - outcome);

				updateStats(modelA, changeA, outcome);
				updateStats(modelB, changeB, 1 - outcome);
			});
		});

		return stats;
	}

	let loaded = false;
	onMount(async () => {
		feedbacks = await getAllFeedbacks(localStorage.token);
		const modelStats = calculateModelStats(feedbacks);

		rankedModels = $models
			.filter((m) => m?.owned_by !== 'arena' && (m?.info?.meta?.hidden ?? false) !== true)
			.map((model) => {
				const stats = modelStats.get(model.name);
				return {
					...model,
					rating: stats ? Math.round(stats.rating) : '-',
					stats: {
						count: stats ? stats.won + stats.draw + stats.lost : 0,
						won: stats ? stats.won.toString() : '-',
						lost: stats ? stats.lost.toString() : '-'
					}
				};
			})
			.sort((a, b) => {
				// Handle sorting by rating ('-' goes to the end)
				if (a.rating === '-' && b.rating !== '-') return 1;
				if (b.rating === '-' && a.rating !== '-') return -1;

				// If both have ratings (non '-'), sort by rating numerically (descending)
				if (a.rating !== '-' && b.rating !== '-') return b.rating - a.rating;

				// If both ratings are '-', sort alphabetically (by 'name')
				return a.name.localeCompare(b.name);
			});

		loaded = true;
	});
</script>

{#if loaded}
	<div class="mt-0.5 mb-2 gap-1 flex flex-col md:flex-row justify-between">
		<div class="flex md:self-center text-lg font-medium px-0.5">
			{$i18n.t('Leaderboard')}

			<div class="flex self-center w-[1px] h-6 mx-2.5 bg-gray-50 dark:bg-gray-850" />

			<span class="text-lg font-medium text-gray-500 dark:text-gray-300">{rankedModels.length}</span
			>
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

	<div class="pb-4"></div>

	<div class="mt-0.5 mb-2 gap-1 flex flex-col md:flex-row justify-between">
		<div class="flex md:self-center text-lg font-medium px-0.5">
			{$i18n.t('Feedback History')}
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
					{#each feedbacks as feedback (feedback.id)}
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
								<FeedbackMenu>
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

	<div class="pb-8"></div>
{/if}
