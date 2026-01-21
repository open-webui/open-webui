<script lang="ts">
	import { config, models, settings, user } from '$lib/stores';
	import { createEventDispatcher, onMount, onDestroy, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import { updateUserInfo } from '$lib/apis/users';
	import { getUserPosition } from '$lib/utils';
	import { setTextScale } from '$lib/utils/text-scale';

	import Minus from '$lib/components/icons/Minus.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import ManageFloatingActionButtonsModal from './Interface/ManageFloatingActionButtonsModal.svelte';
	import ManageImageCompressionModal from './Interface/ManageImageCompressionModal.svelte';

	const dispatch = createEventDispatcher();

	const i18n = getContext('i18n');

	export let saveSettings: Function;

	let backgroundImageUrl = null;
	let inputFiles = null;
	let filesInputElement;

	// Addons
	let titleAutoGenerate = true;
	let autoFollowUps = true;
	let autoTags = true;

	let responseAutoCopy = false;
	let widescreenMode = false;
	let splitLargeChunks = false;
	let scrollOnBranchChange = true;
	let userLocation = false;

	// Interface
	let defaultModelId = '';
	let showUsername = false;

	let notificationSound = true;
	let notificationSoundAlways = false;

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

	let landingPageMode = '';
	let chatBubble = true;
	let chatDirection: 'LTR' | 'RTL' | 'auto' = 'auto';
	let ctrlEnterToSend = false;
	let copyFormatted = false;

	let temporaryChatByDefault = false;
	let chatFadeStreamingText = true;
	let collapseCodeBlocks = false;
	let expandDetails = false;
	let showChatTitleInTab = true;

	let showFloatingActionButtons = true;
	let floatingActionButtons = null;

	let imageCompression = false;
	let imageCompressionSize = {
		width: '',
		height: ''
	};
	let imageCompressionInChannels = true;

	// chat export
	let stylizedPdfExport = true;

	// Admin - Show Update Available Toast
	let showUpdateToast = true;
	let showChangelog = true;

	let showEmojiInCall = false;
	let voiceInterruption = false;
	let hapticFeedback = false;

	let webSearch = null;

	let iframeSandboxAllowSameOrigin = false;
	let iframeSandboxAllowForms = false;

	let showManageFloatingActionButtonsModal = false;
	let showManageImageCompressionModal = false;

	let textScale = null;

	const toggleLandingPageMode = async () => {
		landingPageMode = landingPageMode === '' ? 'chat' : '';
		saveSettings({ landingPageMode: landingPageMode });
	};

	const toggleUserLocation = async () => {
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
				...$settings.title,
				auto: titleAutoGenerate
			}
		});
	};

	const toggleResponseAutoCopy = async () => {
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

	const updateInterfaceHandler = async () => {
		saveSettings({
			models: [defaultModelId],
			imageCompressionSize: imageCompressionSize
		});
	};

	const toggleWebSearch = async () => {
		webSearch = webSearch === null ? 'always' : null;
		saveSettings({ webSearch: webSearch });
	};

	const setTextScaleHandler = (scale) => {
		textScale = scale;
		setTextScale(textScale);

		if (textScale === 1) {
			textScale = null;
		}
		saveSettings({ textScale });
	};

	onMount(async () => {
		titleAutoGenerate = $settings?.title?.auto ?? true;
		autoTags = $settings?.autoTags ?? true;
		autoFollowUps = $settings?.autoFollowUps ?? true;

		highContrastMode = $settings?.highContrastMode ?? false;

		detectArtifacts = $settings?.detectArtifacts ?? true;
		responseAutoCopy = $settings?.responseAutoCopy ?? false;

		showUsername = $settings?.showUsername ?? false;
		showUpdateToast = $settings?.showUpdateToast ?? true;
		showChangelog = $settings?.showChangelog ?? true;

		showEmojiInCall = $settings?.showEmojiInCall ?? false;
		voiceInterruption = $settings?.voiceInterruption ?? false;

		displayMultiModelResponsesInTabs = $settings?.displayMultiModelResponsesInTabs ?? false;
		chatFadeStreamingText = $settings?.chatFadeStreamingText ?? true;

		richTextInput = $settings?.richTextInput ?? true;
		showFormattingToolbar = $settings?.showFormattingToolbar ?? false;
		insertPromptAsRichText = $settings?.insertPromptAsRichText ?? false;
		promptAutocomplete = $settings?.promptAutocomplete ?? false;

		insertSuggestionPrompt = $settings?.insertSuggestionPrompt ?? false;
		keepFollowUpPrompts = $settings?.keepFollowUpPrompts ?? false;
		insertFollowUpPrompt = $settings?.insertFollowUpPrompt ?? false;

		regenerateMenu = $settings?.regenerateMenu ?? true;

		largeTextAsFile = $settings?.largeTextAsFile ?? false;
		copyFormatted = $settings?.copyFormatted ?? false;

		collapseCodeBlocks = $settings?.collapseCodeBlocks ?? false;
		expandDetails = $settings?.expandDetails ?? false;

		landingPageMode = $settings?.landingPageMode ?? '';
		chatBubble = $settings?.chatBubble ?? true;
		widescreenMode = $settings?.widescreenMode ?? false;
		splitLargeChunks = $settings?.splitLargeChunks ?? false;
		scrollOnBranchChange = $settings?.scrollOnBranchChange ?? true;

		temporaryChatByDefault = $settings?.temporaryChatByDefault ?? false;
		chatDirection = $settings?.chatDirection ?? 'auto';
		userLocation = $settings?.userLocation ?? false;
		showChatTitleInTab = $settings?.showChatTitleInTab ?? true;

		notificationSound = $settings?.notificationSound ?? true;
		notificationSoundAlways = $settings?.notificationSoundAlways ?? false;

		iframeSandboxAllowSameOrigin = $settings?.iframeSandboxAllowSameOrigin ?? false;
		iframeSandboxAllowForms = $settings?.iframeSandboxAllowForms ?? false;

		stylizedPdfExport = $settings?.stylizedPdfExport ?? true;

		hapticFeedback = $settings?.hapticFeedback ?? false;
		ctrlEnterToSend = $settings?.ctrlEnterToSend ?? false;

		showFloatingActionButtons = $settings?.showFloatingActionButtons ?? true;
		floatingActionButtons = $settings?.floatingActionButtons ?? null;

		imageCompression = $settings?.imageCompression ?? false;
		imageCompressionSize = $settings?.imageCompressionSize ?? { width: '', height: '' };
		imageCompressionInChannels = $settings?.imageCompressionInChannels ?? true;

		defaultModelId = $settings?.models?.at(0) ?? '';
		if ($config?.default_models) {
			defaultModelId = $config.default_models.split(',')[0];
		}

		backgroundImageUrl = $settings?.backgroundImageUrl ?? null;
		webSearch = $settings?.webSearch ?? null;

		textScale = $settings?.textScale ?? null;
	});
</script>

<ManageFloatingActionButtonsModal
	bind:show={showManageFloatingActionButtonsModal}
	{floatingActionButtons}
	onSave={(buttons) => {
		floatingActionButtons = buttons;
		saveSettings({ floatingActionButtons });
	}}
/>

<ManageImageCompressionModal
	bind:show={showManageImageCompressionModal}
	size={imageCompressionSize}
	onSave={(size) => {
		saveSettings({ imageCompressionSize: size });
	}}
/>

<form
	id="tab-interface"
	class="flex flex-col h-full justify-between text-sm"
	on:submit|preventDefault={() => {
		updateInterfaceHandler();
		dispatch('save');
	}}
>
	<input
		bind:this={filesInputElement}
		bind:files={inputFiles}
		type="file"
		hidden
		accept="image/*"
		on:change={() => {
			let reader = new FileReader();
			reader.onload = (event) => {
				let originalImageUrl = `${event.target.result}`;

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
				console.log(`Unsupported File Type '${inputFiles[0]['type']}'.`);
				inputFiles = null;
			}
		}}
	/>

	<div class="space-y-4 overflow-y-scroll scrollbar-hidden h-full pr-1">
		<!-- UI 设置卡片 -->
		<div class="bg-gray-50 dark:bg-gray-850 rounded-xl p-5 border border-gray-100 dark:border-gray-800">
			<div class="text-sm font-semibold text-gray-800 dark:text-gray-100 mb-4">
				{$i18n.t('UI')}
			</div>

			<div class="space-y-3">
				<!-- UI Scale -->
				<div class="bg-white dark:bg-gray-900 rounded-lg p-4 border border-gray-100 dark:border-gray-800">
					<div class="flex items-center justify-between mb-3">
						<label id="ui-scale-label" class="text-sm font-medium text-gray-700 dark:text-gray-200" for="ui-scale-slider">
							{$i18n.t('UI Scale')}
						</label>
						<button
							class="text-xs font-medium px-3 py-1.5 rounded-lg transition {textScale === null
								? 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-300'
								: 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-200'}"
							type="button"
							on:click={() => {
								if (textScale === null) {
									textScale = 1;
								} else {
									textScale = null;
									setTextScaleHandler(1);
								}
							}}
						>
							{#if textScale === null}
								<span>{$i18n.t('Default')}</span>
							{:else}
								<span>{textScale}x</span>
							{/if}
						</button>
					</div>

					{#if textScale !== null}
						<div class="flex items-center gap-2">
							<button
								type="button"
								class="rounded-lg p-1.5 transition outline-gray-200 hover:bg-gray-100 dark:outline-gray-700 dark:hover:bg-gray-800 text-gray-600 dark:text-gray-300"
								on:click={() => {
									textScale = Math.max(1, parseFloat((textScale - 0.1).toFixed(2)));
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
									class="w-full accent-gray-700 dark:accent-gray-300"
									type="range"
									min="1"
									max="1.5"
									step={0.01}
									bind:value={textScale}
									on:change={() => {
										setTextScaleHandler(textScale);
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
								class="rounded-lg p-1.5 transition outline-gray-200 hover:bg-gray-100 dark:outline-gray-700 dark:hover:bg-gray-800 text-gray-600 dark:text-gray-300"
								on:click={() => {
									textScale = Math.min(1.5, parseFloat((textScale + 0.1).toFixed(2)));
									setTextScaleHandler(textScale);
								}}
								aria-labelledby="ui-scale-label"
								aria-label={$i18n.t('Increase UI Scale')}
							>
								<Plus className="h-3.5 w-3.5" />
							</button>
						</div>
					{/if}
				</div>

				<!-- 其他UI设置 -->
				<div class="flex items-center justify-between bg-white dark:bg-gray-900 rounded-lg px-4 py-3 border border-gray-100 dark:border-gray-800">
					<div id="high-contrast-mode-label" class="text-sm font-medium text-gray-700 dark:text-gray-200">
						{$i18n.t('High Contrast Mode')} ({$i18n.t('Beta')})
					</div>
					<Switch
						ariaLabelledbyId="high-contrast-mode-label"
						tooltip={true}
						bind:state={highContrastMode}
						on:change={() => {
							saveSettings({ highContrastMode });
						}}
					/>
				</div>

				<div class="flex items-center justify-between bg-white dark:bg-gray-900 rounded-lg px-4 py-3 border border-gray-100 dark:border-gray-800">
					<div id="use-chat-title-as-tab-title-label" class="text-sm font-medium text-gray-700 dark:text-gray-200">
						{$i18n.t('Display chat title in tab')}
					</div>
					<Switch
						ariaLabelledbyId="use-chat-title-as-tab-title-label"
						tooltip={true}
						bind:state={showChatTitleInTab}
						on:change={() => {
							saveSettings({ showChatTitleInTab });
						}}
					/>
				</div>

				<div class="flex items-center justify-between bg-white dark:bg-gray-900 rounded-lg px-4 py-3 border border-gray-100 dark:border-gray-800">
					<div id="notification-sound-label" class="text-sm font-medium text-gray-700 dark:text-gray-200">
						{$i18n.t('Notification Sound')}
					</div>
					<Switch
						ariaLabelledbyId="notification-sound-label"
						tooltip={true}
						bind:state={notificationSound}
						on:change={() => {
							saveSettings({ notificationSound });
						}}
					/>
				</div>

				{#if notificationSound}
					<div class="flex items-center justify-between bg-white dark:bg-gray-900 rounded-lg px-4 py-3 border border-gray-100 dark:border-gray-800">
						<div id="play-notification-sound-label" class="text-sm font-medium text-gray-700 dark:text-gray-200">
							{$i18n.t('Always Play Notification Sound')}
						</div>
						<Switch
							ariaLabelledbyId="play-notification-sound-label"
							tooltip={true}
							bind:state={notificationSoundAlways}
							on:change={() => {
								saveSettings({ notificationSoundAlways });
							}}
						/>
					</div>
				{/if}

				<div class="flex items-center justify-between bg-white dark:bg-gray-900 rounded-lg px-4 py-3 border border-gray-100 dark:border-gray-800">
					<div id="allow-user-location-label" class="text-sm font-medium text-gray-700 dark:text-gray-200">
						{$i18n.t('Allow User Location')}
					</div>
					<Switch
						ariaLabelledbyId="allow-user-location-label"
						tooltip={true}
						bind:state={userLocation}
						on:change={() => {
							toggleUserLocation();
						}}
					/>
				</div>

				<div class="flex items-center justify-between bg-white dark:bg-gray-900 rounded-lg px-4 py-3 border border-gray-100 dark:border-gray-800">
					<div id="haptic-feedback-label" class="text-sm font-medium text-gray-700 dark:text-gray-200">
						{$i18n.t('Haptic Feedback')} ({$i18n.t('Android')})
					</div>
					<Switch
						ariaLabelledbyId="haptic-feedback-label"
						tooltip={true}
						bind:state={hapticFeedback}
						on:change={() => {
							saveSettings({ hapticFeedback });
						}}
					/>
				</div>

				<div class="flex items-center justify-between bg-white dark:bg-gray-900 rounded-lg px-4 py-3 border border-gray-100 dark:border-gray-800">
					<div id="copy-formatted-label" class="text-sm font-medium text-gray-700 dark:text-gray-200">
						{$i18n.t('Copy Formatted Text')}
					</div>
					<Switch
						ariaLabelledbyId="copy-formatted-label"
						tooltip={true}
						bind:state={copyFormatted}
						on:change={() => {
							saveSettings({ copyFormatted });
						}}
					/>
				</div>

				{#if $user?.role === 'admin'}
					<div class="flex items-center justify-between bg-white dark:bg-gray-900 rounded-lg px-4 py-3 border border-gray-100 dark:border-gray-800">
						<div id="toast-notifications-label" class="text-sm font-medium text-gray-700 dark:text-gray-200">
							{$i18n.t('Toast notifications for new updates')}
						</div>
						<Switch
							ariaLabelledbyId="toast-notifications-label"
							tooltip={true}
							bind:state={showUpdateToast}
							on:change={() => {
								saveSettings({ showUpdateToast });
							}}
						/>
					</div>

					<div class="flex items-center justify-between bg-white dark:bg-gray-900 rounded-lg px-4 py-3 border border-gray-100 dark:border-gray-800">
						<div id="whats-new-label" class="text-sm font-medium text-gray-700 dark:text-gray-200">
							{$i18n.t(`Show "What's New" modal on login`)}
						</div>
						<Switch
							ariaLabelledbyId="whats-new-label"
							tooltip={true}
							bind:state={showChangelog}
							on:change={() => {
								saveSettings({ showChangelog });
							}}
						/>
					</div>
				{/if}
			</div>
		</div>

		<!-- 聊天设置卡片 -->
		<div class="bg-gray-50 dark:bg-gray-850 rounded-xl p-5 border border-gray-100 dark:border-gray-800">
			<div class="text-sm font-semibold text-gray-800 dark:text-gray-100 mb-4">
				{$i18n.t('Chat')}
			</div>

			<div class="space-y-3">
				<div class="flex items-center justify-between bg-white dark:bg-gray-900 rounded-lg px-4 py-3 border border-gray-100 dark:border-gray-800">
					<div id="chat-direction-label" class="text-sm font-medium text-gray-700 dark:text-gray-200">
						{$i18n.t('Chat direction')}
					</div>
					<button
						aria-labelledby="chat-direction-label chat-direction-mode"
						class="px-3 py-1.5 text-sm rounded-lg transition bg-gray-50 dark:bg-gray-800 hover:bg-gray-100 dark:hover:bg-gray-700 border border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-200"
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

				<div class="flex items-center justify-between bg-white dark:bg-gray-900 rounded-lg px-4 py-3 border border-gray-100 dark:border-gray-800">
					<div id="landing-page-mode-label" class="text-sm font-medium text-gray-700 dark:text-gray-200">
						{$i18n.t('Landing Page Mode')}
					</div>
					<button
						aria-labelledby="landing-page-mode-label notification-sound-state"
						class="px-3 py-1.5 text-sm rounded-lg transition bg-gray-50 dark:bg-gray-800 hover:bg-gray-100 dark:hover:bg-gray-700 border border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-200"
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

				<div class="flex items-center justify-between bg-white dark:bg-gray-900 rounded-lg px-4 py-3 border border-gray-100 dark:border-gray-800">
					<div id="chat-background-label" class="text-sm font-medium text-gray-700 dark:text-gray-200">
						{$i18n.t('Chat Background Image')}
					</div>
					<button
						aria-labelledby="chat-background-label background-image-url-state"
						class="px-3 py-1.5 text-sm rounded-lg transition bg-gray-50 dark:bg-gray-800 hover:bg-gray-100 dark:hover:bg-gray-700 border border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-200"
						on:click={() => {
							if (backgroundImageUrl !== null) {
								backgroundImageUrl = null;
								saveSettings({ backgroundImageUrl });
							} else {
								filesInputElement.click();
							}
						}}
						type="button"
					>
						<span id="background-image-url-state"
							>{backgroundImageUrl !== null ? $i18n.t('Reset') : $i18n.t('Upload')}</span
						>
					</button>
				</div>

				<div class="flex items-center justify-between bg-white dark:bg-gray-900 rounded-lg px-4 py-3 border border-gray-100 dark:border-gray-800">
					<div id="chat-bubble-ui-label" class="text-sm font-medium text-gray-700 dark:text-gray-200">
						{$i18n.t('Chat Bubble UI')}
					</div>
					<Switch
						tooltip={true}
						ariaLabelledbyId="chat-bubble-ui-label"
						bind:state={chatBubble}
						on:change={() => {
							saveSettings({ chatBubble });
						}}
					/>
				</div>

				{#if !$settings.chatBubble}
					<div class="flex items-center justify-between bg-white dark:bg-gray-900 rounded-lg px-4 py-3 border border-gray-100 dark:border-gray-800">
						<div id="chat-bubble-username-label" class="text-sm font-medium text-gray-700 dark:text-gray-200">
							{$i18n.t('Display the username instead of You in the Chat')}
						</div>
						<Switch
							ariaLabelledbyId="chat-bubble-username-label"
							tooltip={true}
							bind:state={showUsername}
							on:change={() => {
								saveSettings({ showUsername });
							}}
						/>
					</div>
				{/if}

				<div class="flex items-center justify-between bg-white dark:bg-gray-900 rounded-lg px-4 py-3 border border-gray-100 dark:border-gray-800">
					<div id="widescreen-mode-label" class="text-sm font-medium text-gray-700 dark:text-gray-200">
						{$i18n.t('Widescreen Mode')}
					</div>
					<Switch
						ariaLabelledbyId="widescreen-mode-label"
						tooltip={true}
						bind:state={widescreenMode}
						on:change={() => {
							saveSettings({ widescreenMode });
						}}
					/>
				</div>

				{#if $user.role === 'admin' || $user?.permissions?.chat?.temporary}
					<div class="flex items-center justify-between bg-white dark:bg-gray-900 rounded-lg px-4 py-3 border border-gray-100 dark:border-gray-800">
						<div id="temp-chat-default-label" class="text-sm font-medium text-gray-700 dark:text-gray-200">
							{$i18n.t('Temporary Chat by Default')}
						</div>
						<Switch
							ariaLabelledbyId="temp-chat-default-label"
							tooltip={true}
							bind:state={temporaryChatByDefault}
							on:change={() => {
								saveSettings({ temporaryChatByDefault });
							}}
						/>
					</div>
				{/if}

				<div class="flex items-center justify-between bg-white dark:bg-gray-900 rounded-lg px-4 py-3 border border-gray-100 dark:border-gray-800">
					<div id="fade-streaming-label" class="text-sm font-medium text-gray-700 dark:text-gray-200">
						{$i18n.t('Fade Effect for Streaming Text')}
					</div>
					<Switch
						ariaLabelledbyId="fade-streaming-label"
						tooltip={true}
						bind:state={chatFadeStreamingText}
						on:change={() => {
							saveSettings({ chatFadeStreamingText });
						}}
					/>
				</div>

				<div class="flex items-center justify-between bg-white dark:bg-gray-900 rounded-lg px-4 py-3 border border-gray-100 dark:border-gray-800">
					<div id="auto-generation-label" class="text-sm font-medium text-gray-700 dark:text-gray-200">
						{$i18n.t('Title Auto-Generation')}
					</div>
					<Switch
						ariaLabelledbyId="auto-generation-label"
						tooltip={true}
						bind:state={titleAutoGenerate}
						on:change={() => {
							toggleTitleAutoGenerate();
						}}
					/>
				</div>

				<div class="flex items-center justify-between bg-white dark:bg-gray-900 rounded-lg px-4 py-3 border border-gray-100 dark:border-gray-800">
					<div class="text-sm font-medium text-gray-700 dark:text-gray-200" id="follow-up-auto-generation-label">
						{$i18n.t('Follow-Up Auto-Generation')}
					</div>
					<Switch
						ariaLabelledbyId="follow-up-auto-generation-label"
						tooltip={true}
						bind:state={autoFollowUps}
						on:change={() => {
							saveSettings({ autoFollowUps });
						}}
					/>
				</div>

				<div class="flex items-center justify-between bg-white dark:bg-gray-900 rounded-lg px-4 py-3 border border-gray-100 dark:border-gray-800">
					<div id="chat-tags-label" class="text-sm font-medium text-gray-700 dark:text-gray-200">
						{$i18n.t('Chat Tags Auto-Generation')}
					</div>
					<Switch
						ariaLabelledbyId="chat-tags-label"
						tooltip={true}
						bind:state={autoTags}
						on:change={() => {
							saveSettings({ autoTags });
						}}
					/>
				</div>

				<div class="flex items-center justify-between bg-white dark:bg-gray-900 rounded-lg px-4 py-3 border border-gray-100 dark:border-gray-800">
					<div id="auto-copy-label" class="text-sm font-medium text-gray-700 dark:text-gray-200">
						{$i18n.t('Auto-Copy Response to Clipboard')}
					</div>
					<Switch
						ariaLabelledbyId="auto-copy-label"
						tooltip={true}
						bind:state={responseAutoCopy}
						on:change={() => {
							toggleResponseAutoCopy();
						}}
					/>
				</div>

				<div class="flex items-center justify-between bg-white dark:bg-gray-900 rounded-lg px-4 py-3 border border-gray-100 dark:border-gray-800">
					<div id="insert-suggestion-prompt-label" class="text-sm font-medium text-gray-700 dark:text-gray-200">
						{$i18n.t('Insert Suggestion Prompt to Input')}
					</div>
					<Switch
						ariaLabelledbyId="insert-suggestion-prompt-label"
						tooltip={true}
						bind:state={insertSuggestionPrompt}
						on:change={() => {
							saveSettings({ insertSuggestionPrompt });
						}}
					/>
				</div>

				<div class="flex items-center justify-between bg-white dark:bg-gray-900 rounded-lg px-4 py-3 border border-gray-100 dark:border-gray-800">
					<div id="keep-follow-up-prompts-label" class="text-sm font-medium text-gray-700 dark:text-gray-200">
						{$i18n.t('Keep Follow-Up Prompts in Chat')}
					</div>
					<Switch
						ariaLabelledbyId="keep-follow-up-prompts-label"
						tooltip={true}
						bind:state={keepFollowUpPrompts}
						on:change={() => {
							saveSettings({ keepFollowUpPrompts });
						}}
					/>
				</div>

				<div class="flex items-center justify-between bg-white dark:bg-gray-900 rounded-lg px-4 py-3 border border-gray-100 dark:border-gray-800">
					<div id="insert-follow-up-prompt-label" class="text-sm font-medium text-gray-700 dark:text-gray-200">
						{$i18n.t('Insert Follow-Up Prompt to Input')}
					</div>
					<Switch
						ariaLabelledbyId="insert-follow-up-prompt-label"
						tooltip={true}
						bind:state={insertFollowUpPrompt}
						on:change={() => {
							saveSettings({ insertFollowUpPrompt });
						}}
					/>
				</div>

				<div class="flex items-center justify-between bg-white dark:bg-gray-900 rounded-lg px-4 py-3 border border-gray-100 dark:border-gray-800">
					<div id="regenerate-menu-label" class="text-sm font-medium text-gray-700 dark:text-gray-200">
						{$i18n.t('Regenerate Menu')}
					</div>
					<Switch
						ariaLabelledbyId="regenerate-menu-label"
						tooltip={true}
						bind:state={regenerateMenu}
						on:change={() => {
							saveSettings({ regenerateMenu });
						}}
					/>
				</div>

				<div class="flex items-center justify-between bg-white dark:bg-gray-900 rounded-lg px-4 py-3 border border-gray-100 dark:border-gray-800">
					<div id="always-collapse-label" class="text-sm font-medium text-gray-700 dark:text-gray-200">
						{$i18n.t('Always Collapse Code Blocks')}
					</div>
					<Switch
						ariaLabelledbyId="always-collapse-label"
						tooltip={true}
						bind:state={collapseCodeBlocks}
						on:change={() => {
							saveSettings({ collapseCodeBlocks });
						}}
					/>
				</div>

				<div class="flex items-center justify-between bg-white dark:bg-gray-900 rounded-lg px-4 py-3 border border-gray-100 dark:border-gray-800">
					<div id="always-expand-label" class="text-sm font-medium text-gray-700 dark:text-gray-200">
						{$i18n.t('Always Expand Details')}
					</div>
					<Switch
						ariaLabelledbyId="always-expand-label"
						tooltip={true}
						bind:state={expandDetails}
						on:change={() => {
							saveSettings({ expandDetails });
						}}
					/>
				</div>

				<div class="flex items-center justify-between bg-white dark:bg-gray-900 rounded-lg px-4 py-3 border border-gray-100 dark:border-gray-800">
					<div id="keep-followup-prompts-label" class="text-sm font-medium text-gray-700 dark:text-gray-200">
						{$i18n.t('Display Multi-model Responses in Tabs')}
					</div>
					<Switch
						ariaLabelledbyId="keep-followup-prompts-label"
						tooltip={true}
						bind:state={displayMultiModelResponsesInTabs}
						on:change={() => {
							saveSettings({ displayMultiModelResponsesInTabs });
						}}
					/>
				</div>

				<div class="flex items-center justify-between bg-white dark:bg-gray-900 rounded-lg px-4 py-3 border border-gray-100 dark:border-gray-800">
					<div id="scroll-on-branch-change-label" class="text-sm font-medium text-gray-700 dark:text-gray-200">
						{$i18n.t('Scroll On Branch Change')}
					</div>
					<Switch
						ariaLabelledbyId="scroll-on-branch-change-label"
						tooltip={true}
						bind:state={scrollOnBranchChange}
						on:change={() => {
							saveSettings({ scrollOnBranchChange });
						}}
					/>
				</div>

				<div class="flex items-center justify-between bg-white dark:bg-gray-900 rounded-lg px-4 py-3 border border-gray-100 dark:border-gray-800">
					<div id="stylized-pdf-export-label" class="text-sm font-medium text-gray-700 dark:text-gray-200">
						{$i18n.t('Stylized PDF Export')}
					</div>
					<Switch
						ariaLabelledbyId="stylized-pdf-export-label"
						tooltip={true}
						bind:state={stylizedPdfExport}
						on:change={() => {
							saveSettings({ stylizedPdfExport });
						}}
					/>
				</div>

				<div class="flex items-center justify-between bg-white dark:bg-gray-900 rounded-lg px-4 py-3 border border-gray-100 dark:border-gray-800">
					<label id="floating-action-buttons-label" class="text-sm font-medium text-gray-700 dark:text-gray-200">
						{$i18n.t('Floating Quick Actions')}
					</label>
					<div class="flex items-center gap-3">
						{#if showFloatingActionButtons}
							<button
								class="text-xs text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 font-medium underline"
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
							on:change={() => {
								saveSettings({ showFloatingActionButtons });
							}}
						/>
					</div>
				</div>

				<div class="flex items-center justify-between bg-white dark:bg-gray-900 rounded-lg px-4 py-3 border border-gray-100 dark:border-gray-800">
					<div id="web-search-in-chat-label" class="text-sm font-medium text-gray-700 dark:text-gray-200">
						{$i18n.t('Web Search in Chat')}
					</div>
					<button
						aria-labelledby="web-search-in-chat-label web-search-state"
						class="px-3 py-1.5 text-sm rounded-lg transition bg-gray-50 dark:bg-gray-800 hover:bg-gray-100 dark:hover:bg-gray-700 border border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-200"
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
			</div>
		</div>

		<!-- 输入设置卡片 -->
		<div class="bg-gray-50 dark:bg-gray-850 rounded-xl p-5 border border-gray-100 dark:border-gray-800">
			<div class="text-sm font-semibold text-gray-800 dark:text-gray-100 mb-4">
				{$i18n.t('Input')}
			</div>

			<div class="space-y-3">
				<div class="flex items-center justify-between bg-white dark:bg-gray-900 rounded-lg px-4 py-3 border border-gray-100 dark:border-gray-800">
					<div id="enter-key-behavior-label ctrl-enter-to-send-state" class="text-sm font-medium text-gray-700 dark:text-gray-200">
						{$i18n.t('Enter Key Behavior')}
					</div>
					<button
						aria-labelledby="enter-key-behavior-label"
						class="px-3 py-1.5 text-sm rounded-lg transition bg-gray-50 dark:bg-gray-800 hover:bg-gray-100 dark:hover:bg-gray-700 border border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-200"
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

				<div class="flex items-center justify-between bg-white dark:bg-gray-900 rounded-lg px-4 py-3 border border-gray-100 dark:border-gray-800">
					<div id="rich-input-label" class="text-sm font-medium text-gray-700 dark:text-gray-200">
						{$i18n.t('Rich Text Input for Chat')}
					</div>
					<Switch
						tooltip={true}
						ariaLabelledbyId="rich-input-label"
						bind:state={richTextInput}
						on:change={() => {
							saveSettings({ richTextInput });
						}}
					/>
				</div>

				{#if $config?.features?.enable_autocomplete_generation}
					<div class="flex items-center justify-between bg-white dark:bg-gray-900 rounded-lg px-4 py-3 border border-gray-100 dark:border-gray-800">
						<div id="prompt-autocompletion-label" class="text-sm font-medium text-gray-700 dark:text-gray-200">
							{$i18n.t('Prompt Autocompletion')}
						</div>
						<Switch
							ariaLabelledbyId="prompt-autocompletion-label"
							tooltip={true}
							bind:state={promptAutocomplete}
							on:change={() => {
								saveSettings({ promptAutocomplete });
							}}
						/>
					</div>
				{/if}

				{#if richTextInput}
					<div class="flex items-center justify-between bg-white dark:bg-gray-900 rounded-lg px-4 py-3 border border-gray-100 dark:border-gray-800">
						<div id="show-formatting-toolbar-label" class="text-sm font-medium text-gray-700 dark:text-gray-200">
							{$i18n.t('Show Formatting Toolbar')}
						</div>
						<Switch
							ariaLabelledbyId="show-formatting-toolbar-label"
							tooltip={true}
							bind:state={showFormattingToolbar}
							on:change={() => {
								saveSettings({ showFormattingToolbar });
							}}
						/>
					</div>

					<div class="flex items-center justify-between bg-white dark:bg-gray-900 rounded-lg px-4 py-3 border border-gray-100 dark:border-gray-800">
						<div id="insert-prompt-as-rich-text-label" class="text-sm font-medium text-gray-700 dark:text-gray-200">
							{$i18n.t('Insert Prompt as Rich Text')}
						</div>
						<Switch
							ariaLabelledbyId="insert-prompt-as-rich-text-label"
							tooltip={true}
							bind:state={insertPromptAsRichText}
							on:change={() => {
								saveSettings({ insertPromptAsRichText });
							}}
						/>
					</div>
				{/if}

				<div class="flex items-center justify-between bg-white dark:bg-gray-900 rounded-lg px-4 py-3 border border-gray-100 dark:border-gray-800">
					<div id="paste-large-label" class="text-sm font-medium text-gray-700 dark:text-gray-200">
						{$i18n.t('Paste Large Text as File')}
					</div>
					<Switch
						tooltip={true}
						ariaLabelledbyId="paste-large-label"
						bind:state={largeTextAsFile}
						on:change={() => {
							saveSettings({ largeTextAsFile });
						}}
					/>
				</div>
			</div>
		</div>

		<!-- Artifacts 设置卡片 -->
		<div class="bg-gray-50 dark:bg-gray-850 rounded-xl p-5 border border-gray-100 dark:border-gray-800">
			<div class="text-sm font-semibold text-gray-800 dark:text-gray-100 mb-4">
				{$i18n.t('Artifacts')}
			</div>

			<div class="space-y-3">
				<div class="flex items-center justify-between bg-white dark:bg-gray-900 rounded-lg px-4 py-3 border border-gray-100 dark:border-gray-800">
					<div id="detect-artifacts-label" class="text-sm font-medium text-gray-700 dark:text-gray-200">
						{$i18n.t('Detect Artifacts Automatically')}
					</div>
					<Switch
						ariaLabelledbyId="detect-artifacts-label"
						tooltip={true}
						bind:state={detectArtifacts}
						on:change={() => {
							saveSettings({ detectArtifacts });
						}}
					/>
				</div>

				<div class="flex items-center justify-between bg-white dark:bg-gray-900 rounded-lg px-4 py-3 border border-gray-100 dark:border-gray-800">
					<div id="iframe-sandbox-allow-same-origin-label" class="text-sm font-medium text-gray-700 dark:text-gray-200">
						{$i18n.t('iframe Sandbox Allow Same Origin')}
					</div>
					<Switch
						ariaLabelledbyId="iframe-sandbox-allow-same-origin-label"
						tooltip={true}
						bind:state={iframeSandboxAllowSameOrigin}
						on:change={() => {
							saveSettings({ iframeSandboxAllowSameOrigin });
						}}
					/>
				</div>

				<div class="flex items-center justify-between bg-white dark:bg-gray-900 rounded-lg px-4 py-3 border border-gray-100 dark:border-gray-800">
					<div id="iframe-sandbox-allow-forms-label" class="text-sm font-medium text-gray-700 dark:text-gray-200">
						{$i18n.t('iframe Sandbox Allow Forms')}
					</div>
					<Switch
						ariaLabelledbyId="iframe-sandbox-allow-forms-label"
						tooltip={true}
						bind:state={iframeSandboxAllowForms}
						on:change={() => {
							saveSettings({ iframeSandboxAllowForms });
						}}
					/>
				</div>
			</div>
		</div>

		<!-- 语音设置卡片 -->
		<div class="bg-gray-50 dark:bg-gray-850 rounded-xl p-5 border border-gray-100 dark:border-gray-800">
			<div class="text-sm font-semibold text-gray-800 dark:text-gray-100 mb-4">
				{$i18n.t('Voice')}
			</div>

			<div class="space-y-3">
				<div class="flex items-center justify-between bg-white dark:bg-gray-900 rounded-lg px-4 py-3 border border-gray-100 dark:border-gray-800">
					<div class="text-sm font-medium text-gray-700 dark:text-gray-200" id="allow-voice-interruption-in-call-label">
						{$i18n.t('Allow Voice Interruption in Call')}
					</div>
					<Switch
						ariaLabelledbyId="allow-voice-interruption-in-call-label"
						tooltip={true}
						bind:state={voiceInterruption}
						on:change={() => {
							saveSettings({ voiceInterruption });
						}}
					/>
				</div>

				<div class="flex items-center justify-between bg-white dark:bg-gray-900 rounded-lg px-4 py-3 border border-gray-100 dark:border-gray-800">
					<div id="display-emoji-label" class="text-sm font-medium text-gray-700 dark:text-gray-200">
						{$i18n.t('Display Emoji in Call')}
					</div>
					<Switch
						ariaLabelledbyId="display-emoji-label"
						tooltip={true}
						bind:state={showEmojiInCall}
						on:change={() => {
							saveSettings({ showEmojiInCall });
						}}
					/>
				</div>
			</div>
		</div>

		<!-- 文件设置卡片 -->
		<div class="bg-gray-50 dark:bg-gray-850 rounded-xl p-5 border border-gray-100 dark:border-gray-800">
			<div class="text-sm font-semibold text-gray-800 dark:text-gray-100 mb-4">
				{$i18n.t('File')}
			</div>

			<div class="space-y-3">
				<div class="flex items-center justify-between bg-white dark:bg-gray-900 rounded-lg px-4 py-3 border border-gray-100 dark:border-gray-800">
					<div id="image-compression-label" class="text-sm font-medium text-gray-700 dark:text-gray-200">
						{$i18n.t('Image Compression')}
					</div>
					<div class="flex items-center gap-3">
						{#if imageCompression}
							<button
								class="text-xs text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 font-medium underline"
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
							on:change={() => {
								saveSettings({ imageCompression });
							}}
						/>
					</div>
				</div>

				{#if imageCompression}
					<div class="flex items-center justify-between bg-white dark:bg-gray-900 rounded-lg px-4 py-3 border border-gray-100 dark:border-gray-800">
						<div id="image-compression-in-channels-label" class="text-sm font-medium text-gray-700 dark:text-gray-200">
							{$i18n.t('Compress Images in Channels')}
						</div>
						<Switch
							ariaLabelledbyId="image-compression-in-channels-label"
							tooltip={true}
							bind:state={imageCompressionInChannels}
							on:change={() => {
								saveSettings({ imageCompressionInChannels });
							}}
						/>
					</div>
				{/if}
			</div>
		</div>
	</div>

	<div class="flex justify-end pt-4 text-sm font-medium">
		<button
			class="px-4 py-2 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full"
			type="submit"
		>
			{$i18n.t('Save')}
		</button>
	</div>
</form>
