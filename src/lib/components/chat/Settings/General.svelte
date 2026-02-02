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
	let themes = ['dark', 'light', 'rose-pine dark', 'rose-pine-dawn light', 'oled-dark'];
	let selectedTheme = 'system';

	let languages: Awaited<ReturnType<typeof getLanguages>> = [];
	let lang = $i18n.language;
	let notificationEnabled = false;
	let system = '';

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

	// Advanced
	let requestFormat = null;
	let keepAlive: string | null = null;

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

	const validateJSON = (json) => {
		try {
			const obj = JSON.parse(json);

			if (obj && typeof obj === 'object') {
				return true;
			}
		} catch (e) {}
		return false;
	};

	const toggleRequestFormat = async () => {
		if (requestFormat === null) {
			requestFormat = 'json';
		} else {
			requestFormat = null;
		}

		saveSettings({ requestFormat: requestFormat !== null ? requestFormat : undefined });
	};

	const saveHandler = async () => {
		if (requestFormat !== null && requestFormat !== 'json') {
			if (validateJSON(requestFormat) === false) {
				toast.error($i18n.t('Invalid JSON schema'));
				return;
			} else {
				requestFormat = JSON.parse(requestFormat);
			}
		}

		saveSettings({
			system: system !== '' ? system : undefined,
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
				num_gpu: params.num_gpu !== null ? params.num_gpu : undefined
			},
			keepAlive: keepAlive ? (isNaN(keepAlive) ? keepAlive : parseInt(keepAlive)) : undefined,
			requestFormat: requestFormat !== null ? requestFormat : undefined
		});
		dispatch('save');

		requestFormat =
			typeof requestFormat === 'object' ? JSON.stringify(requestFormat, null, 2) : requestFormat;
	};

	onMount(async () => {
		selectedTheme = localStorage.theme ?? 'system';

		languages = await getLanguages();

		notificationEnabled = $settings.notificationEnabled ?? false;
		system = $settings.system ?? '';

		requestFormat = $settings.requestFormat ?? null;
		if (requestFormat !== null && requestFormat !== 'json') {
			requestFormat =
				typeof requestFormat === 'object' ? JSON.stringify(requestFormat, null, 2) : requestFormat;
		}

		keepAlive = $settings.keepAlive ?? null;

		params = { ...params, ...$settings.params };
		params.stop = $settings?.params?.stop ? ($settings?.params?.stop ?? []).join(',') : null;
	});

	const applyTheme = (_theme: string) => {
		let themeToApply = _theme === 'oled-dark' ? 'dark' : _theme;

		if (_theme === 'system') {
			themeToApply = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
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
					_theme === 'dark'
						? '#171717'
						: _theme === 'oled-dark'
							? '#000000'
							: _theme === 'her'
								? '#983724'
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

<div class="flex flex-col h-full justify-between">
	<div class="space-y-6 overflow-y-auto">
		<!-- WebUI Settings Section -->
		<div class="space-y-4">
			<div>
				<h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-1">
					{$i18n.t('WebUI Settings')}
				</h3>
				<p class="text-sm text-gray-500 dark:text-gray-400">Customize your interface preferences</p>
			</div>

			<!-- Theme Setting -->
			<div class="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-4">
				<div class="flex items-center justify-between gap-4">
					<div class="flex-1">
						<div class="font-medium text-gray-800 dark:text-gray-200">
							{$i18n.t('Theme')}
						</div>
						<div class="text-xs text-gray-500 dark:text-gray-400 mt-1">
							Choose your preferred color theme
						</div>
					</div>
					<select
						class="px-4 py-2 text-sm bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-colors cursor-pointer hover:border-gray-300 dark:hover:border-gray-500"
						bind:value={selectedTheme}
						on:change={() => themeChangeHandler(selectedTheme)}
					>
						<option value="system">{$i18n.t('System')}</option>
						<option value="dark"> {$i18n.t('Dark')}</option>
						<option value="oled-dark"> {$i18n.t('OLED Dark')}</option>
						<option value="light"> {$i18n.t('Light')}</option>
						
					</select>
				</div>
			</div>

			<!-- Language Setting -->
			<div class="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-4 space-y-3">
				<div class="flex items-center justify-between">
					<div>
						<div class="text-sm font-medium text-gray-900 dark:text-white">
							{$i18n.t('Language')}
						</div>
						<div class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
							Select your preferred language
						</div>
					</div>
					<select
						class="bg-white dark:bg-gray-900 border border-gray-300 dark:border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all"
						bind:value={lang}
						on:change={(e) => {
							changeLanguage(lang);
						}}
					>
						{#each languages as language}
							<option value={language['code']}>{language['title']}</option>
						{/each}
					</select>
				</div>

				{#if $i18n.language === 'en-US'}
					<div
						class="text-xs text-gray-500 dark:text-gray-400 pt-2 border-t border-gray-200 dark:border-gray-700"
					>
						Couldn't find your language?
						<a
							class="text-blue-600 dark:text-blue-400 font-medium hover:underline"
							href="https://github.com/open-webui/open-webui/blob/main/docs/CONTRIBUTING.md#-translations-and-internationalization"
							target="_blank"
						>
							Help us translate Open WebUI!
						</a>
					</div>
				{/if}
			</div>

			<!-- Notifications Setting -->
			<div class="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-4">
				<div class="flex items-center justify-between">
					<div>
						<div class="text-sm font-medium text-gray-900 dark:text-white">
							{$i18n.t('Notifications')}
						</div>
						<div class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
							Enable browser notifications for responses
						</div>
					</div>
					<button
						class="relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 {notificationEnabled
							? 'bg-blue-600'
							: 'bg-gray-300 dark:bg-gray-700'}"
						on:click={() => {
							toggleNotification();
						}}
						type="button"
					>
						<span
							class="inline-block h-4 w-4 transform rounded-full bg-white transition-transform {notificationEnabled
								? 'translate-x-6'
								: 'translate-x-1'}"
						/>
					</button>
				</div>
			</div>
		</div>

		{#if $user?.role === 'admin' || $user?.permissions.chat?.controls}
			<!-- System Prompt Section -->
			<div class="space-y-4 pt-2">
				<div>
					<h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-1">
						{$i18n.t('System Prompt')}
					</h3>
					<p class="text-sm text-gray-500 dark:text-gray-400">
						Define default system behavior and instructions
					</p>
				</div>

				<div class="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-4">
					<Textarea
						bind:value={system}
						className="w-full text-sm bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 border border-gray-300 dark:border-gray-700 rounded-lg p-3 focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none resize-none transition-all"
						rows="4"
						placeholder={$i18n.t('Enter system prompt here')}
					/>
				</div>
			</div>

			<!-- Advanced Parameters Section -->
			<div class="space-y-4 pt-2">
				<div class="flex items-center justify-between">
					<div>
						<h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-1">
							{$i18n.t('Advanced Parameters')}
						</h3>
						<p class="text-sm text-gray-500 dark:text-gray-400">
							Fine-tune model behavior and performance
						</p>
					</div>
					<button
						class="text-sm font-medium text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 transition-colors"
						type="button"
						on:click={() => {
							showAdvanced = !showAdvanced;
						}}
					>
						{showAdvanced ? $i18n.t('Hide') : $i18n.t('Show')}
					</button>
				</div>

				{#if showAdvanced}
					<div class="space-y-4">
						<div class="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-4">
							<AdvancedParams admin={$user?.role === 'admin'} bind:params />
						</div>

						<!-- Keep Alive Setting -->
						<div class="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-4 space-y-3">
							<div class="flex items-center justify-between">
								<div>
									<div class="text-sm font-medium text-gray-900 dark:text-white">
										{$i18n.t('Keep Alive')}
									</div>
									<div class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
										Control model memory duration
									</div>
								</div>
								<button
									class="px-4 py-1.5 text-sm font-medium rounded-lg transition-colors {keepAlive ===
									null
										? 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300'
										: 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400'}"
									type="button"
									on:click={() => {
										keepAlive = keepAlive === null ? '5m' : null;
									}}
								>
									{keepAlive === null ? $i18n.t('Default') : $i18n.t('Custom')}
								</button>
							</div>

							{#if keepAlive !== null}
								<div class="pt-2 border-t border-gray-200 dark:border-gray-700">
									<input
										class="w-full px-3 py-2 text-sm bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 border border-gray-300 dark:border-gray-700 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all"
										type="text"
										placeholder={$i18n.t("e.g. '30s','10m'. Valid time units are 's', 'm', 'h'.")}
										bind:value={keepAlive}
									/>
								</div>
							{/if}
						</div>

						<!-- Request Mode Setting -->
						<div class="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-4 space-y-3">
							<div class="flex items-center justify-between">
								<div>
									<div class="text-sm font-medium text-gray-900 dark:text-white">
										{$i18n.t('Request Mode')}
									</div>
									<div class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
										Configure response format
									</div>
								</div>
								<button
									class="px-4 py-1.5 text-sm font-medium rounded-lg transition-colors {requestFormat ===
									null
										? 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300'
										: 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400'}"
									on:click={() => {
										toggleRequestFormat();
									}}
								>
									{requestFormat === null ? $i18n.t('Default') : $i18n.t('JSON')}
								</button>
							</div>

							{#if requestFormat !== null}
								<div class="pt-2 border-t border-gray-200 dark:border-gray-700">
									<Textarea
										className="w-full text-sm bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 border border-gray-300 dark:border-gray-700 rounded-lg p-3 focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none resize-none transition-all"
										placeholder={$i18n.t('e.g. "json" or a JSON schema')}
										bind:value={requestFormat}
										rows="3"
									/>
								</div>
							{/if}
						</div>
					</div>
				{/if}
			</div>
		{/if}
	</div>

	<!-- Save Button -->
	<div class="flex justify-end pt-6 border-t border-gray-200 dark:border-gray-700 mt-6">
		<button
			class="px-6 py-2.5 text-sm font-medium bg-orange-600 hover:bg-orange-700 text-white rounded-lg transition-colors shadow-sm hover:shadow-md focus:outline-none focus:ring-2 focus:ring-orange-500 focus:ring-offset-2"
			on:click={() => {
				saveHandler();
			}}
		>
			{$i18n.t('Save')}
		</button>
	</div>
</div>

<style>
	/* Custom scrollbar styling */
	::-webkit-scrollbar {
		width: 8px;
		height: 8px;
	}

	::-webkit-scrollbar-track {
		background: transparent;
	}

	::-webkit-scrollbar-thumb {
		background: rgba(156, 163, 175, 0.5);
		border-radius: 4px;
	}

	::-webkit-scrollbar-thumb:hover {
		background: rgba(156, 163, 175, 0.7);
	}

	:global(.dark) ::-webkit-scrollbar-thumb {
		background: rgba(75, 85, 99, 0.5);
	}

	:global(.dark) ::-webkit-scrollbar-thumb:hover {
		background: rgba(75, 85, 99, 0.7);
	}
</style>
