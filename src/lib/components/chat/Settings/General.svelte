<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { createEventDispatcher, onMount, getContext } from 'svelte';
	import { getLanguages, changeLanguage } from '$lib/i18n';
	const dispatch = createEventDispatcher();

	import { models, settings, theme, user } from '$lib/stores';

	const i18n = getContext('i18n');

	import AdvancedParams from './Advanced/AdvancedParams.svelte';
	import Textarea from '$lib/components/common/Textarea.svelte';
	export let saveSettings: Function;
	export let getModels: Function;

	// General
	let themes = ['dark', 'light', 'oled-dark', 'mai-professional', 'mai-creative', 'mai-minimalist', 'mai-warm'];
	let selectedTheme = 'system';

	let languages: Awaited<ReturnType<typeof getLanguages>> = [];
	let lang = $i18n.language;
	let notificationEnabled = false;
	let system = '';

	// Background pattern settings
	let backgroundPattern = 'none';
	let backgroundOpacity = 5;

	let showAdvanced = false;

	const toggleNotification = async () => {
		const permission = await Notification.requestPermission();

		if (permission === 'granted') {
			notificationEnabled = !notificationEnabled;
			saveSettings({ notificationEnabled: notificationEnabled });
		} else {
			toast.error(
				$i18n.t(
					'Response notifications cannot be activated as the website permissions have been denied. Please visit your browser settings to grant the necessary access.'
				)
			);
		}
	};

	let params = {
		// Advanced
		stream_response: null,
		function_calling: null,
		seed: null,
		temperature: null,
		reasoning_effort: null,
		logit_bias: null,
		frequency_penalty: null,
		presence_penalty: null,
		repeat_penalty: null,
		repeat_last_n: null,
		mirostat: null,
		mirostat_eta: null,
		mirostat_tau: null,
		top_k: null,
		top_p: null,
		min_p: null,
		stop: null,
		tfs_z: null,
		num_ctx: null,
		num_batch: null,
		num_keep: null,
		max_tokens: null,
		num_gpu: null
	};

	// Background pattern variables are initialized in onMount and updated on save

	const saveHandler = async () => {
		saveSettings({
			system: system !== '' ? system : undefined,
			backgroundPattern: backgroundPattern,
			backgroundOpacity: backgroundOpacity,
			params: {
				stream_response: params.stream_response !== null ? params.stream_response : undefined,
				function_calling: params.function_calling !== null ? params.function_calling : undefined,
				seed: (params.seed !== null ? params.seed : undefined) ?? undefined,
				stop: params.stop ? params.stop.split(',').filter((e) => e) : undefined,
				temperature: params.temperature !== null ? params.temperature : undefined,
				reasoning_effort: params.reasoning_effort !== null ? params.reasoning_effort : undefined,
				logit_bias: params.logit_bias !== null ? params.logit_bias : undefined,
				frequency_penalty: params.frequency_penalty !== null ? params.frequency_penalty : undefined,
				presence_penalty: params.frequency_penalty !== null ? params.frequency_penalty : undefined,
				repeat_penalty: params.frequency_penalty !== null ? params.frequency_penalty : undefined,
				repeat_last_n: params.repeat_last_n !== null ? params.repeat_last_n : undefined,
				mirostat: params.mirostat !== null ? params.mirostat : undefined,
				mirostat_eta: params.mirostat_eta !== null ? params.mirostat_eta : undefined,
				mirostat_tau: params.mirostat_tau !== null ? params.mirostat_tau : undefined,
				top_k: params.top_k !== null ? params.top_k : undefined,
				top_p: params.top_p !== null ? params.top_p : undefined,
				min_p: params.min_p !== null ? params.min_p : undefined,
				tfs_z: params.tfs_z !== null ? params.tfs_z : undefined,
				num_ctx: params.num_ctx !== null ? params.num_ctx : undefined,
				num_batch: params.num_batch !== null ? params.num_batch : undefined,
				num_keep: params.num_keep !== null ? params.num_keep : undefined,
				max_tokens: params.max_tokens !== null ? params.max_tokens : undefined,
				use_mmap: params.use_mmap !== null ? params.use_mmap : undefined,
				use_mlock: params.use_mlock !== null ? params.use_mlock : undefined,
				num_thread: params.num_thread !== null ? params.num_thread : undefined,
				num_gpu: params.num_gpu !== null ? params.num_gpu : undefined,
				think: params.think !== null ? params.think : undefined,
				keep_alive: params.keep_alive !== null ? params.keep_alive : undefined,
				format: params.format !== null ? params.format : undefined
			}
		});
		dispatch('save');
	};

	onMount(async () => {
		// Migrate deprecated themes
		let currentTheme = localStorage.theme ?? 'system';
		if (currentTheme === 'dark') {
			currentTheme = 'oled-dark';
			localStorage.setItem('theme', currentTheme);
		} else if (currentTheme === 'light') {
			currentTheme = 'mai-minimalist';
			localStorage.setItem('theme', currentTheme);
		}
		selectedTheme = currentTheme;

		languages = await getLanguages();

		notificationEnabled = $settings.notificationEnabled ?? false;
		system = $settings.system ?? '';

		// Load background pattern settings
		backgroundPattern = $settings.backgroundPattern || 'none';
		backgroundOpacity = $settings.backgroundOpacity || 5;

		params = { ...params, ...$settings.params };
		params.stop = $settings?.params?.stop ? ($settings?.params?.stop ?? []).join(',') : null;
	});

	const applyTheme = (_theme: string) => {
		let themeToApply = _theme === 'oled-dark' ? 'dark' : _theme;

		if (_theme === 'system') {
			themeToApply = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
		}

		// Handle mAI custom themes
		if (_theme.startsWith('mai-')) {
			themeToApply = _theme.includes('minimalist') ? 'light' : 'dark';
		}

		if (themeToApply === 'dark' && !_theme.includes('oled')) {
			document.documentElement.style.setProperty('--color-gray-800', '#333');
			document.documentElement.style.setProperty('--color-gray-850', '#262626');
			document.documentElement.style.setProperty('--color-gray-900', '#171717');
			document.documentElement.style.setProperty('--color-gray-950', '#0d0d0d');
		}

		themes
			.filter((e) => e !== themeToApply)
			.forEach((e) => {
				e.split(' ').forEach((e) => {
					document.documentElement.classList.remove(e);
				});
			});

		themeToApply.split(' ').forEach((e) => {
			document.documentElement.classList.add(e);
		});

		// Apply custom mAI theme styles
		if (_theme === 'mai-professional') {
			// Deep Navy Corporate Theme - Professional, authoritative, trustworthy
			document.documentElement.style.setProperty('--color-gray-800', '#1e293b');
			document.documentElement.style.setProperty('--color-gray-850', '#0f172a');
			document.documentElement.style.setProperty('--color-gray-900', '#020617');
			document.documentElement.style.setProperty('--color-gray-950', '#020617');
			document.documentElement.style.setProperty('--color-primary', '#2563eb');  // Professional blue
			document.documentElement.style.setProperty('--color-secondary', '#475569'); // Steel gray
			document.documentElement.style.setProperty('--color-accent', '#06b6d4');   // Cyan highlights
		} else if (_theme === 'mai-creative') {
			// Vibrant Purple Creative Theme - Imaginative, energetic, innovative
			document.documentElement.style.setProperty('--color-gray-800', '#2d1b69');  // Deep purple base
			document.documentElement.style.setProperty('--color-gray-850', '#1e1065');  // Deeper purple
			document.documentElement.style.setProperty('--color-gray-900', '#0f0a2e');  // Almost black purple
			document.documentElement.style.setProperty('--color-gray-950', '#0f0a2e');
			document.documentElement.style.setProperty('--color-primary', '#a855f7');  // Vibrant purple
			document.documentElement.style.setProperty('--color-secondary', '#ec4899'); // Hot pink
			document.documentElement.style.setProperty('--color-accent', '#06b6d4');   // Electric cyan
		} else if (_theme === 'mai-minimalist') {
			// Ultra-clean Monochrome Theme - Pure, focused, distraction-free
			document.documentElement.style.setProperty('--color-gray-50', '#ffffff');   // Pure white
			document.documentElement.style.setProperty('--color-gray-100', '#f8f9fa');  // Off-white
			document.documentElement.style.setProperty('--color-gray-200', '#e9ecef');  // Light gray
			document.documentElement.style.setProperty('--color-gray-300', '#dee2e6');  // Slightly darker
			document.documentElement.style.setProperty('--color-gray-400', '#ced4da');  // Medium gray
			document.documentElement.style.setProperty('--color-gray-500', '#6c757d');  // Neutral gray
			document.documentElement.style.setProperty('--color-gray-600', '#495057');  // Dark gray
			document.documentElement.style.setProperty('--color-gray-700', '#343a40');  // Very dark gray
			document.documentElement.style.setProperty('--color-primary', '#212529');  // Near black
			document.documentElement.style.setProperty('--color-secondary', '#6c757d'); // Neutral gray
			document.documentElement.style.setProperty('--color-accent', '#495057');   // Dark gray accent
		} else if (_theme === 'mai-warm') {
			// Cozy Amber Theme - Comfortable, inviting, human-centered
			document.documentElement.style.setProperty('--color-gray-800', '#451a03');  // Deep amber brown
			document.documentElement.style.setProperty('--color-gray-850', '#292524');  // Rich brown
			document.documentElement.style.setProperty('--color-gray-900', '#1c1917');  // Dark brown
			document.documentElement.style.setProperty('--color-gray-950', '#0c0a09');  // Almost black brown
			document.documentElement.style.setProperty('--color-primary', '#f59e0b');  // Warm amber
			document.documentElement.style.setProperty('--color-secondary', '#ea580c'); // Deep orange
			document.documentElement.style.setProperty('--color-accent', '#dc2626');   // Warm red
		}

		const metaThemeColor = document.querySelector('meta[name="theme-color"]');
		if (metaThemeColor) {
			if (_theme.includes('system')) {
				const systemTheme = window.matchMedia('(prefers-color-scheme: dark)').matches
					? 'dark'
					: 'light';
				console.log('Setting system meta theme color: ' + systemTheme);
				metaThemeColor.setAttribute('content', systemTheme === 'light' ? '#ffffff' : '#171717');
			} else {
				console.log('Setting meta theme color: ' + _theme);
				metaThemeColor.setAttribute(
					'content',
					_theme === 'oled-dark'
						? '#000000'
						: _theme === 'mai-professional'
							? '#020617'
							: _theme === 'mai-creative'
								? '#0f0a2e'
								: _theme === 'mai-minimalist'
									? '#ffffff'
									: _theme === 'mai-warm'
										? '#0c0a09'
										: '#ffffff'
				);
			}
		}

		if (typeof window !== 'undefined' && window.applyTheme) {
			window.applyTheme();
		}

		if (_theme.includes('oled')) {
			document.documentElement.style.setProperty('--color-gray-800', '#101010');
			document.documentElement.style.setProperty('--color-gray-850', '#050505');
			document.documentElement.style.setProperty('--color-gray-900', '#000000');
			document.documentElement.style.setProperty('--color-gray-950', '#000000');
			document.documentElement.classList.add('dark');
		}

		console.log(_theme);
	};

	const themeChangeHandler = (_theme: string) => {
		theme.set(_theme);
		localStorage.setItem('theme', _theme);
		applyTheme(_theme);
	};
</script>

<div class="flex flex-col h-full justify-between text-sm" id="tab-general">
	<div class="  overflow-y-scroll max-h-[28rem] lg:max-h-full">
		<div class="">
			<div class=" mb-1 text-sm font-medium">{$i18n.t('WebUI Settings')}</div>

			<div class="w-full">
				<div class="mb-3 text-xs font-medium">{$i18n.t('Theme')}</div>
				<div class="grid grid-cols-2 gap-2">
					{#each [
						{ value: 'system', label: 'System', emoji: '⚙️', colors: ['#f3f4f6', '#1f2937'] },
						{ value: 'oled-dark', label: 'OLED Dark', emoji: '🌃', colors: ['#000000', '#050505'] },
						{ value: 'mai-professional', label: 'mAI Professional', emoji: '💼', colors: ['#020617', '#1e293b'] },
						{ value: 'mai-creative', label: 'mAI Creative', emoji: '🎨', colors: ['#0f0a2e', '#2d1b69'] },
						{ value: 'mai-minimalist', label: 'mAI Minimalist', emoji: '⚡', colors: ['#ffffff', '#f8f9fa'] },
						{ value: 'mai-warm', label: 'mAI Warm', emoji: '🔥', colors: ['#0c0a09', '#451a03'] }
					] as themeOption}
						<button
							class="theme-card flex items-center p-2 rounded-lg border-2 transition-all duration-200 hover:shadow-md {selectedTheme === themeOption.value 
								? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20' 
								: 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'}"
							on:click={() => {
								selectedTheme = themeOption.value;
								themeChangeHandler(selectedTheme);
							}}
						>
							<div class="flex items-center space-x-2 flex-1">
								<div class="flex space-x-1">
									<div 
										class="w-4 h-4 rounded-full border border-gray-300 dark:border-gray-600" 
										style="background-color: {themeOption.colors[0]}"
									></div>
									<div 
										class="w-4 h-4 rounded-full border border-gray-300 dark:border-gray-600" 
										style="background-color: {themeOption.colors[1]}"
									></div>
								</div>
								<div class="flex-1 text-left">
									<div class="text-xs font-medium text-gray-900 dark:text-gray-100">
										{themeOption.emoji} {themeOption.label}
									</div>
								</div>
							</div>
							{#if selectedTheme === themeOption.value}
								<div class="text-blue-500 text-xs">✓</div>
							{/if}
						</button>
					{/each}
				</div>
			</div>

			<div class=" flex w-full justify-between">
				<div class=" self-center text-xs font-medium">{$i18n.t('Language')}</div>
				<div class="flex items-center relative">
					<select
						class="dark:bg-gray-900 w-fit pr-8 rounded-sm py-2 px-2 text-xs bg-transparent text-right {$settings.highContrastMode
							? ''
							: 'outline-hidden'}"
						bind:value={lang}
						placeholder="Select a language"
						on:change={(e) => {
							changeLanguage(lang);
						}}
					>
						{#each languages as language}
							<option value={language['code']}>{language['title']}</option>
						{/each}
					</select>
				</div>
			</div>
			{#if $i18n.language === 'en-US'}
				<div class="mb-2 text-xs text-gray-400 dark:text-gray-500">
					Couldn't find your language?
					<a
						class=" text-gray-300 font-medium underline"
						href="https://github.com/open-webui/open-webui/blob/main/docs/CONTRIBUTING.md#-translations-and-internationalization"
						target="_blank"
					>
						Help us translate Open WebUI!
					</a>
				</div>
			{/if}

			<div>
				<div class=" py-0.5 flex w-full justify-between">
					<div class=" self-center text-xs font-medium">{$i18n.t('Notifications')}</div>

					<button
						class="p-1 px-3 text-xs flex rounded-sm transition"
						on:click={() => {
							toggleNotification();
						}}
						type="button"
					>
						{#if notificationEnabled === true}
							<span class="ml-2 self-center">{$i18n.t('On')}</span>
						{:else}
							<span class="ml-2 self-center">{$i18n.t('Off')}</span>
						{/if}
					</button>
				</div>
			</div>

			<!-- Background Pattern Settings -->
			<div class="mt-4">
				<div class="mb-3 text-xs font-medium">{$i18n.t('Background Pattern')}</div>
				
				<!-- Pattern Type -->
				<div class="mb-3">
					<div class="flex w-full justify-between items-center">
						<div class="self-center text-xs font-medium">{$i18n.t('Pattern Type')}</div>
						<select
							bind:value={backgroundPattern}
							class="w-fit pr-8 rounded-sm py-1 px-2 text-xs bg-transparent text-right {$settings.highContrastMode
								? 'border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800'
								: 'dark:bg-gray-900 outline-hidden'}"
						>
							<option value="none">{$i18n.t('None')}</option>
							<option value="dots">{$i18n.t('Dots')}</option>
							<option value="grid">{$i18n.t('Grid')}</option>
							<option value="diagonal">{$i18n.t('Diagonal')}</option>
						</select>
					</div>
				</div>

				<!-- Pattern Opacity -->
				<div class="mb-3">
					<div class="flex w-full justify-between items-center">
						<div class="self-center text-xs font-medium">{$i18n.t('Pattern Opacity')}</div>
						<div class="flex items-center space-x-2">
							<input
								type="range"
								min="0"
								max="100"
								bind:value={backgroundOpacity}
								class="w-20 h-1 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer"
							/>
							<span class="text-xs text-gray-600 dark:text-gray-400 w-8">{backgroundOpacity}%</span>
						</div>
					</div>
				</div>
			</div>
		</div>

		{#if $user?.role === 'admin' || ($user?.permissions.chat?.system_prompt ?? true)}
			<hr class="border-gray-50 dark:border-gray-850 my-3" />

			<div>
				<div class=" my-2.5 text-sm font-medium">{$i18n.t('System Prompt')}</div>
				<Textarea
					bind:value={system}
					className={'w-full text-sm outline-hidden resize-vertical' +
						($settings.highContrastMode
							? ' p-2.5 border-2 border-gray-300 dark:border-gray-700 rounded-lg bg-gray-50 dark:bg-gray-850 text-gray-900 dark:text-gray-100 focus:ring-1 focus:ring-blue-500 focus:border-blue-500 overflow-y-hidden'
							: ' bg-white dark:text-gray-300 dark:bg-gray-900')}
					rows="4"
					placeholder={$i18n.t('Enter system prompt here')}
				/>
			</div>
		{/if}

		{#if $user?.role === 'admin' || ($user?.permissions.chat?.controls ?? true)}
			<div class="mt-2 space-y-3 pr-1.5">
				<div class="flex justify-between items-center text-sm">
					<div class="  font-medium">{$i18n.t('Advanced Parameters')}</div>
					<button
						class=" text-xs font-medium text-gray-500"
						type="button"
						on:click={() => {
							showAdvanced = !showAdvanced;
						}}>{showAdvanced ? $i18n.t('Hide') : $i18n.t('Show')}</button
					>
				</div>

				{#if showAdvanced}
					<AdvancedParams admin={$user?.role === 'admin'} bind:params />
				{/if}
			</div>
		{/if}
	</div>

	<div class="flex justify-end pt-3 text-sm font-medium">
		<button
			class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full"
			on:click={() => {
				saveHandler();
			}}
		>
			{$i18n.t('Save')}
		</button>
	</div>
</div>
