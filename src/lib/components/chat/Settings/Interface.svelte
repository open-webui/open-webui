<script lang="ts">
	import { config, models, settings, user } from '$lib/stores';
	import { createEventDispatcher, onMount, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import { updateUserInfo } from '$lib/apis/users';
	import { getUserPosition } from '$lib/utils';
	import Minus from '$lib/components/icons/Minus.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import ManageFloatingActionButtonsModal from './Interface/ManageFloatingActionButtonsModal.svelte';
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

	let keepFollowUpPrompts = false;
	let insertFollowUpPrompt = false;

	let landingPageMode = '';
	let chatBubble = true;
	let chatDirection: 'LTR' | 'RTL' | 'auto' = 'auto';
	let ctrlEnterToSend = false;
	let copyFormatted = false;

	let chatFadeStreamingText = true;
	let collapseCodeBlocks = false;
	let expandDetails = false;

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

		keepFollowUpPrompts = $settings?.keepFollowUpPrompts ?? false;
		insertFollowUpPrompt = $settings?.insertFollowUpPrompt ?? false;

		largeTextAsFile = $settings?.largeTextAsFile ?? false;
		copyFormatted = $settings?.copyFormatted ?? false;

		collapseCodeBlocks = $settings?.collapseCodeBlocks ?? false;
		expandDetails = $settings?.expandDetails ?? false;

		landingPageMode = $settings?.landingPageMode ?? '';
		chatBubble = $settings?.chatBubble ?? true;
		widescreenMode = $settings?.widescreenMode ?? false;
		splitLargeChunks = $settings?.splitLargeChunks ?? false;
		scrollOnBranchChange = $settings?.scrollOnBranchChange ?? true;
		chatDirection = $settings?.chatDirection ?? 'auto';
		userLocation = $settings?.userLocation ?? false;

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

<form
	id="tab-interface"
	class="flex flex-col h-full justify-between space-y-3 text-sm"
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

	<div class=" space-y-3 overflow-y-scroll max-h-[28rem] lg:max-h-full">
		<div>
			<h1 class=" mb-2 text-sm font-medium">{$i18n.t('UI')}</h1>

			<div>
				<div class=" py-0.5 flex w-full justify-between">
					<div id="high-contrast-mode-label" class=" self-center text-xs">
						{$i18n.t('High Contrast Mode')} ({$i18n.t('Beta')})
					</div>

					<div class="flex items-center gap-2 p-1">
						<Switch
							tooltip={true}
							bind:state={highContrastMode}
							on:change={() => {
								saveSettings({ highContrastMode });
							}}
						/>
					</div>
				</div>
			</div>

			<div>
				<div class="py-0.5 flex w-full justify-between">
					<div id="notification-sound-label" class=" self-center text-xs">
						{$i18n.t('Notification Sound')}
					</div>

					<div class="flex items-center gap-2 p-1">
						<Switch
							tooltip={true}
							bind:state={notificationSound}
							on:change={() => {
								saveSettings({ notificationSound });
							}}
						/>
					</div>
				</div>
			</div>

			{#if notificationSound}
				<div>
					<div class=" py-0.5 flex w-full justify-between">
						<div id="play-notification-sound-label" class=" self-center text-xs">
							{$i18n.t('Always Play Notification Sound')}
						</div>

						<div class="flex items-center gap-2 p-1">
							<Switch
								tooltip={true}
								bind:state={notificationSoundAlways}
								on:change={() => {
									saveSettings({ notificationSoundAlways });
								}}
							/>
						</div>
					</div>
				</div>
			{/if}

			<div>
				<div id="allow-user-location-label" class=" py-0.5 flex w-full justify-between">
					<div class=" self-center text-xs">{$i18n.t('Allow User Location')}</div>

					<div class="flex items-center gap-2 p-1">
						<Switch
							tooltip={true}
							bind:state={userLocation}
							on:change={() => {
								toggleUserLocation();
							}}
						/>
					</div>
				</div>
			</div>

			<div>
				<div class=" py-0.5 flex w-full justify-between">
					<div id="haptic-feedback-label" class=" self-center text-xs">
						{$i18n.t('Haptic Feedback')} ({$i18n.t('Android')})
					</div>

					<div class="flex items-center gap-2 p-1">
						<Switch
							tooltip={true}
							bind:state={hapticFeedback}
							on:change={() => {
								saveSettings({ hapticFeedback });
							}}
						/>
					</div>
				</div>
			</div>

			<div>
				<div class=" py-0.5 flex w-full justify-between">
					<div id="copy-formatted-label" class=" self-center text-xs">
						{$i18n.t('Copy Formatted Text')}
					</div>

					<div class="flex items-center gap-2 p-1">
						<Switch
							tooltip={true}
							bind:state={copyFormatted}
							on:change={() => {
								saveSettings({ copyFormatted });
							}}
						/>
					</div>
				</div>
			</div>

			{#if $user?.role === 'admin'}
				<div>
					<div class=" py-0.5 flex w-full justify-between">
						<div id="toast-notifications-label" class=" self-center text-xs">
							{$i18n.t('Toast notifications for new updates')}
						</div>

						<div class="flex items-center gap-2 p-1">
							<Switch
								tooltip={true}
								bind:state={showUpdateToast}
								on:change={() => {
									saveSettings({ showUpdateToast });
								}}
							/>
						</div>
					</div>
				</div>

				<div>
					<div class=" py-0.5 flex w-full justify-between">
						<div id="whats-new-label" class=" self-center text-xs">
							{$i18n.t(`Show "What's New" modal on login`)}
						</div>

						<div class="flex items-center gap-2 p-1">
							<Switch
								tooltip={true}
								bind:state={showChangelog}
								on:change={() => {
									saveSettings({ showChangelog });
								}}
							/>
						</div>
					</div>
				</div>
			{/if}

			<div class=" my-2 text-sm font-medium">{$i18n.t('Chat')}</div>

			<div>
				<div class=" py-0.5 flex w-full justify-between">
					<div id="chat-direction-label" class=" self-center text-xs">
						{$i18n.t('Chat direction')}
					</div>

					<button
						aria-labelledby="chat-direction-label"
						class="p-1 px-3 text-xs flex rounded-sm transition"
						on:click={toggleChangeChatDirection}
						type="button"
					>
						{#if chatDirection === 'LTR'}
							<span class="ml-2 self-center">{$i18n.t('LTR')}</span>
						{:else if chatDirection === 'RTL'}
							<span class="ml-2 self-center">{$i18n.t('RTL')}</span>
						{:else}
							<span class="ml-2 self-center">{$i18n.t('Auto')}</span>
						{/if}
					</button>
				</div>
			</div>

			<div>
				<div class=" py-0.5 flex w-full justify-between">
					<div id="landing-page-mode-label" class=" self-center text-xs">
						{$i18n.t('Landing Page Mode')}
					</div>

					<button
						aria-labelledby="landing-page-mode-label"
						class="p-1 px-3 text-xs flex rounded-sm transition"
						on:click={() => {
							toggleLandingPageMode();
						}}
						type="button"
					>
						{#if landingPageMode === ''}
							<span class="ml-2 self-center">{$i18n.t('Default')}</span>
						{:else}
							<span class="ml-2 self-center">{$i18n.t('Chat')}</span>
						{/if}
					</button>
				</div>
			</div>

			<div>
				<div class=" py-0.5 flex w-full justify-between">
					<div id="chat-background-label" class=" self-center text-xs">
						{$i18n.t('Chat Background Image')}
					</div>

					<button
						aria-labelledby="chat-background-label"
						class="p-1 px-3 text-xs flex rounded-sm transition"
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
						{#if backgroundImageUrl !== null}
							<span class="ml-2 self-center">{$i18n.t('Reset')}</span>
						{:else}
							<span class="ml-2 self-center">{$i18n.t('Upload')}</span>
						{/if}
					</button>
				</div>
			</div>

			<div>
				<div class=" py-0.5 flex w-full justify-between">
					<div id="chat-bubble-ui-label" class=" self-center text-xs">
						{$i18n.t('Chat Bubble UI')}
					</div>

					<div class="flex items-center gap-2 p-1">
						<Switch
							tooltip={true}
							bind:state={chatBubble}
							on:change={() => {
								saveSettings({ chatBubble });
							}}
						/>
					</div>
				</div>
			</div>

			{#if !$settings.chatBubble}
				<div>
					<div class=" py-0.5 flex w-full justify-between">
						<div id="chat-bubble-username-label" class=" self-center text-xs">
							{$i18n.t('Display the username instead of You in the Chat')}
						</div>

						<div class="flex items-center gap-2 p-1">
							<Switch
								tooltip={true}
								bind:state={showUsername}
								on:change={() => {
									saveSettings({ showUsername });
								}}
							/>
						</div>
					</div>
				</div>
			{/if}

			<div>
				<div class=" py-0.5 flex w-full justify-between">
					<div id="widescreen-mode-label" class=" self-center text-xs">
						{$i18n.t('Widescreen Mode')}
					</div>

					<div class="flex items-center gap-2 p-1">
						<Switch
							tooltip={true}
							bind:state={widescreenMode}
							on:change={() => {
								saveSettings({ widescreenMode });
							}}
						/>
					</div>
				</div>
			</div>

			<div>
				<div class=" py-0.5 flex w-full justify-between">
					<div id="fade-streaming-label" class=" self-center text-xs">
						{$i18n.t('Fade Effect for Streaming Text')}
					</div>

					<div class="flex items-center gap-2 p-1">
						<Switch
							tooltip={true}
							bind:state={chatFadeStreamingText}
							on:change={() => {
								saveSettings({ chatFadeStreamingText });
							}}
						/>
					</div>
				</div>
			</div>

			<div>
				<div class=" py-0.5 flex w-full justify-between">
					<div id="auto-generation-label" class=" self-center text-xs">
						{$i18n.t('Title Auto-Generation')}
					</div>

					<div class="flex items-center gap-2 p-1">
						<Switch
							tooltip={true}
							bind:state={titleAutoGenerate}
							on:change={() => {
								toggleTitleAutoGenerate();
							}}
						/>
					</div>
				</div>
			</div>

			<div>
				<div class=" py-0.5 flex w-full justify-between">
					<div class=" self-center text-xs">{$i18n.t('Follow-Up Auto-Generation')}</div>

					<div class="flex items-center gap-2 p-1">
						<Switch
							tooltip={true}
							bind:state={autoFollowUps}
							on:change={() => {
								saveSettings({ autoFollowUps });
							}}
						/>
					</div>
				</div>
			</div>

			<div>
				<div class=" py-0.5 flex w-full justify-between">
					<div id="chat-tags-label" class=" self-center text-xs">
						{$i18n.t('Chat Tags Auto-Generation')}
					</div>

					<div class="flex items-center gap-2 p-1">
						<Switch
							tooltip={true}
							bind:state={autoTags}
							on:change={() => {
								saveSettings({ autoTags });
							}}
						/>
					</div>
				</div>
			</div>

			<div>
				<div class=" py-0.5 flex w-full justify-between">
					<div id="auto-copy-label" class=" self-center text-xs">
						{$i18n.t('Auto-Copy Response to Clipboard')}
					</div>

					<div class="flex items-center gap-2 p-1">
						<Switch
							tooltip={true}
							bind:state={responseAutoCopy}
							on:change={() => {
								toggleResponseAutoCopy();
							}}
						/>
					</div>
				</div>
			</div>

			<div>
				<div class=" py-0.5 flex w-full justify-between">
					<div id="keep-followup-prompts-label" class=" self-center text-xs">
						{$i18n.t('Keep Follow-Up Prompts in Chat')}
					</div>

					<div class="flex items-center gap-2 p-1">
						<Switch
							tooltip={true}
							bind:state={keepFollowUpPrompts}
							on:change={() => {
								saveSettings({ keepFollowUpPrompts });
							}}
						/>
					</div>
				</div>
			</div>

			<div>
				<div class=" py-0.5 flex w-full justify-between">
					<div id="insert-followup-prompt-label" class=" self-center text-xs">
						{$i18n.t('Insert Follow-Up Prompt to Input')}
					</div>

					<div class="flex items-center gap-2 p-1">
						<Switch
							tooltip={true}
							bind:state={insertFollowUpPrompt}
							on:change={() => {
								saveSettings({ insertFollowUpPrompt });
							}}
						/>
					</div>
				</div>
			</div>

			<div>
				<div class=" py-0.5 flex w-full justify-between">
					<div id="always-collapse-label" class=" self-center text-xs">
						{$i18n.t('Always Collapse Code Blocks')}
					</div>

					<div class="flex items-center gap-2 p-1">
						<Switch
							tooltip={true}
							bind:state={collapseCodeBlocks}
							on:change={() => {
								saveSettings({ collapseCodeBlocks });
							}}
						/>
					</div>
				</div>
			</div>

			<div>
				<div class=" py-0.5 flex w-full justify-between">
					<div id="always-expand-label" class=" self-center text-xs">
						{$i18n.t('Always Expand Details')}
					</div>

					<div class="flex items-center gap-2 p-1">
						<Switch
							tooltip={true}
							bind:state={expandDetails}
							on:change={() => {
								saveSettings({ expandDetails });
							}}
						/>
					</div>
				</div>
			</div>

			<div>
				<div class=" py-0.5 flex w-full justify-between">
					<div id="keep-followup-prompts-label" class=" self-center text-xs">
						{$i18n.t('Display Multi-model Responses in Tabs')}
					</div>

					<div class="flex items-center gap-2 p-1">
						<Switch
							tooltip={true}
							bind:state={displayMultiModelResponsesInTabs}
							on:change={() => {
								saveSettings({ displayMultiModelResponsesInTabs });
							}}
						/>
					</div>
				</div>
			</div>

			<div>
				<div class=" py-0.5 flex w-full justify-between">
					<div id="scroll-on-branch-change-label" class=" self-center text-xs">
						{$i18n.t('Scroll On Branch Change')}
					</div>

					<div class="flex items-center gap-2 p-1">
						<Switch
							tooltip={true}
							bind:state={scrollOnBranchChange}
							on:change={() => {
								saveSettings({ scrollOnBranchChange });
							}}
						/>
					</div>
				</div>
			</div>

			<div>
				<div class=" py-0.5 flex w-full justify-between">
					<div id="stylized-pdf-export-label" class=" self-center text-xs">
						{$i18n.t('Stylized PDF Export')}
					</div>

					<div class="flex items-center gap-2 p-1">
						<Switch
							tooltip={true}
							bind:state={stylizedPdfExport}
							on:change={() => {
								saveSettings({ stylizedPdfExport });
							}}
						/>
					</div>
				</div>
			</div>

			<div>
				<div class=" py-0.5 flex w-full justify-between">
					<div id="floating-action-buttons-label" class=" self-center text-xs">
						{$i18n.t('Floating Action Buttons')}
					</div>

					<div class="flex items-center gap-3 p-1">
						{#if showFloatingActionButtons}
							<button
								class="text-xs text-gray-700 dark:text-gray-400 underline"
								type="button"
								on:click={() => {
									showManageFloatingActionButtonsModal = true;
								}}
							>
								{$i18n.t('Manage')}
							</button>
						{/if}

						<Switch
							tooltip={true}
							bind:state={showFloatingActionButtons}
							on:change={() => {
								saveSettings({ showFloatingActionButtons });
							}}
						/>
					</div>
				</div>
			</div>

			<div>
				<div class=" py-0.5 flex w-full justify-between">
					<div id="web-search-in-chat-label" class=" self-center text-xs">
						{$i18n.t('Web Search in Chat')}
					</div>

					<button
						aria-labelledby="web-search-in-chat-label"
						class="p-1 px-3 text-xs flex rounded-sm transition"
						on:click={() => {
							toggleWebSearch();
						}}
						type="button"
					>
						{#if webSearch === 'always'}
							<span class="ml-2 self-center">{$i18n.t('Always')}</span>
						{:else}
							<span class="ml-2 self-center">{$i18n.t('Default')}</span>
						{/if}
					</button>
				</div>
			</div>

			<div class=" my-2 text-sm font-medium">{$i18n.t('Input')}</div>

			<div>
				<div class=" py-0.5 flex w-full justify-between">
					<div id="enter-key-behavior-label" class=" self-center text-xs">
						{$i18n.t('Enter Key Behavior')}
					</div>

					<button
						aria-labelledby="enter-key-behavior-label"
						class="p-1 px-3 text-xs flex rounded transition"
						on:click={() => {
							togglectrlEnterToSend();
						}}
						type="button"
					>
						{#if ctrlEnterToSend === true}
							<span class="ml-2 self-center">{$i18n.t('Ctrl+Enter to Send')}</span>
						{:else}
							<span class="ml-2 self-center">{$i18n.t('Enter to Send')}</span>
						{/if}
					</button>
				</div>
			</div>

			<div>
				<div class=" py-0.5 flex w-full justify-between">
					<div id="rich-input-label" class=" self-center text-xs">
						{$i18n.t('Rich Text Input for Chat')}
					</div>

					<div class="flex items-center gap-2 p-1">
						<Switch
							tooltip={true}
							bind:state={richTextInput}
							on:change={() => {
								saveSettings({ richTextInput });
							}}
						/>
					</div>
				</div>
			</div>

			{#if richTextInput}
				<div>
					<div class=" py-0.5 flex w-full justify-between">
						<div id="rich-input-label" class=" self-center text-xs">
							{$i18n.t('Show Formatting Toolbar')}
						</div>

						<div class="flex items-center gap-2 p-1">
							<Switch
								tooltip={true}
								bind:state={showFormattingToolbar}
								on:change={() => {
									saveSettings({ showFormattingToolbar });
								}}
							/>
						</div>
					</div>
				</div>

				<div>
					<div class=" py-0.5 flex w-full justify-between">
						<div id="rich-input-label" class=" self-center text-xs">
							{$i18n.t('Insert Prompt as Rich Text')}
						</div>

						<div class="flex items-center gap-2 p-1">
							<Switch
								tooltip={true}
								bind:state={insertPromptAsRichText}
								on:change={() => {
									saveSettings({ insertPromptAsRichText });
								}}
							/>
						</div>
					</div>
				</div>

				{#if $config?.features?.enable_autocomplete_generation}
					<div>
						<div class=" py-0.5 flex w-full justify-between">
							<div id="prompt-autocompletion-label" class=" self-center text-xs">
								{$i18n.t('Prompt Autocompletion')}
							</div>

							<div class="flex items-center gap-2 p-1">
								<Switch
									tooltip={true}
									bind:state={promptAutocomplete}
									on:change={() => {
										saveSettings({ promptAutocomplete });
									}}
								/>
							</div>
						</div>
					</div>
				{/if}
			{/if}

			<div>
				<div class=" py-0.5 flex w-full justify-between">
					<div id="paste-large-label" class=" self-center text-xs">
						{$i18n.t('Paste Large Text as File')}
					</div>

					<div class="flex items-center gap-2 p-1">
						<Switch
							tooltip={true}
							bind:state={largeTextAsFile}
							on:change={() => {
								saveSettings({ largeTextAsFile });
							}}
						/>
					</div>
				</div>
			</div>

			<div class=" my-2 text-sm font-medium">{$i18n.t('Artifacts')}</div>

			<div>
				<div class=" py-0.5 flex w-full justify-between">
					<div id="detect-artifacts-label" class=" self-center text-xs">
						{$i18n.t('Detect Artifacts Automatically')}
					</div>

					<div class="flex items-center gap-2 p-1">
						<Switch
							tooltip={true}
							bind:state={detectArtifacts}
							on:change={() => {
								saveSettings({ detectArtifacts });
							}}
						/>
					</div>
				</div>
			</div>

			<div>
				<div class=" py-0.5 flex w-full justify-between">
					<div id="iframe-sandbox-allow-same-origin-label" class=" self-center text-xs">
						{$i18n.t('iframe Sandbox Allow Same Origin')}
					</div>

					<div class="flex items-center gap-2 p-1">
						<Switch
							tooltip={true}
							bind:state={iframeSandboxAllowSameOrigin}
							on:change={() => {
								saveSettings({ iframeSandboxAllowSameOrigin });
							}}
						/>
					</div>
				</div>
			</div>

			<div>
				<div class=" py-0.5 flex w-full justify-between">
					<div id="iframe-sandbox-allow-forms-label" class=" self-center text-xs">
						{$i18n.t('iframe Sandbox Allow Forms')}
					</div>

					<div class="flex items-center gap-2 p-1">
						<Switch
							tooltip={true}
							bind:state={iframeSandboxAllowForms}
							on:change={() => {
								saveSettings({ iframeSandboxAllowForms });
							}}
						/>
					</div>
				</div>
			</div>

			<div class=" my-2 text-sm font-medium">{$i18n.t('Voice')}</div>

			<div>
				<div class=" py-0.5 flex w-full justify-between">
					<div class=" self-center text-xs">{$i18n.t('Allow Voice Interruption in Call')}</div>

					<div class="flex items-center gap-2 p-1">
						<Switch
							tooltip={true}
							bind:state={voiceInterruption}
							on:change={() => {
								saveSettings({ voiceInterruption });
							}}
						/>
					</div>
				</div>
			</div>

			<div>
				<div class=" py-0.5 flex w-full justify-between">
					<div id="display-emoji-label" class=" self-center text-xs">
						{$i18n.t('Display Emoji in Call')}
					</div>

					<div class="flex items-center gap-2 p-1">
						<Switch
							tooltip={true}
							bind:state={showEmojiInCall}
							on:change={() => {
								saveSettings({ showEmojiInCall });
							}}
						/>
					</div>
				</div>
			</div>

			<div class=" my-2 text-sm font-medium">{$i18n.t('File')}</div>

			<div>
				<div class=" py-0.5 flex w-full justify-between">
					<div id="image-compression-label" class=" self-center text-xs">
						{$i18n.t('Image Compression')}
					</div>

					<div class="flex items-center gap-2 p-1">
						<Switch
							tooltip={true}
							bind:state={imageCompression}
							on:change={() => {
								saveSettings({ imageCompression });
							}}
						/>
					</div>
				</div>
			</div>

			{#if imageCompression}
				<div>
					<div class=" py-0.5 flex w-full justify-between text-xs">
						<div id="image-compression-size-label" class=" self-center text-xs">
							{$i18n.t('Image Max Compression Size')}
						</div>

						<div class="p-1">
							<label class="sr-only" for="image-comp-width"
								>{$i18n.t('Image Max Compression Size width')}</label
							>
							<input
								bind:value={imageCompressionSize.width}
								type="number"
								class="w-20 bg-transparent outline-hidden text-center"
								min="0"
								placeholder="Width"
							/>x
							<label class="sr-only" for="image-comp-height"
								>{$i18n.t('Image Max Compression Size height')}</label
							>
							<input
								bind:value={imageCompressionSize.height}
								type="number"
								class="w-20 bg-transparent outline-hidden text-center"
								min="0"
								placeholder="Height"
							/>
						</div>
					</div>
				</div>

				<div>
					<div class=" py-0.5 flex w-full justify-between">
						<div id="image-compression-label" class=" self-center text-xs">
							{$i18n.t('Compress Images in Channels')}
						</div>

						<div class="flex items-center gap-2 p-1">
							<Switch
								tooltip={true}
								bind:state={imageCompressionInChannels}
								on:change={() => {
									saveSettings({ imageCompressionInChannels });
								}}
							/>
						</div>
					</div>
				</div>
			{/if}
		</div>
	</div>

	<div class="flex justify-end text-sm font-medium">
		<button
			class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full"
			type="submit"
		>
			{$i18n.t('Save')}
		</button>
	</div>
</form>
