<script lang="ts">
	import { getContext } from 'svelte';
	import { getModelEndpoints } from '$lib/apis/openai';
	import Switch from '$lib/components/common/Switch.svelte';

	const i18n = getContext('i18n');

	export let baseModelId = '';
	export let providerOnly: string[] = [];
	export let providerOrder: string[] = [];

	let endpoints: any[] = [];
	let loading = false;
	let enabled = false;

	$: enabled = providerOnly.length > 0;

	const fetchEndpoints = async (modelId: string) => {
		if (!modelId) {
			endpoints = [];
			return;
		}
		loading = true;
		try {
			console.log('OpenRouterProviderSelector: fetching endpoints for', modelId);
			const res = await getModelEndpoints(localStorage.token, modelId);
			console.log('OpenRouterProviderSelector: got response', res);
			endpoints = res?.data?.endpoints ?? [];
		} catch (e) {
			console.error('Failed to fetch endpoints:', e);
			endpoints = [];
		} finally {
			loading = false;
		}
	};

	$: fetchEndpoints(baseModelId);

	const handleToggle = () => {
		if (!enabled) {
			providerOnly = [];
			providerOrder = [];
		}
	};

	const toggleProvider = (tag: string) => {
		if (providerOnly.includes(tag)) {
			providerOnly = providerOnly.filter((t) => t !== tag);
			providerOrder = providerOrder.filter((t) => t !== tag);
		} else {
			providerOnly = [...providerOnly, tag];
			providerOrder = [...providerOrder, tag];
		}
	};

	const moveUp = (idx: number) => {
		if (idx <= 0) return;
		const newOrder = [...providerOrder];
		[newOrder[idx - 1], newOrder[idx]] = [newOrder[idx], newOrder[idx - 1]];
		providerOrder = newOrder;
	};

	const moveDown = (idx: number) => {
		if (idx >= providerOrder.length - 1) return;
		const newOrder = [...providerOrder];
		[newOrder[idx], newOrder[idx + 1]] = [newOrder[idx + 1], newOrder[idx]];
		providerOrder = newOrder;
	};

	const formatPrice = (priceStr: string) => {
		const price = parseFloat(priceStr);
		if (isNaN(price)) return '-';
		const perMillion = price * 1_000_000;
		if (perMillion < 0.01) return '<$0.01';
		return `$${perMillion.toFixed(2)}`;
	};

	const getEndpointByTag = (tag: string) => {
		return endpoints.find((e) => e.tag === tag);
	};
</script>

{#if true}
	<div class="my-2">
		<div class="px-4 py-3 bg-gray-50 dark:bg-gray-950 rounded-3xl">
			<div class="flex w-full justify-between items-center">
				<div class="self-center text-sm font-semibold">{$i18n.t('Provider Routing')}</div>
				<div class="flex items-center gap-2">
					{#if loading}
						<span class="text-xs text-gray-400">{$i18n.t('Loading...')}</span>
					{/if}
					{#if endpoints.length > 0}
						<Switch bind:state={enabled} on:change={handleToggle} />
					{/if}
				</div>
			</div>
			<div class="mt-1 text-xs text-gray-500 dark:text-gray-500 mb-3">
				{$i18n.t('Select and order which OpenRouter providers handle requests for this model.')}
			</div>

			{#if !loading && endpoints.length === 0}
				<div class="text-xs text-gray-400 dark:text-gray-500 italic">
					{baseModelId ? 'No providers found for this model (may not be an OpenRouter model).' : 'No base model selected.'}
				</div>
			{:else if endpoints.length > 0}
				<div class="overflow-x-auto">
					<table class="w-full text-xs">
						<thead>
							<tr class="text-left text-gray-500 dark:text-gray-400 border-b border-gray-200 dark:border-gray-800">
								<th class="pb-1.5 pr-2 w-6"></th>
								<th class="pb-1.5 pr-3">{$i18n.t('Provider')}</th>
								<th class="pb-1.5 pr-3 text-right">{$i18n.t('Prompt')}</th>
								<th class="pb-1.5 pr-3 text-right">{$i18n.t('Completion')}</th>
								<th class="pb-1.5 pr-3 text-right">{$i18n.t('Throughput')}</th>
								<th class="pb-1.5 pr-3 text-right">{$i18n.t('Latency')}</th>
								<th class="pb-1.5 text-right">{$i18n.t('Uptime')}</th>
							</tr>
						</thead>
						<tbody>
							{#each endpoints as endpoint}
								<tr
									class="border-b border-gray-100 dark:border-gray-800/50 hover:bg-gray-100 dark:hover:bg-gray-900 transition cursor-pointer"
									on:click={() => toggleProvider(endpoint.tag)}
								>
									<td class="py-1.5 pr-2">
										<input
											type="checkbox"
											checked={providerOnly.includes(endpoint.tag)}
											on:click|stopPropagation={() => toggleProvider(endpoint.tag)}
											class="cursor-pointer"
										/>
									</td>
									<td class="py-1.5 pr-3 font-medium text-gray-700 dark:text-gray-300 whitespace-nowrap">
										{endpoint.provider_name}
									</td>
									<td class="py-1.5 pr-3 text-right text-gray-500 dark:text-gray-400 whitespace-nowrap">
										{formatPrice(endpoint.pricing?.prompt ?? '0')}/M
									</td>
									<td class="py-1.5 pr-3 text-right text-gray-500 dark:text-gray-400 whitespace-nowrap">
										{formatPrice(endpoint.pricing?.completion ?? '0')}/M
									</td>
									<td class="py-1.5 pr-3 text-right text-gray-500 dark:text-gray-400 whitespace-nowrap">
										{endpoint.throughput_last_30m?.p50 ?? '-'} tok/s
									</td>
									<td class="py-1.5 pr-3 text-right text-gray-500 dark:text-gray-400 whitespace-nowrap">
										{endpoint.latency_last_30m?.p50
											? `${(endpoint.latency_last_30m.p50 / 1000).toFixed(1)}s`
											: '-'}
									</td>
									<td class="py-1.5 text-right whitespace-nowrap">
										<span
											class={endpoint.uptime_last_30m >= 99
												? 'text-green-600 dark:text-green-400'
												: endpoint.uptime_last_30m >= 95
													? 'text-yellow-600 dark:text-yellow-400'
													: 'text-red-600 dark:text-red-400'}
										>
											{endpoint.uptime_last_30m?.toFixed(1) ?? '-'}%
										</span>
									</td>
								</tr>
							{/each}
						</tbody>
					</table>
				</div>

				{#if providerOrder.length > 0}
					<div class="mt-3 pt-3 border-t border-gray-200 dark:border-gray-800">
						<div class="text-xs font-semibold text-gray-600 dark:text-gray-400 mb-2">
							{$i18n.t('Provider Order')}
						</div>
						<div class="flex flex-col gap-1">
							{#each providerOrder as tag, idx}
								{@const endpoint = getEndpointByTag(tag)}
								<div
									class="flex items-center justify-between px-2.5 py-1.5 bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800"
								>
									<div class="flex items-center gap-2">
										<span class="text-xs text-gray-400 w-4 text-center">{idx + 1}</span>
										<span class="text-xs font-medium text-gray-700 dark:text-gray-300">
											{endpoint?.provider_name ?? tag}
										</span>
									</div>
									<div class="flex items-center gap-0.5">
										<button
											type="button"
											class="p-0.5 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 disabled:opacity-30 transition"
											disabled={idx === 0}
											on:click={() => moveUp(idx)}
										>
											<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" class="size-3.5">
												<path fill-rule="evenodd" d="M8 14a.75.75 0 0 1-.75-.75V4.56L4.03 7.78a.75.75 0 0 1-1.06-1.06l4.5-4.5a.75.75 0 0 1 1.06 0l4.5 4.5a.75.75 0 0 1-1.06 1.06L8.75 4.56v8.69A.75.75 0 0 1 8 14Z" clip-rule="evenodd" />
											</svg>
										</button>
										<button
											type="button"
											class="p-0.5 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 disabled:opacity-30 transition"
											disabled={idx === providerOrder.length - 1}
											on:click={() => moveDown(idx)}
										>
											<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" class="size-3.5">
												<path fill-rule="evenodd" d="M8 2a.75.75 0 0 1 .75.75v8.69l3.22-3.22a.75.75 0 1 1 1.06 1.06l-4.5 4.5a.75.75 0 0 1-1.06 0l-4.5-4.5a.75.75 0 0 1 1.06-1.06l3.22 3.22V2.75A.75.75 0 0 1 8 2Z" clip-rule="evenodd" />
											</svg>
										</button>
									</div>
								</div>
							{/each}
						</div>
					</div>
				{/if}
			{/if}
		</div>
	</div>
{/if}
