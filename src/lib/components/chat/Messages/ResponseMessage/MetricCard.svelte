<script>
  import { createEventDispatcher, onDestroy, onMount, tick } from 'svelte';

  export let title;
  export let metricValue;
  export let timeframe;

  const dispatch = createEventDispatcher();
  const onClose = () => dispatch('close');

  let titleEl;
  let valueEl;
  let titleIsWrapped = false;
  let valueIsWrapped = false;
  let resizeObserver;
  let valueFontSize = '';

  const measureWrap = (element, baseClass, smallClass) => {
    if (!element) {
      return false;
    }
    let appliedBaseClass = false;
    let removedSmallClass = false;
    if (baseClass) {
      appliedBaseClass = !element.classList.contains(baseClass);
      if (appliedBaseClass) element.classList.add(baseClass);
    }
    if (smallClass) {
      removedSmallClass = element.classList.contains(smallClass);
      if (removedSmallClass) element.classList.remove(smallClass);
    }
    const previousWhiteSpace = element.style.whiteSpace;
    element.style.whiteSpace = 'nowrap';
    const wouldOverflow = element.scrollWidth > element.clientWidth + 1;
    element.style.whiteSpace = previousWhiteSpace;
    if (appliedBaseClass) element.classList.remove(baseClass);
    if (removedSmallClass) element.classList.add(smallClass);
    if (wouldOverflow) {
      return true;
    }
    const rects = element.getClientRects();
    if (rects && rects.length > 0) {
      return rects.length > 1;
    }
    const styles = getComputedStyle(element);
    const fontSize = parseFloat(styles.fontSize) || 0;
    const lineHeightRaw = parseFloat(styles.lineHeight);
    const lineHeight = lineHeightRaw || fontSize * 1.2;
    return element.clientHeight > lineHeight * 1.1;
  };

  const fitsInOneLine = (element) => {
    if (!element) {
      return true;
    }
    const previousWhiteSpace = element.style.whiteSpace;
    element.style.whiteSpace = 'nowrap';
    const fits = element.scrollWidth <= element.clientWidth + 1;
    element.style.whiteSpace = previousWhiteSpace;
    return fits;
  };

  const updateValueFontSize = () => {
    if (!valueEl) {
      return;
    }
    const styles = getComputedStyle(valueEl);
    const baseFontSize = parseFloat(styles.fontSize) || 0;
    if (!baseFontSize) {
      return;
    }
    const minFontSize = 16;
    let size = baseFontSize;
    valueEl.style.fontSize = `${size}px`;
    let guard = 0;
    while (!fitsInOneLine(valueEl) && size > minFontSize && guard < 12) {
      size = Math.max(minFontSize, Math.floor(size * 0.9));
      valueEl.style.fontSize = `${size}px`;
      guard += 1;
    }
    valueFontSize = `${size}px`;
  };

  const updateWraps = () => {
    titleIsWrapped = measureWrap(titleEl, 'text-[11px]', 'text-[9px]');
    valueIsWrapped = !fitsInOneLine(valueEl);
    updateValueFontSize();
  };

  onMount(async () => {
    await tick();
    updateWraps();
    if (typeof ResizeObserver !== 'undefined') {
      resizeObserver = new ResizeObserver(() => updateWraps());
      if (titleEl) {
        resizeObserver.observe(titleEl);
      }
      if (valueEl) {
        resizeObserver.observe(valueEl);
      }
    }
  });

  onDestroy(() => {
    if (resizeObserver) {
      resizeObserver.disconnect();
    }
  });

  $: title, tick().then(updateWraps);
  $: metricValue, tick().then(updateWraps);
</script>

<div class="rounded-xl border-2 p-2 shadow-lg bg-white dark:bg-gray-900" style="width: 180px; border-color: rgba(23,206,211,0.5);">
  <div class="flex items-start justify-between mb-1">
    <div
      bind:this={titleEl}
      class="font-semibold text-gray-500 uppercase tracking-wide {titleIsWrapped ? 'text-[9px] leading-tight' : 'text-[11px]'}"
    >{title}</div>
    <button
      aria-label="close"
      on:click={onClose}
      class="text-gray-400 hover:text-gray-600 text-sm leading-none"
    >✕</button>
  </div>

  <div class="flex items-center">
    <div class="flex-1 min-w-0">
      <div
        bind:this={valueEl}
        class="block w-full whitespace-normal break-words font-medium text-gray-900 dark:text-gray-100 leading-none text-4xl"
        style="font-size: {valueFontSize};"
      >{metricValue}</div>
      {#if timeframe}
        <div class="text-[13px] text-gray-900 font-medium mt-1">{timeframe}</div>
      {/if}
    </div>
  </div>
</div>
