<script lang="ts">
  import { createEventDispatcher, getContext } from 'svelte';
  import type { Theme } from '$lib/types';
  import Switch from '$lib/components/common/Switch.svelte';
  import Tooltip from '$lib/components/common/Tooltip.svelte';
  import CodeBlock from '$lib/components/chat/Messages/CodeBlock.svelte';
  import { objectToCss, cssToObject } from '$lib/utils/theme';
  import { toast } from 'svelte-sonner';
  import { Vibrant } from 'node-vibrant/browser';

  export let themeCopy: Theme;
  export let variablesText: string;
  export let cssText: string;

  let imageImportInput: HTMLInputElement;

  const dispatch = createEventDispatcher();
  const i18n = getContext('i18n');

  const handleVariablesInput = (e) => {
    variablesText = e.detail;
    themeCopy.variables = cssToObject(variablesText);
    dispatch('update', { ...themeCopy });
  };

  const handleCssInput = (e) => {
    cssText = e.detail;
    themeCopy.css = cssText;
    dispatch('update', { ...themeCopy });
  };

  const generateRandomColors = () => {
    const getRandomHexColor = () => {
      const letters = '0123456789ABCDEF';
      let color = '#';
      for (let i = 0; i < 6; i++) {
        color += letters[Math.floor(Math.random() * 16)];
      }
      return color;
    };

    const newVariables = {
      ...cssToObject(variablesText),
      '--color-gray-950': getRandomHexColor(),
      '--color-gray-900': getRandomHexColor(),
      '--color-gray-850': getRandomHexColor(),
      '--color-gray-800': getRandomHexColor(),
      '--color-gray-100': getRandomHexColor(),
      '--color-gray-50': getRandomHexColor(),
      '--color-blue-600': getRandomHexColor()
    };

    variablesText = objectToCss(newVariables);
    themeCopy.variables = newVariables;

    const updatedTheme = { ...themeCopy };
    dispatch('update', updatedTheme);

    toast.success(`Theme variables updated with random colors.`);
  };

  const generateThemeFromImage = async (event) => {
    const file = event.target.files[0];
    if (!file) {
      return;
    }

    const imageUrl = URL.createObjectURL(file);

    Vibrant.from(imageUrl)
      .getPalette()
      .then((palette) => {
        const newVariables = {
          ...cssToObject(variablesText),
          '--color-gray-950': palette.DarkMuted?.hex ?? '#0d0d0d',
          '--color-gray-900': palette.DarkVibrant?.hex ?? '#171717',
          '--color-gray-850': palette.Muted?.hex ?? '#262626',
          '--color-gray-800': palette.Vibrant?.hex ?? '#333333',
          '--color-gray-100': palette.LightMuted?.hex ?? '#ececec',
          '--color-gray-50': palette.LightVibrant?.hex ?? '#f9f9f9',
          '--color-blue-600': palette.Vibrant?.hex ?? '#2563eb'
        };

        variablesText = objectToCss(newVariables);
        themeCopy.variables = newVariables;
        themeCopy.imageFingerprint = {
          name: file.name,
          size: file.size,
          lastModified: file.lastModified
        };

        const updatedTheme = { ...themeCopy };
        dispatch('update', updatedTheme);

        toast.success(`Theme variables updated from ${file.name}`);
        URL.revokeObjectURL(imageUrl);
      });
  };
</script>

<input
  bind:this={imageImportInput}
  type="file"
  accept="image/*"
  class="hidden"
  on:change={generateThemeFromImage}
/>

<div class="space-y-4">
  <div>
    <div class="flex items-center gap-2">
      <Switch bind:state={themeCopy.toggles.cssVariables} on:change={() => dispatch('update', { ...themeCopy })} />
      <Tooltip content="Define custom CSS variables to be used in your theme. These are the core of the theming system.">
        <label for="theme-variables" class="block text-sm font-medium text-gray-700 dark:text-gray-300">{$i18n.t('Custom CSS Variables')}</label>
      </Tooltip>
    </div>
    {#if themeCopy.toggles.cssVariables}
      {#key 'css-variables'}
        <div class="mt-1 rounded-lg overflow-hidden">
          <CodeBlock
            id="theme-variables-editor"
            code={variablesText}
            lang={'css'}
            edit={true}
            on:change={handleVariablesInput}
          />
        </div>
      {/key}
      <div class="flex justify-end mt-2 space-x-2">
        <button
          class="px-3.5 py-1.5 text-sm font-medium bg-gray-100 hover:bg-gray-200 text-black dark:bg-gray-800 dark:text-white dark:hover:bg-gray-700 transition rounded-full disabled:opacity-50 whitespace-nowrap"
          on:click={generateRandomColors}
        >
          {$i18n.t('Random')}
        </button>
        <button
          class="px-3.5 py-1.5 text-sm font-medium bg-gray-100 hover:bg-gray-200 text-black dark:bg-gray-800 dark:text-white dark:hover:bg-gray-700 transition rounded-full disabled:opacity-50 whitespace-nowrap"
          on:click={() => {
            imageImportInput.click();
          }}
        >
          {$i18n.t('Generate from Image')}
        </button>
      </div>
    {/if}
  </div>
  <div>
    <div class="flex items-center gap-2">
      <Switch
        bind:state={themeCopy.toggles.customCss}
        on:change={() => dispatch('update', { ...themeCopy })}
      />
      <Tooltip
        content="Add custom CSS rules to style the UI. This is for more advanced styling that can't be achieved with variables alone."
      >
        <label
          for="theme-css"
          class="block text-sm font-medium text-gray-700 dark:text-gray-300"
          >{$i18n.t('Custom CSS')}</label
        >
      </Tooltip>
    </div>
    {#if themeCopy.toggles.customCss}
      {#key 'custom-css'}
        <div class="mt-1 rounded-lg overflow-hidden">
          <CodeBlock
            id="theme-css-editor"
            code={cssText}
            lang={'css'}
            edit={true}
            on:change={handleCssInput}
          />
        </div>
      {/key}
    {/if}
  </div>
</div>
