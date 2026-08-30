<script lang="ts">
	import { config, settings, user } from '$lib/stores';
	import { onMount, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { updateUserInfo } from '$lib/apis/users';
	import { getUserPosition } from '$lib/utils';
	import { normalizeAppFontFamily, setAppFontFamily, setTextScale } from '$lib/utils/text-scale';

	import Minus from '$lib/components/icons/Minus.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import ManageFloatingActionButtonsModal from '$lib/components/chat/Settings/Interface/ManageFloatingActionButtonsModal.svelte';
	import ManageImageCompressionModal from '$lib/components/chat/Settings/Interface/ManageImageCompressionModal.svelte';

	const i18n: any = getContext('i18n');

	export let saveSettings: Function;
	export let settingsValue: Record<string, any> | null = null;
	export let personalSettingsValue: Record<string, any> = {};

	$: currentSettings = (settingsValue ?? $settings ?? {}) as Record<string, any>;
	$: externalSettings = settingsValue !== null;
	$: defaultSettings = ($config?.ui?.default_interface_settings ?? {}) as Record<string, any>;

	let backgroundImageUrl: string | null = null;
	let inputFiles: FileList | null = null;
	let filesInputElement: HTMLInputElement | null = null;

	// Addons
	let titleAutoGenerate = true;
	let autoFollowUps = true;
	let autoTags = true;

	let responseAutoCopy = false;
	let widescreenMode = false;
	let splitLargeChunks = false;
	let scrollOnBranchChange = true;
	let scrollOnResponseGeneration = true;
	let showFilesOnTerminalSelect = true;
	let terminalFileDisplay: 'sidebar' | 'inline' = 'sidebar';
	let userLocation = false;

	// Interface
	let defaultModelId = '';
	let showUsername = false;

	let highContrastMode = false;

	let detectArtifacts = true;
	let displayMultiModelResponsesInTabs = false;

	let richTextInput = true;
	let showFormattingToolbar = false;
	let insertPromptAsRichText = false;
	let promptAutocomplete = false;

	let largeTextAsFile = false;

	let insertSuggestionPrompt = false;
	let keepFollowUpPrompts = false;
	let insertFollowUpPrompt = false;

	let regenerateMenu = true;
	let enableMessageQueue = true;

	let landingPageMode = '';
	let chatBubble = true;
	let chatDirection: 'LTR' | 'RTL' | 'auto' = 'auto';
	let ctrlEnterToSend = false;
	let copyFormatted = false;

	let temporaryChatByDefault = false;
	let chatFadeStreamingText = true;
	let collapseCodeBlocks = false;
	let renderMarkdownInUserMessages = true;
	let renderMarkdownInAssistantMessages = true;
	let expandDetails = false;
	let chatHoverPreview = true;
	let renderMarkdownInPreviews = true;
	let showChatTitleInTab = true;

	let showFloatingActionButtons = true;
	let floatingActionButtons: any = null;

	let imageCompression = false;
	let imageCompressionSize: any = {
		width: '',
		height: ''
	};
	let imageCompressionInChannels = true;

	// chat export
	let stylizedPdfExport = true;

	// Admin - Show Update Available Toast
	let showUpdateToast = true;
	let showChangelog = true;

	// File
	let defaultUploadContext: 'full' | 'focused' = 'focused';

	let showEmojiInCall = false;
	let voiceInterruption = false;
	let hapticFeedback = false;

	let webSearch: string | null = null;

	let iframeSandboxAllowScripts = true;
	let iframeSandboxAllowSameOrigin = false;
	let iframeSandboxAllowForms = true;
	let iframeSandboxAllowDownloads = true;
	let terminalPreviewAllowSameOrigin = false;

	let showManageFloatingActionButtonsModal = false;
	let showManageImageCompressionModal = false;

	let textScale: number | null = null;
	let fontFamily: string | null = null;
	let fontFamilyInput = '';
	let showTextScaleSlider = false;
	let showFontFamilyInput = false;
	const settingRowClass = 'flex items-center justify-between gap-2.5';
	const settingLabelClass = 'min-w-0 text-xs text-gray-600 dark:text-gray-400';
	const settingControlClass = 'flex shrink-0 items-center justify-end gap-1.5';
	const sectionHeadingClass = 'mt-4 text-xs text-gray-400 dark:text-gray-600';
	const firstSectionHeadingClass = 'text-xs text-gray-400 dark:text-gray-600';
	const settingDescriptionClass = 'mt-1.5 text-[0.6875rem] text-gray-400 dark:text-gray-600';
	const actionButtonClass =
		'text-xs text-gray-500 transition-colors hover:text-gray-900 dark:text-gray-500 dark:hover:text-white';

	const hasSettingPath = (source: Record<string, any>, path: string) => {
		let current: any = source;
		for (const part of path.split('.')) {
			if (
				!current ||
				typeof current !== 'object' ||
				!Object.prototype.hasOwnProperty.call(current, part)
			) {
				return false;
			}
			current = current[part];
		}
		return true;
	};

	const settingPathByState: Record<string, string> = {
		titleAutoGenerate: 'title.auto'
	};

	const isDefaultSetting = (stateKey: string) => {
		const path = settingPathByState[stateKey] ?? stateKey;
		return (
			!externalSettings &&
			hasSettingPath(defaultSettings, path) &&
			!hasSettingPath(personalSettingsValue, path)
		);
	};

	const toggleLandingPageMode = async () => {
		landingPageMode = landingPageMode === '' ? 'chat' : '';
		saveSettings({ landingPageMode: landingPageMode });
	};

	const toggleUserLocation = async () => {
		if (externalSettings) {
			saveSettings({ userLocation });
			return;
		}

		if (userLocation) {
			const position = await getUserPosition().catch((error) => {
				toast.error(error.message);
				return null;
			});

			if (position) {
				await updateUserInfo(localStorage.token, { location: position });
				toast.success($i18n.t('User location successfully retrieved.'));
			} else {
				userLocation = false;
			}
		}

		saveSettings({ userLocation });
	};

	const toggleTitleAutoGenerate = async () => {
		saveSettings({
			title: {
				...(currentSettings.title ?? {}),
				auto: titleAutoGenerate
			}
		});
	};

	const toggleResponseAutoCopy = async () => {
		if (externalSettings) {
			saveSettings({ responseAutoCopy: responseAutoCopy });
			return;
		}

		const permission = await navigator.clipboard
			.readText()
			.then(() => {
				return 'granted';
			})
			.catch(() => {
				return '';
			});

		if (permission === 'granted') {
			saveSettings({ responseAutoCopy: responseAutoCopy });
		} else {
			responseAutoCopy = false;
			toast.error(
				$i18n.t(
					'Clipboard write permission denied. Please check your browser settings to grant the necessary access.'
				)
			);
		}
	};

	const toggleChangeChatDirection = async () => {
		if (chatDirection === 'auto') {
			chatDirection = 'LTR';
		} else if (chatDirection === 'LTR') {
			chatDirection = 'RTL';
		} else if (chatDirection === 'RTL') {
			chatDirection = 'auto';
		}
		saveSettings({ chatDirection });
	};

	const togglectrlEnterToSend = async () => {
		ctrlEnterToSend = !ctrlEnterToSend;
		saveSettings({ ctrlEnterToSend });
	};

	export const save = async () => {
		const normalizedFontFamily = normalizeAppFontFamily(fontFamilyInput) || null;
		fontFamily = normalizedFontFamily;
		fontFamilyInput = normalizedFontFamily ?? '';

		if (!externalSettings) {
			setAppFontFamily(fontFamily || defaultFontFamily());
		}

		saveSettings({
			models: [defaultModelId],
			imageCompressionSize: imageCompressionSize,
			fontFamily
		});
	};

	const toggleWebSearch = async () => {
		webSearch = webSearch === null ? 'always' : null;
		saveSettings({ webSearch: webSearch });
	};

	const setTextScaleHandler = (scale: number) => {
		textScale = scale;

		if (!externalSettings) {
			setTextScale(textScale);
		}

		saveSettings({ textScale });
	};

	const defaultFontFamily = () => normalizeAppFontFamily(defaultSettings.fontFamily) || null;

	const previewFontFamily = (value: string) => {
		fontFamilyInput = value;
		fontFamily = normalizeAppFontFamily(value) || null;

		if (!externalSettings) {
			setAppFontFamily(fontFamily || defaultFontFamily());
		}
	};

	const setFontFamilyHandler = (value: string | null) => {
		const normalized = normalizeAppFontFamily(value);
		fontFamily = normalized || null;
		fontFamilyInput = normalized;

		if (!externalSettings) {
			setAppFontFamily(fontFamily || defaultFontFamily());
		}

		saveSettings({ fontFamily });
	};

	const toggleFontFamilyInput = () => {
		if (!showFontFamilyInput && (fontFamily === null || isDefaultSetting('fontFamily'))) {
			fontFamily = fontFamily ?? defaultFontFamily();
			fontFamilyInput = fontFamily ?? '';
			showFontFamilyInput = true;

			if (!externalSettings) {
				setAppFontFamily(fontFamily);
			}
		} else {
			showFontFamilyInput = false;
			fontFamily = null;
			fontFamilyInput = '';

			if (!externalSettings) {
				setAppFontFamily(defaultFontFamily());
			}

			saveSettings({ fontFamily });
		}
	};

	const init = () => {
		titleAutoGenerate = currentSettings?.title?.auto ?? true;
		autoTags = currentSettings?.autoTags ?? true;
		autoFollowUps = currentSettings?.autoFollowUps ?? true;

		highContrastMode = currentSettings?.highContrastMode ?? false;

		detectArtifacts = currentSettings?.detectArtifacts ?? true;
		responseAutoCopy = currentSettings?.responseAutoCopy ?? false;

		showUsername = currentSettings?.showUsername ?? false;
		showUpdateToast = currentSettings?.showUpdateToast ?? true;
		showChangelog = currentSettings?.showChangelog ?? true;

		showEmojiInCall = currentSettings?.showEmojiInCall ?? false;
		voiceInterruption = currentSettings?.voiceInterruption ?? false;

		displayMultiModelResponsesInTabs = currentSettings?.displayMultiModelResponsesInTabs ?? false;
		chatFadeStreamingText = currentSettings?.chatFadeStreamingText ?? true;

		richTextInput = currentSettings?.richTextInput ?? true;
		showFormattingToolbar = currentSettings?.showFormattingToolbar ?? false;
		insertPromptAsRichText = currentSettings?.insertPromptAsRichText ?? false;
		promptAutocomplete = currentSettings?.promptAutocomplete ?? false;

		insertSuggestionPrompt = currentSettings?.insertSuggestionPrompt ?? false;
		keepFollowUpPrompts = currentSettings?.keepFollowUpPrompts ?? false;
		insertFollowUpPrompt = currentSettings?.insertFollowUpPrompt ?? false;

		regenerateMenu = currentSettings?.regenerateMenu ?? true;
		enableMessageQueue = currentSettings?.enableMessageQueue ?? true;

		largeTextAsFile = currentSettings?.largeTextAsFile ?? false;
		copyFormatted = currentSettings?.copyFormatted ?? false;

		collapseCodeBlocks = currentSettings?.collapseCodeBlocks ?? false;
		renderMarkdownInUserMessages = currentSettings?.renderMarkdownInUserMessages ?? true;
		renderMarkdownInAssistantMessages = currentSettings?.renderMarkdownInAssistantMessages ?? true;
		expandDetails = currentSettings?.expandDetails ?? false;
		chatHoverPreview = currentSettings?.chatHoverPreview ?? true;
		renderMarkdownInPreviews = currentSettings?.renderMarkdownInPreviews ?? true;

		landingPageMode = currentSettings?.landingPageMode ?? '';
		chatBubble = currentSettings?.chatBubble ?? true;
		widescreenMode = currentSettings?.widescreenMode ?? false;
		splitLargeChunks = currentSettings?.splitLargeChunks ?? false;
		scrollOnBranchChange = currentSettings?.scrollOnBranchChange ?? true;
		scrollOnResponseGeneration = currentSettings?.scrollOnResponseGeneration ?? true;
		showFilesOnTerminalSelect = currentSettings?.showFilesOnTerminalSelect ?? true;
		terminalFileDisplay = currentSettings?.terminalFileDisplay === 'inline' ? 'inline' : 'sidebar';

		temporaryChatByDefault = currentSettings?.temporaryChatByDefault ?? false;
		chatDirection = currentSettings?.chatDirection ?? 'auto';
		userLocation = currentSettings?.userLocation ?? false;
		showChatTitleInTab = currentSettings?.showChatTitleInTab ?? true;

		iframeSandboxAllowScripts = currentSettings?.iframeSandboxAllowScripts ?? true;
		iframeSandboxAllowSameOrigin = currentSettings?.iframeSandboxAllowSameOrigin ?? false;
		iframeSandboxAllowForms = currentSettings?.iframeSandboxAllowForms ?? true;
		iframeSandboxAllowDownloads = currentSettings?.iframeSandboxAllowDownloads ?? true;
		terminalPreviewAllowSameOrigin = currentSettings?.terminalPreviewAllowSameOrigin ?? false;

		stylizedPdfExport = currentSettings?.stylizedPdfExport ?? true;

		hapticFeedback = currentSettings?.hapticFeedback ?? false;
		ctrlEnterToSend = currentSettings?.ctrlEnterToSend ?? false;

		showFloatingActionButtons = currentSettings?.showFloatingActionButtons ?? true;
		floatingActionButtons = currentSettings?.floatingActionButtons ?? null;

		imageCompression = currentSettings?.imageCompression ?? false;
		imageCompressionSize = currentSettings?.imageCompressionSize ?? { width: '', height: '' };
		imageCompressionInChannels = currentSettings?.imageCompressionInChannels ?? true;

		defaultModelId = currentSettings?.models?.at(0) ?? '';
		if ($config?.default_models) {
			defaultModelId = $config.default_models.split(',')[0];
		}

		backgroundImageUrl = currentSettings?.backgroundImageUrl ?? null;
		webSearch = currentSettings?.webSearch ?? null;

		textScale = currentSettings?.textScale ?? null;
		fontFamily = normalizeAppFontFamily(currentSettings?.fontFamily) || null;
		fontFamilyInput = fontFamily ?? '';
		showTextScaleSlider = false;
		showFontFamilyInput = false;

		defaultUploadContext = currentSettings?.defaultUploadContext ?? 'focused';
	};

	let lastSettingsValue = settingsValue;
	$: if (settingsValue !== lastSettingsValue) {
		lastSettingsValue = settingsValue;
		init();
	}
	onMount(async () => {
		init();
	});
</script>

<ManageFloatingActionButtonsModal
	bind:show={showManageFloatingActionButtonsModal}
	bind:floatingActionButtons
	onSave={() => {
		saveSettings({ floatingActionButtons });
	}}
/>

<ManageImageCompressionModal
	bind:show={showManageImageCompressionModal}
	bind:size={imageCompressionSize}
	onSave={() => {
		saveSettings({ imageCompressionSize });
	}}
/>

<input
	bind:this={filesInputElement}
	bind:files={inputFiles}
	type="file"
	hidden
	accept="image/*"
	on:change={() => {
		let reader = new FileReader();
		reader.onload = (event) => {
			let originalImageUrl = `${(event.target as FileReader).result}`;

			backgroundImageUrl = originalImageUrl;
			saveSettings({ backgroundImageUrl });
		};

		if (
			inputFiles &&
			inputFiles.length > 0 &&
			['image/gif', 'image/webp', 'image/jpeg', 'image/png'].includes(inputFiles[0]['type'])
		) {
			reader.readAsDataURL(inputFiles[0]);
		} else {
			console.log(`Unsupported File Type '${inputFiles?.[0]?.type}'.`);
			inputFiles = null;
		}
	}}
/>

<div class="flex flex-col gap-2.5">
	<h3 class={firstSectionHeadingClass}>{$i18n.t('UI')}</h3>

	<div>
		<div class={settingRowClass}>
			<label id="ui-scale-label" class={settingLabelClass} for="ui-scale-slider">
				{$i18n.t('UI Scale')}
			</label>

			<div class={settingControlClass}>
				<button
					class={actionButtonClass}
					aria-live="polite"
					type="button"
					on:click={() => {
						if (textScale === null || (isDefaultSetting('textScale') && !showTextScaleSlider)) {
							textScale = textScale ?? defaultSettings.textScale ?? 1;
							showTextScaleSlider = true;
						} else {
							showTextScaleSlider = false;
							if (!externalSettings) {
								setTextScale(defaultSettings.textScale ?? 1);
							}
							textScale = null;
							saveSettings({ textScale });
						}
					}}
				>
					{#if textScale === null || (isDefaultSetting('textScale') && !showTextScaleSlider)}
						<span>{$i18n.t('Default')}</span>
					{:else}
						<span>{textScale}x</span>
					{/if}
				</button>
			</div>
		</div>

		{#if textScale !== null && (showTextScaleSlider || !isDefaultSetting('textScale'))}
			<div class=" flex items-center gap-2 px-1 pb-1">
				<button
					type="button"
					class="rounded-lg p-1 transition outline-gray-200 hover:bg-gray-100 dark:outline-gray-700 dark:hover:bg-gray-800"
					on:click={() => {
						textScale = Math.max(1, parseFloat(((textScale ?? 1) - 0.1).toFixed(2)));
						setTextScaleHandler(textScale);
					}}
					aria-labelledby="ui-scale-label"
					aria-label={$i18n.t('Decrease UI Scale')}
				>
					<Minus className="h-3.5 w-3.5" />
				</button>

				<div class="flex-1 flex items-center">
					<input
						id="ui-scale-slider"
						class="w-full"
						type="range"
						min="1"
						max="1.5"
						step={0.01}
						bind:value={textScale}
						on:change={() => {
							setTextScaleHandler(textScale ?? 1);
						}}
						aria-labelledby="ui-scale-label"
						aria-valuemin="1"
						aria-valuemax="1.5"
						aria-valuenow={textScale}
						aria-valuetext={`${textScale}x`}
					/>
				</div>

				<button
					type="button"
					class="rounded-lg p-1 transition outline-gray-200 hover:bg-gray-100 dark:outline-gray-700 dark:hover:bg-gray-800"
					on:click={() => {
						textScale = Math.min(1.5, parseFloat(((textScale ?? 1) + 0.1).toFixed(2)));
						setTextScaleHandler(textScale);
					}}
					aria-labelledby="ui-scale-label"
					aria-label={$i18n.t('Increase UI Scale')}
				>
					<Plus className="h-3.5 w-3.5" />
				</button>
			</div>
		{/if}
		<p class={settingDescriptionClass}>
			{$i18n.t('Set a local zoom level for the app interface.')}
		</p>
	</div>

	<div>
		<div class={settingRowClass}>
			<label id="font-family-label" class={settingLabelClass} for="font-family-input">
				{$i18n.t('Font Family')}
			</label>

			<div class={settingControlClass}>
				<button
					class={actionButtonClass}
					aria-labelledby="font-family-label font-family-state"
					type="button"
					on:click={toggleFontFamilyInput}
				>
					<span id="font-family-state">
						{!showFontFamilyInput && (fontFamily === null || isDefaultSetting('fontFamily'))
							? $i18n.t('Default')
							: $i18n.t('Custom')}
					</span>
				</button>
			</div>
		</div>

		{#if showFontFamilyInput || (fontFamily !== null && !isDefaultSetting('fontFamily'))}
			<div class="mt-1.5 flex items-center pb-1">
				<input
					id="font-family-input"
					class="h-7 w-full rounded-lg border border-gray-100/50 bg-gray-50/40 px-2 text-xs text-gray-700 outline-hidden transition-colors placeholder:text-gray-300 focus:border-blue-400 dark:border-white/[0.04] dark:bg-white/[0.03] dark:text-gray-300 dark:placeholder:text-gray-700 dark:focus:border-blue-500"
					type="text"
					placeholder="Aptos"
					bind:value={fontFamilyInput}
					on:input={(event) => previewFontFamily(event.currentTarget.value)}
					on:change={(event) => setFontFamilyHandler(event.currentTarget.value)}
				/>
			</div>
		{/if}
		<p class={settingDescriptionClass}>
			{$i18n.t('Use a local font family for the app interface.')}
		</p>
	</div>

	<div>
		<div class={settingRowClass}>
			<div id="accessibility-mode-label" class={settingLabelClass}>
				{$i18n.t('Accessibility Mode')}
			</div>

			<div class={settingControlClass}>
				<Switch
					ariaLabelledbyId="accessibility-mode-label"
					tooltip={true}
					bind:state={highContrastMode}
					inherited={isDefaultSetting('highContrastMode')}
					on:change={() => {
						saveSettings({ highContrastMode });
					}}
				/>
			</div>
		</div>
		<p class={settingDescriptionClass}>
			{$i18n.t('Enable accessibility-focused visual enhancements.')}
		</p>
	</div>

	<div>
		<div class={settingRowClass}>
			<div id="use-chat-title-as-tab-title-label" class={settingLabelClass}>
				{$i18n.t('Display Chat Title in Tab')}
			</div>

			<div class={settingControlClass}>
				<Switch
					ariaLabelledbyId="use-chat-title-as-tab-title-label"
					tooltip={true}
					bind:state={showChatTitleInTab}
					inherited={isDefaultSetting('showChatTitleInTab')}
					on:change={() => {
						saveSettings({ showChatTitleInTab });
					}}
				/>
			</div>
		</div>
		<p class={settingDescriptionClass}>
			{$i18n.t('Use the active chat title as the browser tab title.')}
		</p>
	</div>

	<div>
		<div id="allow-user-location-label" class={settingRowClass}>
			<div class={settingLabelClass}>{$i18n.t('Allow User Location')}</div>

			<div class={settingControlClass}>
				<Switch
					ariaLabelledbyId="allow-user-location-label"
					tooltip={true}
					bind:state={userLocation}
					inherited={isDefaultSetting('userLocation')}
					on:change={() => {
						toggleUserLocation();
					}}
				/>
			</div>
		</div>
		<p class={settingDescriptionClass}>
			{$i18n.t('Share your current location with features that can use it.')}
		</p>
	</div>

	<div>
		<div class={settingRowClass}>
			<div id="haptic-feedback-label" class={settingLabelClass}>
				{$i18n.t('Haptic Feedback')} ({$i18n.t('Android')})
			</div>

			<div class={settingControlClass}>
				<Switch
					ariaLabelledbyId="haptic-feedback-label"
					tooltip={true}
					bind:state={hapticFeedback}
					inherited={isDefaultSetting('hapticFeedback')}
					on:change={() => {
						saveSettings({ hapticFeedback });
					}}
				/>
			</div>
		</div>
		<p class={settingDescriptionClass}>
			{$i18n.t('Use device vibration feedback on supported Android devices.')}
		</p>
	</div>

	<div>
		<div class={settingRowClass}>
			<div id="copy-formatted-label" class={settingLabelClass}>
				{$i18n.t('Copy Formatted Text')}
			</div>

			<div class={settingControlClass}>
				<Switch
					ariaLabelledbyId="copy-formatted-label"
					tooltip={true}
					bind:state={copyFormatted}
					inherited={isDefaultSetting('copyFormatted')}
					on:change={() => {
						saveSettings({ copyFormatted });
					}}
				/>
			</div>
		</div>
		<p class={settingDescriptionClass}>
			{$i18n.t('Copy rich formatted content instead of plain text.')}
		</p>
	</div>

	{#if $user?.role === 'admin'}
		<div>
			<div class={settingRowClass}>
				<div id="toast-notifications-label" class={settingLabelClass}>
					{$i18n.t('Toast Notifications for New Updates')}
				</div>

				<div class={settingControlClass}>
					<Switch
						ariaLabelledbyId="toast-notifications-label"
						tooltip={true}
						bind:state={showUpdateToast}
						inherited={isDefaultSetting('showUpdateToast')}
						on:change={() => {
							saveSettings({ showUpdateToast });
						}}
					/>
				</div>
			</div>
			<p class={settingDescriptionClass}>
				{$i18n.t('Show update toasts to admins when new versions are available.')}
			</p>
		</div>

		<div>
			<div class={settingRowClass}>
				<div id="whats-new-label" class={settingLabelClass}>
					{$i18n.t(`Show "What's New" Modal on Login`)}
				</div>

				<div class={settingControlClass}>
					<Switch
						ariaLabelledbyId="whats-new-label"
						tooltip={true}
						bind:state={showChangelog}
						inherited={isDefaultSetting('showChangelog')}
						on:change={() => {
							saveSettings({ showChangelog });
						}}
					/>
				</div>
			</div>
			<p class={settingDescriptionClass}>
				{$i18n.t('Open the changelog modal after sign-in when enabled.')}
			</p>
		</div>
	{/if}

	<div class={sectionHeadingClass}>{$i18n.t('Chat')}</div>

	<div>
		<div class={settingRowClass}>
			<div id="enable-message-queue-label" class={settingLabelClass}>
				{$i18n.t('Enable Message Queue')}
			</div>

			<div class={settingControlClass}>
				<Switch
					ariaLabelledbyId="enable-message-queue-label"
					tooltip={true}
					bind:state={enableMessageQueue}
					inherited={isDefaultSetting('enableMessageQueue')}
					on:change={() => {
						saveSettings({ enableMessageQueue });
					}}
				/>
			</div>
		</div>
		<p class={settingDescriptionClass}>
			{$i18n.t('Queue outgoing messages instead of interrupting active responses.')}
		</p>
	</div>

	<div>
		<div class={settingRowClass}>
			<div id="chat-direction-label" class={settingLabelClass}>
				{$i18n.t('Chat Direction')}
			</div>

			<button
				aria-labelledby="chat-direction-label chat-direction-mode"
				class={actionButtonClass}
				on:click={toggleChangeChatDirection}
				type="button"
			>
				<span id="chat-direction-mode">
					{chatDirection === 'LTR'
						? $i18n.t('LTR')
						: chatDirection === 'RTL'
							? $i18n.t('RTL')
							: $i18n.t('Auto')}
				</span>
			</button>
		</div>
		<p class={settingDescriptionClass}>
			{$i18n.t('Choose automatic, left-to-right, or right-to-left text flow.')}
		</p>
	</div>

	<div>
		<div class={settingRowClass}>
			<div id="landing-page-mode-label" class={settingLabelClass}>
				{$i18n.t('Landing Page Mode')}
			</div>

			<button
				aria-labelledby="landing-page-mode-label notification-sound-state"
				class={actionButtonClass}
				on:click={() => {
					toggleLandingPageMode();
				}}
				type="button"
			>
				<span id="notification-sound-state"
					>{landingPageMode === '' ? $i18n.t('Default') : $i18n.t('Chat')}</span
				>
			</button>
		</div>
		<p class={settingDescriptionClass}>
			{$i18n.t('Choose whether the app opens to the default home or chat view.')}
		</p>
	</div>

	<div>
		<div class={settingRowClass}>
			<div id="chat-background-label" class={settingLabelClass}>
				{$i18n.t('Chat Background Image')}
			</div>

			<button
				aria-labelledby="chat-background-label background-image-url-state"
				class={actionButtonClass}
				on:click={() => {
					if (backgroundImageUrl !== null) {
						backgroundImageUrl = null;
						saveSettings({ backgroundImageUrl });
					} else {
						filesInputElement?.click();
					}
				}}
				type="button"
			>
				<span id="background-image-url-state"
					>{backgroundImageUrl !== null ? $i18n.t('Reset') : $i18n.t('Upload')}</span
				>
			</button>
		</div>
		<p class={settingDescriptionClass}>
			{$i18n.t('Upload or reset the image shown behind chat content.')}
		</p>
	</div>

	<div>
		<div class={settingRowClass}>
			<div id="chat-bubble-ui-label" class={settingLabelClass}>
				{$i18n.t('Chat Bubble UI')}
			</div>

			<div class={settingControlClass}>
				<Switch
					tooltip={true}
					ariaLabelledbyId="chat-bubble-ui-label"
					bind:state={chatBubble}
					inherited={isDefaultSetting('chatBubble')}
					on:change={() => {
						saveSettings({ chatBubble });
					}}
				/>
			</div>
		</div>
		<p class={settingDescriptionClass}>
			{$i18n.t('Render messages in compact bubble containers.')}
		</p>
	</div>

	{#if !chatBubble}
		<div>
			<div class={settingRowClass}>
				<div id="chat-bubble-username-label" class={settingLabelClass}>
					{$i18n.t('Display the Username Instead of You in the Chat')}
				</div>

				<div class={settingControlClass}>
					<Switch
						ariaLabelledbyId="chat-bubble-username-label"
						tooltip={true}
						bind:state={showUsername}
						inherited={isDefaultSetting('showUsername')}
						on:change={() => {
							saveSettings({ showUsername });
						}}
					/>
				</div>
			</div>
			<p class={settingDescriptionClass}>
				{$i18n.t('Show your username label instead of You in chat bubbles.')}
			</p>
		</div>
	{/if}

	<div>
		<div class={settingRowClass}>
			<div id="widescreen-mode-label" class={settingLabelClass}>
				{$i18n.t('Widescreen Mode')}
			</div>

			<div class={settingControlClass}>
				<Switch
					ariaLabelledbyId="widescreen-mode-label"
					tooltip={true}
					bind:state={widescreenMode}
					inherited={isDefaultSetting('widescreenMode')}
					on:change={() => {
						saveSettings({ widescreenMode });
					}}
				/>
			</div>
		</div>
		<p class={settingDescriptionClass}>
			{$i18n.t('Use a wider chat layout on large displays.')}
		</p>
	</div>

	{#if $user?.role === 'admin' || $user?.permissions?.chat?.temporary}
		<div>
			<div class={settingRowClass}>
				<div id="temp-chat-default-label" class={settingLabelClass}>
					{$i18n.t('Temporary Chat by Default')}
				</div>

				<div class={settingControlClass}>
					<Switch
						ariaLabelledbyId="temp-chat-default-label"
						tooltip={true}
						bind:state={temporaryChatByDefault}
						inherited={isDefaultSetting('temporaryChatByDefault')}
						on:change={() => {
							saveSettings({ temporaryChatByDefault });
						}}
					/>
				</div>
			</div>
			<p class={settingDescriptionClass}>
				{$i18n.t('Start new chats as temporary unless changed.')}
			</p>
		</div>
	{/if}

	<div>
		<div class={settingRowClass}>
			<div id="fade-streaming-label" class={settingLabelClass}>
				{$i18n.t('Fade Effect for Streaming Text')}
			</div>

			<div class={settingControlClass}>
				<Switch
					ariaLabelledbyId="fade-streaming-label"
					tooltip={true}
					bind:state={chatFadeStreamingText}
					inherited={isDefaultSetting('chatFadeStreamingText')}
					on:change={() => {
						saveSettings({ chatFadeStreamingText });
					}}
				/>
			</div>
		</div>
		<p class={settingDescriptionClass}>
			{$i18n.t('Fade streaming text as it arrives.')}
		</p>
	</div>

	<div>
		<div class={settingRowClass}>
			<div id="render-markdown-user-label" class={settingLabelClass}>
				{$i18n.t('Render Markdown in User Messages')}
			</div>

			<div class={settingControlClass}>
				<Switch
					ariaLabelledbyId="render-markdown-user-label"
					tooltip={true}
					bind:state={renderMarkdownInUserMessages}
					inherited={isDefaultSetting('renderMarkdownInUserMessages')}
					on:change={() => {
						saveSettings({ renderMarkdownInUserMessages });
					}}
				/>
			</div>
		</div>
		<p class={settingDescriptionClass}>
			{$i18n.t('Format Markdown syntax in your own messages.')}
		</p>
	</div>

	<div>
		<div class={settingRowClass}>
			<div id="render-markdown-assistant-label" class={settingLabelClass}>
				{$i18n.t('Render Markdown in Assistant Messages')}
			</div>

			<div class={settingControlClass}>
				<Switch
					ariaLabelledbyId="render-markdown-assistant-label"
					tooltip={true}
					bind:state={renderMarkdownInAssistantMessages}
					inherited={isDefaultSetting('renderMarkdownInAssistantMessages')}
					on:change={() => {
						saveSettings({ renderMarkdownInAssistantMessages });
					}}
				/>
			</div>
		</div>
		<p class={settingDescriptionClass}>
			{$i18n.t('Format Markdown syntax in assistant responses.')}
		</p>
	</div>

	<div>
		<div class={settingRowClass}>
			<div id="render-markdown-in-previews-label" class={settingLabelClass}>
				{$i18n.t('Render Markdown in Previews')}
			</div>

			<div class={settingControlClass}>
				<Switch
					ariaLabelledbyId="render-markdown-in-previews-label"
					tooltip={true}
					bind:state={renderMarkdownInPreviews}
					inherited={isDefaultSetting('renderMarkdownInPreviews')}
					on:change={() => {
						saveSettings({ renderMarkdownInPreviews });
					}}
				/>
			</div>
		</div>
		<p class={settingDescriptionClass}>
			{$i18n.t('Format Markdown in previews and compact content surfaces.')}
		</p>
	</div>

	<div>
		<div class={settingRowClass}>
			<div id="auto-generation-label" class={settingLabelClass}>
				{$i18n.t('Title Auto-Generation')}
			</div>

			<div class={settingControlClass}>
				<Switch
					ariaLabelledbyId="auto-generation-label"
					tooltip={true}
					bind:state={titleAutoGenerate}
					inherited={isDefaultSetting('titleAutoGenerate')}
					on:change={() => {
						toggleTitleAutoGenerate();
					}}
				/>
			</div>
		</div>
		<p class={settingDescriptionClass}>
			{$i18n.t('Generate chat titles automatically from conversation content.')}
		</p>
	</div>

	<div>
		<div class={settingRowClass}>
			<div class={settingLabelClass} id="follow-up-auto-generation-label">
				{$i18n.t('Follow-Up Auto-Generation')}
			</div>

			<div class={settingControlClass}>
				<Switch
					ariaLabelledbyId="follow-up-auto-generation-label"
					tooltip={true}
					bind:state={autoFollowUps}
					inherited={isDefaultSetting('autoFollowUps')}
					on:change={() => {
						saveSettings({ autoFollowUps });
					}}
				/>
			</div>
		</div>
		<p class={settingDescriptionClass}>
			{$i18n.t('Generate suggested follow-up prompts after responses.')}
		</p>
	</div>

	<div>
		<div class={settingRowClass}>
			<div id="chat-tags-label" class={settingLabelClass}>
				{$i18n.t('Chat Tags Auto-Generation')}
			</div>

			<div class={settingControlClass}>
				<Switch
					ariaLabelledbyId="chat-tags-label"
					tooltip={true}
					bind:state={autoTags}
					inherited={isDefaultSetting('autoTags')}
					on:change={() => {
						saveSettings({ autoTags });
					}}
				/>
			</div>
		</div>
		<p class={settingDescriptionClass}>
			{$i18n.t('Generate tags for chats automatically.')}
		</p>
	</div>

	<div>
		<div class={settingRowClass}>
			<div id="auto-copy-label" class={settingLabelClass}>
				{$i18n.t('Auto-Copy Response to Clipboard')}
			</div>

			<div class={settingControlClass}>
				<Switch
					ariaLabelledbyId="auto-copy-label"
					tooltip={true}
					bind:state={responseAutoCopy}
					inherited={isDefaultSetting('responseAutoCopy')}
					on:change={() => {
						toggleResponseAutoCopy();
					}}
				/>
			</div>
		</div>
		<p class={settingDescriptionClass}>
			{$i18n.t('Copy the latest assistant response when it completes.')}
		</p>
	</div>

	<div>
		<div class={settingRowClass}>
			<div id="response-auto-scroll-label" class={settingLabelClass}>
				{$i18n.t('Response Auto-Scroll')}
			</div>

			<div class={settingControlClass}>
				<Switch
					ariaLabelledbyId="response-auto-scroll-label"
					tooltip={true}
					bind:state={scrollOnResponseGeneration}
					inherited={isDefaultSetting('scrollOnResponseGeneration')}
					on:change={() => {
						saveSettings({ scrollOnResponseGeneration });
					}}
				/>
			</div>
		</div>
		<p class={settingDescriptionClass}>
			{$i18n.t('Follow assistant responses as they are generated.')}
		</p>
	</div>

	<div>
		<div class={settingRowClass}>
			<div id="scroll-on-branch-change-label" class={settingLabelClass}>
				{$i18n.t('Scroll On Branch Change')}
			</div>

			<div class={settingControlClass}>
				<Switch
					ariaLabelledbyId="scroll-on-branch-change-label"
					tooltip={true}
					bind:state={scrollOnBranchChange}
					inherited={isDefaultSetting('scrollOnBranchChange')}
					on:change={() => {
						saveSettings({ scrollOnBranchChange });
					}}
				/>
			</div>
		</div>
		<p class={settingDescriptionClass}>
			{$i18n.t('Scroll to the active branch when switching response branches.')}
		</p>
	</div>

	<div>
		<div class={settingRowClass}>
			<div id="insert-suggestion-prompt-label" class={settingLabelClass}>
				{$i18n.t('Insert Suggestion Prompt to Input')}
			</div>

			<div class={settingControlClass}>
				<Switch
					ariaLabelledbyId="insert-suggestion-prompt-label"
					tooltip={true}
					bind:state={insertSuggestionPrompt}
					inherited={isDefaultSetting('insertSuggestionPrompt')}
					on:change={() => {
						saveSettings({ insertSuggestionPrompt });
					}}
				/>
			</div>
		</div>
		<p class={settingDescriptionClass}>
			{$i18n.t('Place selected suggestion text into the composer.')}
		</p>
	</div>

	<div>
		<div class={settingRowClass}>
			<div id="keep-follow-up-prompts-label" class={settingLabelClass}>
				{$i18n.t('Keep Follow-Up Prompts in Chat')}
			</div>

			<div class={settingControlClass}>
				<Switch
					ariaLabelledbyId="keep-follow-up-prompts-label"
					tooltip={true}
					bind:state={keepFollowUpPrompts}
					inherited={isDefaultSetting('keepFollowUpPrompts')}
					on:change={() => {
						saveSettings({ keepFollowUpPrompts });
					}}
				/>
			</div>
		</div>
		<p class={settingDescriptionClass}>
			{$i18n.t('Keep generated follow-up prompts visible in the chat.')}
		</p>
	</div>

	<div>
		<div class={settingRowClass}>
			<div id="insert-follow-up-prompt-label" class={settingLabelClass}>
				{$i18n.t('Insert Follow-Up Prompt to Input')}
			</div>

			<div class={settingControlClass}>
				<Switch
					ariaLabelledbyId="insert-follow-up-prompt-label"
					tooltip={true}
					bind:state={insertFollowUpPrompt}
					inherited={isDefaultSetting('insertFollowUpPrompt')}
					on:change={() => {
						saveSettings({ insertFollowUpPrompt });
					}}
				/>
			</div>
		</div>
		<p class={settingDescriptionClass}>
			{$i18n.t('Insert selected follow-up prompts directly into the composer.')}
		</p>
	</div>

	<div>
		<div class={settingRowClass}>
			<div id="regenerate-menu-label" class={settingLabelClass}>
				{$i18n.t('Regenerate Menu')}
			</div>

			<div class={settingControlClass}>
				<Switch
					ariaLabelledbyId="regenerate-menu-label"
					tooltip={true}
					bind:state={regenerateMenu}
					inherited={isDefaultSetting('regenerateMenu')}
					on:change={() => {
						saveSettings({ regenerateMenu });
					}}
				/>
			</div>
		</div>
		<p class={settingDescriptionClass}>
			{$i18n.t('Show the regenerate action menu for assistant responses.')}
		</p>
	</div>

	<div>
		<div class={settingRowClass}>
			<div id="always-collapse-label" class={settingLabelClass}>
				{$i18n.t('Always Collapse Code Blocks')}
			</div>

			<div class={settingControlClass}>
				<Switch
					ariaLabelledbyId="always-collapse-label"
					tooltip={true}
					bind:state={collapseCodeBlocks}
					inherited={isDefaultSetting('collapseCodeBlocks')}
					on:change={() => {
						saveSettings({ collapseCodeBlocks });
					}}
				/>
			</div>
		</div>
		<p class={settingDescriptionClass}>
			{$i18n.t('Collapse code blocks by default.')}
		</p>
	</div>

	<div>
		<div class={settingRowClass}>
			<div id="always-expand-label" class={settingLabelClass}>
				{$i18n.t('Always Expand Details')}
			</div>

			<div class={settingControlClass}>
				<Switch
					ariaLabelledbyId="always-expand-label"
					tooltip={true}
					bind:state={expandDetails}
					inherited={isDefaultSetting('expandDetails')}
					on:change={() => {
						saveSettings({ expandDetails });
					}}
				/>
			</div>
		</div>
		<p class={settingDescriptionClass}>
			{$i18n.t('Open detail blocks by default.')}
		</p>
	</div>

	<div>
		<div class={settingRowClass}>
			<div id="chat-hover-preview-label" class={settingLabelClass}>
				{$i18n.t('Chat Hover Previews')}
			</div>

			<div class={settingControlClass}>
				<Switch
					ariaLabelledbyId="chat-hover-preview-label"
					tooltip={true}
					bind:state={chatHoverPreview}
					inherited={isDefaultSetting('chatHoverPreview')}
					on:change={() => {
						saveSettings({ chatHoverPreview });
					}}
				/>
			</div>
		</div>
		<p class={settingDescriptionClass}>
			{$i18n.t('Show a floating preview of recent messages when hovering a chat in the sidebar.')}
		</p>
	</div>

	<div>
		<div class={settingRowClass}>
			<div id="keep-followup-prompts-label" class={settingLabelClass}>
				{$i18n.t('Display Multi-model Responses in Tabs')}
			</div>

			<div class={settingControlClass}>
				<Switch
					ariaLabelledbyId="keep-followup-prompts-label"
					tooltip={true}
					bind:state={displayMultiModelResponsesInTabs}
					inherited={isDefaultSetting('displayMultiModelResponsesInTabs')}
					on:change={() => {
						saveSettings({ displayMultiModelResponsesInTabs });
					}}
				/>
			</div>
		</div>
		<p class={settingDescriptionClass}>
			{$i18n.t('Group multi-model responses into tabs.')}
		</p>
	</div>

	<div>
		<div class={settingRowClass}>
			<div id="terminal-file-display-label" class={settingLabelClass}>
				{$i18n.t('Terminal File Display')}
			</div>

			<button
				aria-labelledby="terminal-file-display-label terminal-file-display-state"
				class={actionButtonClass}
				on:click={() => {
					terminalFileDisplay = terminalFileDisplay === 'inline' ? 'sidebar' : 'inline';
					saveSettings({ terminalFileDisplay });
				}}
				type="button"
			>
				<span id="terminal-file-display-state">
					{terminalFileDisplay === 'inline' ? $i18n.t('Inline') : $i18n.t('Sidebar')}
				</span>
			</button>
		</div>
		<p class={settingDescriptionClass}>
			{$i18n.t('Choose where terminal display_file results appear by default.')}
		</p>
	</div>

	<div>
		<div class={settingRowClass}>
			<div id="show-files-on-terminal-select-label" class={settingLabelClass}>
				{$i18n.t('Show Files on Terminal Select')}
			</div>

			<div class={settingControlClass}>
				<Switch
					ariaLabelledbyId="show-files-on-terminal-select-label"
					tooltip={true}
					bind:state={showFilesOnTerminalSelect}
					inherited={isDefaultSetting('showFilesOnTerminalSelect')}
					on:change={() => {
						saveSettings({ showFilesOnTerminalSelect });
					}}
				/>
			</div>
		</div>
		<p class={settingDescriptionClass}>
			{$i18n.t('Open the file browser after selecting a terminal.')}
		</p>
	</div>

	<div>
		<div class={settingRowClass}>
			<div id="terminal-preview-allow-same-origin-label" class={settingLabelClass}>
				{$i18n.t('Terminal Preview Allow Same Origin')}
			</div>

			<div class={settingControlClass}>
				<Switch
					ariaLabelledbyId="terminal-preview-allow-same-origin-label"
					tooltip={true}
					bind:state={terminalPreviewAllowSameOrigin}
					inherited={isDefaultSetting('terminalPreviewAllowSameOrigin')}
					on:change={() => {
						saveSettings({ terminalPreviewAllowSameOrigin });
					}}
				/>
			</div>
		</div>
		<p class={settingDescriptionClass}>
			{$i18n.t('Allow terminal previews to access same-origin browser APIs.')}
		</p>
	</div>

	<div>
		<div class={settingRowClass}>
			<div id="stylized-pdf-export-label" class={settingLabelClass}>
				{$i18n.t('Stylized PDF Export')}
			</div>

			<div class={settingControlClass}>
				<Switch
					ariaLabelledbyId="stylized-pdf-export-label"
					tooltip={true}
					bind:state={stylizedPdfExport}
					inherited={isDefaultSetting('stylizedPdfExport')}
					on:change={() => {
						saveSettings({ stylizedPdfExport });
					}}
				/>
			</div>
		</div>
		<p class={settingDescriptionClass}>
			{$i18n.t('Use styled formatting when exporting chats to PDF.')}
		</p>
	</div>

	<div>
		<div class={settingRowClass}>
			<div id="floating-action-buttons-label" class={settingLabelClass}>
				{$i18n.t('Floating Quick Actions')}
			</div>

			<div class={settingControlClass}>
				{#if showFloatingActionButtons}
					<button
						class={actionButtonClass}
						type="button"
						aria-label={$i18n.t('Open Modal To Manage Floating Quick Actions')}
						on:click={() => {
							showManageFloatingActionButtonsModal = true;
						}}
					>
						{$i18n.t('Manage')}
					</button>
				{/if}

				<Switch
					ariaLabelledbyId="floating-action-buttons-label"
					tooltip={true}
					bind:state={showFloatingActionButtons}
					inherited={isDefaultSetting('showFloatingActionButtons')}
					on:change={() => {
						saveSettings({ showFloatingActionButtons });
					}}
				/>
			</div>
		</div>
		<p class={settingDescriptionClass}>
			{$i18n.t('Show the floating quick-action toolbar in chat.')}
		</p>
	</div>

	<div>
		<div class={settingRowClass}>
			<div id="web-search-in-chat-label" class={settingLabelClass}>
				{$i18n.t('Web Search in Chat')}
			</div>

			<button
				aria-labelledby="web-search-in-chat-label web-search-state"
				class={actionButtonClass}
				on:click={() => {
					toggleWebSearch();
				}}
				type="button"
			>
				<span id="web-search-state"
					>{webSearch === 'always' ? $i18n.t('Always') : $i18n.t('Default')}</span
				>
			</button>
		</div>
		<p class={settingDescriptionClass}>
			{$i18n.t('Set web search availability for new chats.')}
		</p>
	</div>

	<div class={sectionHeadingClass}>{$i18n.t('Input')}</div>

	<div>
		<div class={settingRowClass}>
			<div id="enter-key-behavior-label ctrl-enter-to-send-state" class={settingLabelClass}>
				{$i18n.t('Enter Key Behavior')}
			</div>

			<button
				aria-labelledby="enter-key-behavior-label"
				class={actionButtonClass}
				on:click={() => {
					togglectrlEnterToSend();
				}}
				type="button"
			>
				<span id="ctrl-enter-to-send-state"
					>{ctrlEnterToSend === true
						? $i18n.t('Ctrl+Enter to Send')
						: $i18n.t('Enter to Send')}</span
				>
			</button>
		</div>
		<p class={settingDescriptionClass}>
			{$i18n.t('Choose whether Enter sends immediately or uses Ctrl+Enter.')}
		</p>
	</div>

	<div>
		<div class={settingRowClass}>
			<div id="rich-input-label" class={settingLabelClass}>
				{$i18n.t('Rich Text Input for Chat')}
			</div>

			<div class={settingControlClass}>
				<Switch
					tooltip={true}
					ariaLabelledbyId="rich-input-label"
					bind:state={richTextInput}
					inherited={isDefaultSetting('richTextInput')}
					on:change={() => {
						saveSettings({ richTextInput });
					}}
				/>
			</div>
		</div>
		<p class={settingDescriptionClass}>
			{$i18n.t('Use the rich composer instead of a plain textarea.')}
		</p>
	</div>

	{#if $config?.features?.enable_autocomplete_generation}
		<div>
			<div class={settingRowClass}>
				<div id="prompt-autocompletion-label" class={settingLabelClass}>
					{$i18n.t('Prompt Autocompletion')}
				</div>

				<div class={settingControlClass}>
					<Switch
						ariaLabelledbyId="prompt-autocompletion-label"
						tooltip={true}
						bind:state={promptAutocomplete}
						inherited={isDefaultSetting('promptAutocomplete')}
						on:change={() => {
							saveSettings({ promptAutocomplete });
						}}
					/>
				</div>
			</div>
			<p class={settingDescriptionClass}>
				{$i18n.t('Suggest completions while composing prompts.')}
			</p>
		</div>
	{/if}

	{#if richTextInput}
		<div>
			<div class={settingRowClass}>
				<div id="show-formatting-toolbar-label" class={settingLabelClass}>
					{$i18n.t('Show Formatting Toolbar')}
				</div>

				<div class={settingControlClass}>
					<Switch
						ariaLabelledbyId="show-formatting-toolbar-label"
						tooltip={true}
						bind:state={showFormattingToolbar}
						inherited={isDefaultSetting('showFormattingToolbar')}
						on:change={() => {
							saveSettings({ showFormattingToolbar });
						}}
					/>
				</div>
			</div>
			<p class={settingDescriptionClass}>
				{$i18n.t('Show formatting controls in the rich text composer.')}
			</p>
		</div>

		<div>
			<div class={settingRowClass}>
				<div id="insert-prompt-as-rich-text-label" class={settingLabelClass}>
					{$i18n.t('Insert Prompt as Rich Text')}
				</div>

				<div class={settingControlClass}>
					<Switch
						ariaLabelledbyId="insert-prompt-as-rich-text-label"
						tooltip={true}
						bind:state={insertPromptAsRichText}
						inherited={isDefaultSetting('insertPromptAsRichText')}
						on:change={() => {
							saveSettings({ insertPromptAsRichText });
						}}
					/>
				</div>
			</div>
			<p class={settingDescriptionClass}>
				{$i18n.t('Paste inserted prompts as rich text when possible.')}
			</p>
		</div>
	{/if}

	<div>
		<div class={settingRowClass}>
			<div id="paste-large-label" class={settingLabelClass}>
				{$i18n.t('Paste Large Text as File')}
			</div>

			<div class={settingControlClass}>
				<Switch
					tooltip={true}
					ariaLabelledbyId="paste-large-label"
					bind:state={largeTextAsFile}
					inherited={isDefaultSetting('largeTextAsFile')}
					on:change={() => {
						saveSettings({ largeTextAsFile });
					}}
				/>
			</div>
		</div>
		<p class={settingDescriptionClass}>
			{$i18n.t('Convert long pasted text into a file attachment.')}
		</p>
	</div>

	<div class={sectionHeadingClass}>{$i18n.t('Artifacts')}</div>

	<div>
		<div class={settingRowClass}>
			<div id="detect-artifacts-label" class={settingLabelClass}>
				{$i18n.t('Detect Artifacts Automatically')}
			</div>

			<div class={settingControlClass}>
				<Switch
					ariaLabelledbyId="detect-artifacts-label"
					tooltip={true}
					bind:state={detectArtifacts}
					inherited={isDefaultSetting('detectArtifacts')}
					on:change={() => {
						saveSettings({ detectArtifacts });
					}}
				/>
			</div>
		</div>
		<p class={settingDescriptionClass}>
			{$i18n.t('Detect generated artifacts and show them in the artifact workspace.')}
		</p>
	</div>

	<div>
		<div class={settingRowClass}>
			<div id="iframe-sandbox-allow-scripts-label" class={settingLabelClass}>
				{$i18n.t('iframe Sandbox Allow Scripts')}
			</div>

			<div class={settingControlClass}>
				<Switch
					ariaLabelledbyId="iframe-sandbox-allow-scripts-label"
					tooltip={true}
					bind:state={iframeSandboxAllowScripts}
					inherited={isDefaultSetting('iframeSandboxAllowScripts')}
					on:change={() => {
						saveSettings({ iframeSandboxAllowScripts });
					}}
				/>
			</div>
		</div>
		<p class={settingDescriptionClass}>
			{$i18n.t('Allow scripts inside sandboxed iframes.')}
		</p>
	</div>

	<div>
		<div class={settingRowClass}>
			<div id="iframe-sandbox-allow-same-origin-label" class={settingLabelClass}>
				{$i18n.t('iframe Sandbox Allow Same Origin')}
			</div>

			<div class={settingControlClass}>
				<Switch
					ariaLabelledbyId="iframe-sandbox-allow-same-origin-label"
					tooltip={true}
					bind:state={iframeSandboxAllowSameOrigin}
					inherited={isDefaultSetting('iframeSandboxAllowSameOrigin')}
					on:change={() => {
						saveSettings({ iframeSandboxAllowSameOrigin });
					}}
				/>
			</div>
		</div>
		<p class={settingDescriptionClass}>
			{$i18n.t('Allow artifacts to access same-origin browser APIs inside the sandbox.')}
		</p>
	</div>

	<div>
		<div class={settingRowClass}>
			<div id="iframe-sandbox-allow-forms-label" class={settingLabelClass}>
				{$i18n.t('iframe Sandbox Allow Forms')}
			</div>

			<div class={settingControlClass}>
				<Switch
					ariaLabelledbyId="iframe-sandbox-allow-forms-label"
					tooltip={true}
					bind:state={iframeSandboxAllowForms}
					inherited={isDefaultSetting('iframeSandboxAllowForms')}
					on:change={() => {
						saveSettings({ iframeSandboxAllowForms });
					}}
				/>
			</div>
		</div>
		<p class={settingDescriptionClass}>
			{$i18n.t('Allow forms inside sandboxed artifact iframes.')}
		</p>
	</div>

	<div>
		<div class={settingRowClass}>
			<div id="iframe-sandbox-allow-downloads-label" class={settingLabelClass}>
				{$i18n.t('iframe Sandbox Allow Downloads')}
			</div>

			<div class={settingControlClass}>
				<Switch
					ariaLabelledbyId="iframe-sandbox-allow-downloads-label"
					tooltip={true}
					bind:state={iframeSandboxAllowDownloads}
					inherited={isDefaultSetting('iframeSandboxAllowDownloads')}
					on:change={() => {
						saveSettings({ iframeSandboxAllowDownloads });
					}}
				/>
			</div>
		</div>
		<p class={settingDescriptionClass}>
			{$i18n.t('Allow downloads inside sandboxed iframes.')}
		</p>
	</div>

	<div class={sectionHeadingClass}>{$i18n.t('Voice')}</div>

	<div>
		<div class={settingRowClass}>
			<div class={settingLabelClass} id="allow-voice-interruption-in-call-label">
				{$i18n.t('Allow Voice Interruption in Call')}
			</div>

			<div class={settingControlClass}>
				<Switch
					ariaLabelledbyId="allow-voice-interruption-in-call-label"
					tooltip={true}
					bind:state={voiceInterruption}
					inherited={isDefaultSetting('voiceInterruption')}
					on:change={() => {
						saveSettings({ voiceInterruption });
					}}
				/>
			</div>
		</div>
		<p class={settingDescriptionClass}>
			{$i18n.t('Let speech interrupt the assistant during a voice call.')}
		</p>
	</div>

	<div>
		<div class={settingRowClass}>
			<div id="display-emoji-label" class={settingLabelClass}>
				{$i18n.t('Display Emoji in Call')}
			</div>

			<div class={settingControlClass}>
				<Switch
					ariaLabelledbyId="display-emoji-label"
					tooltip={true}
					bind:state={showEmojiInCall}
					inherited={isDefaultSetting('showEmojiInCall')}
					on:change={() => {
						saveSettings({ showEmojiInCall });
					}}
				/>
			</div>
		</div>
		<p class={settingDescriptionClass}>
			{$i18n.t('Show emoji feedback in the call interface.')}
		</p>
	</div>

	<div class={sectionHeadingClass}>{$i18n.t('File')}</div>

	<div>
		<div class={settingRowClass}>
			<div id="default-upload-mode-label" class={settingLabelClass}>
				{$i18n.t('Default Upload Mode')}
			</div>

			<button
				aria-labelledby="default-upload-mode-label default-upload-mode-state"
				class={actionButtonClass}
				on:click={() => {
					defaultUploadContext = defaultUploadContext === 'full' ? 'focused' : 'full';
					saveSettings({ defaultUploadContext });
				}}
				type="button"
			>
				<span id="default-upload-mode-state">
					{defaultUploadContext === 'full'
						? $i18n.t('Using Entire Document')
						: $i18n.t('Using Focused Retrieval')}
				</span>
			</button>
		</div>
		<p class={settingDescriptionClass}>
			{$i18n.t('Attach files with full content or focused retrieval by default.')}
		</p>
	</div>

	<div>
		<div class={settingRowClass}>
			<div id="image-compression-label" class={settingLabelClass}>
				{$i18n.t('Image Compression')}
			</div>

			<div class={settingControlClass}>
				{#if imageCompression}
					<button
						class={actionButtonClass}
						type="button"
						aria-label={$i18n.t('Open Modal To Manage Image Compression')}
						on:click={() => {
							showManageImageCompressionModal = true;
						}}
					>
						{$i18n.t('Manage')}
					</button>
				{/if}

				<Switch
					ariaLabelledbyId="image-compression-label"
					tooltip={true}
					bind:state={imageCompression}
					inherited={isDefaultSetting('imageCompression')}
					on:change={() => {
						saveSettings({ imageCompression });
					}}
				/>
			</div>
		</div>
		<p class={settingDescriptionClass}>
			{$i18n.t('Compress uploaded images before sending or storage.')}
		</p>
	</div>

	{#if imageCompression}
		<div>
			<div class={settingRowClass}>
				<div id="image-compression-in-channels-label" class={settingLabelClass}>
					{$i18n.t('Compress Images in Channels')}
				</div>

				<div class={settingControlClass}>
					<Switch
						ariaLabelledbyId="image-compression-in-channels-label"
						tooltip={true}
						bind:state={imageCompressionInChannels}
						inherited={isDefaultSetting('imageCompressionInChannels')}
						on:change={() => {
							saveSettings({ imageCompressionInChannels });
						}}
					/>
				</div>
			</div>
			<p class={settingDescriptionClass}>
				{$i18n.t('Apply image compression to channel uploads too.')}
			</p>
		</div>
	{/if}
</div>
