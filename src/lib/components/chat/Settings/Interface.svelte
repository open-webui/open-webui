<script lang="ts">
	import { config, models, settings, user } from '$lib/stores';
	import { createEventDispatcher, onMount, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import { updateUserInfo } from '$lib/apis/users';
	import { getUserPosition } from '$lib/utils';
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

	let richTextInput = true;
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

	let imageCompression = false;
	let imageCompressionSize = {
		width: '',
		height: ''
	};

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

	const toggleExpandDetails = () => {
		expandDetails = !expandDetails;
		saveSettings({ expandDetails });
	};

	const toggleCollapseCodeBlocks = () => {
		collapseCodeBlocks = !collapseCodeBlocks;
		saveSettings({ collapseCodeBlocks });
	};

	const toggleSplitLargeChunks = async () => {
		splitLargeChunks = !splitLargeChunks;
		saveSettings({ splitLargeChunks: splitLargeChunks });
	};

	const toggleHighContrastMode = async () => {
		highContrastMode = !highContrastMode;
		saveSettings({ highContrastMode: highContrastMode });
	};

	const togglePromptAutocomplete = async () => {
		promptAutocomplete = !promptAutocomplete;
		saveSettings({ promptAutocomplete: promptAutocomplete });
	};

	const togglesScrollOnBranchChange = async () => {
		scrollOnBranchChange = !scrollOnBranchChange;
		saveSettings({ scrollOnBranchChange: scrollOnBranchChange });
	};

	const toggleWidescreenMode = async () => {
		widescreenMode = !widescreenMode;
		saveSettings({ widescreenMode: widescreenMode });
	};

	const toggleChatBubble = async () => {
		chatBubble = !chatBubble;
		saveSettings({ chatBubble: chatBubble });
	};

	const toggleLandingPageMode = async () => {
		landingPageMode = landingPageMode === '' ? 'chat' : '';
		saveSettings({ landingPageMode: landingPageMode });
	};

	const toggleShowUpdateToast = async () => {
		showUpdateToast = !showUpdateToast;
		saveSettings({ showUpdateToast: showUpdateToast });
	};

	const toggleNotificationSound = async () => {
		notificationSound = !notificationSound;
		saveSettings({ notificationSound: notificationSound });
	};

	const toggleNotificationSoundAlways = async () => {
		notificationSoundAlways = !notificationSoundAlways;
		saveSettings({ notificationSoundAlways: notificationSoundAlways });
	};

	const toggleShowChangelog = async () => {
		showChangelog = !showChangelog;
		saveSettings({ showChangelog: showChangelog });
	};

	const toggleShowUsername = async () => {
		showUsername = !showUsername;
		saveSettings({ showUsername: showUsername });
	};

	const toggleEmojiInCall = async () => {
		showEmojiInCall = !showEmojiInCall;
		saveSettings({ showEmojiInCall: showEmojiInCall });
	};

	const toggleVoiceInterruption = async () => {
		voiceInterruption = !voiceInterruption;
		saveSettings({ voiceInterruption: voiceInterruption });
	};

	const toggleImageCompression = async () => {
		imageCompression = !imageCompression;
		saveSettings({ imageCompression });
	};

	const toggleChatFadeStreamingText = async () => {
		chatFadeStreamingText = !chatFadeStreamingText;
		saveSettings({ chatFadeStreamingText: chatFadeStreamingText });
	};

	const toggleHapticFeedback = async () => {
		hapticFeedback = !hapticFeedback;
		saveSettings({ hapticFeedback: hapticFeedback });
	};

	const toggleStylizedPdfExport = async () => {
		stylizedPdfExport = !stylizedPdfExport;
		saveSettings({ stylizedPdfExport: stylizedPdfExport });
	};

	const toggleUserLocation = async () => {
		userLocation = !userLocation;

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
		titleAutoGenerate = !titleAutoGenerate;
		saveSettings({
			title: {
				...$settings.title,
				auto: titleAutoGenerate
			}
		});
	};

	const toggleAutoFollowUps = async () => {
		autoFollowUps = !autoFollowUps;
		saveSettings({ autoFollowUps });
	};

	const toggleAutoTags = async () => {
		autoTags = !autoTags;
		saveSettings({ autoTags });
	};

	const toggleDetectArtifacts = async () => {
		detectArtifacts = !detectArtifacts;
		saveSettings({ detectArtifacts });
	};

	const toggleRichTextInput = async () => {
		richTextInput = !richTextInput;
		saveSettings({ richTextInput });
	};

	const toggleInsertPromptAsRichText = async () => {
		insertPromptAsRichText = !insertPromptAsRichText;
		saveSettings({ insertPromptAsRichText });
	};

	const toggleKeepFollowUpPrompts = async () => {
		keepFollowUpPrompts = !keepFollowUpPrompts;
		saveSettings({ keepFollowUpPrompts });
	};

	const toggleInsertFollowUpPrompt = async () => {
		insertFollowUpPrompt = !insertFollowUpPrompt;
		saveSettings({ insertFollowUpPrompt });
	};

	const toggleLargeTextAsFile = async () => {
		largeTextAsFile = !largeTextAsFile;
		saveSettings({ largeTextAsFile });
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

		console.log(permission);

		if (permission === 'granted') {
			responseAutoCopy = !responseAutoCopy;
			saveSettings({ responseAutoCopy: responseAutoCopy });
		} else {
			toast.error(
				$i18n.t(
					'Clipboard write permission denied. Please check your browser settings to grant the necessary access.'
				)
			);
		}
	};

	const toggleCopyFormatted = async () => {
		copyFormatted = !copyFormatted;
		saveSettings({ copyFormatted });
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

	const toggleIframeSandboxAllowSameOrigin = async () => {
		iframeSandboxAllowSameOrigin = !iframeSandboxAllowSameOrigin;
		saveSettings({ iframeSandboxAllowSameOrigin });
	};

	const toggleIframeSandboxAllowForms = async () => {
		iframeSandboxAllowForms = !iframeSandboxAllowForms;
		saveSettings({ iframeSandboxAllowForms });
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

		chatFadeStreamingText = $settings?.chatFadeStreamingText ?? true;

		richTextInput = $settings?.richTextInput ?? true;
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

		imageCompression = $settings?.imageCompression ?? false;
		imageCompressionSize = $settings?.imageCompressionSize ?? { width: '', height: '' };

		defaultModelId = $settings?.models?.at(0) ?? '';
		if ($config?.default_models) {
			defaultModelId = $config.default_models.split(',')[0];
		}

		backgroundImageUrl = $settings?.backgroundImageUrl ?? null;
		webSearch = $settings?.webSearch ?? null;
	});
</script>

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
			<h1 class=" mb-1.5 text-sm font-medium">{$i18n.t('UI')}</h1>

			<div>
				<div class=" py-0.5 flex w-full justify-between">
					<div id="high-contrast-mode-label" class=" self-center text-xs">
						{$i18n.t('High Contrast Mode')} ({$i18n.t('Beta')})
					</div>

					<button
						aria-labelledby="high-contrast-mode-label"
						class="p-1 px-3 text-xs flex rounded-sm transition"
						on:click={() => {
							toggleHighContrastMode();
						}}
						type="button"
					>
						{#if highContrastMode === true}
							<span class="ml-2 self-center">{$i18n.t('On')}</span>
						{:else}
							<span class="ml-2 self-center">{$i18n.t('Off')}</span>
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
					<div id="chat-bubble-ui-label" class=" self-center text-xs">
						{$i18n.t('Chat Bubble UI')}
					</div>

					<button
						aria-labelledby="chat-bubble-ui-label"
						class="p-1 px-3 text-xs flex rounded-sm transition"
						on:click={() => {
							toggleChatBubble();
						}}
						type="button"
					>
						{#if chatBubble === true}
							<span class="ml-2 self-center">{$i18n.t('On')}</span>
						{:else}
							<span class="ml-2 self-center">{$i18n.t('Off')}</span>
						{/if}
					</button>
				</div>
			</div>

			{#if !$settings.chatBubble}
				<div>
					<div class=" py-0.5 flex w-full justify-between">
						<div id="chat-bubble-username-label" class=" self-center text-xs">
							{$i18n.t('Display the username instead of You in the Chat')}
						</div>

						<button
							aria-labelledby="chat-bubble-username-label"
							class="p-1 px-3 text-xs flex rounded-sm transition"
							on:click={() => {
								toggleShowUsername();
							}}
							type="button"
						>
							{#if showUsername === true}
								<span class="ml-2 self-center">{$i18n.t('On')}</span>
							{:else}
								<span class="ml-2 self-center">{$i18n.t('Off')}</span>
							{/if}
						</button>
					</div>
				</div>
			{/if}

			<div>
				<div class=" py-0.5 flex w-full justify-between">
					<div id="widescreen-mode-label" class=" self-center text-xs">
						{$i18n.t('Widescreen Mode')}
					</div>

					<button
						class="p-1 px-3 text-xs flex rounded-sm transition"
						on:click={() => {
							toggleWidescreenMode();
						}}
						aria-labelledby="widescreen-mode-label"
						type="button"
					>
						{#if widescreenMode === true}
							<span class="ml-2 self-center">{$i18n.t('On')}</span>
						{:else}
							<span class="ml-2 self-center">{$i18n.t('Off')}</span>
						{/if}
					</button>
				</div>
			</div>

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
				<div class="py-0.5 flex w-full justify-between">
					<div id="notification-sound-label" class=" self-center text-xs">
						{$i18n.t('Notification Sound')}
					</div>

					<button
						aria-labelledby="notification-sound-label"
						class="p-1 px-3 text-xs flex rounded-sm transition"
						on:click={() => {
							toggleNotificationSound();
						}}
						type="button"
					>
						{#if notificationSound === true}
							<span class="ml-2 self-center">{$i18n.t('On')}</span>
						{:else}
							<span class="ml-2 self-center">{$i18n.t('Off')}</span>
						{/if}
					</button>
				</div>
			</div>

			{#if notificationSound}
				<div>
					<div class=" py-0.5 flex w-full justify-between">
						<div id="play-notification-sound-label" class=" self-center text-xs">
							{$i18n.t('Always Play Notification Sound')}
						</div>

						<button
							aria-labelledby="play-notification-sound-label"
							class="p-1 px-3 text-xs flex rounded-sm transition"
							on:click={() => {
								toggleNotificationSoundAlways();
							}}
							type="button"
						>
							{#if notificationSoundAlways === true}
								<span class="ml-2 self-center">{$i18n.t('On')}</span>
							{:else}
								<span class="ml-2 self-center">{$i18n.t('Off')}</span>
							{/if}
						</button>
					</div>
				</div>
			{/if}

			{#if $user?.role === 'admin'}
				<div>
					<div class=" py-0.5 flex w-full justify-between">
						<div id="toast-notifications-label" class=" self-center text-xs">
							{$i18n.t('Toast notifications for new updates')}
						</div>

						<button
							aria-labelledby="toast-notifications-label"
							class="p-1 px-3 text-xs flex rounded-sm transition"
							on:click={() => {
								toggleShowUpdateToast();
							}}
							type="button"
						>
							{#if showUpdateToast === true}
								<span class="ml-2 self-center">{$i18n.t('On')}</span>
							{:else}
								<span class="ml-2 self-center">{$i18n.t('Off')}</span>
							{/if}
						</button>
					</div>
				</div>

				<div>
					<div class=" py-0.5 flex w-full justify-between">
						<div id="whats-new-label" class=" self-center text-xs">
							{$i18n.t(`Show "What's New" modal on login`)}
						</div>

						<button
							aria-labelledby="whats-new-label"
							class="p-1 px-3 text-xs flex rounded-sm transition"
							on:click={() => {
								toggleShowChangelog();
							}}
							type="button"
						>
							{#if showChangelog === true}
								<span class="ml-2 self-center">{$i18n.t('On')}</span>
							{:else}
								<span class="ml-2 self-center">{$i18n.t('Off')}</span>
							{/if}
						</button>
					</div>
				</div>
			{/if}

			<div class=" my-1.5 text-sm font-medium">{$i18n.t('Chat')}</div>

			<div>
				<div class=" py-0.5 flex w-full justify-between">
					<div id="auto-generation-label" class=" self-center text-xs">
						{$i18n.t('Title Auto-Generation')}
					</div>

					<button
						aria-labelledby="auto-generation-label"
						class="p-1 px-3 text-xs flex rounded-sm transition"
						on:click={() => {
							toggleTitleAutoGenerate();
						}}
						type="button"
					>
						{#if titleAutoGenerate === true}
							<span class="ml-2 self-center">{$i18n.t('On')}</span>
						{:else}
							<span class="ml-2 self-center">{$i18n.t('Off')}</span>
						{/if}
					</button>
				</div>
			</div>

			<div>
				<div class=" py-0.5 flex w-full justify-between">
					<div class=" self-center text-xs">{$i18n.t('Follow-Up Auto-Generation')}</div>

					<button
						aria-labelledby="auto-generation-label"
						class="p-1 px-3 text-xs flex rounded-sm transition"
						on:click={() => {
							toggleAutoFollowUps();
						}}
						type="button"
					>
						{#if autoFollowUps === true}
							<span class="ml-2 self-center">{$i18n.t('On')}</span>
						{:else}
							<span class="ml-2 self-center">{$i18n.t('Off')}</span>
						{/if}
					</button>
				</div>
			</div>

			<div>
				<div class=" py-0.5 flex w-full justify-between">
					<div id="chat-tags-label" class=" self-center text-xs">
						{$i18n.t('Chat Tags Auto-Generation')}
					</div>

					<button
						aria-labelledby="chat-tags-label"
						class="p-1 px-3 text-xs flex rounded-sm transition"
						on:click={() => {
							toggleAutoTags();
						}}
						type="button"
					>
						{#if autoTags === true}
							<span class="ml-2 self-center">{$i18n.t('On')}</span>
						{:else}
							<span class="ml-2 self-center">{$i18n.t('Off')}</span>
						{/if}
					</button>
				</div>
			</div>

			<div>
				<div class=" py-0.5 flex w-full justify-between">
					<div id="detect-artifacts-label" class=" self-center text-xs">
						{$i18n.t('Detect Artifacts Automatically')}
					</div>

					<button
						aria-labelledby="detect-artifacts-label"
						class="p-1 px-3 text-xs flex rounded-sm transition"
						on:click={() => {
							toggleDetectArtifacts();
						}}
						type="button"
					>
						{#if detectArtifacts === true}
							<span class="ml-2 self-center">{$i18n.t('On')}</span>
						{:else}
							<span class="ml-2 self-center">{$i18n.t('Off')}</span>
						{/if}
					</button>
				</div>
			</div>

			<div>
				<div class=" py-0.5 flex w-full justify-between">
					<div id="auto-copy-label" class=" self-center text-xs">
						{$i18n.t('Auto-Copy Response to Clipboard')}
					</div>

					<button
						aria-labelledby="auto-copy-label"
						class="p-1 px-3 text-xs flex rounded-sm transition"
						on:click={() => {
							toggleResponseAutoCopy();
						}}
						type="button"
					>
						{#if responseAutoCopy === true}
							<span class="ml-2 self-center">{$i18n.t('On')}</span>
						{:else}
							<span class="ml-2 self-center">{$i18n.t('Off')}</span>
						{/if}
					</button>
				</div>
			</div>

			<div>
				<div class=" py-0.5 flex w-full justify-between">
					<div id="fade-streaming-label" class=" self-center text-xs">
						{$i18n.t('Fade Effect for Streaming Text')}
					</div>

					<button
						aria-labelledby="fade-streaming-label"
						class="p-1 px-3 text-xs flex rounded-sm transition"
						on:click={() => {
							toggleChatFadeStreamingText();
						}}
						type="button"
					>
						{#if chatFadeStreamingText === true}
							<span class="ml-2 self-center">{$i18n.t('On')}</span>
						{:else}
							<span class="ml-2 self-center">{$i18n.t('Off')}</span>
						{/if}
					</button>
				</div>
			</div>

			<div>
				<div class=" py-0.5 flex w-full justify-between">
					<div id="keep-followup-prompts-label" class=" self-center text-xs">
						{$i18n.t('Keep Follow-Up Prompts in Chat')}
					</div>

					<button
						aria-labelledby="keep-followup-prompts-label"
						class="p-1 px-3 text-xs flex rounded-sm transition"
						on:click={() => {
							toggleKeepFollowUpPrompts();
						}}
						type="button"
					>
						{#if keepFollowUpPrompts === true}
							<span class="ml-2 self-center">{$i18n.t('On')}</span>
						{:else}
							<span class="ml-2 self-center">{$i18n.t('Off')}</span>
						{/if}
					</button>
				</div>
			</div>

			<div>
				<div class=" py-0.5 flex w-full justify-between">
					<div id="insert-followup-prompt-label" class=" self-center text-xs">
						{$i18n.t('Insert Follow-Up Prompt to Input')}
					</div>

					<button
						aria-labelledby="insert-followup-prompt-label"
						class="p-1 px-3 text-xs flex rounded-sm transition"
						on:click={() => {
							toggleInsertFollowUpPrompt();
						}}
						type="button"
					>
						{#if insertFollowUpPrompt === true}
							<span class="ml-2 self-center">{$i18n.t('On')}</span>
						{:else}
							<span class="ml-2 self-center">{$i18n.t('Off')}</span>
						{/if}
					</button>
				</div>
			</div>

			<div>
				<div class=" py-0.5 flex w-full justify-between">
					<div id="rich-input-label" class=" self-center text-xs">
						{$i18n.t('Rich Text Input for Chat')}
					</div>

					<button
						aria-labelledby="rich-input-label"
						class="p-1 px-3 text-xs flex rounded-sm transition"
						on:click={() => {
							toggleRichTextInput();
						}}
						type="button"
					>
						{#if richTextInput === true}
							<span class="ml-2 self-center">{$i18n.t('On')}</span>
						{:else}
							<span class="ml-2 self-center">{$i18n.t('Off')}</span>
						{/if}
					</button>
				</div>
			</div>

			{#if richTextInput}
				<div>
					<div class=" py-0.5 flex w-full justify-between">
						<div id="rich-input-label" class=" self-center text-xs">
							{$i18n.t('Insert Prompt as Rich Text')}
						</div>

						<button
							aria-labelledby="rich-input-label"
							class="p-1 px-3 text-xs flex rounded-sm transition"
							on:click={() => {
								toggleInsertPromptAsRichText();
							}}
							type="button"
						>
							{#if insertPromptAsRichText === true}
								<span class="ml-2 self-center">{$i18n.t('On')}</span>
							{:else}
								<span class="ml-2 self-center">{$i18n.t('Off')}</span>
							{/if}
						</button>
					</div>
				</div>

				{#if $config?.features?.enable_autocomplete_generation}
					<div>
						<div class=" py-0.5 flex w-full justify-between">
							<div id="prompt-autocompletion-label" class=" self-center text-xs">
								{$i18n.t('Prompt Autocompletion')}
							</div>

							<button
								aria-labelledby="prompt-autocompletion-label"
								class="p-1 px-3 text-xs flex rounded-sm transition"
								on:click={() => {
									togglePromptAutocomplete();
								}}
								type="button"
							>
								{#if promptAutocomplete === true}
									<span class="ml-2 self-center">{$i18n.t('On')}</span>
								{:else}
									<span class="ml-2 self-center">{$i18n.t('Off')}</span>
								{/if}
							</button>
						</div>
					</div>
				{/if}
			{/if}

			<div>
				<div class=" py-0.5 flex w-full justify-between">
					<div id="paste-large-label" class=" self-center text-xs">
						{$i18n.t('Paste Large Text as File')}
					</div>

					<button
						aria-labelledby="paste-large-label"
						class="p-1 px-3 text-xs flex rounded-sm transition"
						on:click={() => {
							toggleLargeTextAsFile();
						}}
						type="button"
					>
						{#if largeTextAsFile === true}
							<span class="ml-2 self-center">{$i18n.t('On')}</span>
						{:else}
							<span class="ml-2 self-center">{$i18n.t('Off')}</span>
						{/if}
					</button>
				</div>
			</div>

			<div>
				<div class=" py-0.5 flex w-full justify-between">
					<div id="copy-formatted-label" class=" self-center text-xs">
						{$i18n.t('Copy Formatted Text')}
					</div>

					<button
						aria-labelledby="copy-formatted-label"
						class="p-1 px-3 text-xs flex rounded-sm transition"
						on:click={() => {
							toggleCopyFormatted();
						}}
						type="button"
					>
						{#if copyFormatted === true}
							<span class="ml-2 self-center">{$i18n.t('On')}</span>
						{:else}
							<span class="ml-2 self-center">{$i18n.t('Off')}</span>
						{/if}
					</button>
				</div>
			</div>

			<div>
				<div class=" py-0.5 flex w-full justify-between">
					<div id="always-collapse-label" class=" self-center text-xs">
						{$i18n.t('Always Collapse Code Blocks')}
					</div>

					<button
						aria-labelledby="always-collapse-label"
						class="p-1 px-3 text-xs flex rounded-sm transition"
						on:click={() => {
							toggleCollapseCodeBlocks();
						}}
						type="button"
					>
						{#if collapseCodeBlocks === true}
							<span class="ml-2 self-center">{$i18n.t('On')}</span>
						{:else}
							<span class="ml-2 self-center">{$i18n.t('Off')}</span>
						{/if}
					</button>
				</div>
			</div>

			<div>
				<div class=" py-0.5 flex w-full justify-between">
					<div id="always-expand-label" class=" self-center text-xs">
						{$i18n.t('Always Expand Details')}
					</div>

					<button
						aria-labelledby="always-expand-label"
						class="p-1 px-3 text-xs flex rounded-sm transition"
						on:click={() => {
							toggleExpandDetails();
						}}
						type="button"
					>
						{#if expandDetails === true}
							<span class="ml-2 self-center">{$i18n.t('On')}</span>
						{:else}
							<span class="ml-2 self-center">{$i18n.t('Off')}</span>
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
				<div id="allow-user-location-label" class=" py-0.5 flex w-full justify-between">
					<div class=" self-center text-xs">{$i18n.t('Allow User Location')}</div>

					<button
						aria-labelledby="allow-user-location-label"
						class="p-1 px-3 text-xs flex rounded-sm transition"
						on:click={() => {
							toggleUserLocation();
						}}
						type="button"
					>
						{#if userLocation === true}
							<span class="ml-2 self-center">{$i18n.t('On')}</span>
						{:else}
							<span class="ml-2 self-center">{$i18n.t('Off')}</span>
						{/if}
					</button>
				</div>
			</div>

			<div>
				<div class=" py-0.5 flex w-full justify-between">
					<div id="haptic-feedback-label" class=" self-center text-xs">
						{$i18n.t('Haptic Feedback')} ({$i18n.t('Android')})
					</div>

					<button
						aria-labelledby="haptic-feedback-label"
						class="p-1 px-3 text-xs flex rounded-sm transition"
						on:click={() => {
							toggleHapticFeedback();
						}}
						type="button"
					>
						{#if hapticFeedback === true}
							<span class="ml-2 self-center">{$i18n.t('On')}</span>
						{:else}
							<span class="ml-2 self-center">{$i18n.t('Off')}</span>
						{/if}
					</button>
				</div>
			</div>

			<!-- <div>
				<div class=" py-0.5 flex w-full justify-between">
					<div id="fluidly-stream-label" class=" self-center text-xs">
						{$i18n.t('Fluidly stream large external response chunks')}
					</div>

					<button
					aria-labelledby="fluidly-stream-label"
						class="p-1 px-3 text-xs flex rounded-sm transition"
						on:click={() => {
							toggleSplitLargeChunks();
						}}
						type="button"
					>
						{#if splitLargeChunks === true}
							<span class="ml-2 self-center">{$i18n.t('On')}</span>
						{:else}
							<span class="ml-2 self-center">{$i18n.t('Off')}</span>
						{/if}
					</button>
				</div>
			</div> -->

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
					<div id="scroll-on-branch-change-label" class=" self-center text-xs">
						{$i18n.t('Scroll On Branch Change')}
					</div>

					<button
						aria-labelledby="scroll-on-branch-change-label"
						class="p-1 px-3 text-xs flex rounded-sm transition"
						on:click={() => {
							togglesScrollOnBranchChange();
						}}
						type="button"
					>
						{#if scrollOnBranchChange === true}
							<span class="ml-2 self-center">{$i18n.t('On')}</span>
						{:else}
							<span class="ml-2 self-center">{$i18n.t('Off')}</span>
						{/if}
					</button>
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

			<div>
				<div class=" py-0.5 flex w-full justify-between">
					<div id="iframe-sandbox-allow-same-origin-label" class=" self-center text-xs">
						{$i18n.t('iframe Sandbox Allow Same Origin')}
					</div>

					<button
						aria-labelledby="iframe-sandbox-allow-same-origin-label"
						class="p-1 px-3 text-xs flex rounded-sm transition"
						on:click={() => {
							toggleIframeSandboxAllowSameOrigin();
						}}
						type="button"
					>
						{#if iframeSandboxAllowSameOrigin === true}
							<span class="ml-2 self-center">{$i18n.t('On')}</span>
						{:else}
							<span class="ml-2 self-center">{$i18n.t('Off')}</span>
						{/if}
					</button>
				</div>
			</div>

			<div>
				<div class=" py-0.5 flex w-full justify-between">
					<div id="iframe-sandbox-allow-forms-label" class=" self-center text-xs">
						{$i18n.t('iframe Sandbox Allow Forms')}
					</div>

					<button
						aria-labelledby="iframe-sandbox-allow-forms-label"
						class="p-1 px-3 text-xs flex rounded-sm transition"
						on:click={() => {
							toggleIframeSandboxAllowForms();
						}}
						type="button"
					>
						{#if iframeSandboxAllowForms === true}
							<span class="ml-2 self-center">{$i18n.t('On')}</span>
						{:else}
							<span class="ml-2 self-center">{$i18n.t('Off')}</span>
						{/if}
					</button>
				</div>
			</div>

			<div>
				<div class=" py-0.5 flex w-full justify-between">
					<div id="stylized-pdf-export-label" class=" self-center text-xs">
						{$i18n.t('Stylized PDF Export')}
					</div>

					<button
						aria-labelledby="stylized-pdf-export-label"
						class="p-1 px-3 text-xs flex rounded-sm transition"
						on:click={() => {
							toggleStylizedPdfExport();
						}}
						type="button"
					>
						{#if stylizedPdfExport === true}
							<span class="ml-2 self-center">{$i18n.t('On')}</span>
						{:else}
							<span class="ml-2 self-center">{$i18n.t('Off')}</span>
						{/if}
					</button>
				</div>
			</div>

			<div class=" my-1.5 text-sm font-medium">{$i18n.t('Voice')}</div>

			<div>
				<div class=" py-0.5 flex w-full justify-between">
					<div class=" self-center text-xs">{$i18n.t('Allow Voice Interruption in Call')}</div>

					<button
						aria-labelledby="allow-voice-interruption-label"
						class="p-1 px-3 text-xs flex rounded-sm transition"
						on:click={() => {
							toggleVoiceInterruption();
						}}
						type="button"
					>
						{#if voiceInterruption === true}
							<span class="ml-2 self-center">{$i18n.t('On')}</span>
						{:else}
							<span class="ml-2 self-center">{$i18n.t('Off')}</span>
						{/if}
					</button>
				</div>
			</div>

			<div>
				<div class=" py-0.5 flex w-full justify-between">
					<div id="display-emoji-label" class=" self-center text-xs">
						{$i18n.t('Display Emoji in Call')}
					</div>

					<button
						aria-labelledby="display-emoji-label"
						class="p-1 px-3 text-xs flex rounded-sm transition"
						on:click={() => {
							toggleEmojiInCall();
						}}
						type="button"
					>
						{#if showEmojiInCall === true}
							<span class="ml-2 self-center">{$i18n.t('On')}</span>
						{:else}
							<span class="ml-2 self-center">{$i18n.t('Off')}</span>
						{/if}
					</button>
				</div>
			</div>

			<div class=" my-1.5 text-sm font-medium">{$i18n.t('File')}</div>

			<div>
				<div class=" py-0.5 flex w-full justify-between">
					<div id="image-compression-label" class=" self-center text-xs">
						{$i18n.t('Image Compression')}
					</div>

					<button
						aria-labelledby="image-compression-label"
						class="p-1 px-3 text-xs flex rounded-sm transition"
						on:click={() => {
							toggleImageCompression();
						}}
						type="button"
					>
						{#if imageCompression === true}
							<span class="ml-2 self-center">{$i18n.t('On')}</span>
						{:else}
							<span class="ml-2 self-center">{$i18n.t('Off')}</span>
						{/if}
					</button>
				</div>
			</div>

			{#if imageCompression}
				<div>
					<div class=" py-0.5 flex w-full justify-between text-xs">
						<div id="image-compression-size-label" class=" self-center text-xs">
							{$i18n.t('Image Max Compression Size')}
						</div>

						<div>
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
