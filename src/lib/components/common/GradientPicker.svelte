<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import type { Theme } from '$lib/types';
  import ColorPicker from 'svelte-awesome-color-picker';
  import { Vibrant } from 'node-vibrant/browser';
  import { toast } from 'svelte-sonner';

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
    if (colors.length < 6) { 
      colors = [...colors, '#ffffff'];
    }
  };

  const removeColor = (index: number) => {
    colors = colors.filter((_, i) => i !== index);
  };
  
  const generateRandomGradient = () => {
    const numColors = Math.floor(Math.random() * 5) + 2; // 2 to 6 colors
    const newColors = [];
    for (let i = 0; i < numColors; i++) {
      newColors.push('#' + Math.floor(Math.random()*16777215).toString(16));
    }
    colors = newColors;
    toast.success(`Generated a random ${numColors}-color gradient.`);
  };

  const generateGradientFromImage = async (event) => {
    const file = event.target.files[0];
    if (!file) {
      return;
    }

    const imageUrl = URL.createObjectURL(file);

    Vibrant.from(imageUrl)
      .getPalette()
      .then((palette) => {
        const newColors = [];
        if (palette.Vibrant) newColors.push(palette.Vibrant.hex);
        if (palette.Muted) newColors.push(palette.Muted.hex);
        if (palette.DarkVibrant) newColors.push(palette.DarkVibrant.hex);
        if (palette.DarkMuted) newColors.push(palette.DarkMuted.hex);
        if (palette.LightVibrant) newColors.push(palette.LightVibrant.hex);
        if (palette.LightMuted) newColors.push(palette.LightMuted.hex);
        
        if (newColors.length > 0) {
          colors = newColors.slice(0, 6); // Limit to 6 colors
          toast.success(`Generated a ${colors.length}-color gradient from ${file.name}.`);
        } else {
          toast.error('Could not extract a palette from the image.');
        }

        URL.revokeObjectURL(imageUrl);
      });
  };

</script>

<div class="space-y-4">
  <div>
    <h3 class="text-lg font-medium mb-2">Colors</h3>
    <div class="flex items-center justify-center space-x-2">
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
      {#if colors.length < 6}
        <button on:click={addColor} class="w-12 h-12 border-2 border-dashed border-gray-400 dark:border-gray-600 rounded-md flex items-center justify-center text-gray-500 dark:text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:border-gray-500 dark:hover:border-gray-500 transition-colors">
          +
        </button>
      {/if}
    </div>
    <div class="mt-4 color-picker-wrapper flex justify-center">
      <ColorPicker bind:hex={colors[selectedColorIndex]} isDialog={false} />
    </div>
  </div>

  <div>
    <h3 class="text-lg font-medium mb-2">Controls</h3>
    <div class="space-y-4">
      <div class="flex items-center justify-between">
        <label for="direction" class="font-medium">Gradient Direction</label>
        <span class="text-gray-500 dark:text-gray-400">{direction}°</span>
      </div>
      <input type="range" id="direction" min="0" max="360" bind:value={direction} class="w-full" />

      <div class="flex items-center justify-between">
        <label for="intensity" class="font-medium">Color Intensity</label>
        <span class="text-gray-500 dark:text-gray-400">{intensity}%</span>
      </div>
      <input type="range" id="intensity" min="0" max="100" bind:value={intensity} class="w-full" />
    
      <div class="flex justify-end mt-2 space-x-2">
        <button
          class="px-3.5 py-1.5 text-sm font-medium bg-gray-300 dark:bg-gray-800 hover:bg-gray-400 dark:hover:bg-gray-700 transition rounded-full"
          on:click={generateRandomGradient}
        >
          Random
        </button>
        <input
          id="image-import-input-gradient"
          type="file"
          accept="image/*"
          class="hidden"
          on:change={generateGradientFromImage}
        />
        <button
          class="px-3.5 py-1.5 text-sm font-medium bg-gray-300 dark:bg-gray-800 hover:bg-gray-400 dark:hover:bg-gray-700 transition rounded-full"
          on:click={() => document.getElementById('image-import-input-gradient')?.click()}
        >
          Generate from Image
        </button>
      </div>
    </div>
  </div>
</div>

<style>
	:global(.dark .color-picker-wrapper) {
		--cp-bg-color: transparent;
		--cp-border-color: #374151; /* bg-gray-700 */
		--cp-text-color: #f9fafb; /* text-gray-50 */
		--cp-input-color: #374151; /* bg-gray-700 */
		--cp-button-hover-color: #4b5563; /* bg-gray-600 */
	}
    :global(.color-picker-wrapper) {
		--cp-bg-color: transparent;
		--cp-border-color: #d1d5db; /* bg-gray-300 */
		--cp-text-color: #111827; /* text-gray-900 */
		--cp-input-color: #e5e7eb; /* bg-gray-200 */
		--cp-button-hover-color: #d1d5db; /* bg-gray-300 */
	}
</style>
