<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { createEventDispatcher, onMount, getContext } from 'svelte';
	import { getLanguages } from '$lib/i18n';
	const dispatch = createEventDispatcher();

	import { models, settings, theme, user, config } from '$lib/stores';
	import { onClickOutside } from '$lib/utils';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import { getVoices as _getVoices } from '$lib/apis/audio';
	import ManageModal from './Personalization/ManageModal.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import SystemIcon from '$lib/components/icons/SystemIcon.svelte';
	import DarkIcon from '$lib/components/icons/DarkIcon.svelte';
	import LightIcon from '$lib/components/icons/LightIcon.svelte';

	const i18n = getContext('i18n');

	import AdvancedParams from './Advanced/AdvancedParams.svelte';

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
	let requestFormat = '';
	let keepAlive: string | null = null;

	let params = {
		// Advanced
		stream_response: null,
		function_calling: null,
		seed: null,
		temperature: null,
		frequency_penalty: null,
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

	const toggleRequestFormat = async () => {
		if (requestFormat === '') {
			requestFormat = 'json';
		} else {
			requestFormat = '';
		}

		saveSettings({ requestFormat: requestFormat !== '' ? requestFormat : undefined });
	};

	onMount(async () => {
		selectedTheme = localStorage.theme ?? 'system';

		languages = await getLanguages();

		notificationEnabled = $settings.notificationEnabled ?? false;
		system = $settings.system ?? '';

		requestFormat = $settings.requestFormat ?? '';
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

		console.log(_theme);
	};

	const themeChangeHandler = (_theme: string) => {
		theme.set(_theme);
		localStorage.setItem('theme', _theme);
		if (_theme.includes('oled')) {
			document.documentElement.style.setProperty('--color-gray-800', '#101010');
			document.documentElement.style.setProperty('--color-gray-850', '#050505');
			document.documentElement.style.setProperty('--color-gray-900', '#000000');
			document.documentElement.style.setProperty('--color-gray-950', '#000000');
			document.documentElement.classList.add('dark');
		}
		applyTheme(_theme);
		selectedTheme = _theme;
	};
	let showLanguageDropdown = false;
	let languageDropdownRef;

	let selectedLanguage;

	$: selectedLanguage = languages?.find(item => item.code === lang);

	// Audio
	let conversationMode = false;
	let speechAutoSend = false;
	let responseAutoPlayback = false;
	let nonLocalVoices = false;

	let STTEngine = '';

	let voices = [];
	let voice = '';

	// Audio speed control
	let playbackRate = 1;

	const getVoices = async () => {
		if ($config.audio.tts.engine === '') {
			const getVoicesLoop = setInterval(async () => {
				voices = await speechSynthesis.getVoices();

				// do your loop
				if (voices.length > 0) {
					clearInterval(getVoicesLoop);
				}
			}, 100);
		} else {
			const res = await _getVoices(localStorage.token).catch((e) => {
				toast.error(`${e}`);
			});

			if (res) {
				console.log(res);
				voices = [...res.voices, {id: 'alloy', name: 'alloy'}];
			}
		}
	};
	

	onMount(async () => {
		playbackRate = $settings.audio?.tts?.playbackRate ?? 1;
		conversationMode = $settings.conversationMode ?? false;
		speechAutoSend = $settings.speechAutoSend ?? false;
		responseAutoPlayback = $settings.responseAutoPlayback ?? false;

		STTEngine = $settings?.audio?.stt?.engine ?? '';

		if ($settings?.audio?.tts?.defaultVoice === $config.audio.tts.voice) {
			voice = $settings?.audio?.tts?.voice ?? $config.audio.tts.voice ?? '';
		} else {
			voice = $config.audio.tts.voice ?? '';
		}

		// nonLocalVoices = $settings.audio?.tts?.nonLocalVoices ?? false;

		// Set this to true for now, because I'm not sure where it is set in the backend
		nonLocalVoices = true;

		await getVoices();
	});

	let showVoiceDropdown = false;
	let voiceDropdownRef;

	let showManageModal = false;

	// Addons
	let enableMemory = false;

	onMount(async () => {
		enableMemory = $settings?.memory ?? false;
	});


</script>

<ManageModal bind:show={showManageModal} />

<div class="flex flex-col h-full justify-between text-sm pt-5 pb-5">
	<div class="">
		<div class="">
			<div class="my-1" use:onClickOutside={() => (showLanguageDropdown = false)}>
				<div class="relative" bind:this={languageDropdownRef}>
					<button
						type="button"
						class={`flex items-center justify-between w-full text-sm h-10 px-3 py-2 ${
							showLanguageDropdown ? 'border' : ''
						} border-lightGray-400 dark:border-customGray-700 rounded-md bg-lightGray-300 dark:bg-customGray-900 cursor-pointer`}
						on:click={() => {
							showLanguageDropdown = !showLanguageDropdown
							}}
					>
						<span class="text-lightGray-100 dark:text-customGray-100"
							>{$i18n.t('Language')}</span
						>
						<div class="flex items-center gap-2 text-xs text-lightGray-100 dark:text-customGray-100/50">
							{selectedLanguage?.['title']?.replace(/\s*\(.*?\)/, '')}
							<ChevronDown className="size-3" />
						</div>
					</button>

					{#if showLanguageDropdown}
						<div
							class="max-h-40 overflow-y-auto absolute z-50 w-full -mt-1 bg-lightGray-300 pb-1 dark:bg-customGray-900 border-l border-r border-b border-lightGray-400 dark:border-customGray-700 rounded-b-md"
						>
							<hr class="border-t border-lightGray-400 dark:border-customGray-700 mb-2 mt-1 mx-0.5" />
							<div class="px-1">
								{#each languages as language}
									<button
										class="px-3 py-2 flex items-center gap-2 w-full rounded-xl text-sm hover:bg-gray-100 dark:hover:bg-customGray-950 dark:text-customGray-100 cursor-pointer text-gray-900"
										on:click={() => {
											$i18n.changeLanguage(language['code']);
											selectedLanguage = language;
											showLanguageDropdown = false;
										}}
									>
										{language['title']}
									</button>
								{/each}
							</div>
						</div>
					{/if}
				</div>
			</div>
			<div>
				<div class="my-1" use:onClickOutside={() => (showVoiceDropdown = false)}>
					<div class="relative" bind:this={voiceDropdownRef}>
						<button
							type="button"
							class={`flex items-center justify-between w-full bg-lightGray-300 text-sm h-10 px-3 py-2 ${
								showVoiceDropdown ? 'border' : ''
							} border-lightGray-400 dark:border-customGray-700 rounded-md bg-lightGray-300 dark:bg-customGray-900 cursor-pointer`}
							on:click={() => {
								showVoiceDropdown = !showVoiceDropdown
								}}
						>
							<span class="text-lightGray-100 dark:text-customGray-100"
								>{$i18n.t('Voice for audio output')}</span>
							<div class="flex items-center gap-2 text-xs text-lightGray-100 dark:text-customGray-100/50">
								<div class="flex items-center gap-2 text-xs text-lightGray-100 dark:text-customGray-100/50 capitalize">
									{voice}
								<ChevronDown className="size-3" />
							</div>
						</button>

						{#if showVoiceDropdown}
							<div
								class="max-h-40 overflow-y-auto absolute z-50 w-full -mt-1 pb-1 bg-lightGray-300 dark:bg-customGray-900 border-l border-r border-b border-gray-300 dark:border-customGray-700 rounded-b-md shadow"
							>
								<hr class="border-t border-lightGray-400 dark:border-customGray-700 mb-2 mt-1 mx-0.5" />
								<div class="px-1">
									{#each voices.filter((v) => nonLocalVoices || v.localService === true) as _voice}
										<button
											class="px-3 py-2 flex items-center gap-2 w-full rounded-xl text-sm hover:bg-gray-100 dark:hover:bg-customGray-950 dark:text-customGray-100 cursor-pointer capitalize text-gray-900"
											on:click={() => {
												voice = _voice.name;
												saveSettings({
													audio: {
														stt: {
															engine: STTEngine !== '' ? STTEngine : undefined
														},
														tts: {
															playbackRate: playbackRate,
															voice: _voice.name !== '' ? _voice.name : undefined,
															defaultVoice: $config?.audio?.tts?.voice ?? '',
															nonLocalVoices: $config.audio.tts.engine === '' ? nonLocalVoices : undefined
														}
													}
												});												
												showVoiceDropdown = false;
											}}
										>
											{_voice.name}
										</button>
									{/each}
								</div>
							</div>
						{/if}
					</div>
				</div>
				<!-- <div class=" mb-2.5 text-sm font-medium">{$i18n.t('Set Voice')}</div>
				<div class="flex w-full">
					<div class="flex-1">
						<select
							class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none"
							bind:value={voice}
						>
							<option value="" selected={voice !== ''}>{$i18n.t('Default')}</option>
							{#each voices.filter((v) => nonLocalVoices || v.localService === true) as _voice}
								<option
									value={_voice.name}
									class="bg-gray-100 dark:bg-gray-700"
									selected={voice === _voice.name}>{_voice.name}</option
								>
							{/each}
						</select>
					</div>
				</div> -->
				<!-- <div class="flex items-center justify-between my-1.5">
					<div class="text-xs">
						{$i18n.t('Allow non-local voices')}
					</div>

					<div class="mt-1">
						<Switch bind:state={nonLocalVoices} />
					</div>
				</div> -->
			</div>
			<!-- <div class=" flex w-full justify-between">
				<div class=" self-center text-xs font-medium">{$i18n.t('Language')}</div>
				<div class="flex items-center relative">
					<select
						class=" dark:bg-gray-900 w-fit pr-8 rounded py-2 px-2 text-xs bg-transparent outline-none text-right"
						bind:value={lang}
						placeholder="Select a language"
						on:change={(e) => {
							$i18n.changeLanguage(lang);
						}}
					>
						{#each languages as language}
							<option value={language['code']}>{language['title']}</option>
						{/each}
					</select>
				</div>
			</div> -->

			<div
				class="flex w-full justify-between items-center py-2.5 border-b border-lightGray-400 dark:border-customGray-700 mb-2"
			>
				<div class="flex w-full justify-between items-center">
					<div class="text-xs text-lightGray-100 dark:text-customGray-300">{$i18n.t('Theme')}</div>
				</div>
			</div>

			<div class="flex gap-x-2.5">
				<div on:click={() => themeChangeHandler('system')} class="relative rounded-lg {selectedTheme === "system" ? "border-2 border-[#305BE4]" : ""}">
					<img class="rounded-lg max-w-full" src="/system.png" alt="system theme"/>
					<div class="flex items-center pl-2.5 absolute bottom-[0.625rem] text-customGray-550 text-xs">
						<SystemIcon className="size-3.5 mr-1"/>
						{$i18n.t('System (Default)')}
					</div>
				</div>
				<div on:click={() => themeChangeHandler('light')}  class="relative rounded-lg {selectedTheme === "light" ? "border-2 border-[#305BE4]" : ""}">
					<img class="rounded-lg max-w-full" src="/light.png" alt="light theme"/>
					<div class="flex items-center pl-2.5 absolute bottom-[0.625rem] text-customGray-550 text-xs">
						<LightIcon className="size-3.5 mr-1"/>
						{$i18n.t('Light')}
					</div>
				</div>
				<div on:click={() => themeChangeHandler('dark')} class="relative rounded-lg {selectedTheme === "dark" ? "border-2 border-[#305BE4]" : ""}">
					<img class="rounded-lg max-w-full" src="/dark.png" alt="dark theme"/>
					<div class="flex items-center pl-2.5 absolute bottom-[0.625rem] text-customGray-550 text-xs">
						<DarkIcon className="size-3.5 mr-1"/>
						{$i18n.t('Dark')}
					</div>
				</div>
			</div>

			<!-- <div class="flex w-full justify-between">
				<div class=" self-center text-xs font-medium">{$i18n.t('Theme')}</div>
				<div class="flex items-center relative">
					<select
						class=" dark:bg-gray-900 w-fit pr-8 rounded py-2 px-2 text-xs bg-transparent outline-none text-right"
						bind:value={selectedTheme}
						placeholder="Select a theme"
						on:change={() => themeChangeHandler(selectedTheme)}
					>
						<option value="system">⚙️ {$i18n.t('System')}</option>
						<option value="dark">🌑 {$i18n.t('Dark')}</option>
						<option value="oled-dark">🌃 {$i18n.t('OLED Dark')}</option>
						<option value="light">☀️ {$i18n.t('Light')}</option>
						<option value="her">🌷 Her</option>
					</select>
				</div>
			</div> -->
			<!-- {#if $i18n.language === 'en-US'}
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
			{/if} -->

			<!-- <div>
				<div class=" py-0.5 flex w-full justify-between">
					<div class=" self-center text-xs font-medium">{$i18n.t('Notifications')}</div>

					<button
						class="p-1 px-3 text-xs flex rounded transition"
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
			</div> -->
		</div>

		 {#if $user.role === 'admin' || $user?.permissions.chat?.controls}
			<div
				class="flex w-full justify-between items-center py-2.5 border-b border-lightGray-400 dark:border-customGray-700 mb-2"
			>
				<div class="flex w-full justify-between items-center">
					<div class="text-xs text-lightGray-100 dark:text-customGray-300">{$i18n.t('Custom Instructions')}</div>
				</div>
			</div>

			<div class="relative w-full bg-lightGray-300 dark:bg-customGray-900 rounded-md mb-2.5">
				{#if system}
					<div class="text-xs absolute left-2 top-1 text-lightGray-100/50 dark:text-customGray-100/50">{$i18n.t('System Prompt')}</div>
				{/if}
				<textarea
					bind:value={system}
					placeholder={$i18n.t('System Prompt')}
					class="px-2.5 py-2 text-sm {system ? "pt-4" : "pt-2"} text-lightGray-100 placeholder:text-lightGray-100 w-full h-20 bg-transparent dark:text-white dark:placeholder:text-customGray-100 outline-none"
					rows="4"
				/>
			</div>
			<div class="text-xs text-gray-600 dark:text-customGray-100/50 mb-5">
				<div>
					{$i18n.t('Adding a system prompt shapes LLM responses to better fit specific objectives.')}
				</div>
			</div>

			
			<div class="mb-2.5">
				<div class="flex items-center justify-between mb-1 w-full bg-lightGray-300 dark:bg-customGray-900 rounded-md h-10 px-2.5 py-2">
					
						<div class="text-sm text-lightGray-100 dark:text-customGray-100">
							{$i18n.t('Memory')}
						</div>
	
					<div class="">
						<Switch
							bind:state={enableMemory}
							on:change={async () => {
								saveSettings({ memory: enableMemory });
							}}
						/>
					</div>
				</div>
			</div>
		
			<div class="text-xs text-gray-600 dark:text-customGray-100/50">
				<div>
					{$i18n.t(
						"You can personalize your interactions with LLMs by adding memories through the 'Manage' button below, making them more helpful and tailored to you."
					)}
				</div>
			</div>
		
			<div class="mt-3 mb-1 ml-1">
				<button
					type="button"
					class=" text-xs w-[132px] h-10 px-3 py-2 transition rounded-lg bg-lightGray-300 border-lightGray-400 text-lightGray-100 font-medium hover:bg-lightGray-550 dark:bg-customGray-900 dark:hover:bg-customGray-950 dark:text-customGray-200 border dark:border-customGray-700 flex justify-center items-center"
					on:click={() => {
						showManageModal = true;
					}}
				>
					{$i18n.t('Manage')}
				</button>
			</div>
			

			<!-- <div class="mt-2 space-y-3 pr-1.5">
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
					<hr class=" dark:border-gray-850" />

					<div class=" py-1 w-full justify-between">
						<div class="flex w-full justify-between">
							<div class=" self-center text-xs font-medium">{$i18n.t('Keep Alive')}</div>

							<button
								class="p-1 px-3 text-xs flex rounded transition"
								type="button"
								on:click={() => {
									keepAlive = keepAlive === null ? '5m' : null;
								}}
							>
								{#if keepAlive === null}
									<span class="ml-2 self-center"> {$i18n.t('Default')} </span>
								{:else}
									<span class="ml-2 self-center"> {$i18n.t('Custom')} </span>
								{/if}
							</button>
						</div>

						{#if keepAlive !== null}
							<div class="flex mt-1 space-x-2">
								<input
									class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none"
									type="text"
									placeholder={$i18n.t("e.g. '30s','10m'. Valid time units are 's', 'm', 'h'.")}
									bind:value={keepAlive}
								/>
							</div>
						{/if}
					</div>

					<div>
						<div class=" py-1 flex w-full justify-between">
							<div class=" self-center text-sm font-medium">{$i18n.t('Request Mode')}</div>

							<button
								class="p-1 px-3 text-xs flex rounded transition"
								on:click={() => {
									toggleRequestFormat();
								}}
							>
								{#if requestFormat === ''}
									<span class="ml-2 self-center"> {$i18n.t('Default')} </span>
								{:else if requestFormat === 'json'}
									<span class="ml-2 self-center"> {$i18n.t('JSON')} </span>
								{/if}
							</button>
						</div>
					</div>
				{/if}
			</div> -->
		{/if} 
	</div>

	<div class="flex justify-end pt-3 text-sm font-medium">
		<button
		class=" text-xs w-[168px] h-10 px-3 py-2 transition rounded-lg bg-lightGray-300 border-lightGray-400 text-lightGray-100 font-medium hover:bg-lightGray-550 dark:bg-customGray-900 dark:hover:bg-customGray-950 dark:text-customGray-200 border dark:border-customGray-700 flex justify-center items-center"
		type="submit"
			on:click={() => {
				saveSettings({
					system: system !== '' ? system : undefined
				});
				dispatch('save');
			}}
		>
			{$i18n.t('Save')}
		</button>
	</div>
</div>
