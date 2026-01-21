<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { createEventDispatcher, onMount, getContext } from 'svelte';
	import { getLanguages, changeLanguage } from '$lib/i18n';
	const dispatch = createEventDispatcher();

	import { config, models, settings, theme, user } from '$lib/stores';

	const i18n = getContext('i18n');

	import AdvancedParams from './Advanced/AdvancedParams.svelte';
	import Textarea from '$lib/components/common/Textarea.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	export let saveSettings: Function;
	export let getModels: Function;

	// General
	let themes = ['dark', 'light'];
	let selectedTheme = 'system';

	let languages: Awaited<ReturnType<typeof getLanguages>> = [];
	let lang = $i18n.language;
	let notificationEnabled = false;
	let system = '';

	let showAdvanced = true;

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
		stream_delta_chunk_size: null,
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

	const saveHandler = async () => {
		saveSettings({
			system: system !== '' ? system : undefined,
			params: {
				stream_response: params.stream_response !== null ? params.stream_response : undefined,
				stream_delta_chunk_size:
					params.stream_delta_chunk_size !== null ? params.stream_delta_chunk_size : undefined,
				function_calling:
					params.function_calling === null
						? null
						: params.function_calling !== undefined
							? params.function_calling
							: undefined,
				seed: (params.seed !== null ? params.seed : undefined) ?? undefined,
				stop: params.stop ? params.stop.split(',').filter((e) => e) : undefined,
				temperature: params.temperature !== null ? params.temperature : undefined,
				reasoning_effort: params.reasoning_effort ? params.reasoning_effort : undefined,
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
		selectedTheme = localStorage.theme ?? 'system';

		languages = await getLanguages();

		notificationEnabled = $settings.notificationEnabled ?? false;
		system = $settings.system ?? '';

		params = { ...params, ...$settings.params };
		params.stop = $settings?.params?.stop ? ($settings?.params?.stop ?? []).join(',') : null;
	});

	const applyTheme = (_theme: string) => {
		let themeToApply = _theme;

		if (_theme === 'system') {
			themeToApply = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
		}

		if (themeToApply === 'dark') {
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
			if (_theme === 'system') {
				const systemTheme = window.matchMedia('(prefers-color-scheme: dark)').matches
					? 'dark'
					: 'light';
				console.log('Setting system meta theme color: ' + systemTheme);
				metaThemeColor.setAttribute('content', systemTheme === 'light' ? '#ffffff' : '#171717');
			} else {
				console.log('Setting meta theme color: ' + _theme);
				metaThemeColor.setAttribute('content', _theme === 'dark' ? '#171717' : '#ffffff');
			}
		}

		if (typeof window !== 'undefined' && window.applyTheme) {
			window.applyTheme();
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
	<div class="space-y-4 overflow-y-scroll scrollbar-hidden h-full pr-1">
		<!-- WebUI 设置卡片 -->
		<div class="bg-gray-50 dark:bg-gray-850 rounded-xl p-5 border border-gray-100 dark:border-gray-800">
			<div class="text-sm font-semibold text-gray-800 dark:text-gray-100 mb-4">
				{$i18n.t('WebUI Settings')}
			</div>

			<div class="space-y-3">
				<!-- 主题设置 -->
				<div class="flex items-center justify-between bg-white dark:bg-gray-900 rounded-lg px-4 py-3 border border-gray-100 dark:border-gray-800">
					<div class="text-sm font-medium text-gray-700 dark:text-gray-200">{$i18n.t('Theme')}</div>
					<select
						class="dark:bg-gray-800 w-fit pr-8 rounded-lg px-3 py-1.5 text-sm bg-gray-50 outline-none border border-gray-200 dark:border-gray-700 text-right cursor-pointer transition hover:border-gray-300 dark:hover:border-gray-600"
						bind:value={selectedTheme}
						placeholder={$i18n.t('Select a theme')}
						on:change={() => themeChangeHandler(selectedTheme)}
					>
						<option value="system">{$i18n.t('System')}</option>
						<option value="dark">{$i18n.t('Dark')}</option>
						<option value="light">{$i18n.t('Light')}</option>
					</select>
				</div>

				<!-- 语言设置 -->
				<div class="flex items-center justify-between bg-white dark:bg-gray-900 rounded-lg px-4 py-3 border border-gray-100 dark:border-gray-800">
					<div class="text-sm font-medium text-gray-700 dark:text-gray-200">{$i18n.t('Language')}</div>
					<select
						class="dark:bg-gray-800 rounded-lg px-3 py-1.5 text-sm bg-gray-50 outline-none border border-gray-200 dark:border-gray-700 cursor-pointer transition hover:border-gray-300 dark:hover:border-gray-600"
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

				{#if $i18n.language === 'en-US' && !($config?.license_metadata ?? false)}
					<div class="text-xs text-gray-500 dark:text-gray-400 px-1">
						Couldn't find your language?
						<a
							class="font-medium text-blue-500 hover:text-blue-600 dark:text-blue-400 dark:hover:text-blue-300 underline"
							href="https://github.com/open-webui/open-webui/blob/main/docs/CONTRIBUTING.md#-translations-and-internationalization"
							target="_blank"
						>
							Help us translate Open WebUI!
						</a>
					</div>
				{/if}

				<!-- 通知设置 -->
				<div class="flex items-center justify-between bg-white dark:bg-gray-900 rounded-lg px-4 py-3 border border-gray-100 dark:border-gray-800">
					<div class="text-sm font-medium text-gray-700 dark:text-gray-200">{$i18n.t('Notifications')}</div>
					<Switch
						bind:state={notificationEnabled}
						on:change={() => {
							toggleNotification();
						}}
					/>
				</div>
			</div>
		</div>

		{#if $user?.role === 'admin' || (($user?.permissions.chat?.controls ?? true) && ($user?.permissions.chat?.system_prompt ?? true))}
			<!-- 系统提示词卡片 -->
			<div class="bg-gray-50 dark:bg-gray-850 rounded-xl p-5 border border-gray-100 dark:border-gray-800">
				<div class="text-sm font-semibold text-gray-800 dark:text-gray-100 mb-4">
					{$i18n.t('System Prompt')}
				</div>

				<div class="bg-white dark:bg-gray-900 rounded-lg p-4 border border-gray-100 dark:border-gray-800">
					<Textarea
						bind:value={system}
						className={'w-full text-sm outline-none resize-vertical rounded-lg' +
							($settings.highContrastMode
								? ' p-2.5 border-2 border-gray-300 dark:border-gray-700 bg-transparent text-gray-900 dark:text-gray-100 focus:ring-1 focus:ring-blue-500 focus:border-blue-500 overflow-y-hidden'
								: ' dark:text-gray-300 bg-transparent')}
						rows="4"
						placeholder={$i18n.t('Enter system prompt here')}
					/>
				</div>
			</div>
		{/if}

		{#if $user?.role === 'admin' || (($user?.permissions.chat?.controls ?? true) && ($user?.permissions.chat?.params ?? true))}
			<!-- 高级参数卡片 -->
			<div class="bg-gray-50 dark:bg-gray-850 rounded-xl p-5 border border-gray-100 dark:border-gray-800">
				<div class="flex justify-between items-center mb-4">
					<div class="text-sm font-semibold text-gray-800 dark:text-gray-100">
						{$i18n.t('Advanced Parameters')}
					</div>
					<button
						class="text-xs font-medium px-3 py-1.5 rounded-lg transition {showAdvanced
							? 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-200'
							: 'bg-white dark:bg-gray-900 text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 border border-gray-200 dark:border-gray-700'}"
						type="button"
						on:click={() => {
							showAdvanced = !showAdvanced;
						}}
					>
						{showAdvanced ? $i18n.t('Hide') : $i18n.t('Show')}
					</button>
				</div>

				{#if showAdvanced}
					<div class="bg-white dark:bg-gray-900 rounded-lg p-4 border border-gray-100 dark:border-gray-800">
						<AdvancedParams admin={$user?.role === 'admin'} bind:params />
					</div>
				{/if}
			</div>
		{/if}
	</div>

	<div class="flex justify-end pt-4 text-sm font-medium">
		<button
			class="px-4 py-2 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full"
			on:click={() => {
				saveHandler();
			}}
		>
			{$i18n.t('Save')}
		</button>
	</div>
</div>
