<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import type { Theme } from '$lib/types';

  export let gradient: Theme['gradient'] | undefined = {
    colors: ['#ff0000', '#0000ff'],
    direction: 90,
    intensity: 100,
  };

  const dispatch = createEventDispatcher();

  let colors = gradient?.colors ?? ['#ff0000', '#0000ff'];
  let direction = gradient?.direction ?? 90;
  let intensity = gradient?.intensity ?? 100;

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

  const handleColorChange = (index: number, event: Event) => {
    const target = event.target as HTMLInputElement;
    colors[index] = target.value;
    colors = [...colors]; // Trigger reactivity
  };
</script>

<div class="space-y-4 p-4 bg-gray-800 text-white rounded-lg">
  <div>
    <h3 class="text-lg font-medium mb-2">Colors</h3>
    <div class="flex items-center space-x-2 p-2 bg-gray-900 rounded-lg">
      {#each colors as color, i}
        <div class="relative group">
          <input type="color" value={color} on:input={(e) => handleColorChange(i, e)} class="w-12 h-12 p-1 border-2 border-transparent rounded-md appearance-none bg-transparent cursor-pointer" style="background-color: {color};" />
          <button on:click={() => removeColor(i)} class="absolute top-0 right-0 -mt-1 -mr-1 w-5 h-5 bg-red-500 text-white rounded-full flex items-center justify-center text-xs opacity-0 group-hover:opacity-100 transition-opacity">
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
