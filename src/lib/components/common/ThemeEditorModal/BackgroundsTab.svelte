<script lang="ts">
  import { createEventDispatcher, getContext } from 'svelte';
  import type { Theme } from '$lib/types';
  import Switch from '$lib/components/common/Switch.svelte';
  import Tooltip from '$lib/components/common/Tooltip.svelte';
  import GradientPicker from '$lib/components/common/GradientPicker.svelte';
  import { toast } from 'svelte-sonner';

  export let themeCopy: Theme;
  export let systemBgInputValue: string | undefined;
  export let chatBgInputValue: string | undefined;

  let systemBgInput: HTMLInputElement;
  let chatBgInput: HTMLInputElement;
  let systemBgInputFiles;
  let chatBgInputFiles;

  const dispatch = createEventDispatcher();
  const i18n = getContext('i18n');

  const handleSystemBackgroundImageUpload = (event) => {
    const file = event.target.files[0];
    if (!file) {
      return;
    }

    const reader = new FileReader();
    reader.onload = (e) => {
      themeCopy.systemBackgroundImageUrl = e.target.result as string;
      systemBgInputValue = file.name;
      dispatch('update', { ...themeCopy });
    };

    if (['image/gif', 'image/webp', 'image/jpeg', 'image/png'].includes(file.type)) {
      reader.readAsDataURL(file);
    } else {
      toast.error(`Unsupported File Type '${file.type}'.`);
    }
  };

  const handleChatBackgroundImageUpload = (event) => {
    const file = event.target.files[0];
    if (!file) {
      return;
    }

    const reader = new FileReader();
    reader.onload = (e) => {
      themeCopy.chatBackgroundImageUrl = e.target.result as string;
      chatBgInputValue = file.name;
      dispatch('update', { ...themeCopy });
    };

    if (['image/gif', 'image/webp', 'image/jpeg', 'image/png'].includes(file.type)) {
      reader.readAsDataURL(file);
    } else {
      toast.error(`Unsupported File Type '${file.type}'.`);
    }
  };
</script>

<input
  bind:this={systemBgInput}
  bind:files={systemBgInputFiles}
  type="file"
  accept="image/*"
  class="hidden"
  on:change={handleSystemBackgroundImageUpload}
/>
<input
  bind:this={chatBgInput}
  bind:files={chatBgInputFiles}
  type="file"
  accept="image/*"
  class="hidden"
  on:change={handleChatBackgroundImageUpload}
/>

<div class="space-y-4">
  <div>
    <div class="flex items-center gap-2">
      <Switch bind:state={themeCopy.toggles.gradient} on:change={() => dispatch('update', { ...themeCopy })} />
      <Tooltip content="Adds a gradient to the background of the app.">
        <label for="theme-gradient" class="block text-sm font-medium text-gray-700 dark:text-gray-300">{$i18n.t('System Gradient Background')}</label>
      </Tooltip>
    </div>
    {#if themeCopy.toggles.gradient}
      <div class="mt-1">
        <GradientPicker
          gradient={themeCopy.gradient}
          on:update={(e) => {
            themeCopy.gradient = { ...themeCopy.gradient, ...e.detail };
            const updatedTheme = { ...themeCopy };
            dispatch('update', updatedTheme);
          }}
        />
      </div>
    {/if}
  </div>
  <div>
    <div class="flex items-center gap-2">
      <Switch bind:state={themeCopy.toggles.systemBackgroundImage} on:change={() => dispatch('update', { ...themeCopy })} />
      <Tooltip content="Adds a background image to the app.">
        <label for="theme-background-image" class="block text-sm font-medium text-gray-700 dark:text-gray-300">{$i18n.t('System Background Image')}</label>
      </Tooltip>
    </div>
    {#if themeCopy.toggles.systemBackgroundImage}
      <div class="mt-1 space-y-2">
        <label for="theme-background-image-url" class="block text-sm font-medium text-gray-700 dark:text-gray-300">{$i18n.t('Image URL')}</label>
        <div class="flex items-center gap-2">
          <input
            type="text"
            id="theme-background-image-url"
            class="flex-grow rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-none"
            bind:value={systemBgInputValue}
            on:input={() => {
              themeCopy.systemBackgroundImageUrl = systemBgInputValue;
              dispatch('update', { ...themeCopy });
            }}
          />
          <button
            type="button"
            class="px-3.5 py-1.5 text-sm font-medium bg-gray-100 hover:bg-gray-200 text-black dark:bg-gray-800 dark:text-white dark:hover:bg-gray-700 transition rounded-full"
            on:click={() => {
              systemBgInput.click();
            }}
          >
            {$i18n.t('Upload')}
          </button>
          <button
            type="button"
            class="px-3.5 py-1.5 text-sm font-medium bg-gray-100 hover:bg-gray-200 text-black dark:bg-gray-800 dark:text-white dark:hover:bg-gray-700 transition rounded-full"
            on:click={() => {
              themeCopy.systemBackgroundImageUrl = '';
              themeCopy.systemBackgroundImageDarken = 0;
              systemBgInputFiles = undefined;
              dispatch('update', { ...themeCopy });
            }}
          >
            {$i18n.t('Reset')}
          </button>
        </div>
        <label for="theme-background-image-darken" class="block text-sm font-medium text-gray-700 dark:text-gray-300">{$i18n.t('Darken')}: {themeCopy.systemBackgroundImageDarken}%</label>
        <input
          type="range"
          id="theme-background-image-darken"
          class="w-full"
          min="0"
          max="100"
          bind:value={themeCopy.systemBackgroundImageDarken}
          on:input={() => dispatch('update', { ...themeCopy })}
        />
      </div>
    {/if}
  </div>
  <div>
    <div class="flex items-center gap-2">
      <Switch bind:state={themeCopy.toggles.chatBackgroundImage} on:change={() => dispatch('update', { ...themeCopy })} />
      <Tooltip content="Adds a background image to the chat.">
        <label for="theme-chat-background-image" class="block text-sm font-medium text-gray-700 dark:text-gray-300">{$i18n.t('Chat Background Image')}</label>
      </Tooltip>
    </div>
    {#if themeCopy.toggles.chatBackgroundImage}
      <div class="mt-1 space-y-2">
        <label for="theme-chat-background-image-url" class="block text-sm font-medium text-gray-700 dark:text-gray-300">{$i18n.t('Image URL')}</label>
        <div class="flex items-center gap-2">
          <input
            type="text"
            id="theme-chat-background-image-url"
            class="flex-grow rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-none"
            bind:value={chatBgInputValue}
            on:input={() => {
              themeCopy.chatBackgroundImageUrl = chatBgInputValue;
              dispatch('update', { ...themeCopy });
            }}
          />
          <button
            type="button"
            class="px-3.5 py-1.5 text-sm font-medium bg-gray-100 hover:bg-gray-200 text-black dark:bg-gray-800 dark:text-white dark:hover:bg-gray-700 transition rounded-full"
            on:click={() => {
              chatBgInput.click();
            }}
          >
            {$i18n.t('Upload')}
          </button>
          <button
            type="button"
            class="px-3.5 py-1.5 text-sm font-medium bg-gray-100 hover:bg-gray-200 text-black dark:bg-gray-800 dark:text-white dark:hover:bg-gray-700 transition rounded-full"
            on:click={() => {
              themeCopy.chatBackgroundImageUrl = '';
              themeCopy.chatBackgroundImageDarken = 0;
              chatBgInputFiles = undefined;
              dispatch('update', { ...themeCopy });
            }}
          >
            {$i18n.t('Reset')}
          </button>
        </div>
        <label for="theme-chat-background-image-darken" class="block text-sm font-medium text-gray-700 dark:text-gray-300">{$i18n.t('Darken')}: {themeCopy.chatBackgroundImageDarken}%</label>
        <input
          type="range"
          id="theme-chat-background-image-darken"
          class="w-full"
          min="0"
          max="100"
          bind:value={themeCopy.chatBackgroundImageDarken}
          on:input={() => dispatch('update', { ...themeCopy })}
        />
      </div>
    {/if}
  </div>
</div>
