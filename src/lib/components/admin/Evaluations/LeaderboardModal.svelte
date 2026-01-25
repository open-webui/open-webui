<script lang="ts">
	import Modal from '$lib/components/common/Modal.svelte';
	import { getContext } from 'svelte';
	import { getModelHistory } from '$lib/apis/evaluations';
	import ModelActivityChart from './ModelActivityChart.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';

	export let show = false;
	export let model = null;
	export let onClose: () => void = () => {};

	const i18n = getContext('i18n');

	type TimeRange = '30d' | '1y' | 'all';
	const TIME_RANGES: { key: TimeRange; label: string; days: number }[] = [
		{ key: '30d', label: '30D', days: 30 },
		{ key: '1y', label: '1Y', days: 365 },
		{ key: 'all', label: 'All', days: 0 } // 0 = all time, starts from first feedback
	];

	let selectedRange: TimeRange = '30d';
	let history: Array<{ date: string; won: number; lost: number }> = [];
	let loadingHistory = false;

	const close = () => {
		show = false;
		onClose();
	};

	const loadHistory = async (days: number) => {
		if (!model?.id) return;
		loadingHistory = true;
		try {
			const result = await getModelHistory(localStorage.token, model.id, days);
			history = result?.history ?? [];
		} catch (err) {
			console.error('Failed to load model history:', err);
			history = [];
		}
		loadingHistory = false;
	};

	const selectRange = (range: TimeRange) => {
		selectedRange = range;
		const config = TIME_RANGES.find((r) => r.key === range);
		if (config) {
			loadHistory(config.days);
		}
	};

	// Load history when model changes and modal is shown
	$: if (show && model?.id) {
		selectRange(selectedRange);
	}

	// Use top_tags from backend response (already computed)
	$: topTags = model?.top_tags ?? [];
</script>

<Modal size="md" bind:show>
	{#if model}
		<div class="flex justify-between dark:text-gray-300 px-5 pt-4 pb-2">
			<div class="text-lg font-medium self-center">
				{model.name}
			</div>
			<button class="self-center" on:click={close} aria-label="Close">
				<XMark className={'size-5'} />
			</button>
		</div>
		<div class="px-5 pb-4 dark:text-gray-200">
			<!-- Activity Chart -->
			<div class="mb-4">
				<div class="flex items-center justify-between mb-2">
					<div class="text-xs text-gray-500 font-medium uppercase tracking-wide">
						{$i18n.t('Activity')}
					</div>
					<div
						class="inline-flex rounded-full bg-gray-100/80 p-0.5 dark:bg-gray-800/80 backdrop-blur-sm"
					>
						{#each TIME_RANGES as range}
							<button
								type="button"
								class="rounded-full transition-all duration-200 px-2.5 py-0.5 text-xs font-medium {selectedRange ===
								range.key
									? 'bg-white text-gray-900 shadow-sm dark:bg-gray-700 dark:text-white'
									: 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'}"
								on:click={() => selectRange(range.key)}
							>
								{range.label}
							</button>
						{/each}
					</div>
				</div>
				<ModelActivityChart
					{history}
					loading={loadingHistory}
					aggregateWeekly={selectedRange === '1y' || selectedRange === 'all'}
				/>
			</div>

			<div class="mb-4">
				<div class="text-xs text-gray-500 mb-2 font-medium uppercase tracking-wide">
					{$i18n.t('Tags')}
				</div>
				{#if topTags.length}
					<div class="flex flex-wrap gap-1 -mx-1">
						{#each topTags as tagInfo}
							<span class="px-2 py-0.5 rounded-full bg-gray-100 dark:bg-gray-850 text-xs">
								{tagInfo.tag} <span class="text-gray-500 font-medium">{tagInfo.count}</span>
							</span>
						{/each}
					</div>
				{:else}
					<span class="text-gray-500 text-sm">-</span>
				{/if}
			</div>

			<div class="flex justify-end pt-2">
				<button
					class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full"
					type="button"
					on:click={close}
				>
					{$i18n.t('Close')}
				</button>
			</div>
		</div>
	{/if}
</Modal>
