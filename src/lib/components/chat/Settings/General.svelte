<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { createEventDispatcher, onMount, getContext } from 'svelte';
	import { getLanguages, changeLanguage } from '$lib/i18n';
	const dispatch = createEventDispatcher();

	import { models, settings, theme, user } from '$lib/stores';
	import type { Settings } from '$lib/stores';

	import type { i18n as i18nType } from 'i18next';
	import type { Writable } from 'svelte/store';

	const i18n = getContext<Writable<i18nType>>('i18n');
	let i18nInstance: i18nType | undefined;
	let i18nReady = false;

	// Subscribe to i18n store and check initialization
	$: if ($i18n) {
		i18nInstance = $i18n;
		i18nReady = i18nInstance?.isInitialized ?? false;
	}

	// Fallback translation function
	const t = (key: string, params?: Record<string, any>) => {
		try {
			return i18nInstance?.t?.(key, params) ?? key;
		} catch (e) {
			return key;
		}
	};

	import AdvancedParams from './Advanced/AdvancedParams.svelte';
	import Textarea from '$lib/components/common/Textarea.svelte';

	export let saveSettings: Function;
	export let getModels: Function;

	// General
	let themes = ['dark', 'light'];
	let selectedTheme = 'system';

	let languages: Awaited<ReturnType<typeof getLanguages>> = [];
	let lang = '';
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
				t(
					'Response notifications cannot be activated as the website permissions have been denied. Please visit your browser settings to grant the necessary access.'
				)
			);
		}
	};

	// Advanced
	let requestFormat = null;
	let keepAlive: string | null = null;

	type ParamValue = string | number | boolean | string[] | null;

	interface Params {
		[key: string]: ParamValue;
		stream_response: boolean | null;
		function_calling: string | null;
		seed: number | null;
		stop: string | null;
		temperature: number | null;
		reasoning_effort: number | null;
		frequency_penalty: number | null;
		presence_penalty: number | null;
		repeat_penalty: number | null;
		repeat_last_n: number | null;
		mirostat: number | null;
		mirostat_eta: number | null;
		mirostat_tau: number | null;
		top_k: number | null;
		top_p: number | null;
		min_p: number | null;
		tfs_z: number | null;
		num_ctx: number | null;
		num_batch: number | null;
		num_keep: number | null;
		max_tokens: number | null;
		use_mmap: boolean | null;
		use_mlock: boolean | null;
		num_thread: number | null;
		num_gpu: number | null;
		template: string | null;
	}

	let params: Params = {
		stream_response: null,
		function_calling: null,
		seed: null,
		stop: null,
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
		tfs_z: null,
		num_ctx: null,
		num_batch: null,
		num_keep: null,
		max_tokens: null,
		use_mmap: null,
		use_mlock: null,
		num_thread: null,
		num_gpu: null,
		template: null
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
		// Wait for i18n to initialize if needed
		if (!i18nReady && i18nInstance) {
			await new Promise<void>((resolve) => {
				const unsubscribe = i18n.subscribe((instance) => {
					if (instance?.isInitialized) {
						i18nReady = true;
						unsubscribe();
						resolve();
					}
				});
			});
		}

		selectedTheme = localStorage.theme ?? 'system';
		themeChangeHandler(selectedTheme);

		languages = await getLanguages();
		lang = i18nInstance?.language ?? 'en';

		notificationEnabled = $settings.notificationEnabled ?? false;
		system = $settings.system ?? '';

		requestFormat = $settings.requestFormat ?? null;
		if (requestFormat !== null && requestFormat !== 'json') {
			requestFormat =
				typeof requestFormat === 'object' ? JSON.stringify(requestFormat, null, 2) : requestFormat;
		}

		keepAlive = $settings.keepAlive ?? null;

		if ($settings.params) {
			const newParams = { ...params };
			Object.entries($settings.params).forEach(([key, value]) => {
				if (key === 'stop' && Array.isArray(value)) {
					newParams[key] = value.join(',');
				} else if (key in newParams) {
					newParams[key] = value;
				}
			});
			params = newParams as unknown as Params;
		}
	});

	const applyTheme = (_theme: string) => {
		let themeToApply = _theme === 'oled-dark' ? 'dark' : _theme;

		if (_theme === 'system') {
			themeToApply = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
		}

		if (themeToApply === 'dark' && !_theme.includes('oled')) {
			document.documentElement.style.setProperty('--color-gray-800', '#333');
			document.documentElement.style.setProperty('--color-gray-850', '#262626');
			document.documentElement.style.setProperty('--color-gray-900', '#161616');
			document.documentElement.style.setProperty('--color-gray-950', '#0d0d0d');
		}

		document.documentElement.setAttribute('theme', themeToApply);

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

	const saveParams = () => {
		const savedParams: Record<string, any> = {};
		Object.entries(params).forEach(([key, value]) => {
			if (value !== null) {
				if (key === 'stop' && typeof value === 'string') {
					savedParams[key] = value.split(',').filter(Boolean);
				} else {
					savedParams[key] = value;
				}
			}
		});
		return savedParams;
	};
</script>

	<div class="flex flex-col h-full justify-between text-sm">
		<div class="  overflow-y-scroll max-h-[28rem] lg:max-h-full">
			<div class="">
				<div class=" mb-1 text-sm font-medium">{i18nInstance?.t('WebUI Settings')}</div>

				<!-- https://linear.app/albert-conversation/issue/ALB-149/desactiver-totalement-le-theme-dark-dans-openwebui-le-temps-de-fixer -->
				<!-- <div class="flex w-full justify-between">
					<div class=" self-center text-xs font-medium">{i18nInstance?.t('Theme')}</div>
					<div class="flex items-center relative">
						<select
							class=" dark:bg-gray-900 w-fit pr-8 rounded-sm py-2 px-2 text-xs bg-transparent outline-hidden text-right"
							bind:value={selectedTheme}
							placeholder="Select a theme"
							on:change={() => themeChangeHandler(selectedTheme)}
						>
							<option value="system">⚙️ {i18nInstance?.t('System')}</option>
							<option value="dark">🌑 {i18nInstance?.t('Dark')}</option>
							<option value="light">☀️ {i18nInstance?.t('Light')}</option>
						</select>
					</div>
				</div> -->

				<div class=" flex w-full justify-between">
					<div class=" self-center text-xs font-medium">{i18nInstance?.t('Language')}</div>
					<div class="flex items-center relative">
						<select
							class=" dark:bg-gray-900 w-fit pr-8 rounded-sm py-2 px-2 text-xs bg-transparent outline-hidden text-right"
							bind:value={lang}
							placeholder="Select a language"
							on:change={async () => {
								await i18nInstance?.changeLanguage(lang);
							}}
						>
							{#each languages as language}
								<option value={language['code']}>{language['title']}</option>
							{/each}
						</select>
					</div>
				</div>
				{#if i18nInstance?.language === 'en-US'}
					<div class="mb-2 text-xs text-gray-400 dark:text-gray-500">
						{i18nInstance?.t("Couldn't find your language?")}
						<a
							class=" text-gray-300 font-medium underline"
							href="https://github.com/open-webui/open-webui/blob/main/docs/CONTRIBUTING.md#-translations-and-internationalization"
							target="_blank"
						>
							{i18nInstance?.t('Help us translate Open WebUI!')}
						</a>
					</div>
				{/if}

				<div>
					<div class=" py-0.5 flex w-full justify-between">
						<div class=" self-center text-xs font-medium">{i18nInstance?.t('Notifications')}</div>

						<button
							class="p-1 px-3 text-xs flex rounded-sm transition"
							on:click={() => {
								toggleNotification();
							}}
							type="button"
						>
							{#if notificationEnabled === true}
								<span class="ml-2 self-center">{i18nInstance?.t('On')}</span>
							{:else}
								<span class="ml-2 self-center">{i18nInstance?.t('Off')}</span>
							{/if}
						</button>
					</div>
				</div>
			</div>

			{#if $user?.role === 'admin' || $user?.permissions?.chat?.controls}
				<hr class="border-gray-100 dark:border-gray-850 my-3" />

				<div>
					<div class=" my-2.5 text-sm font-medium">{i18nInstance?.t('System Prompt')}</div>
					<textarea
						bind:value={system}
						class="w-full rounded-lg p-4 text-sm bg-white dark:text-gray-300 dark:bg-gray-850 outline-hidden resize-none"
						rows="4"
					/>
				</div>

				<div class="mt-2 space-y-3 pr-1.5">
					<div class="flex justify-between items-center text-sm">
						<div class="  font-medium">{i18nInstance?.t('Advanced Parameters')}</div>
						<button
							class=" text-xs font-medium text-gray-500"
							type="button"
							on:click={() => {
								showAdvanced = !showAdvanced;
							}}>{showAdvanced ? i18nInstance?.t('Hide') : i18nInstance?.t('Show')}</button
						>
					</div>

					{#if showAdvanced}
						<AdvancedParams admin={$user?.role === 'admin'} bind:params />
						<hr class=" border-gray-100 dark:border-gray-850" />

						<div class=" py-1 w-full justify-between">
							<div class="flex w-full justify-between">
								<div class=" self-center text-xs font-medium">{i18nInstance?.t('Keep Alive')}</div>

								<button
									class="p-1 px-3 text-xs flex rounded-sm transition"
									type="button"
									on:click={() => {
										keepAlive = keepAlive === null ? '5m' : null;
									}}
								>
									{#if keepAlive === null}
										<span class="ml-2 self-center"> {i18nInstance?.t('Default')} </span>
									{:else}
										<span class="ml-2 self-center"> {i18nInstance?.t('Custom')} </span>
									{/if}
								</button>
							</div>

							{#if keepAlive !== null}
								<div class="flex mt-1 space-x-2">
									<input
										class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-hidden"
										type="text"
										placeholder={i18nInstance?.t(
											"e.g. '30s','10m'. Valid time units are 's', 'm', 'h'."
										)}
										bind:value={keepAlive}
									/>
								</div>
							{/if}
						</div>

						<div>
							<div class=" py-1 flex w-full justify-between">
								<div class=" self-center text-sm font-medium">
									{i18nInstance?.t('Request Mode')}
								</div>

								<button
									class="p-1 px-3 text-xs flex rounded-sm transition"
									on:click={() => {
										toggleRequestFormat();
									}}
								>
									{#if requestFormat === ''}
										<span class="ml-2 self-center"> {i18nInstance?.t('Default')} </span>
									{:else if requestFormat === 'json'}
										<span class="ml-2 self-center"> {i18nInstance?.t('JSON')} </span>
									{/if}
								</button>
							</div>
						</div>
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
