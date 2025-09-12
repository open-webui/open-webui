<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import type { Theme } from '$lib/types';
  import ColorPicker from 'svelte-awesome-color-picker';

  export let gradient: Theme['gradient'] | undefined = {
    colors: ['#ff0000', '#0000ff'],
    direction: 90,
    intensity: 100,
  };

  const dispatch = createEventDispatcher();

  let colors = gradient?.colors ?? ['#ff0000', '#0000ff'];
  let direction = gradient?.direction ?? 90;
  let intensity = gradient?.intensity ?? 100;
  let selectedColorIndex = 0;

  $: {
    // Reactive statement to dispatch updates when any value changes
    dispatch('update', {
      colors,
      direction,
      intensity,
    });
  }

  const addColor = () => {
    if (colors.length < 5) {
      colors = [...colors, '#ffffff'];
    }
  };

  const removeColor = (index: number) => {
    colors = colors.filter((_, i) => i !== index);
  };
</script>

<div class="space-y-4 p-4 bg-gray-800 text-white rounded-lg">
  <div>
    <h3 class="text-lg font-medium mb-2">Colors</h3>
    <div class="flex items-center space-x-2 p-2 bg-gray-900 rounded-lg">
      {#each colors as color, i}
        <div
          class="relative group border-2 rounded-md p-1 cursor-pointer"
          class:border-blue-500={selectedColorIndex === i}
          class:border-transparent={selectedColorIndex !== i}
          on:click={() => selectedColorIndex = i}
        >
          <div class="w-10 h-10 rounded-sm" style="background-color: {color};"></div>
          <button on:click|stopPropagation={() => removeColor(i)} class="absolute top-0 right-0 -mt-2 -mr-2 w-5 h-5 bg-red-500 text-white rounded-full flex items-center justify-center text-xs opacity-0 group-hover:opacity-100 transition-opacity">
            &times;
          </button>
        </div>
      {/each}
      {#if colors.length < 5}
        <button on:click={addColor} class="w-12 h-12 border-2 border-dashed border-gray-600 rounded-md flex items-center justify-center text-gray-400 hover:text-gray-300 hover:border-gray-500 transition-colors">
          +
        </button>
      {/if}
    </div>
    <div class="mt-4 p-2 bg-gray-900 rounded-lg color-picker-wrapper">
      <ColorPicker bind:hex={colors[selectedColorIndex]} isDialog={false} />
    </div>
  </div>

  <div>
    <h3 class="text-lg font-medium mb-2">Controls</h3>
    <div class="space-y-4 p-4 bg-gray-900 rounded-lg">
      <div class="flex items-center justify-between">
        <label for="direction" class="font-medium">Gradient Direction</label>
        <span class="text-gray-400">{direction}°</span>
      </div>
      <input type="range" id="direction" min="0" max="360" bind:value={direction} class="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer" />

      <div class="flex items-center justify-between">
        <label for="intensity" class="font-medium">Color Intensity</label>
        <span class="text-gray-400">{intensity}%</span>
      </div>
      <input type="range" id="intensity" min="0" max="100" bind:value={intensity} class="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer" />
    </div>
  </div>
</div>

<style>
	:global(.dark .color-picker-wrapper) {
		--cp-bg-color: #2d2d2d;
		--cp-border-color: #4a4a4a;
		--cp-text-color: #f0f0f0;
		--cp-input-color: #3a3a3a;
		--cp-button-hover-color: #5a5a5a;
	}
</style>
