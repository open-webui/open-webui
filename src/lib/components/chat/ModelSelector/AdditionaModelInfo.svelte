<script>
	import { modelsInfo } from '../../../../data/modelsInfo';
	import { getContext, onMount } from 'svelte';
	import SpeedRating from '../../chat/ModelSelector/SpeedRating.svelte';
	import StarRating from '../../chat/ModelSelector/IntelligenceRating.svelte';
    import InfoIcon from '$lib/components/icons/InfoIcon.svelte';

	const i18n = getContext('i18n');
	export let hoveredItem = null;

	let knowledgeCutoff = null;

	$: {
		if (modelsInfo?.[hoveredItem?.name]?.knowledge_cutoff) {
			const date = new Date(modelsInfo?.[hoveredItem?.name]?.knowledge_cutoff);

			const formatted = date.toLocaleString('default', {
				year: 'numeric',
				month: 'long'
			});
			knowledgeCutoff = formatted;
		}
	}
let tooltipEl;
let triggerEl;
let placeAbove = false;

function positionTooltip() {
	if (!tooltipEl || !triggerEl) return;

	const tooltipRect = tooltipEl.getBoundingClientRect();
	const triggerRect = triggerEl.getBoundingClientRect();

	const spaceBelow = window.innerHeight - triggerRect.bottom;
	const spaceAbove = triggerRect.top;

	placeAbove = spaceBelow < tooltipRect.height && spaceAbove > tooltipRect.height;
}

onMount(() => {
	window.addEventListener('resize', positionTooltip);
	window.addEventListener('scroll', positionTooltip, true);

	return () => {
		window.removeEventListener('resize', positionTooltip);
		window.removeEventListener('scroll', positionTooltip, true);
	};
});
</script>


<div bind:this={triggerEl}
on:mouseenter={positionTooltip} class="ml-1 cursor-pointer group relative flex justify-center items-center w-[18px] h-[18px] rounded-full text-white dark:text-white bg-customBlue-600 dark:bg-customGray-700">
    <InfoIcon className="size-6" />
<div
bind:this={tooltipEl}
class={`invisible group-hover:visible absolute px-3 py-1 left-full ml-2 w-52 p-2 rounded-xl border border-lightGray-400 dark:border-customGray-700 bg-lightGray-550 dark:bg-customGray-900 text-sm text-gray-800 dark:text-white z-50 shadow
	${placeAbove ? 'bottom-full mb-2' : 'top-0'}`}
>
	{#if modelsInfo?.[hoveredItem?.name]?.organization}
		<div class="py-1.5 border-b dark:border-customGray-700 last:border-b-0">
			<p class="text-xs dark:text-white">
				{modelsInfo?.[hoveredItem?.name]?.organization}
			</p>
			<p class="text-2xs dark:text-white/50">{$i18n.t('Organization')}</p>
		</div>
	{/if}
	{#if modelsInfo?.[hoveredItem?.name]?.hosted_in}
		<div class="py-1.5 border-b dark:border-customGray-700 last:border-b-0">
			<p class="text-xs dark:text-white">{modelsInfo?.[hoveredItem?.name]?.hosted_in}</p>
			<p class="text-2xs dark:text-white/50">{$i18n.t('Hosted In')}</p>
		</div>
	{/if}

	<div class="py-1.5 border-b dark:border-customGray-700 last:border-b-0">
		<p class="text-xs dark:text-white">
			{#if modelsInfo?.[hoveredItem?.name]?.context_window}
				{modelsInfo?.[hoveredItem?.name]?.context_window}
			{:else}
				N/A
			{/if}
		</p>
		<p class="text-2xs dark:text-white/50">{$i18n.t('Context Window')}</p>
	</div>

	<div class="py-1.5 border-b dark:border-customGray-700 last:border-b-0">
		<p class="text-xs dark:text-white">
			{#if knowledgeCutoff}
				{knowledgeCutoff}
			{:else}
				N/A
			{/if}
		</p>
		<p class="text-2xs dark:text-white/50">{$i18n.t('Knowledge Cutoff')}</p>
	</div>

	<div class="py-1.5 text-xs border-b dark:border-customGray-700 last:border-b-0">
		{#if modelsInfo?.[hoveredItem?.name]?.intelligence_score}
			<StarRating rating={modelsInfo?.[hoveredItem?.name]?.intelligence_score} />
		{:else}
			N/A
		{/if}
		<p class="text-2xs dark:text-white/50">{$i18n.t('Intelligence Score')}</p>
	</div>

	<div class="py-1.5 text-xs border-b dark:border-customGray-700 last:border-b-0">
		{#if modelsInfo?.[hoveredItem?.name]?.speed}
			<SpeedRating rating={modelsInfo?.[hoveredItem?.name]?.speed} />
		{:else}
			N/A
		{/if}
		<p class="text-2xs dark:text-white/50">{$i18n.t('Speed')}</p>
	</div>

	{#if modelsInfo?.[hoveredItem?.name]?.multimodal}
		<div class="py-2.5 border-b dark:border-customGray-700 last:border-b-0">
			<p class="text-xs dark:text-white">{$i18n.t('Multimodal')}</p>
		</div>
	{/if}
	{#if modelsInfo?.[hoveredItem?.name]?.reasoning}
		<div class="py-2.5 border-b dark:border-customGray-700 last:border-b-0">
			<p class="text-xs dark:text-white">{$i18n.t('Reasoning')}</p>
		</div>
	{/if}
</div>
</div>
