<script lang="ts">
	import { getContext } from 'svelte';
	import type { Theme } from '$lib/types';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import EmojiPicker from '$lib/components/common/EmojiPicker.svelte';

	export let themeCopy: Theme;

	import { createEventDispatcher } from 'svelte';
	const dispatch = createEventDispatcher();
	const i18n = getContext('i18n');

	const handleBaseThemeChange = () => {
		dispatch('update', { ...themeCopy });
	};

	const handleCodeMirrorThemeChange = () => {
		dispatch('update', { ...themeCopy });
	};
</script>

<div class="grid grid-cols-2 gap-4">
	<div>
		<label for="theme-name" class="block text-sm font-medium text-gray-700 dark:text-gray-300"
			>{$i18n.t('Name')}</label
		>
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
		<label
			for="theme-description"
			class="block text-sm font-medium text-gray-700 dark:text-gray-300"
			>{$i18n.t('Description')}</label
		>
		<Tooltip content="A brief description of the theme.">
			<input
				type="text"
				id="theme-description"
				class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-none mt-1"
				bind:value={themeCopy.description}
			/>
		</Tooltip>
	</div>
	<div>
		<label for="theme-author" class="block text-sm font-medium text-gray-700 dark:text-gray-300"
			>{$i18n.t('Author')}</label
		>
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
		<label for="theme-meta-color" class="block text-sm font-medium text-gray-700 dark:text-gray-300"
			>{$i18n.t('Meta Theme Color')}</label
		>
		<Tooltip
			content="The color used by the browser for the UI around the webpage. Affects the color of the status bar on mobile browsers."
		>
			<input
				type="text"
				id="theme-meta-color"
				class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-none mt-1"
				bind:value={themeCopy.metaThemeColor}
			/>
		</Tooltip>
	</div>
	<div>
		<label for="theme-version" class="block text-sm font-medium text-gray-700 dark:text-gray-300"
			>{$i18n.t('Theme Version')}</label
		>
		<Tooltip
			content="The version of the theme, preferably in semantic versioning format (e.g., 1.0.0)."
		>
			<input
				type="text"
				id="theme-version"
				class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-none mt-1"
				bind:value={themeCopy.version}
			/>
		</Tooltip>
	</div>
	<div>
		<label for="theme-version" class="block text-sm font-medium text-gray-700 dark:text-gray-300"
			>{$i18n.t('Target WebUI Version')}</label
		>
		<Tooltip
			content="The version of Open WebUI that this theme was designed for. Helps to warn users about potential incompatibilities."
		>
			<input
				type="text"
				id="theme-target-version"
				class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-none mt-1"
				bind:value={themeCopy.targetWebUIVersion}
			/>
		</Tooltip>
	</div>
	<div>
		<label for="theme-base" class="block text-sm font-medium text-gray-700 dark:text-gray-300"
			>{$i18n.t('Base Theme')}</label
		>
		<Tooltip
			content="The base theme to inherit styles from. Your theme will be applied on top of this."
		>
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
		<label for="theme-codemirror" class="block text-sm font-medium text-gray-700 dark:text-gray-300"
			>{$i18n.t('CodeMirror Theme')}</label
		>
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
		<label for="theme-repo" class="block text-sm font-medium text-gray-700 dark:text-gray-300"
			>{$i18n.t('Repository URL')}</label
		>
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
		<label for="theme-update-url" class="block text-sm font-medium text-gray-700 dark:text-gray-300"
			>{$i18n.t('Theme Update URL')}</label
		>
		<Tooltip content="The URL to a raw JSON file for theme updates.">
			<input
				type="text"
				id="theme-update-url"
				class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-none mt-1"
				bind:value={themeCopy.sourceUrl}
			/>
		</Tooltip>
	</div>
	<div>
		<label for="theme-emoji" class="block text-sm font-medium text-gray-700 dark:text-gray-300"
			>{$i18n.t('Emoji')}</label
		>
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
