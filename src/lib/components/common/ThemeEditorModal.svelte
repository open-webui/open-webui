<script lang="ts">
  import { createEventDispatcher, onMount } from 'svelte';
  import { getContext } from 'svelte';
  import { toast } from 'svelte-sonner';
  import Modal from '$lib/components/common/Modal.svelte';
  import CodeEditor from '$lib/components/common/CodeEditor.svelte';
  import Tooltip from '$lib/components/common/Tooltip.svelte';
  import Switch from '$lib/components/common/Switch.svelte';
  import { WEBUI_VERSION } from '$lib/constants';
  import type { Theme } from '$lib/types';
  import Info from '$lib/components/icons/Info.svelte';
  import Collapsible from '$lib/components/common/Collapsible.svelte';
  import CodeBlock from '$lib/components/chat/Messages/CodeBlock.svelte';
  import { themes, communityThemes } from '$lib/theme';
  import { Vibrant } from 'node-vibrant/browser';
  import GradientPicker from '$lib/components/common/GradientPicker.svelte';
  import GeneralTab from './ThemeEditorModal/GeneralTab.svelte';
  import StylingTab from './ThemeEditorModal/StylingTab.svelte';
  import BackgroundsTab from './ThemeEditorModal/BackgroundsTab.svelte';
  import AnimationsTab from './ThemeEditorModal/AnimationsTab.svelte';
  import DocumentationTab from './ThemeEditorModal/DocumentationTab.svelte';

  export let theme: Theme;
  export let show: boolean;
  export let isEditing: boolean;

  let chatBgInputValue: string | undefined;
  let systemBgInputValue: string | undefined;

  const dispatch = createEventDispatcher();
  const i18n = getContext('i18n');

  let themeCopy: Theme;
  let variablesText: string;
  let cssText: string;
  let animationScriptText: string;
  let tsParticleConfigText: string;
  let manualEditMode = false;
  let themeJsonText = '';

  let activeTab = 'General';

  import variables from '$lib/themes/variables.json';
  import { codeMirrorTheme } from '$lib/stores';
  import { objectToCss, cssToObject } from '$lib/utils/theme';

  let originalCodeMirrorTheme = $codeMirrorTheme;

  onMount(() => {
    if (theme) {
      themeCopy = JSON.parse(JSON.stringify(theme));

      if (!isEditing) {
        const importantVariables = [
          '--color-gray-950',
          '--color-gray-900',
          '--color-gray-850',
          '--color-gray-800',
          '--color-gray-100',
          '--color-gray-50',
          '--color-blue-600'
        ];

        const newVariables = {};
        for (const v of variables) {
          if (importantVariables.includes(v.name)) {
            newVariables[v.name] = v.defaultValue;
          }
        }
        themeCopy.variables = newVariables;
      }

      chatBgInputValue =
        themeCopy.chatBackgroundImageUrl && themeCopy.chatBackgroundImageUrl.startsWith('data:image')
          ? 'Uploaded Image'
          : themeCopy.chatBackgroundImageUrl;

      systemBgInputValue =
        themeCopy.systemBackgroundImageUrl && themeCopy.systemBackgroundImageUrl.startsWith('data:image')
          ? 'Uploaded Image'
          : themeCopy.systemBackgroundImageUrl;

      if (typeof themeCopy.systemBackgroundImageDarken === 'undefined') {
        themeCopy.systemBackgroundImageDarken = 75;
      }
      if (typeof themeCopy.chatBackgroundImageDarken === 'undefined') {
        themeCopy.chatBackgroundImageDarken = 75;
      }

      if (!themeCopy.gradient) {
        themeCopy.gradient = {
          enabled: false,
          colors: ['#0d0d0d', '#333333'],
          direction: 45,
          intensity: 100
        };
      } else if (typeof themeCopy.gradient.enabled === 'undefined') {
        themeCopy.gradient.enabled = false;
      }

      originalCodeMirrorTheme = themeCopy.codeMirrorTheme ?? $codeMirrorTheme;

      variablesText = objectToCss(themeCopy.variables);
      cssText = themeCopy.css ?? '';
      animationScriptText = themeCopy.animationScript ?? '';
      tsParticleConfigText = themeCopy.tsparticlesConfig
        ? JSON.stringify(themeCopy.tsparticlesConfig, null, 2)
        : '';
      themeJsonText = JSON.stringify(themeCopy, null, 2);

      if (!themeCopy.toggles) {
        themeCopy.toggles = {
          cssVariables: isEditing ? !!variablesText : true,
          customCss: isEditing ? !!cssText : false,
          animationScript: isEditing ? !!animationScriptText : false,
          tsParticles: isEditing
            ? !!tsParticleConfigText &&
              tsParticleConfigText.trim() !== '{}' &&
              tsParticleConfigText.trim() !== 'null'
            : false,
          gradient: isEditing ? themeCopy.gradient?.enabled ?? false : false,
          systemBackgroundImage: isEditing ? !!themeCopy.systemBackgroundImageUrl : false,
          chatBackgroundImage: isEditing ? !!themeCopy.chatBackgroundImageUrl : false
        };
      }
    }
  });

  const save = () => {
    if (manualEditMode) {
      try {
        const newTheme = JSON.parse(themeJsonText);
        themeCopy = newTheme;
      } catch (e) {
        toast.error('Invalid JSON format. Please fix it before saving.');
        return;
      }
    } else {
      // Form-based validation
      if (!themeCopy.name) {
        toast.error('Theme name cannot be empty.');
        return;
      }
      if (!themeCopy.author) {
        toast.error('Author name cannot be empty.');
        return;
      }
      if (!themeCopy.version || !/^\d+(\.\d+){0,2}$/.test(themeCopy.version)) {
        toast.error('Version must be in the format X, X.Y, or X.Y.Z (e.g., 1.0.0).');
        return;
      }
      if (themeCopy.repository && !/^https?:\/\/[^\s/$.?#].[^\s]*$/i.test(themeCopy.repository)) {
        toast.error('Repository must be a valid URL.');
        return;
      }

      themeCopy.variables = cssToObject(variablesText);
      themeCopy.css = cssText;
      themeCopy.animationScript = animationScriptText;
      try {
        themeCopy.tsparticlesConfig = tsParticleConfigText
          ? JSON.parse(tsParticleConfigText)
          : undefined;
      } catch (e) {
        toast.error('Invalid JSON format for Particle Config. Please fix it before saving.');
        return;
      }
    }

    if (!themeCopy.targetWebUIVersion) {
      themeCopy.targetWebUIVersion = WEBUI_VERSION;
    }

    dispatch('save', themeCopy);
  };

  const handleManualJsonInput = (event) => {
    themeJsonText = event.detail;
    try {
      themeCopy = JSON.parse(themeJsonText);
      dispatch('update', themeCopy);
    } catch (e) {
      // Do not dispatch update if JSON is invalid
    }
  };

  const toggleView = () => {
    if (manualEditMode) {
      // Switching from manual to form
      try {
        const newTheme = JSON.parse(themeJsonText);
        themeCopy = newTheme;

        if (!themeCopy.gradient) {
          themeCopy.gradient = {
            enabled: false,
            colors: ['#0d0d0d', '#333333'],
            direction: 45,
            intensity: 100
          };
        } else if (typeof themeCopy.gradient.enabled === 'undefined') {
          themeCopy.gradient.enabled = false;
        }

        variablesText = objectToCss(themeCopy.variables);
        cssText = themeCopy.css ?? '';
        animationScriptText = themeCopy.animationScript ?? '';
        tsParticleConfigText = themeCopy.tsparticlesConfig
          ? JSON.stringify(themeCopy.tsparticlesConfig, null, 2)
          : '';

        // Re-evaluate toggles based on content when switching from manual to form
        themeCopy.toggles = {
          cssVariables: !!variablesText,
          customCss: !!cssText,
          animationScript: !!animationScriptText,
          tsParticles:
            !!themeCopy.tsparticlesConfig && Object.keys(themeCopy.tsparticlesConfig).length > 0,
          gradient: themeCopy.gradient?.enabled ?? false,
          systemBackgroundImage: !!themeCopy.systemBackgroundImageUrl,
          chatBackgroundImage: !!themeCopy.chatBackgroundImageUrl
        };
      } catch (e) {
        toast.error('Invalid JSON format.');
        return; // Don't switch view if JSON is invalid
      }
    } else {
      // Switching from form to manual
      themeCopy.variables = cssToObject(variablesText);
      themeCopy.css = cssText;
      themeCopy.animationScript = animationScriptText;
      try {
        themeCopy.tsparticlesConfig = tsParticleConfigText
          ? JSON.parse(tsParticleConfigText)
          : undefined;
      } catch (e) {
        toast.error('Invalid JSON format for Particle Config. Please fix it before saving.');
        return;
      }
      themeJsonText = JSON.stringify(themeCopy, null, 2);
    }
    manualEditMode = !manualEditMode;
  };

  $: if (themeCopy && themeCopy.toggles) {
    themeCopy.gradient.enabled = themeCopy.toggles.gradient;
  }

  const cancel = () => {
    codeMirrorTheme.set(originalCodeMirrorTheme);
    dispatch('cancel');
  };
</script>

<Modal bind:show cancel={cancel} width="w-full max-w-6xl">
  <div class="p-4">
    <div class="flex justify-between items-center">
      <h2 class="text-lg font-medium">{$i18n.t('Edit Theme')}</h2>
      <div class="flex items-center space-x-2">
        <button
          class="text-sm text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
          on:click={toggleView}
        >
          {manualEditMode ? $i18n.t('Return to Form Editor') : $i18n.t('Swap to Manual Editor')}
        </button>
      </div>
    </div>

    {#if themeCopy}
      {#if !manualEditMode}
        <div class="border-b border-gray-200 dark:border-gray-700">
          <nav class="-mb-px flex space-x-8" aria-label="Tabs">
            <button
              class="whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm"
              class:border-blue-500={activeTab === 'General'}
              class:text-blue-600={activeTab === 'General'}
              class:border-transparent={activeTab !== 'General'}
              class:text-gray-500={activeTab !== 'General'}
              class:hover:text-gray-700={activeTab !== 'General'}
              class:hover:border-gray-300={activeTab !== 'General'}
              on:click={() => (activeTab = 'General')}
            >
              {$i18n.t('General')}
            </button>
            <button
              class="whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm"
              class:border-blue-500={activeTab === 'Styling'}
              class:text-blue-600={activeTab === 'Styling'}
              class:border-transparent={activeTab !== 'Styling'}
              class:text-gray-500={activeTab !== 'Styling'}
              class:hover:text-gray-700={activeTab !== 'Styling'}
              class:hover:border-gray-300={activeTab !== 'Styling'}
              on:click={() => (activeTab = 'Styling')}
            >
              {$i18n.t('Styling')}
            </button>
            <button
              class="whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm"
              class:border-blue-500={activeTab === 'Backgrounds'}
              class:text-blue-600={activeTab === 'Backgrounds'}
              class:border-transparent={activeTab !== 'Backgrounds'}
              class:text-gray-500={activeTab !== 'Backgrounds'}
              class:hover:text-gray-700={activeTab !== 'Backgrounds'}
              class:hover:border-gray-300={activeTab !== 'Backgrounds'}
              on:click={() => (activeTab = 'Backgrounds')}
            >
              {$i18n.t('Backgrounds')}
            </button>
            <button
              class="whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm"
              class:border-blue-500={activeTab === 'Animations'}
              class:text-blue-600={activeTab === 'Animations'}
              class:border-transparent={activeTab !== 'Animations'}
              class:text-gray-500={activeTab !== 'Animations'}
              class:hover:text-gray-700={activeTab !== 'Animations'}
              class:hover:border-gray-300={activeTab !== 'Animations'}
              on:click={() => (activeTab = 'Animations')}
            >
              {$i18n.t('Animations')}
            </button>
            <button
              class="whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm"
              class:border-blue-500={activeTab === 'Documentation'}
              class:text-blue-600={activeTab === 'Documentation'}
              class:border-transparent={activeTab !== 'Documentation'}
              class:text-gray-500={activeTab !== 'Documentation'}
              class:hover:text-gray-700={activeTab !== 'Documentation'}
              class:hover:border-gray-300={activeTab !== 'Documentation'}
              on:click={() => (activeTab = 'Documentation')}
            >
              {$i18n.t('Documentation')}
            </button>
          </nav>
        </div>
        <div class="mt-4">
          {#if activeTab === 'General'}
            <GeneralTab bind:themeCopy on:update />
          {/if}
          {#if activeTab === 'Styling'}
            <StylingTab bind:themeCopy bind:variablesText bind:cssText on:update />
          {/if}
          {#if activeTab === 'Animations'}
            <AnimationsTab
              bind:themeCopy
              bind:animationScriptText
              bind:tsParticleConfigText
              on:update
            />
          {/if}
          {#if activeTab === 'Backgrounds'}
            <BackgroundsTab
              bind:themeCopy
              bind:systemBgInputValue
              bind:chatBgInputValue
              on:update
            />
          {/if}
          {#if activeTab === 'Documentation'}
            <DocumentationTab />
          {/if}
        </div>
      {:else}
        <div class="mt-4 rounded-lg overflow-hidden">
          <CodeBlock
            id="theme-json-editor"
            code={themeJsonText}
            lang={'json'}
            edit={true}
            on:change={handleManualJsonInput}
          />
        </div>
      {/if}
    {/if}

    <div class="mt-6 flex justify-end space-x-2">
      <button
        class="px-3.5 py-1.5 text-sm font-medium bg-gray-100 hover:bg-gray-200 dark:bg-gray-800 dark:hover:bg-gray-700 transition rounded-full"
        on:click={cancel}
      >
        {$i18n.t('Cancel')}
      </button>
      <button
        class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full"
        on:click={save}
      >
        {$i18n.t('Save')}
      </button>
    </div>
  </div>
</Modal>
