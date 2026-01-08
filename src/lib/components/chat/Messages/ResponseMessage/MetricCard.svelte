<script>
  import { createEventDispatcher } from 'svelte';

  export let title;
  export let metricValue;
  export let timeframe;

  const dispatch = createEventDispatcher();
  const onClose = () => dispatch('close');
</script>

<div class="rounded-xl border-2 p-2 shadow-lg bg-white dark:bg-gray-900" style="width: 180px; border-color: rgba(23,206,211,0.5);">
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
      <div class="text-4xl font-medium text-gray-900 dark:text-gray-100 leading-none">{metricValue}</div>
      {#if timeframe}
        <div class="text-[13px] text-gray-900 font-medium mt-1">{timeframe}</div>
      {/if}
    </div>
  </div>
</div>
