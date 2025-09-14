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
  import Info from '$lib/components/icons/Info.svelte';
  import Collapsible from '$lib/components/common/Collapsible.svelte';
  import CodeBlock from '$lib/components/chat/Messages/CodeBlock.svelte';
  import { themes, communityThemes } from '$lib/theme';
  import { Vibrant } from 'node-vibrant/browser';
  import GradientPicker from '$lib/components/common/GradientPicker.svelte';

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
  let systemBgInputFiles;
  let chatBgInputFiles;

  let activeTab = 'General';

  import variables from '$lib/themes/variables.json';
  import { codeMirrorTheme } from '$lib/stores';

  let originalCodeMirrorTheme = $codeMirrorTheme;

  const fullThemeSchema = {
    id: 'custom-theme-example',
    name: 'Custom Theme Example',
    version: '1.0.0',
    author: 'Your Name',
    repository: 'https://github.com/user/repo',
    targetWebUIVersion: '0.6.29',
    base: 'dark',
    emoji: '🎨',
    metaThemeColor: '#000000',
    systemBackgroundImageUrl: '',
    systemBackgroundImageDarken: 0,
    chatBackgroundImageUrl: '',
    chatBackgroundImageDarken: 30,
    variables: variables.reduce((acc, v) => ({ ...acc, [v.name]: v.defaultValue }), {}),
    gradient: {
        enabled: true,
        direction: 45,
        intensity: 100,
        colors: ['#ff0000', '#0000ff']
    },
    tsparticlesConfig: {},
    animationScript: '',
    css: '/* Custom CSS rules go here */',
    sourceUrl:
        'https://raw.githubusercontent.com/open-webui/open-webui/main/src/lib/themes/oled-dark.json',
    codeMirrorTheme: 'abcdef',
    toggles: {
        cssVariables: true,
        customCss: true,
        animationScript: true,
        tsParticles: true,
        gradient: true,
        systemBackgroundImage: true,
        chatBackgroundImage: true
    }
  };

  const descriptions = variables.reduce((acc, curr) => {
    acc[curr.name] = curr.description;
    return acc;
  }, {});

  const objectToCss = (obj) => {
    if (!obj) return '';
    let css = '';
    for (const key in obj) {
      css += `${key}: ${obj[key]};\n`;
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

  const handleVariablesInput = (event) => {
    variablesText = event.detail;
    themeCopy.variables = cssToObject(variablesText);
    dispatch('update', { ...themeCopy });
  };

  const handleCssInput = (event) => {
    cssText = event.detail;
    themeCopy.css = cssText;
    dispatch('update', { ...themeCopy });
  };

  const handleAnimationScriptInput = (event) => {
    animationScriptText = event.detail;
    themeCopy.animationScript = animationScriptText;
    dispatch('update', { ...themeCopy });
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

  const handleBaseThemeChange = () => {
    // themeCopy.base is updated by bind:value
    dispatch('update', { ...themeCopy });
  };

  const handleCodeMirrorThemeChange = () => {
    // themeCopy.codeMirrorTheme is updated by bind:value
    dispatch('update', { ...themeCopy });
  };

  const handleTsParticleConfigInput = (event) => {
    tsParticleConfigText = event.detail;
    try {
      themeCopy.tsparticlesConfig = JSON.parse(tsParticleConfigText);
      dispatch('update', { ...themeCopy });
    } catch (e) {
      if (tsParticleConfigText.trim() === '') {
        themeCopy.tsparticlesConfig = undefined;
        dispatch('update', { ...themeCopy });
      }
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

<Modal bind:show {cancel} width="w-full max-w-6xl">
  <input
    id="system-bg-image-input"
    type="file"
    accept="image/*"
    class="hidden"
    bind:files={systemBgInputFiles}
    on:change={handleSystemBackgroundImageUpload}
  />
  <input
    id="chat-bg-image-input"
    type="file"
    accept="image/*"
    class="hidden"
    bind:files={chatBgInputFiles}
    on:change={handleChatBackgroundImageUpload}
  />
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
          <div class="grid grid-cols-2 gap-4">
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
              <label for="theme-version" class="block text-sm font-medium text-gray-700 dark:text-gray-300">{$i18n.t('Theme Version')}</label>
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
          </div>
          {/if}
          {#if activeTab === 'Styling'}
          <div class="space-y-4">
            <div>
              <div class="flex items-center gap-2">
                <Switch bind:state={themeCopy.toggles.cssVariables} on:change={() => dispatch('update', { ...themeCopy })} />
              <Tooltip content="Define custom CSS variables to be used in your theme. These are the core of the theming system.">
                <label for="theme-variables" class="block text-sm font-medium text-gray-700 dark:text-gray-300">{$i18n.t('Custom CSS Variables')}</label>
              </Tooltip>
            </div>
            {#if themeCopy.toggles.cssVariables}
              <div class="mt-1 h-48 rounded-lg overflow-hidden">
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
          <div>
            <div class="flex items-center gap-2">
              <Switch bind:state={themeCopy.toggles.customCss} on:change={() => dispatch('update', { ...themeCopy })} />
              <Tooltip content="Add custom CSS rules to style the UI. This is for more advanced styling that can't be achieved with variables alone.">
                <label for="theme-css" class="block text-sm font-medium text-gray-700 dark:text-gray-300">{$i18n.t('Custom CSS')}</label>
              </Tooltip>
            </div>
            {#if themeCopy.toggles.customCss}
              <div class="mt-1 h-48 rounded-lg overflow-hidden">
                <CodeEditor id="theme-css-editor" bind:value={cssText} lang={'css'} on:input={handleCssInput} />
              </div>
            {/if}
          </div>
          </div>
          {/if}
          {#if activeTab === 'Animations'}
          <div class="space-y-4">
            <div>
              <div class="flex items-center gap-2">
              <Switch bind:state={themeCopy.toggles.animationScript} on:change={() => dispatch('update', { ...themeCopy })} />
              <Tooltip content="Add custom Javascript to create animations. This is for advanced themes that use canvas or other dynamic elements.">
                <label for="theme-animation-script" class="block text-sm font-medium text-gray-700 dark:text-gray-300">{$i18n.t('Animation Script')}</label>
              </Tooltip>
            </div>
            {#if themeCopy.toggles.animationScript}
              <div class="mt-1 h-48 rounded-lg overflow-hidden">
                <CodeEditor id="theme-animation-script-editor" bind:value={animationScriptText} lang={'javascript'} on:input={handleAnimationScriptInput} />
              </div>
            {/if}
          </div>
          <div>
            <div class="flex items-center gap-2">
              <Switch bind:state={themeCopy.toggles.tsParticles} on:change={() => dispatch('update', { ...themeCopy })} />
              <Tooltip content="Configuration object for tsParticles animations.">
                <label for="theme-tsparticle-config" class="block text-sm font-medium text-gray-700 dark:text-gray-300">{$i18n.t('tsParticles Config')}</label>
              </Tooltip>
            </div>
            {#if themeCopy.toggles.tsParticles}
              <div class="mt-1 h-48 rounded-lg overflow-hidden">
                <CodeEditor id="theme-tsparticle-config-editor" bind:value={tsParticleConfigText} lang={'json'} on:input={handleTsParticleConfigInput} />
              </div>
            {/if}
          </div>
          </div>
          {/if}
          {#if activeTab === 'Backgrounds'}
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
                    const input = document.getElementById('system-bg-image-input');
                    if (input) {
                      input.click();
                    }
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
                    const input = document.getElementById('chat-bg-image-input');
                    if (input) {
                      input.click();
                    }
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
          {/if}
          {#if activeTab === 'Documentation'}
            <div class="mt-4 space-y-4 overflow-y-auto max-h-[70vh] text-sm">
              <Collapsible title="Full Theme Schema" open={false}>
                <div slot="content" class="pt-2">
                  <p class="text-gray-500">
                    This is the full schema of the JSON file that is acceptable by the theming system.
                  </p>
                  <div class="mt-2">
                    <CodeBlock
                      code={JSON.stringify(fullThemeSchema, null, 2)}
                      language="json"
                      header={false}
                      canCopy={true}
                      edit={false}
                    />
                  </div>
                </div>
              </Collapsible>
              <Collapsible title="Key Theme Properties" open={false}>
                <div slot="content" class="pt-2">
                  <p>
                    Here are the main properties you can use to define your theme. For a complete guide,
                    refer to the <a
                      href="https://github.com/open-webui/open-webui/blob/main/docs/THEMES.md"
                      target="_blank"
                      class="text-blue-500 hover:underline">full documentation</a
                    >.
                  </p>
                  <ul class="mt-2 list-disc list-inside space-y-1">
                    <li>
                      <strong>base:</strong> The base theme to inherit styles from. Can be 'light' or 'dark'.
                      Your theme will be applied on top of this.
                    </li>
                    <li>
                      <strong>css:</strong> Add custom CSS rules to style the UI. This is for more advanced
                      styling that can't be achieved with variables alone.
                    </li>
                    <li>
                      <strong>variables:</strong> Define custom values for the core CSS variables. This is the
                      primary way to change the colors of the UI.
                    </li>
                    <li>
                      <strong>animationScript:</strong> Custom Javascript for canvas-based animations.
                    </li>
                    <li>
                      <strong>tsparticlesConfig:</strong> Configuration for modern
                      <a
                        href="https://tsparticles.dev"
                        target="_blank"
                        class="text-blue-500 hover:underline">tsParticles</a
                      > animations.
                    </li>
                    <li>
                      <strong>systemBackgroundImageUrl:</strong> URL for the system-wide background image.
                    </li>
                    <li>
                      <strong>systemBackgroundImageDarken:</strong> How much to darken the system background image (0-100).
                    </li>
                    <li>
                      <strong>chatBackgroundImageUrl:</strong> URL for the chat-specific background image.
                    </li>
                    <li>
                      <strong>chatBackgroundImageDarken:</strong> How much to darken the chat background image (0-100).
                    </li>
                  </ul>
                </div>
              </Collapsible>

              <Collapsible title="Animation Resources" open={false}>
                <div slot="content" class="pt-2">
                  <p>
                    You can create complex particle animations using one of the supported libraries. Use
                    their official editors to build your configuration, then paste the exported JSON into the
                    corresponding field in the theme editor.
                  </p>
                  <ul class="mt-2 list-disc list-inside">
                    <li>
                      <a
                        href="https://particles.js.org/"
                        target="_blank"
                        class="text-blue-500 hover:underline">tsParticles Official Editor & Samples</a
                      >
                    </li>
                  </ul>
                </div>
              </Collapsible>

              <Collapsible title="Available CSS Variables">
                <div slot="content" class="pt-2">
                  <p class="text-gray-500">
                    Here is a list of all the available CSS variables that you can use to customize your
                    theme.
                  </p>

                  <div class="mt-4 overflow-y-auto max-h-96">
                    <table class="w-full text-sm text-left">
                      <thead
                        class="text-xs text-gray-700 uppercase bg-gray-50 dark:bg-gray-700 dark:text-gray-400"
                      >
                        <tr>
                          <th scope="col" class="px-6 py-3"> Variable </th>
                          <th scope="col" class="px-6 py-3"> Default Value </th>
                          <th scope="col" class="px-6 py-3"> Description </th>
                        </tr>
                      </thead>
                      <tbody>
                        {#each variables as variable}
                          <tr class="bg-white border-b dark:bg-gray-800 dark:border-gray-700">
                            <td class="px-6 py-4 font-mono"> {variable.name} </td>
                            <td class="px-6 py-4 font-mono"> {variable.defaultValue} </td>
                            <td class="px-6 py-4"> {variable.description} </td>
                          </tr>
                        {/each}
                      </tbody>
                    </table>
                  </div>
                </div>
              </Collapsible>
            </div>
          {/if}
        </div>
      {:else}
        <div class="mt-4 rounded-lg overflow-hidden">
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
