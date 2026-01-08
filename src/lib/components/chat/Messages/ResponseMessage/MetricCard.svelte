<script>
  import { createEventDispatcher } from 'svelte';
  import { extractMetricValue } from '$lib/utils/metric';

  export let title = 'DOWN & INVERTED';
  export let value = '35';
  export let timeframe = 'Past 24 hrs';
  export let width = '180px';
  export let message;

  const dispatch = createEventDispatcher();
  const onClose = () => dispatch('close');

  $: metricValue = extractMetricValue(message?.content ?? '');
  $: displayValue = metricValue || value;
</script>

<div class="rounded-xl border-2 p-2 shadow-lg bg-white dark:bg-gray-900" style="width: {width}; border-color: rgba(23,206,211,0.5);">
  <div class="flex items-start justify-between mb-1">
    <div class="text-[11px] font-semibold text-gray-500 uppercase tracking-wide">{title}</div>
    <button
      aria-label="close"
      on:click={onClose}
      class="text-gray-400 hover:text-gray-600 text-sm leading-none"
    >✕</button>
  </div>

  <div class="flex items-center">
    <div class="flex-1 min-w-0">
      <div class="text-4xl font-medium text-gray-900 dark:text-gray-100 leading-none">{displayValue}</div>
      {#if timeframe}
        <div class="text-[13px] text-gray-900 font-medium mt-1">{timeframe}</div>
      {/if}
    </div>
  </div>
</div>
