<script lang="ts">
	// @ts-ignore
	import fileSaver from 'file-saver';
	const { saveAs } = fileSaver;

	// @ts-ignore
	import { v4 as uuidv4 } from 'uuid';
	import { toast } from 'svelte-sonner';

	import { getBackendConfig, getModels, getTaskConfig, updateTaskConfig } from '$lib/apis';
	import { setDefaultPromptSuggestions, getUIConfig, setUIConfig } from '$lib/apis/configs';
	import { config, settings, user, tasksConfigCache, bannersCache } from '$lib/stores';
	import { createEventDispatcher, onMount, getContext } from 'svelte';

	import { banners as _banners } from '$lib/stores';
	import type { Banner } from '$lib/types';

	import { getBaseModels } from '$lib/apis/models';
	import { getBanners, setBanners } from '$lib/apis/configs';

	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import Textarea from '$lib/components/common/Textarea.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Banners from './Interface/Banners.svelte';
	import PromptSuggestions from '$lib/components/workspace/Models/PromptSuggestions.svelte';
	import Minus from '$lib/components/icons/Minus.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import ChevronUp from '$lib/components/icons/ChevronUp.svelte';
	import ManageFloatingActionButtonsModal from '$lib/components/chat/Settings/Interface/ManageFloatingActionButtonsModal.svelte';
	import ManageImageCompressionModal from '$lib/components/chat/Settings/Interface/ManageImageCompressionModal.svelte';

	const dispatch = createEventDispatcher();

	import type { Writable } from 'svelte/store';
	const i18n: Writable<any> = getContext('i18n');

	// Collapsible section states
	let expandedSections = {
		tasks: true,
		userInterface: true,
		chat: true,
		input: true,
		artifacts: true,
		voice: true,
		file: true,
		adminUI: true
	};

	let taskConfig: any = {
		TASK_MODEL: '',
		TASK_MODEL_EXTERNAL: '',
		ENABLE_TITLE_GENERATION: true,
		TITLE_GENERATION_PROMPT_TEMPLATE: '',
		ENABLE_FOLLOW_UP_GENERATION: true,
		FOLLOW_UP_GENERATION_PROMPT_TEMPLATE: '',
		IMAGE_PROMPT_GENERATION_PROMPT_TEMPLATE: '',
		ENABLE_AUTOCOMPLETE_GENERATION: true,
		AUTOCOMPLETE_GENERATION_INPUT_MAX_LENGTH: -1,
		TAGS_GENERATION_PROMPT_TEMPLATE: '',
		ENABLE_TAGS_GENERATION: true,
		ENABLE_SUMMARIZE_GENERATION: true,
		SUMMARIZE_GENERATION_PROMPT_TEMPLATE: '',
		ENABLE_SEARCH_QUERY_GENERATION: true,
		ENABLE_RETRIEVAL_QUERY_GENERATION: true,
		QUERY_GENERATION_PROMPT_TEMPLATE: '',
		TOOLS_FUNCTION_CALLING_PROMPT_TEMPLATE: '',
		VOICE_MODE_PROMPT_TEMPLATE: ''
	};

	let promptSuggestions: any[] = [];
	let banners: Banner[] = [];

	// Admin-only Global Config (stored in server API)
	let adminConfig: any = {
		showUpdateToast: true,
		showChangelog: true,
		landingPageMode: ''
	};

	// User-level Config (stored in localStorage, per-user)
	let userConfig: any = {
		// UI Settings
		textScale: null,
		highContrastMode: false,
		showChatTitleInTab: true,
		notificationSound: true,
		notificationSoundAlways: false,
		userLocation: false,
		hapticFeedback: false,
		copyFormatted: false,
		showUsername: false,
		chatDirection: 'auto',
		backgroundImageUrl: null,
		webSearch: null,

		// Chat Settings
		chatBubble: true,
		widescreenMode: false,
		temporaryChatByDefault: false,
		chatFadeStreamingText: true,
		titleAutoGenerate: true,
		autoFollowUps: true,
		autoTags: true,
		responseAutoCopy: false,
		insertSuggestionPrompt: false,
		keepFollowUpPrompts: false,
		insertFollowUpPrompt: false,
		regenerateMenu: true,
		collapseCodeBlocks: false,
		expandDetails: false,
		displayMultiModelResponsesInTabs: false,
		scrollOnBranchChange: true,
		stylizedPdfExport: true,
		showFloatingActionButtons: true,
		floatingActionButtons: null,
		splitLargeChunks: false,

		// Artifacts Settings
		detectArtifacts: true,
		iframeSandboxAllowSameOrigin: false,
		iframeSandboxAllowForms: false,

		// Voice Settings
		showEmojiInCall: false,
		voiceInterruption: false,

		// Input Settings
		ctrlEnterToSend: false,
		richTextInput: true,
		showFormattingToolbar: false,
		insertPromptAsRichText: false,
		promptAutocomplete: false,
		largeTextAsFile: false,

		// File Settings
		imageCompression: false,
		imageCompressionSize: { width: '', height: '' },
		imageCompressionInChannels: true
	};

	let showManageFloatingActionButtonsModal = false;
	let showManageImageCompressionModal = false;
	let backgroundImageInputFiles = null;
	let backgroundImageFilesInputElement: HTMLInputElement;

	const updateInterfaceHandler = async () => {
		taskConfig = await updateTaskConfig(localStorage.token, taskConfig);
		// Update cache after saving
		tasksConfigCache.set(taskConfig);

		promptSuggestions = promptSuggestions.filter((p) => p.content !== '');
		// @ts-ignore
		promptSuggestions = await setDefaultPromptSuggestions(localStorage.token, promptSuggestions);
		await updateBanners();

		// Save admin config to server API (only if admin)
		if ($user?.role === 'admin') {
			await setUIConfig(localStorage.token, adminConfig);
		}

		// Save user config to localStorage (per-user, independent)
		settings.set({
			...$settings,
			...userConfig
		});

		await config.set(await getBackendConfig());
	};

	const updateBanners = async () => {
		const updatedBanners = await setBanners(localStorage.token, banners);
		_banners.set(updatedBanners);
		// Update cache after saving
		bannersCache.set(updatedBanners);
	};

	let workspaceModels: any = null;
	let baseModels: any = null;

	let models: any = null;

	const init = async () => {
		// Use cached taskConfig if available
		if ($tasksConfigCache) {
			taskConfig = JSON.parse(JSON.stringify($tasksConfigCache));
		} else {
			taskConfig = await getTaskConfig(localStorage.token);
			tasksConfigCache.set(taskConfig);
		}

		promptSuggestions = $config?.default_prompt_suggestions ?? [];

		// Use cached banners if available
		if ($bannersCache) {
			banners = JSON.parse(JSON.stringify($bannersCache));
		} else {
			banners = await getBanners(localStorage.token);
			bannersCache.set(banners);
		}

		// Load admin config from server API (only if admin)
		if ($user?.role === 'admin') {
			try {
				const loadedAdminConfig = await getUIConfig(localStorage.token);
				if (loadedAdminConfig) {
					adminConfig = { ...adminConfig, ...loadedAdminConfig };
				}
			} catch (e) {
				console.log('Admin UI config not found, using defaults');
			}
		}

		// Load user config from localStorage (per-user, independent)
		if ($settings) {
			userConfig = {
				...userConfig,
				textScale: $settings.textScale ?? userConfig.textScale,
				highContrastMode: $settings.highContrastMode ?? userConfig.highContrastMode,
				showChatTitleInTab: $settings.showChatTitleInTab ?? userConfig.showChatTitleInTab,
				notificationSound: $settings.notificationSound ?? userConfig.notificationSound,
				notificationSoundAlways: $settings.notificationSoundAlways ?? userConfig.notificationSoundAlways,
				userLocation: $settings.userLocation ?? userConfig.userLocation,
				hapticFeedback: $settings.hapticFeedback ?? userConfig.hapticFeedback,
				copyFormatted: $settings.copyFormatted ?? userConfig.copyFormatted,
				showUsername: $settings.showUsername ?? userConfig.showUsername,
				chatDirection: $settings.chatDirection ?? userConfig.chatDirection,
				backgroundImageUrl: $settings.backgroundImageUrl ?? userConfig.backgroundImageUrl,
				webSearch: $settings.webSearch ?? userConfig.webSearch,
				chatBubble: $settings.chatBubble ?? userConfig.chatBubble,
				widescreenMode: $settings.widescreenMode ?? userConfig.widescreenMode,
				temporaryChatByDefault: $settings.temporaryChatByDefault ?? userConfig.temporaryChatByDefault,
				chatFadeStreamingText: $settings.chatFadeStreamingText ?? userConfig.chatFadeStreamingText,
				titleAutoGenerate: $settings.titleAutoGenerate ?? userConfig.titleAutoGenerate,
				autoFollowUps: $settings.autoFollowUps ?? userConfig.autoFollowUps,
				autoTags: $settings.autoTags ?? userConfig.autoTags,
				responseAutoCopy: $settings.responseAutoCopy ?? userConfig.responseAutoCopy,
				insertSuggestionPrompt: $settings.insertSuggestionPrompt ?? userConfig.insertSuggestionPrompt,
				keepFollowUpPrompts: $settings.keepFollowUpPrompts ?? userConfig.keepFollowUpPrompts,
				insertFollowUpPrompt: $settings.insertFollowUpPrompt ?? userConfig.insertFollowUpPrompt,
				regenerateMenu: $settings.regenerateMenu ?? userConfig.regenerateMenu,
				collapseCodeBlocks: $settings.collapseCodeBlocks ?? userConfig.collapseCodeBlocks,
				expandDetails: $settings.expandDetails ?? userConfig.expandDetails,
				displayMultiModelResponsesInTabs: $settings.displayMultiModelResponsesInTabs ?? userConfig.displayMultiModelResponsesInTabs,
				scrollOnBranchChange: $settings.scrollOnBranchChange ?? userConfig.scrollOnBranchChange,
				stylizedPdfExport: $settings.stylizedPdfExport ?? userConfig.stylizedPdfExport,
				showFloatingActionButtons: $settings.showFloatingActionButtons ?? userConfig.showFloatingActionButtons,
				floatingActionButtons: $settings.floatingActionButtons ?? userConfig.floatingActionButtons,
				splitLargeChunks: $settings.splitLargeChunks ?? userConfig.splitLargeChunks,
				detectArtifacts: $settings.detectArtifacts ?? userConfig.detectArtifacts,
				iframeSandboxAllowSameOrigin: $settings.iframeSandboxAllowSameOrigin ?? userConfig.iframeSandboxAllowSameOrigin,
				iframeSandboxAllowForms: $settings.iframeSandboxAllowForms ?? userConfig.iframeSandboxAllowForms,
				showEmojiInCall: $settings.showEmojiInCall ?? userConfig.showEmojiInCall,
				voiceInterruption: $settings.voiceInterruption ?? userConfig.voiceInterruption,
				ctrlEnterToSend: $settings.ctrlEnterToSend ?? userConfig.ctrlEnterToSend,
				richTextInput: $settings.richTextInput ?? userConfig.richTextInput,
				showFormattingToolbar: $settings.showFormattingToolbar ?? userConfig.showFormattingToolbar,
				insertPromptAsRichText: $settings.insertPromptAsRichText ?? userConfig.insertPromptAsRichText,
				promptAutocomplete: $settings.promptAutocomplete ?? userConfig.promptAutocomplete,
				largeTextAsFile: $settings.largeTextAsFile ?? userConfig.largeTextAsFile,
				imageCompression: $settings.imageCompression ?? userConfig.imageCompression,
				imageCompressionSize: $settings.imageCompressionSize ?? userConfig.imageCompressionSize,
				imageCompressionInChannels: $settings.imageCompressionInChannels ?? userConfig.imageCompressionInChannels
			};
		}

		workspaceModels = await getBaseModels(localStorage.token);
		baseModels = await getModels(localStorage.token, null, false);

		models = baseModels.map((m: any) => {
			const workspaceModel = workspaceModels.find((wm: any) => wm.id === m.id);

			if (workspaceModel) {
				return {
					...m,
					...workspaceModel
				};
			} else {
				return {
					...m,
					id: m.id,
					name: m.name,

					is_active: true
				};
			}
		});

		console.debug('models', models);
	};

	onMount(async () => {
		await init();
	});
</script>

<ManageFloatingActionButtonsModal
	bind:show={showManageFloatingActionButtonsModal}
	floatingActionButtons={userConfig.floatingActionButtons}
	onSave={(buttons) => {
		userConfig.floatingActionButtons = buttons;
	}}
/>

<ManageImageCompressionModal
	bind:show={showManageImageCompressionModal}
	size={userConfig.imageCompressionSize}
	onSave={(size) => {
		userConfig.imageCompressionSize = size;
	}}
/>

{#if models !== null && taskConfig}
	<form
		class="flex flex-col text-sm"
		on:submit|preventDefault={() => {
			updateInterfaceHandler();
			dispatch('save');
		}}
	>
		<div class="pb-24">
			<div class="max-w-5xl mx-auto">
				<!-- ==================== Tasks Section (Admin Only) ==================== -->
				{#if $user?.role === 'admin'}
					<div class="mb-4">
						<div class="bg-gray-50 dark:bg-gray-850 rounded-lg p-5 border border-gray-100 dark:border-gray-800">
							<!-- Section Header -->
							<button
								type="button"
								class="w-full flex items-center justify-between"
								on:click={() => expandedSections.tasks = !expandedSections.tasks}
							>
								<div class="flex items-center gap-2.5">
									<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="w-5 h-5 text-gray-500 dark:text-gray-400">
										<path fill-rule="evenodd" d="M7.502 6h7.128A3.375 3.375 0 0 1 18 9.375v9.375a3 3 0 0 0 3-3V6.108c0-1.505-1.125-2.811-2.664-2.94a48.972 48.972 0 0 0-.673-.05A3 3 0 0 0 15 1.5h-1.5a3 3 0 0 0-2.663 1.618c-.225.015-.45.032-.673.05C8.662 3.295 7.554 4.542 7.502 6ZM13.5 3A1.5 1.5 0 0 0 12 4.5h4.5A1.5 1.5 0 0 0 15 3h-1.5Z" clip-rule="evenodd" />
										<path fill-rule="evenodd" d="M3 9.375C3 8.339 3.84 7.5 4.875 7.5h9.75c1.036 0 1.875.84 1.875 1.875v11.25c0 1.035-.84 1.875-1.875 1.875h-9.75A1.875 1.875 0 0 1 3 20.625V9.375Zm9.586 4.594a.75.75 0 0 0-1.172-.938l-2.476 3.096-.908-.907a.75.75 0 0 0-1.06 1.06l1.5 1.5a.75.75 0 0 0 1.116-.062l3-3.75Z" clip-rule="evenodd" />
									</svg>
									<div class="text-sm font-medium text-gray-800 dark:text-gray-100">
										{$i18n.t('Tasks')}
									</div>
								</div>
								<div class="text-gray-500">
									{#if expandedSections.tasks}
										<ChevronUp className="w-5 h-5" />
									{:else}
										<ChevronDown className="w-5 h-5" />
									{/if}
								</div>
							</button>

							{#if expandedSections.tasks}
								<hr class="border-gray-100 dark:border-gray-800 my-4" />

								<!-- Task Model Selection -->
								<div class="mb-4">
									<div class="flex items-center gap-1.5 mb-2">
										<div class="text-sm font-medium">{$i18n.t('Task Model')}</div>
										<Tooltip content={$i18n.t('A task model is used when performing tasks such as generating titles for chats and web search queries')}>
											<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="size-3.5 text-gray-500">
												<path stroke-linecap="round" stroke-linejoin="round" d="m11.25 11.25.041-.02a.75.75 0 0 1 1.063.852l-.708 2.836a.75.75 0 0 0 1.063.853l.041-.021M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9-3.75h.008v.008H12V8.25Z" />
											</svg>
										</Tooltip>
									</div>
									<div class="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-3">
										<div>
											<div class="text-xs text-gray-500 dark:text-gray-400 mb-1">{$i18n.t('Local Task Model')}</div>
											<select
												class="w-full rounded-lg py-2 px-3 text-sm bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 outline-hidden"
												bind:value={taskConfig.TASK_MODEL}
												on:change={() => {
													if (taskConfig.TASK_MODEL) {
														const model = models.find((m) => m.id === taskConfig.TASK_MODEL);
														if (model?.access_control !== null) {
															toast.error($i18n.t('This model is not publicly available. Please select another model.'));
														}
													}
												}}
											>
												<option value="">{$i18n.t('Current Model')}</option>
												{#each models as model}
													<option value={model.id}>{model.name}{model?.connection_type === 'local' ? ` (${$i18n.t('Local')})` : ''}</option>
												{/each}
											</select>
										</div>
										<div>
											<div class="text-xs text-gray-500 dark:text-gray-400 mb-1">{$i18n.t('External Task Model')}</div>
											<select
												class="w-full rounded-lg py-2 px-3 text-sm bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 outline-hidden"
												bind:value={taskConfig.TASK_MODEL_EXTERNAL}
												on:change={() => {
													if (taskConfig.TASK_MODEL_EXTERNAL) {
														const model = models.find((m) => m.id === taskConfig.TASK_MODEL_EXTERNAL);
														if (model?.access_control !== null) {
															toast.error($i18n.t('This model is not publicly available. Please select another model.'));
														}
													}
												}}
											>
												<option value="">{$i18n.t('Current Model')}</option>
												{#each models as model}
													<option value={model.id}>{model.name}{model?.connection_type === 'local' ? ` (${$i18n.t('Local')})` : ''}</option>
												{/each}
											</select>
										</div>
									</div>
								</div>

								<hr class="border-gray-100 dark:border-gray-800 my-4" />

								<!-- Task Toggles Grid -->
								<div class="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-3 mb-4">
									<div class="flex items-center justify-between">
										<div class="text-sm">{$i18n.t('Title Generation')}</div>
										<Switch bind:state={taskConfig.ENABLE_TITLE_GENERATION} />
									</div>
									<div class="flex items-center justify-between">
										<div class="text-sm">{$i18n.t('Follow Up Generation')}</div>
										<Switch bind:state={taskConfig.ENABLE_FOLLOW_UP_GENERATION} />
									</div>
									<div class="flex items-center justify-between">
										<div class="text-sm">{$i18n.t('Tags Generation')}</div>
										<Switch bind:state={taskConfig.ENABLE_TAGS_GENERATION} />
									</div>
									<div class="flex items-center justify-between">
										<div class="text-sm">{$i18n.t('Autocomplete Generation')}</div>
										<Switch bind:state={taskConfig.ENABLE_AUTOCOMPLETE_GENERATION} />
									</div>
									<div class="flex items-center justify-between">
										<div class="text-sm">{$i18n.t('Search Query Generation')}</div>
										<Switch bind:state={taskConfig.ENABLE_SEARCH_QUERY_GENERATION} />
									</div>
									<div class="flex items-center justify-between">
										<div class="text-sm">{$i18n.t('Retrieval Query Generation')}</div>
										<Switch bind:state={taskConfig.ENABLE_RETRIEVAL_QUERY_GENERATION} />
									</div>
									<div class="flex items-center justify-between">
										<div class="text-sm">{$i18n.t('Summarize Generation')}</div>
										<Switch bind:state={taskConfig.ENABLE_SUMMARIZE_GENERATION} />
									</div>
									<div class="flex items-center justify-between">
										<div class="text-sm">{$i18n.t('Voice Mode Custom Prompt')}</div>
										<Switch
											state={taskConfig.VOICE_MODE_PROMPT_TEMPLATE != null}
											on:change={(e) => {
												taskConfig.VOICE_MODE_PROMPT_TEMPLATE = e.detail ? '' : null;
											}}
										/>
									</div>
								</div>

								{#if taskConfig.ENABLE_AUTOCOMPLETE_GENERATION}
									<div class="mb-4">
										<div class="text-xs text-gray-500 dark:text-gray-400 mb-1">{$i18n.t('Autocomplete Generation Input Max Length')}</div>
										<input
											class="w-full rounded-lg py-2 px-3 text-sm bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 outline-hidden"
											type="number"
											bind:value={taskConfig.AUTOCOMPLETE_GENERATION_INPUT_MAX_LENGTH}
											placeholder={$i18n.t('-1 for no limit')}
										/>
									</div>
								{/if}

								<hr class="border-gray-100 dark:border-gray-800 my-4" />

								<!-- Prompt Templates -->
								<div class="text-[11px] font-medium text-gray-400 dark:text-gray-500 uppercase tracking-wide mb-3">{$i18n.t('Prompt Templates')}</div>
								<div class="space-y-4">
									{#if taskConfig.ENABLE_TITLE_GENERATION}
										<div>
											<div class="text-xs text-gray-500 dark:text-gray-400 mb-1">{$i18n.t('Title Generation Prompt')}</div>
											<Textarea bind:value={taskConfig.TITLE_GENERATION_PROMPT_TEMPLATE} placeholder={$i18n.t('Leave empty to use the default prompt')} />
										</div>
									{/if}
									{#if taskConfig.VOICE_MODE_PROMPT_TEMPLATE != null}
										<div>
											<div class="text-xs text-gray-500 dark:text-gray-400 mb-1">{$i18n.t('Voice Mode Prompt')}</div>
											<Textarea bind:value={taskConfig.VOICE_MODE_PROMPT_TEMPLATE} placeholder={$i18n.t('Leave empty to use the default prompt')} />
										</div>
									{/if}
									{#if taskConfig.ENABLE_FOLLOW_UP_GENERATION}
										<div>
											<div class="text-xs text-gray-500 dark:text-gray-400 mb-1">{$i18n.t('Follow Up Generation Prompt')}</div>
											<Textarea bind:value={taskConfig.FOLLOW_UP_GENERATION_PROMPT_TEMPLATE} placeholder={$i18n.t('Leave empty to use the default prompt')} />
										</div>
									{/if}
									{#if taskConfig.ENABLE_TAGS_GENERATION}
										<div>
											<div class="text-xs text-gray-500 dark:text-gray-400 mb-1">{$i18n.t('Tags Generation Prompt')}</div>
											<Textarea bind:value={taskConfig.TAGS_GENERATION_PROMPT_TEMPLATE} placeholder={$i18n.t('Leave empty to use the default prompt')} />
										</div>
									{/if}
									{#if taskConfig.ENABLE_SUMMARIZE_GENERATION}
										<div>
											<div class="text-xs text-gray-500 dark:text-gray-400 mb-1">{$i18n.t('Summarize Generation Prompt')}</div>
											<Textarea bind:value={taskConfig.SUMMARIZE_GENERATION_PROMPT_TEMPLATE} placeholder={$i18n.t('Leave empty to use the default prompt')} />
										</div>
									{/if}
									{#if taskConfig.ENABLE_SEARCH_QUERY_GENERATION || taskConfig.ENABLE_RETRIEVAL_QUERY_GENERATION}
										<div>
											<div class="text-xs text-gray-500 dark:text-gray-400 mb-1">{$i18n.t('Query Generation Prompt')}</div>
											<Textarea bind:value={taskConfig.QUERY_GENERATION_PROMPT_TEMPLATE} placeholder={$i18n.t('Leave empty to use the default prompt')} />
										</div>
									{/if}
									<div>
										<div class="text-xs text-gray-500 dark:text-gray-400 mb-1">{$i18n.t('Image Prompt Generation Prompt')}</div>
										<Textarea bind:value={taskConfig.IMAGE_PROMPT_GENERATION_PROMPT_TEMPLATE} placeholder={$i18n.t('Leave empty to use the default prompt')} />
									</div>
									<div>
										<div class="text-xs text-gray-500 dark:text-gray-400 mb-1">{$i18n.t('Tools Function Calling Prompt')}</div>
										<Textarea bind:value={taskConfig.TOOLS_FUNCTION_CALLING_PROMPT_TEMPLATE} placeholder={$i18n.t('Leave empty to use the default prompt')} />
									</div>
								</div>
							{/if}
						</div>
					</div>
				{/if}

				<!-- ==================== User Interface Section ==================== -->
				<div class="mb-4">
					<div class="bg-gray-50 dark:bg-gray-850 rounded-lg p-5 border border-gray-100 dark:border-gray-800">
						<!-- Section Header -->
						<button
							type="button"
							class="w-full flex items-center justify-between"
							on:click={() => expandedSections.userInterface = !expandedSections.userInterface}
						>
							<div class="flex items-center gap-2.5">
								<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="w-5 h-5 text-gray-500 dark:text-gray-400">
									<path fill-rule="evenodd" d="M2.25 5.25a3 3 0 013-3h13.5a3 3 0 013 3V15a3 3 0 01-3 3h-3v.257c0 .597.237 1.17.659 1.591l.621.622a.75.75 0 01-.53 1.28h-9a.75.75 0 01-.53-1.28l.621-.622a2.25 2.25 0 00.659-1.59V18h-3a3 3 0 01-3-3V5.25zm1.5 0v7.5a1.5 1.5 0 001.5 1.5h13.5a1.5 1.5 0 001.5-1.5v-7.5a1.5 1.5 0 00-1.5-1.5H5.25a1.5 1.5 0 00-1.5 1.5z" clip-rule="evenodd" />
								</svg>
								<div class="text-sm font-medium text-gray-800 dark:text-gray-100">
									{$i18n.t('User Interface')}
								</div>
							</div>
							<div class="text-gray-500">
								{#if expandedSections.userInterface}
									<ChevronUp className="w-5 h-5" />
								{:else}
									<ChevronDown className="w-5 h-5" />
								{/if}
							</div>
						</button>

						{#if expandedSections.userInterface}
							<hr class="border-gray-100 dark:border-gray-800 my-4" />

							<!-- UI Scale -->
							<div class="mb-4">
								<div class="flex items-center justify-between mb-2">
									<div class="text-sm font-medium">{$i18n.t('UI Scale')}</div>
									<button
										class="text-xs font-medium px-3 py-1.5 rounded-lg transition {userConfig.textScale === null
											? 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-300'
											: 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-200'}"
										type="button"
										on:click={() => {
											userConfig.textScale = userConfig.textScale === null ? 1 : null;
										}}
									>
										{userConfig.textScale === null ? $i18n.t('Default') : `${userConfig.textScale}x`}
									</button>
								</div>

								{#if userConfig.textScale !== null}
									<div class="flex items-center gap-2">
										<button
											type="button"
											class="rounded-lg p-1.5 transition hover:bg-gray-100 dark:hover:bg-gray-800"
											on:click={() => {
												userConfig.textScale = Math.max(1, parseFloat((userConfig.textScale - 0.1).toFixed(2)));
											}}
										>
											<Minus className="h-3.5 w-3.5" />
										</button>
										<input
											class="w-full accent-gray-700 dark:accent-gray-300"
											type="range"
											min="1"
											max="1.5"
											step={0.01}
											bind:value={userConfig.textScale}
										/>
										<button
											type="button"
											class="rounded-lg p-1.5 transition hover:bg-gray-100 dark:hover:bg-gray-800"
											on:click={() => {
												userConfig.textScale = Math.min(1.5, parseFloat((userConfig.textScale + 0.1).toFixed(2)));
											}}
										>
											<Plus className="h-3.5 w-3.5" />
										</button>
									</div>
								{/if}
							</div>

							<hr class="border-gray-100 dark:border-gray-800 my-4" />

							<!-- Display Settings -->
							<div class="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-3">
								<div class="flex items-center justify-between">
									<div class="text-sm">{$i18n.t('High Contrast Mode')}</div>
									<Switch bind:state={userConfig.highContrastMode} />
								</div>
								<div class="flex items-center justify-between">
									<div class="text-sm">{$i18n.t('Display chat title in tab')}</div>
									<Switch bind:state={userConfig.showChatTitleInTab} />
								</div>
								<div class="flex items-center justify-between">
									<div class="text-sm">{$i18n.t('Notification Sound')}</div>
									<Switch bind:state={userConfig.notificationSound} />
								</div>
								{#if userConfig.notificationSound}
									<div class="flex items-center justify-between">
										<div class="text-sm">{$i18n.t('Always Play Notification Sound')}</div>
										<Switch bind:state={userConfig.notificationSoundAlways} />
									</div>
								{/if}
								<div class="flex items-center justify-between">
									<div class="text-sm">{$i18n.t('Allow User Location')}</div>
									<Switch bind:state={userConfig.userLocation} />
								</div>
								<div class="flex items-center justify-between">
									<div class="text-sm">{$i18n.t('Haptic Feedback')} ({$i18n.t('Android')})</div>
									<Switch bind:state={userConfig.hapticFeedback} />
								</div>
								<div class="flex items-center justify-between">
									<div class="text-sm">{$i18n.t('Copy Formatted Text')}</div>
									<Switch bind:state={userConfig.copyFormatted} />
								</div>
							</div>

							{#if $user?.role === 'admin'}
								<hr class="border-gray-100 dark:border-gray-800 my-4" />
								<div class="text-[11px] font-medium text-gray-400 dark:text-gray-500 uppercase tracking-wide mb-3">{$i18n.t('Admin Settings')}</div>
								<div class="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-3">
									<div class="flex items-center justify-between">
										<div class="text-sm">{$i18n.t('Toast notifications for new updates')}</div>
										<Switch bind:state={adminConfig.showUpdateToast} />
									</div>
									<div class="flex items-center justify-between">
										<div class="text-sm">{$i18n.t(`Show "What's New" modal on login`)}</div>
										<Switch bind:state={adminConfig.showChangelog} />
									</div>
								</div>
							{/if}
						{/if}
					</div>
				</div>

				<!-- ==================== Chat Section ==================== -->
				<div class="mb-4">
					<div class="bg-gray-50 dark:bg-gray-850 rounded-lg p-5 border border-gray-100 dark:border-gray-800">
						<!-- Section Header -->
						<button
							type="button"
							class="w-full flex items-center justify-between"
							on:click={() => expandedSections.chat = !expandedSections.chat}
						>
							<div class="flex items-center gap-2.5">
								<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="w-5 h-5 text-gray-500 dark:text-gray-400">
									<path fill-rule="evenodd" d="M4.804 21.644A6.707 6.707 0 006 21.75a6.721 6.721 0 003.583-1.029c.774.182 1.584.279 2.417.279 5.322 0 9.75-3.97 9.75-9 0-5.03-4.428-9-9.75-9s-9.75 3.97-9.75 9c0 2.409 1.025 4.587 2.674 6.192.232.226.277.428.254.543a3.73 3.73 0 01-.814 1.686.75.75 0 00.44 1.223zM8.25 10.875a1.125 1.125 0 100 2.25 1.125 1.125 0 000-2.25zM10.875 12a1.125 1.125 0 112.25 0 1.125 1.125 0 01-2.25 0zm4.875-1.125a1.125 1.125 0 100 2.25 1.125 1.125 0 000-2.25z" clip-rule="evenodd" />
								</svg>
								<div class="text-sm font-medium text-gray-800 dark:text-gray-100">
									{$i18n.t('Chat')}
								</div>
							</div>
							<div class="text-gray-500">
								{#if expandedSections.chat}
									<ChevronUp className="w-5 h-5" />
								{:else}
									<ChevronDown className="w-5 h-5" />
								{/if}
							</div>
						</button>

						{#if expandedSections.chat}
							<hr class="border-gray-100 dark:border-gray-800 my-4" />

							<!-- Appearance -->
							<div class="text-[11px] font-medium text-gray-400 dark:text-gray-500 uppercase tracking-wide mb-3">{$i18n.t('Appearance')}</div>
							<div class="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-3 mb-4">
								<div class="flex items-center justify-between">
									<div class="text-sm">{$i18n.t('Chat direction')}</div>
									<button
										class="px-3 py-1.5 text-xs rounded-lg transition bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700"
										on:click={() => {
											userConfig.chatDirection = userConfig.chatDirection === 'auto' ? 'LTR' : userConfig.chatDirection === 'LTR' ? 'RTL' : 'auto';
										}}
										type="button"
									>
										{userConfig.chatDirection === 'LTR' ? $i18n.t('LTR') : userConfig.chatDirection === 'RTL' ? $i18n.t('RTL') : $i18n.t('Auto')}
									</button>
								</div>
								<div class="flex items-center justify-between">
									<div class="text-sm">{$i18n.t('Chat Background Image')}</div>
									<input
										bind:this={backgroundImageFilesInputElement}
										bind:files={backgroundImageInputFiles}
										type="file"
										hidden
										accept="image/*"
										on:change={() => {
											let reader = new FileReader();
											reader.onload = (event) => {
												userConfig.backgroundImageUrl = `${event.target?.result}`;
											};
											if (backgroundImageInputFiles && backgroundImageInputFiles.length > 0) {
												reader.readAsDataURL(backgroundImageInputFiles[0]);
											}
										}}
									/>
									<button
										class="px-3 py-1.5 text-xs rounded-lg transition bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700"
										on:click={() => {
											userConfig.backgroundImageUrl = userConfig.backgroundImageUrl !== null ? null : void backgroundImageFilesInputElement.click();
										}}
										type="button"
									>
										{userConfig.backgroundImageUrl !== null ? $i18n.t('Reset') : $i18n.t('Upload')}
									</button>
								</div>
								<div class="flex items-center justify-between">
									<div class="text-sm">{$i18n.t('Chat Bubble UI')}</div>
									<Switch bind:state={userConfig.chatBubble} />
								</div>
								{#if !userConfig.chatBubble}
									<div class="flex items-center justify-between">
										<div class="text-sm">{$i18n.t('Display the username instead of You')}</div>
										<Switch bind:state={userConfig.showUsername} />
									</div>
								{/if}
								<div class="flex items-center justify-between">
									<div class="text-sm">{$i18n.t('Widescreen Mode')}</div>
									<Switch bind:state={userConfig.widescreenMode} />
								</div>
								<div class="flex items-center justify-between">
									<div class="text-sm">{$i18n.t('Fade Effect for Streaming Text')}</div>
									<Switch bind:state={userConfig.chatFadeStreamingText} />
								</div>
							</div>

							<hr class="border-gray-100 dark:border-gray-800 my-4" />

							<!-- Auto Generation -->
							<div class="text-[11px] font-medium text-gray-400 dark:text-gray-500 uppercase tracking-wide mb-3">{$i18n.t('Auto Generation')}</div>
							<div class="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-3 mb-4">
								<div class="flex items-center justify-between">
									<div class="text-sm">{$i18n.t('Title Auto-Generation')}</div>
									<Switch bind:state={userConfig.titleAutoGenerate} />
								</div>
								<div class="flex items-center justify-between">
									<div class="text-sm">{$i18n.t('Follow-Up Auto-Generation')}</div>
									<Switch bind:state={userConfig.autoFollowUps} />
								</div>
								<div class="flex items-center justify-between">
									<div class="text-sm">{$i18n.t('Chat Tags Auto-Generation')}</div>
									<Switch bind:state={userConfig.autoTags} />
								</div>
								<div class="flex items-center justify-between">
									<div class="text-sm">{$i18n.t('Auto-Copy Response to Clipboard')}</div>
									<Switch bind:state={userConfig.responseAutoCopy} />
								</div>
							</div>

							<hr class="border-gray-100 dark:border-gray-800 my-4" />

							<!-- Behavior -->
							<div class="text-[11px] font-medium text-gray-400 dark:text-gray-500 uppercase tracking-wide mb-3">{$i18n.t('Behavior')}</div>
							<div class="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-3 mb-4">
								<div class="flex items-center justify-between">
									<div class="text-sm">{$i18n.t('Temporary Chat by Default')}</div>
									<Switch bind:state={userConfig.temporaryChatByDefault} />
								</div>
								<div class="flex items-center justify-between">
									<div class="text-sm">{$i18n.t('Insert Suggestion Prompt to Input')}</div>
									<Switch bind:state={userConfig.insertSuggestionPrompt} />
								</div>
								<div class="flex items-center justify-between">
									<div class="text-sm">{$i18n.t('Keep Follow-Up Prompts in Chat')}</div>
									<Switch bind:state={userConfig.keepFollowUpPrompts} />
								</div>
								<div class="flex items-center justify-between">
									<div class="text-sm">{$i18n.t('Insert Follow-Up Prompt to Input')}</div>
									<Switch bind:state={userConfig.insertFollowUpPrompt} />
								</div>
								<div class="flex items-center justify-between">
									<div class="text-sm">{$i18n.t('Scroll On Branch Change')}</div>
									<Switch bind:state={userConfig.scrollOnBranchChange} />
								</div>
								<div class="flex items-center justify-between">
									<div class="text-sm">{$i18n.t('Web Search in Chat')}</div>
									<button
										class="px-3 py-1.5 text-xs rounded-lg transition bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700"
										on:click={() => {
											userConfig.webSearch = userConfig.webSearch === null ? 'always' : null;
										}}
										type="button"
									>
										{userConfig.webSearch === 'always' ? $i18n.t('Always') : $i18n.t('Default')}
									</button>
								</div>
							</div>

							<hr class="border-gray-100 dark:border-gray-800 my-4" />

							<!-- Display Options -->
							<div class="text-[11px] font-medium text-gray-400 dark:text-gray-500 uppercase tracking-wide mb-3">{$i18n.t('Display Options')}</div>
							<div class="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-3 mb-4">
								<div class="flex items-center justify-between">
									<div class="text-sm">{$i18n.t('Regenerate Menu')}</div>
									<Switch bind:state={userConfig.regenerateMenu} />
								</div>
								<div class="flex items-center justify-between">
									<div class="text-sm">{$i18n.t('Always Collapse Code Blocks')}</div>
									<Switch bind:state={userConfig.collapseCodeBlocks} />
								</div>
								<div class="flex items-center justify-between">
									<div class="text-sm">{$i18n.t('Always Expand Details')}</div>
									<Switch bind:state={userConfig.expandDetails} />
								</div>
								<div class="flex items-center justify-between">
									<div class="text-sm">{$i18n.t('Display Multi-model Responses in Tabs')}</div>
									<Switch bind:state={userConfig.displayMultiModelResponsesInTabs} />
								</div>
								<div class="flex items-center justify-between">
									<div class="text-sm">{$i18n.t('Stylized PDF Export')}</div>
									<Switch bind:state={userConfig.stylizedPdfExport} />
								</div>
								<div class="flex items-center justify-between">
									<div class="text-sm">{$i18n.t('Floating Quick Actions')}</div>
									<div class="flex items-center gap-3">
										{#if userConfig.showFloatingActionButtons}
											<button
												class="text-xs text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 font-medium underline"
												type="button"
												on:click={() => {
													showManageFloatingActionButtonsModal = true;
												}}
											>
												{$i18n.t('Manage')}
											</button>
										{/if}
										<Switch bind:state={userConfig.showFloatingActionButtons} />
									</div>
								</div>
							</div>

							{#if $user?.role === 'admin'}
								<hr class="border-gray-100 dark:border-gray-800 my-4" />
								<div class="text-[11px] font-medium text-gray-400 dark:text-gray-500 uppercase tracking-wide mb-3">{$i18n.t('Admin Settings')}</div>
								<div class="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-3">
									<div class="flex items-center justify-between">
										<div class="text-sm">{$i18n.t('Landing Page Mode')}</div>
										<button
											class="px-3 py-1.5 text-xs rounded-lg transition bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700"
											on:click={() => {
												adminConfig.landingPageMode = adminConfig.landingPageMode === '' ? 'chat' : '';
											}}
											type="button"
										>
											{adminConfig.landingPageMode === '' ? $i18n.t('Default') : $i18n.t('Chat')}
										</button>
									</div>
								</div>
							{/if}

							<!-- Voice -->
							<hr class="border-gray-100 dark:border-gray-800 my-4" />
							<div class="text-[11px] font-medium text-gray-400 dark:text-gray-500 uppercase tracking-wide mb-3">{$i18n.t('Voice')}</div>
							<div class="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-3 mb-4">
								<div class="flex items-center justify-between">
									<div class="text-sm">{$i18n.t('Allow Voice Interruption in Call')}</div>
									<Switch bind:state={userConfig.voiceInterruption} />
								</div>
								<div class="flex items-center justify-between">
									<div class="text-sm">{$i18n.t('Display Emoji in Call')}</div>
									<Switch bind:state={userConfig.showEmojiInCall} />
								</div>
							</div>

							<!-- Artifacts -->
							<hr class="border-gray-100 dark:border-gray-800 my-4" />
							<div class="text-[11px] font-medium text-gray-400 dark:text-gray-500 uppercase tracking-wide mb-3">{$i18n.t('Artifacts')}</div>
							<div class="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-3">
								<div class="flex items-center justify-between">
									<div class="text-sm">{$i18n.t('Detect Artifacts Automatically')}</div>
									<Switch bind:state={userConfig.detectArtifacts} />
								</div>
								<div class="flex items-center justify-between">
									<div class="text-sm">{$i18n.t('iframe Sandbox Allow Same Origin')}</div>
									<Switch bind:state={userConfig.iframeSandboxAllowSameOrigin} />
								</div>
								<div class="flex items-center justify-between">
									<div class="text-sm">{$i18n.t('iframe Sandbox Allow Forms')}</div>
									<Switch bind:state={userConfig.iframeSandboxAllowForms} />
								</div>
							</div>
						{/if}
					</div>
				</div>
			</div>

			<!-- Input Settings -->
			<div class="max-w-5xl mx-auto mb-3.5 bg-gray-50 dark:bg-gray-850 rounded-lg p-5 border border-gray-100 dark:border-gray-800">
				<button
					class="w-full flex items-center justify-between cursor-pointer"
					on:click={() => (expandedSections.input = !expandedSections.input)}
					type="button"
				>
					<div class="flex items-center gap-2.5">
						<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="w-5 h-5 text-gray-500 dark:text-gray-400">
							<path d="M21.731 2.269a2.625 2.625 0 0 0-3.712 0l-1.157 1.157 3.712 3.712 1.157-1.157a2.625 2.625 0 0 0 0-3.712ZM19.513 8.199l-3.712-3.712-8.4 8.4a5.25 5.25 0 0 0-1.32 2.214l-.8 2.685a.75.75 0 0 0 .933.933l2.685-.8a5.25 5.25 0 0 0 2.214-1.32l8.4-8.4Z" />
							<path d="M5.25 5.25a3 3 0 0 0-3 3v10.5a3 3 0 0 0 3 3h10.5a3 3 0 0 0 3-3V13.5a.75.75 0 0 0-1.5 0v5.25a1.5 1.5 0 0 1-1.5 1.5H5.25a1.5 1.5 0 0 1-1.5-1.5V8.25a1.5 1.5 0 0 1 1.5-1.5h5.25a.75.75 0 0 0 0-1.5H5.25Z" />
						</svg>
						<div class="text-sm font-medium text-gray-800 dark:text-gray-100">
							{$i18n.t('Input')}
						</div>
					</div>
					{#if expandedSections.input}
						<ChevronUp className="w-5 h-5 text-gray-500" />
					{:else}
						<ChevronDown className="w-5 h-5 text-gray-500" />
					{/if}
				</button>

				{#if expandedSections.input}
					<hr class="border-gray-100 dark:border-gray-800 my-4" />

					<div class="mb-3 flex w-full items-center justify-between">
						<div class="text-sm">{$i18n.t('Enter Key Behavior')}</div>
						<button
							class="px-3 py-1.5 text-xs rounded-lg transition bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700"
							on:click|stopPropagation={() => {
								userConfig.ctrlEnterToSend = !userConfig.ctrlEnterToSend;
							}}
							type="button"
						>
							{userConfig.ctrlEnterToSend ? $i18n.t('Ctrl+Enter to Send') : $i18n.t('Enter to Send')}
						</button>
					</div>

					<div class="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-3">
						<div class="flex w-full items-center justify-between">
							<div class="text-sm">{$i18n.t('Rich Text Input for Chat')}</div>
							<Switch bind:state={userConfig.richTextInput} />
						</div>

						{#if userConfig.richTextInput}
							<div class="flex w-full items-center justify-between">
								<div class="text-sm">{$i18n.t('Show Formatting Toolbar')}</div>
								<Switch bind:state={userConfig.showFormattingToolbar} />
							</div>

							<div class="flex w-full items-center justify-between">
								<div class="text-sm">{$i18n.t('Insert Prompt as Rich Text')}</div>
								<Switch bind:state={userConfig.insertPromptAsRichText} />
							</div>
						{/if}

						<div class="flex w-full items-center justify-between">
							<div class="text-sm">{$i18n.t('Prompt Autocompletion')}</div>
							<Switch bind:state={userConfig.promptAutocomplete} />
						</div>

						<div class="flex w-full items-center justify-between">
							<div class="text-sm">{$i18n.t('Paste Large Text as File')}</div>
							<Switch bind:state={userConfig.largeTextAsFile} />
						</div>

						<div class="flex w-full items-center justify-between">
							<div class="text-sm">{$i18n.t('Image Compression')}</div>
							<div class="flex items-center gap-3">
								{#if userConfig.imageCompression}
									<button
										class="text-xs text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 font-medium underline"
										type="button"
										on:click|stopPropagation={() => {
											showManageImageCompressionModal = true;
										}}
									>
										{$i18n.t('Manage')}
									</button>
								{/if}
								<Switch bind:state={userConfig.imageCompression} />
							</div>
						</div>

						{#if userConfig.imageCompression}
							<div class="flex w-full items-center justify-between">
								<div class="text-sm">{$i18n.t('Compress Images in Channels')}</div>
								<Switch bind:state={userConfig.imageCompressionInChannels} />
							</div>
						{/if}
					</div>
				{/if}
			</div>


			{#if $user?.role === 'admin'}
				<div class="max-w-5xl mx-auto mb-3.5 bg-gray-50 dark:bg-gray-850 rounded-lg p-5 border border-gray-100 dark:border-gray-800">
					<button
						class="w-full flex items-center justify-between cursor-pointer"
						on:click={() => (expandedSections.adminUI = !expandedSections.adminUI)}
						type="button"
					>
						<div class="flex items-center gap-2.5">
							<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="w-5 h-5 text-gray-500 dark:text-gray-400">
								<path fill-rule="evenodd" d="M11.078 2.25c-.917 0-1.699.663-1.85 1.567L9.05 4.889c-.02.12-.115.26-.297.348a7.493 7.493 0 0 0-.986.57c-.166.115-.334.126-.45.083L6.3 5.508a1.875 1.875 0 0 0-2.282.819l-.922 1.597a1.875 1.875 0 0 0 .432 2.385l.84.692c.095.078.17.229.154.43a7.598 7.598 0 0 0 0 1.139c.015.2-.059.352-.153.43l-.841.692a1.875 1.875 0 0 0-.432 2.385l.922 1.597a1.875 1.875 0 0 0 2.282.818l1.019-.382c.115-.043.283-.031.45.082.312.214.641.405.985.57.182.088.277.228.297.35l.178 1.071c.151.904.933 1.567 1.85 1.567h1.844c.916 0 1.699-.663 1.85-1.567l.178-1.072c.02-.12.114-.26.297-.349.344-.165.673-.356.985-.57.167-.114.335-.125.45-.082l1.02.382a1.875 1.875 0 0 0 2.28-.819l.923-1.597a1.875 1.875 0 0 0-.432-2.385l-.84-.692c-.095-.078-.17-.229-.154-.43a7.614 7.614 0 0 0 0-1.139c-.016-.2.059-.352.153-.43l.84-.692c.708-.582.891-1.59.433-2.385l-.922-1.597a1.875 1.875 0 0 0-2.282-.818l-1.02.382c-.114.043-.282.031-.449-.083a7.49 7.49 0 0 0-.985-.57c-.183-.087-.277-.227-.297-.348l-.179-1.072a1.875 1.875 0 0 0-1.85-1.567h-1.843ZM12 15.75a3.75 3.75 0 1 0 0-7.5 3.75 3.75 0 0 0 0 7.5Z" clip-rule="evenodd" />
							</svg>
							<div class="text-sm font-medium text-gray-800 dark:text-gray-100">
								{$i18n.t('Admin UI')}
							</div>
						</div>
						{#if expandedSections.adminUI}
							<ChevronUp className="w-5 h-5 text-gray-500" />
						{:else}
							<ChevronDown className="w-5 h-5 text-gray-500" />
						{/if}
					</button>

					{#if expandedSections.adminUI}
						<hr class="border-gray-100 dark:border-gray-800 my-4" />

						<!-- Banners -->
						<div class="mb-4">
							<div class="flex w-full justify-between items-center mb-2">
								<div class="text-sm font-medium">{$i18n.t('Banners')}</div>
								<button
									class="p-1.5 px-3 text-xs flex items-center gap-1 rounded-lg transition bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700"
									type="button"
									aria-label="Add Banner"
									on:click|stopPropagation={() => {
										if (banners.length === 0 || banners.at(-1)?.content !== '') {
											banners = [
												...banners,
												{
													id: uuidv4(),
													type: '',
													title: '',
													content: '',
													dismissible: true,
													timestamp: Math.floor(Date.now() / 1000)
												}
											];
										}
									}}
								>
									<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-4 h-4">
										<path d="M10.75 4.75a.75.75 0 00-1.5 0v4.5h-4.5a.75.75 0 000 1.5h4.5v4.5a.75.75 0 001.5 0v-4.5h4.5a.75.75 0 000-1.5h-4.5v-4.5z" />
									</svg>
									{$i18n.t('Add')}
								</button>
							</div>
							<Banners bind:banners />
						</div>

						<!-- Prompt Suggestions -->
						<div>
							<PromptSuggestions bind:promptSuggestions />
							{#if promptSuggestions.length > 0}
								<div class="text-xs text-left w-full mt-2 text-gray-500 dark:text-gray-400">
									{$i18n.t('Adjusting these settings will apply changes universally to all users.')}
								</div>
							{/if}
						</div>
					{/if}
				</div>
			{/if}
		</div>

		<div class="sticky bottom-0 pt-4 pb-4">
			<div class="max-w-5xl mx-auto">
				<div class="flex justify-end px-5">
					<button
						class="px-4 py-2 text-sm font-medium bg-black hover:bg-gray-800 text-white dark:bg-white dark:text-black dark:hover:bg-gray-200 transition-colors rounded-lg"
						type="submit"
					>
						{$i18n.t('Save')}
					</button>
				</div>
			</div>
		</div>
	</form>
{:else}
	<div class=" h-full w-full flex justify-center items-center">
		<Spinner className="size-5" />
	</div>
{/if}
