<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { models } from '$lib/stores';

	import ModelModal from './LeaderboardModal.svelte';

	import Spinner from '$lib/components/common/Spinner.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Search from '$lib/components/icons/Search.svelte';
	import ChevronUp from '$lib/components/icons/ChevronUp.svelte';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';

	import { get } from 'svelte/store';
	import { getLeaderboard } from '$lib/apis/evaluations';

	const i18n = getContext('i18n');

	export let feedbacks = [];

	let rankedModels = [];
	let query = '';
	let loadingLeaderboard = true;
	let debounceTimer;

	let orderBy: string = 'rating'; // default sort column
	let direction: 'asc' | 'desc' = 'desc'; // default sort order

	//////////////////////
	//
	// Aggregate Level Modal
	//
	//////////////////////

	let showLeaderboardModal = false;
	let selectedModel = null;

	const openFeedbackModal = (model) => {
		showLeaderboardModal = true;
		const fullModel = get(models).find((m) => m.id === model.id);
		selectedModel = fullModel ?? model;
	};

	const closeLeaderboardModal = () => {
		showLeaderboardModal = false;
		selectedModel = null;
	};

	//////////////////////
	//
	// Leaderboard fetch and Sort
	//
	//////////////////////

	const setSortKey = (key) => {
		if (orderBy === key) {
			direction = direction === 'asc' ? 'desc' : 'asc';
		} else {
			orderBy = key;
			direction = key === 'name' ? 'asc' : 'desc';
		}
	};

	const fetchLeaderboard = async (query: string) => {
		loadingLeaderboard = true;
		const data = await getLeaderboard(query, localStorage.token ?? '', get(models));
		rankedModels = data?.leaderboard ?? [];
		loadingLeaderboard = false;
	};

	const debouncedQueryHandler = () => {
		clearTimeout(debounceTimer);
		debounceTimer = setTimeout(() => {
			fetchLeaderboard(query);
		}, 500);
	};

	$: query, debouncedQueryHandler();

	onMount(() => {
		fetchLeaderboard('');
	});

	$: sortedModels = [...rankedModels].sort((a, b) => {
		let aVal, bVal;
		if (orderBy === 'name') {
			aVal = a.name;
			bVal = b.name;
			return direction === 'asc' ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
		} else if (orderBy === 'rating') {
			aVal = a.rating === '-' ? -Infinity : a.rating;
			bVal = b.rating === '-' ? -Infinity : b.rating;
			return direction === 'asc' ? aVal - bVal : bVal - aVal;
		} else if (orderBy === 'won') {
			aVal = a.stats.won === '-' ? -Infinity : Number(a.stats.won);
			bVal = b.stats.won === '-' ? -Infinity : Number(b.stats.won);
			return direction === 'asc' ? aVal - bVal : bVal - aVal;
		} else if (orderBy === 'lost') {
			aVal = a.stats.lost === '-' ? -Infinity : Number(a.stats.lost);
			bVal = b.stats.lost === '-' ? -Infinity : Number(b.stats.lost);
			return direction === 'asc' ? aVal - bVal : bVal - aVal;
		}
		return 0;
	});
</script>

<ModelModal
	bind:show={showLeaderboardModal}
	model={selectedModel}
	{feedbacks}
	onClose={closeLeaderboardModal}
/>

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
					<Search className="size-3" />
				</div>
				<input
					class=" w-full text-sm pr-4 py-1 rounded-r-xl outline-hidden bg-transparent"
					bind:value={query}
					placeholder={$i18n.t('Search')}
				/>
			</div>
		</Tooltip>
	</div>
</div>

<div
	class="scrollbar-hidden relative whitespace-nowrap overflow-x-auto max-w-full rounded-sm pt-0.5"
>
	{#if loadingLeaderboard}
		<div class=" absolute top-0 bottom-0 left-0 right-0 flex">
			<div class="m-auto">
				<Spinner className="size-5" />
			</div>
		</div>
	{/if}
	{#if (rankedModels ?? []).length === 0}
		<div class="text-center text-xs text-gray-500 dark:text-gray-400 py-1">
			{$i18n.t('No models found')}
		</div>
	{:else}
		<table
			class="w-full text-sm text-left text-gray-500 dark:text-gray-400 table-auto max-w-full rounded {loadingLeaderboard
				? 'opacity-20'
				: ''}"
		>
			<thead
				class="text-xs text-gray-700 uppercase bg-gray-50 dark:bg-gray-850 dark:text-gray-400 -translate-y-0.5"
			>
				<tr class="">
					<th
						scope="col"
						class="px-3 py-1.5 cursor-pointer select-none w-3"
						on:click={() => setSortKey('rating')}
					>
						<div class="flex gap-1.5 items-center">
							{$i18n.t('RK')}
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
						class="px-3 py-1.5 cursor-pointer select-none"
						on:click={() => setSortKey('name')}
					>
						<div class="flex gap-1.5 items-center">
							{$i18n.t('Model')}
							{#if orderBy === 'name'}
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
							{$i18n.t('Rating')}
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
						class="px-3 py-1.5 text-right cursor-pointer select-none w-5"
						on:click={() => setSortKey('won')}
					>
						<div class="flex gap-1.5 items-center justify-end">
							{$i18n.t('Won')}
							{#if orderBy === 'won'}
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
						class="px-3 py-1.5 text-right cursor-pointer select-none w-5"
						on:click={() => setSortKey('lost')}
					>
						<div class="flex gap-1.5 items-center justify-end">
							{$i18n.t('Lost')}
							{#if orderBy === 'lost'}
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
				</tr>
			</thead>
			<tbody class="">
				{#each sortedModels as model, modelIdx (model.id)}
					<tr
						class="bg-white dark:bg-gray-900 dark:border-gray-850 text-xs group cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-850/50 transition"
						on:click={() => openFeedbackModal(model)}
					>
						<td class="px-3 py-1.5 text-left font-medium text-gray-900 dark:text-white w-fit">
							<div class=" line-clamp-1">
								{model?.rating !== '-' ? modelIdx + 1 : '-'}
							</div>
						</td>
						<td class="px-3 py-1.5 flex flex-col justify-center">
							<div class="flex items-center gap-2">
								<div class="shrink-0">
									<img
										src={model?.profile_image_url ?? '/favicon.png'}
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
