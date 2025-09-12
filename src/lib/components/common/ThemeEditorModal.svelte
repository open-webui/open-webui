<script lang="ts">
  import { createEventDispatcher, onMount } from 'svelte';
  import { getContext } from 'svelte';
  import { toast } from 'svelte-sonner';
  import Modal from '$lib/components/common/Modal.svelte';
  import CodeEditor from '$lib/components/common/CodeEditor.svelte';
  import EmojiPicker from '$lib/components/common/EmojiPicker.svelte';
  import Tooltip from '$lib/components/common/Tooltip.svelte';
  import Switch from '$lib/components/common/Switch.svelte';
  import { WEBUI_VERSION } from '$lib/constants';
  import type { Theme } from '$lib/types';
  import ThemeDocumentationModal from '$lib/components/common/ThemeDocumentationModal.svelte';
  import Info from '$lib/components/icons/Info.svelte';
  import { themes, communityThemes } from '$lib/theme';
  import { Vibrant } from 'node-vibrant/browser';
  import GradientPicker from '$lib/components/common/GradientPicker.svelte';

  export let theme: Theme;
  export let show: boolean;
  export let isEditing: boolean;

  const dispatch = createEventDispatcher();
  const i18n = getContext('i18n');

  let themeCopy: Theme;
  let variablesText: string;
  let cssText: string;
  let animationScriptText: string;
  let particleConfigText: string;
  let tsParticleConfigText: string;
  let manualEditMode = false;
  let themeJsonText = '';

  let showVariables = false;
  let showCss = false;
  let showAnimationScript = false;
  let showParticleConfig = false;
  let showTsParticleConfig = false;
  let showDocumentation = false;

  import variables from '$lib/themes/variables.json';
  import { codeMirrorTheme } from '$lib/stores';

  let originalCodeMirrorTheme = $codeMirrorTheme;

  const descriptions = variables.reduce((acc, curr) => {
    acc[curr.name] = curr.description;
    return acc;
  }, {});

  const objectToCss = (obj) => {
    if (!obj) return '';
    let css = '';
    for (const key in obj) {
      const comment = descriptions[key] ? ` /* ${descriptions[key]} */` : '';
      css += `${key}: ${obj[key]};${comment}\n`;
    }
    return css;
  };

  const cssToObject = (css) => {
    const obj = {};
    // Remove comments, then find all key-value pairs
    const uncommentedCss = css.replace(/\/\*[\s\S]*?\*\/|([^:]|^)\/\/.*$/gm, '$1');
    
    const regex = /([\w-]+)\s*:\s*([^;]+);?/g;
    let match;
    while ((match = regex.exec(uncommentedCss)) !== null) {
      obj[match[1].trim()] = match[2].trim();
    }
    
    return obj;
  };

  onMount(() => {
    if (theme) {
      themeCopy = JSON.parse(JSON.stringify(theme));
      
      if (!themeCopy.gradient) {
        themeCopy.gradient = {
          colors: ['#0d0d0d', '#333333'],
          direction: 45,
          intensity: 100
        };
      }

      originalCodeMirrorTheme = themeCopy.codeMirrorTheme ?? $codeMirrorTheme;

      if (!isEditing) {
        themeCopy.particleConfig = undefined;
      }

      variablesText = objectToCss(themeCopy.variables);
      cssText = themeCopy.css ?? '';
      animationScriptText = themeCopy.animationScript ?? '';
      particleConfigText = themeCopy.particleConfig
        ? JSON.stringify(themeCopy.particleConfig, null, 2)
        : '';
      tsParticleConfigText = themeCopy.tsparticlesConfig
        ? JSON.stringify(themeCopy.tsparticlesConfig, null, 2)
        : '';
      themeJsonText = JSON.stringify(themeCopy, null, 2);

      showVariables = !!variablesText;
      showCss = !!cssText;
      showAnimationScript = !!animationScriptText;
      showParticleConfig =
        !!themeCopy.particleConfig && Object.keys(themeCopy.particleConfig).length > 0;
      showTsParticleConfig =
        !!themeCopy.tsparticlesConfig && Object.keys(themeCopy.tsparticlesConfig).length > 0;
    }
  });

  const save = () => {
    if (manualEditMode) {
      try {
        const newTheme = JSON.parse(themeJsonText);
        const hasParticleConfig = newTheme.particleConfig && Object.keys(newTheme.particleConfig).length > 0;
        const hasTsParticleConfig =
          newTheme.tsparticlesConfig && Object.keys(newTheme.tsparticlesConfig).length > 0;

        if (hasParticleConfig && hasTsParticleConfig) {
          toast.error('A theme cannot have both a particles.js and a tsParticles configuration.');
          return;
        }
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

      const hasParticleConfig =
        particleConfigText &&
        particleConfigText.trim() !== '' &&
        particleConfigText.trim() !== '{}' &&
        particleConfigText.trim() !== 'null';
      const hasTsParticleConfig =
        tsParticleConfigText &&
        tsParticleConfigText.trim() !== '' &&
        tsParticleConfigText.trim() !== '{}' &&
        tsParticleConfigText.trim() !== 'null';

      if (hasParticleConfig && hasTsParticleConfig) {
        toast.error('A theme cannot have both a particles.js and a tsParticles configuration.');
        return;
      }

      themeCopy.variables = cssToObject(variablesText);
      themeCopy.css = cssText;
      themeCopy.animationScript = animationScriptText;
      try {
        themeCopy.particleConfig = particleConfigText ? JSON.parse(particleConfigText) : undefined;
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
  
  const handleVariablesInput = (event) => {
    variablesText = event.detail;
    showVariables = !!variablesText;
    const updatedTheme = { ...themeCopy, variables: cssToObject(variablesText) };
    dispatch('update', updatedTheme);
  };

  const handleCssInput = (event) => {
    cssText = event.detail;
    showCss = !!cssText;
    const updatedTheme = { ...themeCopy, css: cssText };
    dispatch('update', updatedTheme);
  };

  const handleAnimationScriptInput = (event) => {
    animationScriptText = event.detail;
    showAnimationScript = !!animationScriptText;
    const updatedTheme = { ...themeCopy, animationScript: animationScriptText };
    dispatch('update', updatedTheme);
  };

  const handleParticleConfigInput = (event) => {
    particleConfigText = event.detail;
    showParticleConfig =
      !!particleConfigText && particleConfigText.trim() !== '{}' && particleConfigText.trim() !== 'null';
    try {
      const updatedTheme = { ...themeCopy, particleConfig: JSON.parse(particleConfigText) };
      dispatch('update', updatedTheme);
    } catch (e) {
      if (particleConfigText.trim() === '') {
        const updatedTheme = { ...themeCopy, particleConfig: undefined };
        dispatch('update', updatedTheme);
      }
    }
  };

  const handleManualJsonInput = (event) => {
    themeJsonText = event.detail;
    try {
      const updatedTheme = JSON.parse(themeJsonText);
      dispatch('update', updatedTheme);
    } catch (e) {
      // Do not dispatch update if JSON is invalid
    }
  };

  const handleBaseThemeChange = () => {
    let currentVariables;
    if (manualEditMode) {
      try {
        currentVariables = JSON.parse(themeJsonText).variables;
      } catch (e) {
        // If JSON is invalid, use the last known good variables from themeCopy
        currentVariables = themeCopy.variables;
      }
    } else {
      currentVariables = cssToObject(variablesText);
    }

    const updatedTheme = { ...themeCopy, variables: currentVariables };
    dispatch('update', updatedTheme);
  };

  const handleCodeMirrorThemeChange = () => {
    const updatedTheme = { ...themeCopy };
    dispatch('update', updatedTheme);
    codeMirrorTheme.set(updatedTheme.codeMirrorTheme);
  };

  const handleTsParticleConfigInput = (event) => {
    tsParticleConfigText = event.detail;
    showTsParticleConfig =
      !!tsParticleConfigText &&
      tsParticleConfigText.trim() !== '{}' &&
      tsParticleConfigText.trim() !== 'null';
    try {
      const updatedTheme = { ...themeCopy, tsparticlesConfig: JSON.parse(tsParticleConfigText) };
      dispatch('update', updatedTheme);
    } catch (e) {
      if (tsParticleConfigText.trim() === '') {
        const updatedTheme = { ...themeCopy, tsparticlesConfig: undefined };
        dispatch('update', updatedTheme);
      }
    }
  };

  const toggleView = () => {
    if (manualEditMode) {
      // Switching from manual to form
      try {
        const newTheme = JSON.parse(themeJsonText);
        themeCopy = newTheme;
        variablesText = objectToCss(themeCopy.variables);
        cssText = themeCopy.css ?? '';
        animationScriptText = themeCopy.animationScript ?? '';
        particleConfigText = themeCopy.particleConfig
          ? JSON.stringify(themeCopy.particleConfig, null, 2)
          : '';
        tsParticleConfigText = themeCopy.tsparticlesConfig
          ? JSON.stringify(themeCopy.tsparticlesConfig, null, 2)
          : '';
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
        themeCopy.particleConfig = particleConfigText ? JSON.parse(particleConfigText) : undefined;
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

  const cancel = () => {
    codeMirrorTheme.set(originalCodeMirrorTheme);
    dispatch('cancel');
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
</script>

<Modal bind:show {cancel} width="w-full max-w-3xl">
  <div class="p-4">
    <div class="flex justify-between items-center">
      <h2 class="text-lg font-medium">{$i18n.t('Edit Theme')}</h2>
      <div class="flex items-center space-x-2">
        <button
          class="text-sm text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 flex items-center space-x-1"
          on:click={() => (showDocumentation = true)}
        >
          <Info class="w-4 h-4" />
          <span>{$i18n.t('Documentation')}</span>
        </button>
        <button
          class="text-sm text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
          on:click={toggleView}
        >
          {manualEditMode ? $i18n.t('Back to Form Editor') : $i18n.t('Swap to Manual Editor')}
        </button>
      </div>
    </div>

    {#if themeCopy}
      {#if !manualEditMode}
        <div class="mt-4 grid grid-cols-2 gap-4">
          <div>
            <label for="theme-name" class="block text-sm font-medium text-gray-700 dark:text-gray-300">{$i18n.t('Name')}</label>
            <Tooltip content="The name of the theme as it will appear in the theme list.">
              <input
                type="text"
                id="theme-name"
                class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-none mt-1"
                bind:value={themeCopy.name}
              />
            </Tooltip>
          </div>
          <div>
            <label for="theme-author" class="block text-sm font-medium text-gray-700 dark:text-gray-300">{$i18n.t('Author')}</label>
            <Tooltip content="The name of the theme's creator.">
              <input
                type="text"
                id="theme-author"
                class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-none mt-1"
                bind:value={themeCopy.author}
              />
            </Tooltip>
          </div>
          <div>
            <label for="theme-version" class="block text-sm font-medium text-gray-700 dark:text-gray-300">{$i18n.t('Version')}</label>
            <Tooltip content="The version of the theme, preferably in semantic versioning format (e.g., 1.0.0).">
              <input
                type="text"
                id="theme-version"
                class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-none mt-1"
                bind:value={themeCopy.version}
              />
            </Tooltip>
          </div>
          <div>
            <label for="theme-repo" class="block text-sm font-medium text-gray-700 dark:text-gray-300">{$i18n.t('Repository')}</label>
            <Tooltip content="The URL of the theme's source code repository (e.g., on GitHub).">
              <input
                type="text"
                id="theme-repo"
                class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-none mt-1"
                bind:value={themeCopy.repository}
              />
            </Tooltip>
          </div>
          <div>
            <label for="theme-version" class="block text-sm font-medium text-gray-700 dark:text-gray-300">{$i18n.t('Target WebUI Version')}</label>
            <Tooltip content="The version of Open WebUI that this theme was designed for. Helps to warn users about potential incompatibilities.">
              <input
                type="text"
                id="theme-target-version"
                class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-none mt-1"
                bind:value={themeCopy.targetWebUIVersion}
              />
            </Tooltip>
          </div>
          <div>
            <label for="theme-base" class="block text-sm font-medium text-gray-700 dark:text-gray-300">{$i18n.t('Base Theme')}</label>
            <Tooltip content="The base theme to inherit styles from. Your theme will be applied on top of this.">
              <select
                id="theme-base"
                class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-none mt-1"
                bind:value={themeCopy.base}
                on:change={handleBaseThemeChange}
              >
                <option value="system">System</option>
                <option value="light">Light</option>
                <option value="dark">Dark</option>
                <option value="oled-dark">OLED Dark</option>
                <option value="her">Her</option>
              </select>
            </Tooltip>
          </div>
          <div>
            <label for="theme-codemirror" class="block text-sm font-medium text-gray-700 dark:text-gray-300">{$i18n.t('CodeMirror Theme')}</label>
            <Tooltip content="The theme for the editable code editor.">
              <select
                id="theme-codemirror"
                class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-none mt-1"
                bind:value={themeCopy.codeMirrorTheme}
                on:change={handleCodeMirrorThemeChange}
              >
                <option value="one-dark">One Dark</option>
                <option value="abcdef">Abcdef</option>
                <option value="abyss">Abyss</option>
                <option value="androidstudio">Android Studio</option>
                <option value="andromeda">Andromeda</option>
                <option value="atomone">Atom One</option>
                <option value="aura">Aura</option>
                <option value="bbedit">BBEdit</option>
                <option value="basicLight">Basic Light</option>
                <option value="basicDark">Basic Dark</option>
                <option value="bespin">Bespin</option>
                <option value="copilot">Copilot</option>
                <option value="consoleLight">Console Light</option>
                <option value="consoleDark">Console Dark</option>
                <option value="dracula">Dracula</option>
                <option value="darcula">Darcula</option>
                <option value="duotoneLight">Duotone Light</option>
                <option value="duotoneDark">Duotone Dark</option>
                <option value="eclipse">Eclipse</option>
                <option value="githubLight">GitHub Light</option>
                <option value="githubDark">GitHub Dark</option>
                <option value="gruvboxDark">Gruvbox Dark</option>
                <option value="gruvboxLight">Gruvbox Light</option>
                <option value="materialLight">Material Light</option>
                <option value="materialDark">Material Dark</option>
                <option value="monokai">Monokai</option>
                <option value="monokaiDimmed">Monokai Dimmed</option>
                <option value="kimbie">Kimbie</option>
                <option value="noctisLilac">Noctis Lilac</option>
                <option value="nord">Nord</option>
                <option value="okaidia">Okaidia</option>
                <option value="quietlight">Quietlight</option>
                <option value="red">Red</option>
                <option value="solarizedLight">Solarized Light</option>
                <option value="solarizedDark">Solarized Dark</option>
                <option value="sublime">Sublime</option>
                <option value="tokyoNight">Tokyo Night</option>
                <option value="tokyoNightStorm">Tokyo Night Storm</option>
                <option value="tokyoNightDay">Tokyo Night Day</option>
                <option value="tomorrowNightBlue">Tomorrow Night Blue</option>
                <option value="whiteLight">White Light</option>
                <option value="whiteDark">White Dark</option>
                <option value="vscodeDark">VSCode Dark</option>
                <option value="vscodeLight">VSCode Light</option>
                <option value="xcodeLight">Xcode Light</option>
                <option value="xcodeDark">Xcode Dark</option>
              </select>
            </Tooltip>
          </div>
          <div>
            <label for="theme-emoji" class="block text-sm font-medium text-gray-700 dark:text-gray-300">{$i18n.t('Emoji')}</label>
            <Tooltip content="An emoji to represent the theme in the theme list.">
              <EmojiPicker
                onSubmit={(emoji) => {
                  themeCopy.emoji = emoji;
                }}
              >
                <button
                  class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-none mt-1 text-left"
                >
                  {themeCopy.emoji ?? 'Select an emoji'}
                </button>
              </EmojiPicker>
            </Tooltip>
          </div>
          <div>
            <label for="theme-meta-color" class="block text-sm font-medium text-gray-700 dark:text-gray-300">{$i18n.t('Meta Theme Color')}</label>
            <Tooltip content="The color used by the browser for the UI around the webpage. Affects the color of the status bar on mobile browsers.">
              <input
                type="text"
                id="theme-meta-color"
                class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-none mt-1"
                bind:value={themeCopy.metaThemeColor}
              />
            </Tooltip>
          </div>
          <div class="col-span-2">
            <div class="flex items-center gap-2">
              <Switch bind:state={showVariables} />
              <Tooltip content="Define custom CSS variables to be used in your theme. These are the core of the theming system.">
                <label for="theme-variables" class="block text-sm font-medium text-gray-700 dark:text-gray-300">{$i18n.t('CSS Variables')}</label>
              </Tooltip>
            </div>
            {#if showVariables}
              <div class="mt-1 h-48">
                <CodeEditor id="theme-variables-editor" bind:value={variablesText} lang={'css'} on:input={handleVariablesInput} />
              </div>
              <div class="flex justify-end mt-2 space-x-2">
                <button
                  class="px-3.5 py-1.5 text-sm font-medium bg-gray-100 hover:bg-gray-200 text-black dark:bg-gray-800 dark:text-white dark:hover:bg-gray-700 transition rounded-full disabled:opacity-50 whitespace-nowrap"
                  on:click={generateRandomColors}
                >
                  {$i18n.t('Random')}
                </button>
                <input
                  id="image-import-input-modal"
                  type="file"
                  accept="image/*"
                  class="hidden"
                  on:change={generateThemeFromImage}
                />
                <button
                  class="px-3.5 py-1.5 text-sm font-medium bg-gray-100 hover:bg-gray-200 text-black dark:bg-gray-800 dark:text-white dark:hover:bg-gray-700 transition rounded-full disabled:opacity-50 whitespace-nowrap"
                  on:click={() => {
                    const input = document.getElementById('image-import-input-modal');
                    if (input) {
                      input.click();
                    }
                  }}
                >
                  {$i18n.t('Generate from Image')}
                </button>
              </div>
            {/if}
          </div>
          <div class="col-span-2">
            <div class="flex items-center gap-2">
              <Switch bind:state={showCss} />
              <Tooltip content="Add custom CSS rules to style the UI. This is for more advanced styling that can't be achieved with variables alone.">
                <label for="theme-css" class="block text-sm font-medium text-gray-700 dark:text-gray-300">{$i18n.t('CSS')}</label>
              </Tooltip>
            </div>
            {#if showCss}
              <div class="mt-1 h-48">
                <CodeEditor id="theme-css-editor" bind:value={cssText} lang={'css'} on:input={handleCssInput} />
              </div>
            {/if}
          </div>
          <div class="col-span-2">
            <div class="flex items-center gap-2">
              <Switch bind:state={showAnimationScript} />
              <Tooltip content="Add custom Javascript to create animations. This is for advanced themes that use canvas or other dynamic elements.">
                <label for="theme-animation-script" class="block text-sm font-medium text-gray-700 dark:text-gray-300">{$i18n.t('Animation Script')}</label>
              </Tooltip>
            </div>
            {#if showAnimationScript}
              <div class="mt-1 h-48">
                <CodeEditor id="theme-animation-script-editor" bind:value={animationScriptText} lang={'javascript'} on:input={handleAnimationScriptInput} />
              </div>
            {/if}
          </div>
          <div class="col-span-2">
            <div class="flex items-center gap-2">
              <Switch bind:state={showParticleConfig} />
              <Tooltip content="Configuration object for particle.js animations.">
                <label for="theme-particle-config" class="block text-sm font-medium text-gray-700 dark:text-gray-300">{$i18n.t('Particle.js Config')}</label>
              </Tooltip>
            </div>
            {#if showParticleConfig}
              <div class="mt-1 h-48">
                <CodeEditor id="theme-particle-config-editor" bind:value={particleConfigText} lang={'json'} on:input={handleParticleConfigInput} />
              </div>
            {/if}
          </div>
          <div class="col-span-2">
            <div class="flex items-center gap-2">
              <Switch bind:state={showTsParticleConfig} />
              <Tooltip content="Configuration object for tsParticles animations.">
                <label for="theme-tsparticle-config" class="block text-sm font-medium text-gray-700 dark:text-gray-300">{$i18n.t('tsParticles Config')}</label>
              </Tooltip>
            </div>
            {#if showTsParticleConfig}
              <div class="mt-1 h-48">
                <CodeEditor id="theme-tsparticle-config-editor" bind:value={tsParticleConfigText} lang={'json'} on:input={handleTsParticleConfigInput} />
              </div>
            {/if}
          </div>
          <div class="col-span-2">
            <div class="flex items-center gap-2">
              <label for="theme-gradient" class="block text-sm font-medium text-gray-700 dark:text-gray-300">{$i18n.t('Gradient Background')}</label>
            </div>
            <div class="mt-1">
              <GradientPicker
                gradient={themeCopy.gradient}
                on:update={(e) => {
                  themeCopy.gradient = e.detail;
                  const updatedTheme = { ...themeCopy };
                  dispatch('update', updatedTheme);
                }}
              />
            </div>
          </div>
        </div>
      {:else}
        <div class="mt-4">
          <CodeEditor
            id="theme-json-editor"
            bind:value={themeJsonText}
            lang={'json'}
            on:input={handleManualJsonInput}
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

{#if showDocumentation}
  <ThemeDocumentationModal
    bind:show={showDocumentation}
    on:cancel={() => (showDocumentation = false)}
  />
{/if}
