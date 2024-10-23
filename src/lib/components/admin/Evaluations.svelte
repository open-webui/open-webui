<script lang="ts">
	import { onMount, getContext } from 'svelte';

	import { models } from '$lib/stores';
	const i18n = getContext('i18n');

	let rankedModels = [];
	let loaded = false;

	onMount(() => {
		loaded = true;

		rankedModels = $models
			.filter((m) => m?.owned_by !== 'arena' && (m?.info?.meta?.hidden ?? false) !== true)
			.map((model) => {
				return {
					...model,
					rating: '-',
					stats: {
						won: '-',
						draw: '-',
						lost: '-'
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
	});
</script>

{#if loaded}
	<div class="mt-0.5 mb-3 gap-1 flex flex-col md:flex-row justify-between">
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
		<table
			class="w-full text-sm text-left text-gray-500 dark:text-gray-400 table-auto max-w-full rounded"
		>
			<thead
				class="text-xs text-gray-700 uppercase bg-gray-50 dark:bg-gray-850 dark:text-gray-400 -translate-y-0.5"
			>
				<tr class="">
					<th scope="col" class="px-3 py-1.5 cursor-pointer select-none">
						{$i18n.t('Model')}
					</th>
					<th scope="col" class="px-3 py-1.5 text-right cursor-pointer select-none">
						{$i18n.t('Rating')}
					</th>
					<th scope="col" class="px-3 py-1.5 text-right cursor-pointer select-none w-fit">
						{$i18n.t('Won')}
					</th>

					<th scope="col" class="px-3 py-1.5 text-right cursor-pointer select-none w-fit">
						{$i18n.t('Draw')}
					</th>
					<th scope="col" class="px-3 py-1.5 text-right cursor-pointer select-none w-fit">
						{$i18n.t('Lost')}
					</th>
				</tr>
			</thead>
			<tbody class="">
				{#each rankedModels as model (model.id)}
					<tr class="bg-white dark:bg-gray-900 dark:border-gray-850 text-xs">
						<td class="px-3 py-1 flex flex-col justify-center">
							<div class="flex items-center gap-2">
								<div class="flex-shrink-0">
									<img
										src={model?.info?.meta?.profile_image_url ?? '/favicon.png'}
										alt={model.name}
										class="size-6 rounded-full object-cover shrink-0"
									/>
								</div>

								<div class="font-medium text-gray-600 dark:text-gray-400 pr-4">
									{model.name}
								</div>
							</div>
						</td>
						<td class="px-3 py-1 text-right font-medium text-gray-900 dark:text-white w-max">
							{model.rating}
						</td>

						<td class=" px-3 py-1 text-right font-semibold text-green-500"> {model.stats.won} </td>

						<td class=" px-3 py-1 text-right font-semibold">
							{model.stats.draw}
						</td>

						<td class="px-3 py-1 text-right font-semibold text-red-500">
							{model.stats.lost}
						</td>
					</tr>
				{/each}
			</tbody>
		</table>
	</div>

	<div class="pb-4"></div>

	<div class="mt-0.5 mb-3 gap-1 flex flex-col md:flex-row justify-between">
		<div class="flex md:self-center text-lg font-medium px-0.5">
			{$i18n.t('Rating History')}
		</div>
	</div>

	<div class="pb-8"></div>
{/if}
