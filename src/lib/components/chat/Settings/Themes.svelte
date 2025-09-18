<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { WEBUI_VERSION } from '$lib/constants';
	import {
		themes,
		communityThemes,
		addCommunityTheme,
		updateCommunityTheme,
		removeCommunityTheme,
		applyTheme,
		isNewerVersion,
		themeUpdates,
		themeUpdateErrors,
		updateCommunityThemeFromUrl,
		retryThemeUpdateCheck,
		checkForThemeUpdates
	} from '$lib/theme';
	import { settings, theme as themeStore } from '$lib/stores';
	import type { Theme } from '$lib/types';
	import XMark from '$lib/components/icons/XMark.svelte';
	import Download from '$lib/components/icons/Download.svelte';
	import DocumentArrowDown from '$lib/components/icons/DocumentArrowDown.svelte';
	import Clipboard from '$lib/components/icons/Clipboard.svelte';
	import Pencil from '$lib/components/icons/Pencil.svelte';
	import Share from '$lib/components/icons/Share.svelte';
	import ThemeEditorModal from '$lib/components/common/ThemeEditorModal.svelte';
	import ThemeImportWarningModal from '$lib/components/common/ThemeImportWarningModal.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import ChevronRight from '$lib/components/icons/ChevronRight.svelte';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import ChevronUp from '$lib/components/icons/ChevronUp.svelte';
	import ChevronUpDown from '$lib/components/icons/ChevronUpDown.svelte';
	import ArrowPath from '$lib/components/icons/ArrowPath.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import emojiGroups from '$lib/emoji-groups.json';
	import { config, user } from '$lib/stores';
	import variables from '$lib/themes/variables.json';
	import { validateTheme, isDuplicateTheme, isMismatchedVersion } from '$lib/utils/theme';

	const i18n = getContext('i18n');

	const defaultVariables = variables.reduce((acc, curr) => {
		acc[curr.name] = curr.defaultValue;
		return acc;
	}, {});

	let selectedThemeId = 'system';
	let themeUrl = '';
	let isLoading = false;
	let fileInput: HTMLInputElement;
	let showThemeEditor = false;
	let isEditingTheme = false;
	let selectedTheme: Theme | null = null;
	let showConfirmDialog = false;
	let themeToDeleteId = '';
	let searchQuery = '';
	let showThemeImportWarning = false;
	let themeToImport: Theme | null = null;
	let sortOrder = 'default';
	let previousThemeId = '';
	let isCheckingForUpdates = false;

	let showAnimationScriptWarning = false;
	let themeWithScriptToImport: { theme: Theme; source: string } | null = null;

	const handleCheckForUpdates = async () => {
		isCheckingForUpdates = true;
		await checkForThemeUpdates(true); // Pass true for manual check
		isCheckingForUpdates = false;
	};

	const getThemeToggles = (theme: Theme) => {
		const toggles = [];

		if (theme.toggles?.cssVariables && theme.variables && Object.keys(theme.variables).length > 0) {
			const hasCustomVariables = Object.keys(theme.variables).some((key) => {
				return defaultVariables[key] !== theme.variables[key];
			});
			if (hasCustomVariables) {
				toggles.push('CSS Variables');
			}
		}
		if (theme.toggles?.customCss && theme.css) {
			toggles.push('Custom CSS');
		}
		if (theme.toggles?.animationScript && theme.animationScript) {
			toggles.push('Animation Script');
		}
		if (
			theme.toggles?.tsParticles &&
			theme.tsparticlesConfig &&
			Object.keys(theme.tsparticlesConfig).length > 0
		) {
			toggles.push('tsParticles');
		}
		if (theme.toggles?.gradient) {
			toggles.push('System Gradient Background');
		}
		if (theme.toggles?.systemBackgroundImage && theme.systemBackgroundImageUrl) {
			toggles.push('System Background Image');
		}
		if (theme.toggles?.chatBackgroundImage && theme.chatBackgroundImageUrl) {
			toggles.push('Chat Background Image');
		}
		if (toggles.length > 0) {
			return `Active Toggles: ${toggles.join(', ')}`;
		}
		return '';
	};

	$: allThemes = new Map([...$themes, ...$communityThemes]);
	$: sortedThemes = (() => {
		const themes = [...allThemes.values()];
		if (sortOrder === 'default') {
			return themes;
		}
		return themes.sort((a, b) => {
			if (sortOrder === 'asc') {
				return a.name.localeCompare(b.name);
			} else {
				return b.name.localeCompare(a.name);
			}
		});
	})();
	$: filteredThemes = sortedThemes.filter(
		(theme) =>
			theme.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
			(theme.author && theme.author.toLowerCase().includes(searchQuery.toLowerCase()))
	);

	const themeChangeHandler = (_theme: string) => {
		selectedThemeId = _theme;
		themeStore.set(_theme);
		localStorage.setItem('theme', _theme);
	};

	onMount(() => {
		selectedThemeId = localStorage.theme ?? 'system';
	});

	const _finalizeAddTheme = (theme: Theme, source: string = ''): boolean => {
		// Version compatibility check
		const versionMismatch =
			theme.targetWebUIVersion && isMismatchedVersion(WEBUI_VERSION, theme.targetWebUIVersion);

		if (versionMismatch) {
			themeToImport = { ...theme, sourceUrl: source };
			showThemeImportWarning = true;
			return false;
		} else {
			if (source) {
				theme.sourceUrl = source;
			}
			const success = addCommunityTheme(theme);
			if (success) {
				toast.success($i18n.t('Theme "{{name}}" added successfully!', { name: theme.name }));
				themeUrl = ''; // Clear input on success
			}
			return success;
		}
	};

	const processAndAddTheme = (theme: any, source: string = ''): boolean => {
		const validation = validateTheme(theme);
		if (!validation.valid) {
			toast.error($i18n.t(validation.error ?? ''));
			return false;
		}

		if (isDuplicateTheme(theme, Array.from($communityThemes.values()), false)) {
			toast.error($i18n.t('This exact theme is already installed.'));
			return false;
		}

		// Security check for animation script
		if (theme.animationScript) {
			themeWithScriptToImport = { theme, source };
			showAnimationScriptWarning = true;
			return false;
		} else {
			return _finalizeAddTheme(theme, source);
		}
	};

	const addThemeHandler = async () => {
		if (!themeUrl) {
			toast.error($i18n.t('Please enter a theme URL.'));
			return;
		}

		isLoading = true;
		try {
			const res = await fetch(themeUrl);
			if (!res.ok) {
				throw new Error(`Failed to fetch theme: ${res.statusText}`);
			}
			const theme = await res.json();
			processAndAddTheme(theme, themeUrl);
		} catch (error) {
			console.error(`Failed to load theme from ${themeUrl}:`, error);
			toast.error(
				$i18n.t('Failed to load theme. Check the URL and browser console for more details.')
			);
		} finally {
			isLoading = false;
		}
	};

	const importThemeFromFile = (event: Event) => {
		const input = event.target as HTMLInputElement;
		if (!input.files || input.files.length === 0) {
			return;
		}
		const file = input.files[0];
		const reader = new FileReader();
		reader.onload = () => {
			try {
				const theme = JSON.parse(reader.result as string);
				processAndAddTheme(theme);
			} catch (e) {
				toast.error($i18n.t('Invalid JSON file.'));
				console.error(e);
			}
		};
		reader.readAsText(file);
		// Reset file input so the same file can be loaded again
		input.value = '';
	};

	const openThemeEditor = (theme: Theme) => {
		previousThemeId = selectedThemeId;
		selectedTheme = theme;
		isEditingTheme = true;
		showThemeEditor = true;
	};

	const getRandomEmoji = () => {
		const groups = Object.values(emojiGroups);
		const randomGroup = groups[Math.floor(Math.random() * groups.length)];
		const randomEmojiCode = randomGroup[Math.floor(Math.random() * randomGroup.length)];
		return String.fromCodePoint(...randomEmojiCode.split('-').map((code) => parseInt(code, 16)));
	};

	const createNewTheme = () => {
		previousThemeId = selectedThemeId;
		isEditingTheme = false;
		selectedTheme = {
			id: `theme-${crypto.randomUUID()}`,
			name: 'My Custom Theme',
			description: 'A custom theme created by me.',
			author: $user?.name ?? 'Me',
			version: '1.0.0',
			targetWebUIVersion: WEBUI_VERSION,
			base: 'dark',
			emoji: getRandomEmoji(),
			variables: variables.reduce((acc, curr) => {
				acc[curr.name] = curr.defaultValue;
				return acc;
			}, {}),
			css: ``,
			systemBackgroundImageUrl: '',
			systemBackgroundImageDarken: 75,
			chatBackgroundImageUrl: '',
			chatBackgroundImageDarken: 75,
			toggles: {
				cssVariables: false,
				customCss: false,
				animationScript: false,
				tsParticles: false,
				gradient: false,
				systemBackgroundImage: false,
				chatBackgroundImage: false
			}
		};
		showThemeEditor = true;
		applyTheme(selectedTheme, true);
	};

	const saveTheme = (e) => {
		const updatedTheme = e.detail;

		const validation = validateTheme(updatedTheme);
		if (!validation.valid) {
			toast.error($i18n.t(validation.error ?? ''));
			return;
		}

		if (
			isDuplicateTheme(
				updatedTheme,
				Array.from($communityThemes.values()),
				isEditingTheme,
				updatedTheme.id
			)
		) {
			toast.error($i18n.t('A theme with the same content already exists.'));
			return;
		}

		if (isEditingTheme) {
			if (updateCommunityTheme(updatedTheme)) {
				toast.success(
					$i18n.t('Theme "{{name}}" updated successfully!', { name: updatedTheme.name })
				);
				if (updatedTheme.id === selectedThemeId) {
					applyTheme(updatedTheme);
				}
				showThemeEditor = false;
			} else {
				applyTheme(previousThemeId);
			}
		} else {
			if (processAndAddTheme(updatedTheme)) {
				showThemeEditor = false;
				applyTheme(previousThemeId);
			} else {
				// Revert to the previous theme if adding the new theme fails
				// This can happen if the security warning is shown
				if (!showAnimationScriptWarning) {
					applyTheme(previousThemeId);
				}
			}
		}
	};

	const copyTheme = (theme: Theme) => {
		const themeJson = JSON.stringify(theme, null, 2);
		navigator.clipboard.writeText(themeJson);
		toast.success($i18n.t('Theme copied to clipboard!'));
	};

	const exportTheme = (theme: Theme) => {
		const themeJson = JSON.stringify(theme, null, 2);
		const blob = new Blob([themeJson], { type: 'application/json' });
		const url = URL.createObjectURL(blob);
		const a = document.createElement('a');
		a.href = url;
		a.download = `${theme.name}.json`;
		a.click();
		URL.revokeObjectURL(url);
	};
</script>

<div class="flex flex-col h-full justify-between text-sm">
	<div class="space-y-3">
		<div class="space-y-2">
			<div class="flex justify-between items-center">
				<div class="flex items-center self-center text-sm font-medium">
					{$i18n.t('Themes')}
					<div class="flex self-center w-[1px] h-4 mx-2 bg-gray-50 dark:bg-gray-850" />
					<span class="text-gray-500 dark:text-gray-300"
						>{$themes.size + $communityThemes.size}</span
					>
				</div>
				<div class="flex items-center gap-2">
					<div class="relative">
						<input
							type="text"
							bind:value={searchQuery}
							placeholder="Search themes..."
							class="w-full pl-8 pr-4 py-1.5 text-sm rounded-lg bg-gray-50 dark:bg-gray-850 outline-none"
						/>
						<div class="absolute inset-y-0 left-0 flex items-center pl-2">
							<svg
								xmlns="http://www.w3.org/2000/svg"
								viewBox="0 0 20 20"
								fill="currentColor"
								class="w-4 h-4 text-gray-500"
							>
								<path
									fill-rule="evenodd"
									d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z"
									clip-rule="evenodd"
								/>
							</svg>
						</div>
					</div>
					<Tooltip content="Check for Updates" placement="top">
						<button
							class="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800"
							on:click={handleCheckForUpdates}
							disabled={isCheckingForUpdates}
						>
							<ArrowPath class={`w-4 h-4 ${isCheckingForUpdates ? 'animate-spin' : ''}`} />
						</button>
					</Tooltip>
					<Tooltip
						content={sortOrder === 'default'
							? 'Sort Ascending'
							: sortOrder === 'asc'
								? 'Sort Descending'
								: 'Default Sort Order'}
						placement="top"
					>
						<button
							class="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800"
							on:click={() => {
								if (sortOrder === 'default') {
									sortOrder = 'asc';
								} else if (sortOrder === 'asc') {
									sortOrder = 'desc';
								} else {
									sortOrder = 'default';
								}
							}}
						>
							{#if sortOrder === 'default'}
								<ChevronUpDown class="w-4 h-4" />
							{:else if sortOrder === 'asc'}
								<ChevronUp class="w-4 h-4" />
							{:else}
								<ChevronDown class="w-4 h-4" />
							{/if}
						</button>
					</Tooltip>
				</div>
			</div>
			<div
				class="grid grid-cols-2 gap-2 overflow-y-auto max-h-[17rem] min-h-[14.5rem] content-start"
			>
				{#if filteredThemes.length}
					{#each filteredThemes as theme (theme.id)}
						{@const tooltipContent = $themes.has(theme.id) ? '' : getThemeToggles(theme)}
						<Tooltip
							content={tooltipContent}
							placement="top"
							disabled={!tooltipContent}
							className={`w-full rounded-lg transition group ${
								selectedThemeId === theme.id
									? 'bg-gray-100 dark:bg-gray-800'
									: 'hover:bg-gray-100 dark:hover:bg-gray-800'
							}`}
						>
							<button
								class="flex items-center p-2 w-full text-left"
								on:click={() => themeChangeHandler(theme.id)}
							>
								<span class="text-xl mr-2">{theme.emoji}</span>
								<div class="text-left overflow-hidden">
									<div class="flex items-center gap-1.5">
										<p
											class="font-medium leading-tight truncate"
											class:text-red-500={$themeUpdateErrors.has(theme.id)}
											title={theme.name}
										>
											{theme.name}
										</p>
									</div>
									{#if !$themes.has(theme.id)}
										<div class="text-xs text-gray-500 leading-tight truncate">
											<span>
												{#if theme.version}v{theme.version}{/if}
												{$i18n.t('by {{author}}', { author: theme.author ?? 'Unknown' })}
											</span>
											{#if $themeUpdates.has(theme.id)}
												<span class="text-green-500 font-medium">
													(v{$themeUpdates.get(theme.id).version} available)
												</span>
											{:else if $themeUpdateErrors.has(theme.id)}
												<span class="text-red-500 font-medium"> (Update Failed) </span>
											{/if}
										</div>
										{#if theme.description}
											<div class="text-xs text-gray-500 leading-tight truncate">
												{theme.description}
											</div>
										{/if}
									{/if}
								</div>

								{#if !$themes.has(theme.id)}
									<div class="ml-auto items-center flex">
										{#if $themeUpdateErrors.has(theme.id)}
											<Tooltip content="Retry Update Check" placement="top">
												<button
													class="p-1.5 text-gray-500 hover:text-blue-500 dark:hover:text-blue-400 transition rounded-full"
													on:click|stopPropagation={() => retryThemeUpdateCheck(theme)}
													aria-label={$i18n.t('Retry update check')}
												>
													<ArrowPath class="w-4 h-4" />
												</button>
											</Tooltip>
										{/if}
										{#if $themeUpdates.has(theme.id)}
											<Tooltip content="Update Theme" placement="top">
												<button
													class="p-1.5 text-gray-500 hover:text-green-500 dark:hover:text-green-400 transition rounded-full"
													on:click|stopPropagation={() => updateCommunityThemeFromUrl(theme)}
													aria-label={$i18n.t('Update theme')}
												>
													<Download class="w-4 h-4" />
												</button>
											</Tooltip>
										{/if}

										<div class="items-center hidden group-hover:flex">
											<Tooltip content="Copy Theme" placement="top">
												<button
													class="p-1.5 text-gray-500 hover:text-gray-900 dark:hover:text-white transition rounded-full"
													on:click|stopPropagation={() => copyTheme(theme)}
													aria-label={$i18n.t('Copy theme')}
												>
													<Clipboard className="w-4 h-4" />
												</button>
											</Tooltip>
											<Tooltip content="Edit Theme" placement="top">
												<button
													class="p-1.5 text-gray-500 hover:text-yellow-500 dark:hover:text-yellow-400 transition rounded-full"
													on:click|stopPropagation={() => openThemeEditor(theme)}
													aria-label={$i18n.t('Edit theme')}
												>
													<Pencil className="w-4 h-4" />
												</button>
											</Tooltip>
											<Tooltip content="Share Theme" placement="top">
												<button
													on:click={() => window.open('https://openwebui.com/', '_blank')}
													class="p-1.5 text-gray-500 hover:text-gray-900 dark:hover:text-white transition rounded-full"
													aria-label={$i18n.t('Share theme')}
												>
													<Share class="w-4 h-4" />
												</button>
											</Tooltip>
											<Tooltip content="Export Theme" placement="top">
												<button
													class="p-1.5 text-gray-500 hover:text-gray-900 dark:hover:text-white transition rounded-full"
													on:click|stopPropagation={() => exportTheme(theme)}
													aria-label={$i18n.t('Export theme')}
												>
													<DocumentArrowDown class="w-4 h-4" />
												</button>
											</Tooltip>
											<Tooltip content="Remove Theme" placement="top">
												<button
													class="p-1.5 text-gray-500 hover:text-red-500 dark:hover:text-red-400 transition rounded-full"
													on:click|stopPropagation={() => {
														themeToDeleteId = theme.id;
														showConfirmDialog = true;
													}}
													aria-label={$i18n.t('Remove theme')}
												>
													<svg
														xmlns="http://www.w3.org/2000/svg"
														viewBox="0 0 20 20"
														fill="currentColor"
														class="w-4 h-4"
													>
														<path
															fill-rule="evenodd"
															d="M8.75 1A2.75 2.75 0 006 3.75v.443c-.795.077-1.58.22-2.365.468a.75.75 0 10.23 1.482l.149-.022.841 10.518A2.75 2.75 0 007.596 19h4.807a2.75 2.75 0 002.742-2.53l.841-10.52.149.023a.75.75 0 00.23-1.482A41.03 41.03 0 0014 4.193v-.443A2.75 2.75 0 0011.25 1h-2.5zM10 4c.84 0 1.673.025 2.5.075V3.75c0-.69-.56-1.25-1.25-1.25h-2.5c-.69 0-1.25.56-1.25 1.25v.325C8.327 4.025 9.16 4 10 4zM8.58 7.72a.75.75 0 00-1.5.06l.3 7.5a.75.75 0 101.5-.06l-.3-7.5zm4.34.06a.75.75 0 10-1.5-.06l-.3 7.5a.75.75 0 101.5.06l.3-7.5z"
															clip-rule="evenodd"
														/>
													</svg>
												</button>
											</Tooltip>
										</div>
									</div>
								{/if}
							</button>
						</Tooltip>
					{/each}
				{:else}
					<div class="col-span-2 text-center text-gray-500 mt-4">
						{$i18n.t('No themes found.')}
					</div>
				{/if}
			</div>
		</div>

		<hr class="border-gray-50 dark:border-gray-850 my-3" />

		<div class="mb-3.5">
			<div class=" mb-2.5 text-sm font-medium">{$i18n.t('Import Community Theme')}</div>

			<div class="space-y-3">
				<p class="text-sm text-gray-500">
					{$i18n.t('Load a custom theme by providing a URL to a valid theme.json file.')}
				</p>

				<div class="flex items-center gap-2">
					<input
						type="url"
						class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-none"
						placeholder="https://example.com/theme.json"
						bind:value={themeUrl}
						disabled={isLoading}
					/>
					<button
						class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full disabled:opacity-50 whitespace-nowrap"
						on:click={addThemeHandler}
						disabled={isLoading}
					>
						{#if isLoading && !themeUrl}
							{$i18n.t('Loading...')}
						{:else}
							{$i18n.t('Add')}
						{/if}
					</button>
					<input
						type="file"
						accept=".json"
						class="hidden"
						bind:this={fileInput}
						on:change={importThemeFromFile}
					/>
					<button
						class="px-3.5 py-1.5 text-sm font-medium bg-gray-100 hover:bg-gray-200 text-black dark:bg-gray-800 dark:text-white dark:hover:bg-gray-700 transition rounded-full disabled:opacity-50 whitespace-nowrap"
						on:click={() => fileInput.click()}
						disabled={isLoading}
					>
						{$i18n.t('Import File')}
					</button>
					<button
						class="px-3.5 py-1.5 text-sm font-medium bg-gray-100 hover:bg-gray-200 text-black dark:bg-gray-800 dark:text-white dark:hover:bg-gray-700 transition rounded-full disabled:opacity-50 whitespace-nowrap"
						on:click={createNewTheme}
						disabled={isLoading}
					>
						{$i18n.t('Add Manually')}
					</button>
				</div>
			</div>
		</div>
	</div>

	{#if $config?.features.enable_community_sharing && ($user.role === 'admin' || $user.permissions.public_sharing)}
		<div class=" mb-1.5">
			<div class=" text-sm font-medium mb-1 line-clamp-1">
				{$i18n.t('Made by Open WebUI Community')}
			</div>

			<a
				class=" flex cursor-pointer items-center justify-between hover:bg-gray-50 dark:hover:bg-gray-850 w-full mb-2 px-3.5 py-1.5 rounded-xl transition"
				href="https://openwebui.com/"
				target="_blank"
			>
				<div class=" self-center">
					<div class=" font-semibold line-clamp-1">{$i18n.t('Discover Community-made Themes')}</div>
					<div class=" text-sm line-clamp-1">
						{$i18n.t('Discover, Download, & Explore')}
					</div>
				</div>

				<div>
					<div>
						<ChevronRight />
					</div>
				</div>
			</a>
		</div>
	{/if}
</div>

<ThemeImportWarningModal
	bind:show={showThemeImportWarning}
	themeName={themeToImport?.name ?? ''}
	themeVersion={themeToImport?.targetWebUIVersion ?? ''}
	webuiVersion={WEBUI_VERSION}
	on:confirm={() => {
		if (themeToImport) {
			addCommunityTheme(themeToImport);
			toast.success($i18n.t('Theme "{{name}}" added successfully!', { name: themeToImport.name }));
			themeUrl = ''; // Clear input on success
		}
		showThemeImportWarning = false;
		themeToImport = null;
	}}
	on:cancel={() => {
		showThemeImportWarning = false;
		themeToImport = null;
	}}
/>

<ConfirmDialog
	bind:show={showConfirmDialog}
	title={$i18n.t('Delete Theme')}
	message={$i18n.t('Are you sure you want to delete this theme?')}
	on:confirm={() => {
		removeCommunityTheme(themeToDeleteId);
		showConfirmDialog = false;
	}}
/>

<ConfirmDialog
	bind:show={showAnimationScriptWarning}
	title="Security Warning"
	on:confirm={() => {
		if (themeWithScriptToImport) {
			const success = _finalizeAddTheme(
				themeWithScriptToImport.theme,
				themeWithScriptToImport.source
			);
			if (showThemeEditor) {
				if (success) {
					showThemeEditor = false;
				}
				applyTheme(previousThemeId);
			}
		}
		showAnimationScriptWarning = false;
		themeWithScriptToImport = null;
	}}
	on:cancel={() => {
		showAnimationScriptWarning = false;
		themeWithScriptToImport = null;
	}}
>
	<div class="text-sm text-gray-500">
		<div class=" bg-yellow-500/20 text-yellow-700 dark:text-yellow-200 rounded-lg px-4 py-3">
			<div>{$i18n.t('Please carefully review the following warnings:')}</div>

			<ul class=" mt-1 list-disc pl-4 text-xs">
				<li>{$i18n.t('Animation scripts allow arbitrary code execution.')}</li>
				<li>{$i18n.t('Do not install themes from sources you do not fully trust.')}</li>
			</ul>
		</div>

		<div class="my-3">
			{$i18n.t(
				'I acknowledge that I have read and I understand the implications of my action. I am aware of the risks associated with executing arbitrary code and I have verified the trustworthiness of the source.'
			)}
		</div>
	</div>
</ConfirmDialog>

{#if showThemeEditor}
	<ThemeEditorModal
		theme={selectedTheme}
		bind:show={showThemeEditor}
		title={isEditingTheme ? 'Edit Theme' : 'Create New Theme'}
		isEditing={isEditingTheme}
		on:save={saveTheme}
		on:update={(e) => {
			selectedTheme = e.detail;
			applyTheme(e.detail, true);
		}}
		on:cancel={() => {
			showThemeEditor = false;
			applyTheme(previousThemeId);
		}}
	/>
{/if}
