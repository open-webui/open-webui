<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { models } from '$lib/stores';
	import { getModelAnalytics } from '$lib/apis/analytics';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import ChevronUp from '$lib/components/icons/ChevronUp.svelte';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import { WEBUI_API_BASE_URL } from '$lib/constants';

	const i18n = getContext('i18n');

	let modelStats: Array<{ model_id: string; count: number; name?: string }> = [];
	let loading = true;
	let orderBy = 'count';
	let direction: 'asc' | 'desc' = 'desc';

	const toggleSort = (key: string) => {
		if (orderBy === key) {
			direction = direction === 'asc' ? 'desc' : 'asc';
		} else {
			orderBy = key;
			direction = key === 'name' ? 'asc' : 'desc';
		}
	};

	const loadAnalytics = async () => {
		loading = true;
		try {
			const result = await getModelAnalytics(localStorage.token);
			const modelsMap = new Map($models.map((m) => [m.id, m.name || m.id]));

			modelStats = (result?.models ?? []).map((entry) => ({
				...entry,
				name: modelsMap.get(entry.model_id) || entry.model_id
			}));
		} catch (err) {
			console.error('Analytics load failed:', err);
		}
		loading = false;
	};

	$: sortedModels = [...modelStats].sort((a, b) => {
		if (orderBy === 'name') {
			return direction === 'asc' ? a.name.localeCompare(b.name) : b.name.localeCompare(a.name);
		}
		return direction === 'asc' ? a.count - b.count : b.count - a.count;
	});

	$: totalMessages = modelStats.reduce((sum, m) => sum + m.count, 0);

	onMount(loadAnalytics);
</script>

<div
	class="pt-0.5 pb-1 gap-1 flex flex-col md:flex-row justify-between sticky top-0 z-10 bg-white dark:bg-gray-900"
>
	<div class="flex items-center text-xl font-medium px-0.5 gap-2 shrink-0">
		{$i18n.t('Model Usage')}
		<span class="text-lg text-gray-500">{totalMessages} {$i18n.t('messages')}</span>
	</div>
</div>

<div
	class="scrollbar-hidden relative whitespace-nowrap overflow-x-auto max-w-full rounded-sm min-h-[100px]"
>
	{#if loading}
		<div
			class="absolute inset-0 flex items-center justify-center z-10 bg-white/50 dark:bg-gray-900/50"
		>
			<Spinner className="size-5" />
		</div>
	{/if}

	{#if !modelStats.length && !loading}
		<div class="text-center text-xs text-gray-500 py-1">{$i18n.t('No data found')}</div>
	{:else if modelStats.length}
		<table
			class="w-full text-sm text-left text-gray-500 dark:text-gray-400 {loading
				? 'opacity-20'
				: ''}"
		>
			<thead class="text-xs text-gray-800 uppercase bg-transparent dark:text-gray-200">
				<tr class="border-b-[1.5px] border-gray-50 dark:border-gray-850/30">
					<th scope="col" class="px-2.5 py-2 w-8">#</th>
					<th
						scope="col"
						class="px-2.5 py-2 cursor-pointer select-none"
						on:click={() => toggleSort('name')}
					>
						<div class="flex gap-1.5 items-center">
							{$i18n.t('Model')}
							{#if orderBy === 'name'}
								{#if direction === 'asc'}<ChevronUp className="size-2" />{:else}<ChevronDown
										className="size-2"
									/>{/if}
							{:else}
								<span class="invisible"><ChevronUp className="size-2" /></span>
							{/if}
						</div>
					</th>
					<th
						scope="col"
						class="px-2.5 py-2 cursor-pointer select-none text-right"
						on:click={() => toggleSort('count')}
					>
						<div class="flex gap-1.5 items-center justify-end">
							{$i18n.t('Messages')}
							{#if orderBy === 'count'}
								{#if direction === 'asc'}<ChevronUp className="size-2" />{:else}<ChevronDown
										className="size-2"
									/>{/if}
							{:else}
								<span class="invisible"><ChevronUp className="size-2" /></span>
							{/if}
						</div>
					</th>
					<th scope="col" class="px-2.5 py-2 text-right w-24">{$i18n.t('Share')}</th>
				</tr>
			</thead>
			<tbody>
				{#each sortedModels as model, idx (model.model_id)}
					<tr
						class="bg-white dark:bg-gray-900 text-xs hover:bg-gray-50 dark:hover:bg-gray-850/50 transition"
					>
						<td class="px-3 py-1.5 font-medium text-gray-900 dark:text-white">
							{idx + 1}
						</td>
						<td class="px-3 py-1.5">
							<div class="flex items-center gap-2">
								<img
									src="{WEBUI_API_BASE_URL}/models/model/profile/image?id={model.model_id}"
									alt={model.name}
									class="size-5 rounded-full object-cover"
								/>
								<span class="font-medium text-gray-800 dark:text-gray-200">{model.name}</span>
							</div>
						</td>
						<td class="px-3 py-1.5 text-right font-medium text-gray-900 dark:text-white">
							{model.count.toLocaleString()}
						</td>
						<td class="px-3 py-1.5 text-right font-medium text-blue-500">
							{((model.count / totalMessages) * 100).toFixed(1)}%
						</td>
					</tr>
				{/each}
			</tbody>
		</table>
	{/if}
</div>

<div class="text-gray-500 text-xs mt-1.5 w-full flex justify-end">
	<div class="text-right">
		ⓘ {$i18n.t('Message counts are based on assistant responses.')}
	</div>
</div>
