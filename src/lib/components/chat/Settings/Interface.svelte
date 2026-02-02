<script lang="ts">
	import { getBackendConfig } from '$lib/apis';
	import { setDefaultPromptSuggestions } from '$lib/apis/configs';
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

	let detectArtifacts = true;

	let richTextInput = true;
	let promptAutocomplete = false;

	let largeTextAsFile = false;

	let landingPageMode = '';
	let chatBubble = true;
	let chatDirection: 'LTR' | 'RTL' | 'auto' = 'auto';
	let ctrlEnterToSend = false;
	let copyFormatted = false;

	let collapseCodeBlocks = false;
	let expandDetails = false;

	let imageCompression = false;
	let imageCompressionSize = {
		width: '',
		height: ''
	};

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

	const toggleHapticFeedback = async () => {
		hapticFeedback = !hapticFeedback;
		saveSettings({ hapticFeedback: hapticFeedback });
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
		autoTags = $settings.autoTags ?? true;

		detectArtifacts = $settings.detectArtifacts ?? true;
		responseAutoCopy = $settings.responseAutoCopy ?? false;

		showUsername = $settings.showUsername ?? false;
		showUpdateToast = $settings.showUpdateToast ?? true;
		showChangelog = $settings.showChangelog ?? true;

		showEmojiInCall = $settings.showEmojiInCall ?? false;
		voiceInterruption = $settings.voiceInterruption ?? false;

		richTextInput = $settings.richTextInput ?? true;
		promptAutocomplete = $settings.promptAutocomplete ?? false;
		largeTextAsFile = $settings.largeTextAsFile ?? false;
		copyFormatted = $settings.copyFormatted ?? false;

		collapseCodeBlocks = $settings.collapseCodeBlocks ?? false;
		expandDetails = $settings.expandDetails ?? false;

		landingPageMode = $settings.landingPageMode ?? '';
		chatBubble = $settings.chatBubble ?? true;
		widescreenMode = $settings.widescreenMode ?? false;
		splitLargeChunks = $settings.splitLargeChunks ?? false;
		scrollOnBranchChange = $settings.scrollOnBranchChange ?? true;
		chatDirection = $settings.chatDirection ?? 'auto';
		userLocation = $settings.userLocation ?? false;

		notificationSound = $settings.notificationSound ?? true;

		hapticFeedback = $settings.hapticFeedback ?? false;
		ctrlEnterToSend = $settings.ctrlEnterToSend ?? false;

		imageCompression = $settings.imageCompression ?? false;
		imageCompressionSize = $settings.imageCompressionSize ?? { width: '', height: '' };

		defaultModelId = $settings?.models?.at(0) ?? '';
		if ($config?.default_models) {
			defaultModelId = $config.default_models.split(',')[0];
		}

		backgroundImageUrl = $settings.backgroundImageUrl ?? null;
		webSearch = $settings.webSearch ?? null;

		iframeSandboxAllowSameOrigin = $settings.iframeSandboxAllowSameOrigin ?? false;
		iframeSandboxAllowForms = $settings.iframeSandboxAllowForms ?? false;
	});
</script>

<form
	class="flex flex-col h-full justify-between"
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

	<div class="space-y-6 overflow-y-auto">
		<!-- UI Display Section -->
		<div class="space-y-4">
			<div>
				<h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-1">
					{$i18n.t('UI')}
				</h3>
				<p class="text-sm text-gray-500 dark:text-gray-400">
					Customize your interface display and layout
				</p>
			</div>

			<!-- Landing Page Mode -->
			<div class="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-4">
				<div class="flex items-center justify-between">
					<div>
						<div class="text-sm font-medium text-gray-900 dark:text-white">
							{$i18n.t('Landing Page Mode')}
						</div>
						<div class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
							Choose your default starting page
						</div>
					</div>
					<button
						class="px-4 py-1.5 text-sm font-medium rounded-lg transition-colors {landingPageMode ===
						''
							? 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300'
							: 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400'}"
						on:click={() => {
							toggleLandingPageMode();
						}}
						type="button"
					>
						{landingPageMode === '' ? $i18n.t('Default') : $i18n.t('Chat')}
					</button>
				</div>
			</div>

			<!-- Chat Bubble UI -->
			<div class="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-4">
				<div class="flex items-center justify-between">
					<div>
						<div class="text-sm font-medium text-gray-900 dark:text-white">
							{$i18n.t('Chat Bubble UI')}
						</div>
						<div class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
							Display messages in chat bubble style
						</div>
					</div>
					<button
						class="relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 {chatBubble
							? 'bg-blue-600'
							: 'bg-gray-300 dark:bg-gray-700'}"
						on:click={() => {
							toggleChatBubble();
						}}
						type="button"
					>
						<span
							class="inline-block h-4 w-4 transform rounded-full bg-white transition-transform {chatBubble
								? 'translate-x-6'
								: 'translate-x-1'}"
						/>
					</button>
				</div>
			</div>

			<!-- Show Username -->
			{#if !$settings.chatBubble}
				<div class="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-4">
					<div class="flex items-center justify-between">
						<div>
							<div class="text-sm font-medium text-gray-900 dark:text-white">
								{$i18n.t('Display the username instead of You in the Chat')}
							</div>
							<div class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
								Show your username in messages
							</div>
						</div>
						<button
							class="relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 {showUsername
								? 'bg-blue-600'
								: 'bg-gray-300 dark:bg-gray-700'}"
							on:click={() => {
								toggleShowUsername();
							}}
							type="button"
						>
							<span
								class="inline-block h-4 w-4 transform rounded-full bg-white transition-transform {showUsername
									? 'translate-x-6'
									: 'translate-x-1'}"
							/>
						</button>
					</div>
				</div>
			{/if}

			<!-- Widescreen Mode -->
			<div class="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-4">
				<div class="flex items-center justify-between">
					<div>
						<div class="text-sm font-medium text-gray-900 dark:text-white">
							{$i18n.t('Widescreen Mode')}
						</div>
						<div class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
							Expand chat width for larger displays
						</div>
					</div>
					<button
						class="relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 {widescreenMode
							? 'bg-blue-600'
							: 'bg-gray-300 dark:bg-gray-700'}"
						on:click={() => {
							toggleWidescreenMode();
						}}
						type="button"
					>
						<span
							class="inline-block h-4 w-4 transform rounded-full bg-white transition-transform {widescreenMode
								? 'translate-x-6'
								: 'translate-x-1'}"
						/>
					</button>
				</div>
			</div>

			<!-- Chat Direction -->
			<div class="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-4">
				<div class="flex items-center justify-between">
					<div>
						<div class="text-sm font-medium text-gray-900 dark:text-white">
							{$i18n.t('Chat direction')}
						</div>
						<div class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
							Set text direction for chat messages
						</div>
					</div>
					<button
						class="px-4 py-1.5 text-sm font-medium bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg transition-colors hover:bg-gray-300 dark:hover:bg-gray-600"
						on:click={toggleChangeChatDirection}
						type="button"
					>
						{#if chatDirection === 'LTR'}
							{$i18n.t('LTR')}
						{:else if chatDirection === 'RTL'}
							{$i18n.t('RTL')}
						{:else}
							{$i18n.t('Auto')}
						{/if}
					</button>
				</div>
			</div>

			<!-- Notification Sound -->
			<div class="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-4">
				<div class="flex items-center justify-between">
					<div>
						<div class="text-sm font-medium text-gray-900 dark:text-white">
							{$i18n.t('Notification Sound')}
						</div>
						<div class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
							Play sound when receiving responses
						</div>
					</div>
					<button
						class="relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 {notificationSound
							? 'bg-blue-600'
							: 'bg-gray-300 dark:bg-gray-700'}"
						on:click={() => {
							toggleNotificationSound();
						}}
						type="button"
					>
						<span
							class="inline-block h-4 w-4 transform rounded-full bg-white transition-transform {notificationSound
								? 'translate-x-6'
								: 'translate-x-1'}"
						/>
					</button>
				</div>
			</div>

			<!-- Admin Settings -->
			{#if $user?.role === 'admin'}
				<div class="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-4">
					<div class="flex items-center justify-between">
						<div>
							<div class="text-sm font-medium text-gray-900 dark:text-white">
								{$i18n.t('Toast notifications for new updates')}
							</div>
							<div class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
								Show notification when updates are available
							</div>
						</div>
						<button
							class="relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 {showUpdateToast
								? 'bg-blue-600'
								: 'bg-gray-300 dark:bg-gray-700'}"
							on:click={() => {
								toggleShowUpdateToast();
							}}
							type="button"
						>
							<span
								class="inline-block h-4 w-4 transform rounded-full bg-white transition-transform {showUpdateToast
									? 'translate-x-6'
									: 'translate-x-1'}"
							/>
						</button>
					</div>
				</div>

				<div class="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-4">
					<div class="flex items-center justify-between">
						<div>
							<div class="text-sm font-medium text-gray-900 dark:text-white">
								{$i18n.t(`Show "What's New" modal on login`)}
							</div>
							<div class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
								Display changelog on application start
							</div>
						</div>
						<button
							class="relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 {showChangelog
								? 'bg-blue-600'
								: 'bg-gray-300 dark:bg-gray-700'}"
							on:click={() => {
								toggleShowChangelog();
							}}
							type="button"
						>
							<span
								class="inline-block h-4 w-4 transform rounded-full bg-white transition-transform {showChangelog
									? 'translate-x-6'
									: 'translate-x-1'}"
							/>
						</button>
					</div>
				</div>
			{/if}
		</div>

		<!-- Chat Features Section -->
		<div class="space-y-4 pt-2">
			<div>
				<h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-1">
					{$i18n.t('Chat')}
				</h3>
				<p class="text-sm text-gray-500 dark:text-gray-400">
					Configure chat behavior and automation
				</p>
			</div>

			<!-- Title Auto-Generation -->
			<div class="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-4">
				<div class="flex items-center justify-between">
					<div>
						<div class="text-sm font-medium text-gray-900 dark:text-white">
							{$i18n.t('Title Auto-Generation')}
						</div>
						<div class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
							Automatically generate titles for conversations
						</div>
					</div>
					<button
						class="relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 {titleAutoGenerate
							? 'bg-blue-600'
							: 'bg-gray-300 dark:bg-gray-700'}"
						on:click={() => {
							toggleTitleAutoGenerate();
						}}
						type="button"
					>
						<span
							class="inline-block h-4 w-4 transform rounded-full bg-white transition-transform {titleAutoGenerate
								? 'translate-x-6'
								: 'translate-x-1'}"
						/>
					</button>
				</div>
			</div>

			<!-- Auto Tags -->
			<div class="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-4">
				<div class="flex items-center justify-between">
					<div>
						<div class="text-sm font-medium text-gray-900 dark:text-white">
							{$i18n.t('Chat Tags Auto-Generation')}
						</div>
						<div class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
							Automatically tag conversations by topic
						</div>
					</div>
					<button
						class="relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 {autoTags
							? 'bg-blue-600'
							: 'bg-gray-300 dark:bg-gray-700'}"
						on:click={() => {
							toggleAutoTags();
						}}
						type="button"
					>
						<span
							class="inline-block h-4 w-4 transform rounded-full bg-white transition-transform {autoTags
								? 'translate-x-6'
								: 'translate-x-1'}"
						/>
					</button>
				</div>
			</div>

			<!-- Detect Artifacts -->
			<div class="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-4">
				<div class="flex items-center justify-between">
					<div>
						<div class="text-sm font-medium text-gray-900 dark:text-white">
							{$i18n.t('Detect Artifacts Automatically')}
						</div>
						<div class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
							Automatically detect and display artifacts
						</div>
					</div>
					<button
						class="relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 {detectArtifacts
							? 'bg-blue-600'
							: 'bg-gray-300 dark:bg-gray-700'}"
						on:click={() => {
							toggleDetectArtifacts();
						}}
						type="button"
					>
						<span
							class="inline-block h-4 w-4 transform rounded-full bg-white transition-transform {detectArtifacts
								? 'translate-x-6'
								: 'translate-x-1'}"
						/>
					</button>
				</div>
			</div>

			<!-- Auto-Copy Response -->
			<div class="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-4">
				<div class="flex items-center justify-between">
					<div>
						<div class="text-sm font-medium text-gray-900 dark:text-white">
							{$i18n.t('Auto-Copy Response to Clipboard')}
						</div>
						<div class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
							Automatically copy responses to clipboard
						</div>
					</div>
					<button
						class="relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 {responseAutoCopy
							? 'bg-blue-600'
							: 'bg-gray-300 dark:bg-gray-700'}"
						on:click={() => {
							toggleResponseAutoCopy();
						}}
						type="button"
					>
						<span
							class="inline-block h-4 w-4 transform rounded-full bg-white transition-transform {responseAutoCopy
								? 'translate-x-6'
								: 'translate-x-1'}"
						/>
					</button>
				</div>
			</div>

			<!-- Rich Text Input -->
			<div class="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-4">
				<div class="flex items-center justify-between">
					<div>
						<div class="text-sm font-medium text-gray-900 dark:text-white">
							{$i18n.t('Rich Text Input for Chat')}
						</div>
						<div class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
							Enable formatting in message input
						</div>
					</div>
					<button
						class="relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 {richTextInput
							? 'bg-blue-600'
							: 'bg-gray-300 dark:bg-gray-700'}"
						on:click={() => {
							toggleRichTextInput();
						}}
						type="button"
					>
						<span
							class="inline-block h-4 w-4 transform rounded-full bg-white transition-transform {richTextInput
								? 'translate-x-6'
								: 'translate-x-1'}"
						/>
					</button>
				</div>
			</div>

			<!-- Prompt Autocomplete -->
			{#if $config?.features?.enable_autocomplete_generation && richTextInput}
				<div class="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-4">
					<div class="flex items-center justify-between">
						<div>
							<div class="text-sm font-medium text-gray-900 dark:text-white">
								{$i18n.t('Prompt Autocompletion')}
							</div>
							<div class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
								Get AI-powered prompt suggestions
							</div>
						</div>
						<button
							class="relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 {promptAutocomplete
								? 'bg-blue-600'
								: 'bg-gray-300 dark:bg-gray-700'}"
							on:click={() => {
								togglePromptAutocomplete();
							}}
							type="button"
						>
							<span
								class="inline-block h-4 w-4 transform rounded-full bg-white transition-transform {promptAutocomplete
									? 'translate-x-6'
									: 'translate-x-1'}"
							/>
						</button>
					</div>
				</div>
			{/if}

			<!-- Large Text as File -->
			<div class="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-4">
				<div class="flex items-center justify-between">
					<div>
						<div class="text-sm font-medium text-gray-900 dark:text-white">
							{$i18n.t('Paste Large Text as File')}
						</div>
						<div class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
							Convert large pasted text to file attachment
						</div>
					</div>
					<button
						class="relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 {largeTextAsFile
							? 'bg-blue-600'
							: 'bg-gray-300 dark:bg-gray-700'}"
						on:click={() => {
							toggleLargeTextAsFile();
						}}
						type="button"
					>
						<span
							class="inline-block h-4 w-4 transform rounded-full bg-white transition-transform {largeTextAsFile
								? 'translate-x-6'
								: 'translate-x-1'}"
						/>
					</button>
				</div>
			</div>

			<!-- Copy Formatted Text -->
			<div class="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-4">
				<div class="flex items-center justify-between">
					<div>
						<div class="text-sm font-medium text-gray-900 dark:text-white">
							{$i18n.t('Copy Formatted Text')}
						</div>
						<div class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
							Preserve formatting when copying
						</div>
					</div>
					<button
						class="relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 {copyFormatted
							? 'bg-blue-600'
							: 'bg-gray-300 dark:bg-gray-700'}"
						on:click={() => {
							toggleCopyFormatted();
						}}
						type="button"
					>
						<span
							class="inline-block h-4 w-4 transform rounded-full bg-white transition-transform {copyFormatted
								? 'translate-x-6'
								: 'translate-x-1'}"
						/>
					</button>
				</div>
			</div>

			<!-- Collapse Code Blocks -->
			<div class="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-4">
				<div class="flex items-center justify-between">
					<div>
						<div class="text-sm font-medium text-gray-900 dark:text-white">
							{$i18n.t('Always Collapse Code Blocks')}
						</div>
						<div class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
							Collapse code blocks by default
						</div>
					</div>
					<button
						class="relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 {collapseCodeBlocks
							? 'bg-blue-600'
							: 'bg-gray-300 dark:bg-gray-700'}"
						on:click={() => {
							toggleCollapseCodeBlocks();
						}}
						type="button"
					>
						<span
							class="inline-block h-4 w-4 transform rounded-full bg-white transition-transform {collapseCodeBlocks
								? 'translate-x-6'
								: 'translate-x-1'}"
						/>
					</button>
				</div>
			</div>

			<!-- Expand Details -->
			<div class="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-4">
				<div class="flex items-center justify-between">
					<div>
						<div class="text-sm font-medium text-gray-900 dark:text-white">
							{$i18n.t('Always Expand Details')}
						</div>
						<div class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
							Expand details sections by default
						</div>
					</div>
					<button
						class="relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 {expandDetails
							? 'bg-blue-600'
							: 'bg-gray-300 dark:bg-gray-700'}"
						on:click={() => {
							toggleExpandDetails();
						}}
						type="button"
					>
						<span
							class="inline-block h-4 w-4 transform rounded-full bg-white transition-transform {expandDetails
								? 'translate-x-6'
								: 'translate-x-1'}"
						/>
					</button>
				</div>
			</div>

			<!-- Chat Background -->
			<div class="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-4">
				<div class="flex items-center justify-between">
					<div>
						<div class="text-sm font-medium text-gray-900 dark:text-white">
							{$i18n.t('Chat Background Image')}
						</div>
						<div class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
							Set a custom background for chat
						</div>
					</div>
					<button
						class="px-4 py-1.5 text-sm font-medium rounded-lg transition-colors {backgroundImageUrl !==
						null
							? 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400 hover:bg-red-200 dark:hover:bg-red-900/50'
							: 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400 hover:bg-blue-200 dark:hover:bg-blue-900/50'}"
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
						{backgroundImageUrl !== null ? $i18n.t('Reset') : $i18n.t('Upload')}
					</button>
				</div>
			</div>

			<!-- User Location -->
			<div class="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-4">
				<div class="flex items-center justify-between">
					<div>
						<div class="text-sm font-medium text-gray-900 dark:text-white">
							{$i18n.t('Allow User Location')}
						</div>
						<div class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
							Share location for location-aware responses
						</div>
					</div>
					<button
						class="relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 {userLocation
							? 'bg-blue-600'
							: 'bg-gray-300 dark:bg-gray-700'}"
						on:click={() => {
							toggleUserLocation();
						}}
						type="button"
					>
						<span
							class="inline-block h-4 w-4 transform rounded-full bg-white transition-transform {userLocation
								? 'translate-x-6'
								: 'translate-x-1'}"
						/>
					</button>
				</div>
			</div>

			<!-- Haptic Feedback -->
			<div class="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-4">
				<div class="flex items-center justify-between">
					<div>
						<div class="text-sm font-medium text-gray-900 dark:text-white">
							{$i18n.t('Haptic Feedback')} ({$i18n.t('Android')})
						</div>
						<div class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
							Enable vibration feedback on Android
						</div>
					</div>
					<button
						class="relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 {hapticFeedback
							? 'bg-blue-600'
							: 'bg-gray-300 dark:bg-gray-700'}"
						on:click={() => {
							toggleHapticFeedback();
						}}
						type="button"
					>
						<span
							class="inline-block h-4 w-4 transform rounded-full bg-white transition-transform {hapticFeedback
								? 'translate-x-6'
								: 'translate-x-1'}"
						/>
					</button>
				</div>
			</div>

			<!-- Enter Key Behavior -->
			<div class="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-4">
				<div class="flex items-center justify-between">
					<div>
						<div class="text-sm font-medium text-gray-900 dark:text-white">
							{$i18n.t('Enter Key Behavior')}
						</div>
						<div class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
							Configure how Enter key sends messages
						</div>
					</div>
					<button
						class="px-4 py-1.5 text-sm font-medium bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg transition-colors hover:bg-gray-300 dark:hover:bg-gray-600"
						on:click={() => {
							togglectrlEnterToSend();
						}}
						type="button"
					>
						{ctrlEnterToSend ? $i18n.t('Ctrl+Enter to Send') : $i18n.t('Enter to Send')}
					</button>
				</div>
			</div>

			<!-- Scroll on Branch Change -->
			<div class="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-4">
				<div class="flex items-center justify-between">
					<div>
						<div class="text-sm font-medium text-gray-900 dark:text-white">
							{$i18n.t('Scroll to bottom when switching between branches')}
						</div>
						<div class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
							Auto-scroll when navigating conversation branches
						</div>
					</div>
					<button
						class="relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 {scrollOnBranchChange
							? 'bg-blue-600'
							: 'bg-gray-300 dark:bg-gray-700'}"
						on:click={() => {
							togglesScrollOnBranchChange();
						}}
						type="button"
					>
						<span
							class="inline-block h-4 w-4 transform rounded-full bg-white transition-transform {scrollOnBranchChange
								? 'translate-x-6'
								: 'translate-x-1'}"
						/>
					</button>
				</div>
			</div>

			<!-- Web Search -->
			<div class="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-4">
				<div class="flex items-center justify-between">
					<div>
						<div class="text-sm font-medium text-gray-900 dark:text-white">
							{$i18n.t('Web Search in Chat')}
						</div>
						<div class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
							Configure web search availability
						</div>
					</div>
					<button
						class="px-4 py-1.5 text-sm font-medium rounded-lg transition-colors {webSearch ===
						'always'
							? 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400'
							: 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300'}"
						on:click={() => {
							toggleWebSearch();
						}}
						type="button"
					>
						{webSearch === 'always' ? $i18n.t('Always') : $i18n.t('Default')}
					</button>
				</div>
			</div>

			<!-- iframe Sandbox Settings -->
			<div class="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-4">
				<div class="flex items-center justify-between">
					<div>
						<div class="text-sm font-medium text-gray-900 dark:text-white">
							{$i18n.t('iframe Sandbox Allow Same Origin')}
						</div>
						<div class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
							Allow same-origin access in iframes
						</div>
					</div>
					<button
						class="relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 {iframeSandboxAllowSameOrigin
							? 'bg-blue-600'
							: 'bg-gray-300 dark:bg-gray-700'}"
						on:click={() => {
							toggleIframeSandboxAllowSameOrigin();
						}}
						type="button"
					>
						<span
							class="inline-block h-4 w-4 transform rounded-full bg-white transition-transform {iframeSandboxAllowSameOrigin
								? 'translate-x-6'
								: 'translate-x-1'}"
						/>
					</button>
				</div>
			</div>

			<div class="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-4">
				<div class="flex items-center justify-between">
					<div>
						<div class="text-sm font-medium text-gray-900 dark:text-white">
							{$i18n.t('iframe Sandbox Allow Forms')}
						</div>
						<div class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
							Allow form submissions in iframes
						</div>
					</div>
					<button
						class="relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 {iframeSandboxAllowForms
							? 'bg-blue-600'
							: 'bg-gray-300 dark:bg-gray-700'}"
						on:click={() => {
							toggleIframeSandboxAllowForms();
						}}
						type="button"
					>
						<span
							class="inline-block h-4 w-4 transform rounded-full bg-white transition-transform {iframeSandboxAllowForms
								? 'translate-x-6'
								: 'translate-x-1'}"
						/>
					</button>
				</div>
			</div>
		</div>

		<!-- Voice Section -->
		<div class="space-y-4 pt-2">
			<div>
				<h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-1">
					{$i18n.t('Voice')}
				</h3>
				<p class="text-sm text-gray-500 dark:text-gray-400">
					Configure voice call features
				</p>
			</div>

			<!-- Voice Interruption -->
			<div class="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-4">
				<div class="flex items-center justify-between">
					<div>
						<div class="text-sm font-medium text-gray-900 dark:text-white">
							{$i18n.t('Allow Voice Interruption in Call')}
						</div>
						<div class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
							Interrupt AI voice with your voice
						</div>
					</div>
					<button
						class="relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 {voiceInterruption
							? 'bg-blue-600'
							: 'bg-gray-300 dark:bg-gray-700'}"
						on:click={() => {
							toggleVoiceInterruption();
						}}
						type="button"
					>
						<span
							class="inline-block h-4 w-4 transform rounded-full bg-white transition-transform {voiceInterruption
								? 'translate-x-6'
								: 'translate-x-1'}"
						/>
					</button>
				</div>
			</div>

			<!-- Display Emoji -->
			<div class="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-4">
				<div class="flex items-center justify-between">
					<div>
						<div class="text-sm font-medium text-gray-900 dark:text-white">
							{$i18n.t('Display Emoji in Call')}
						</div>
						<div class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
							Show emoji reactions during voice calls
						</div>
					</div>
					<button
						class="relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 {showEmojiInCall
							? 'bg-blue-600'
							: 'bg-gray-300 dark:bg-gray-700'}"
						on:click={() => {
							toggleEmojiInCall();
						}}
						type="button"
					>
						<span
							class="inline-block h-4 w-4 transform rounded-full bg-white transition-transform {showEmojiInCall
								? 'translate-x-6'
								: 'translate-x-1'}"
						/>
					</button>
				</div>
			</div>
		</div>

		<!-- File Section -->
		<div class="space-y-4 pt-2">
			<div>
				<h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-1">
					{$i18n.t('File')}
				</h3>
				<p class="text-sm text-gray-500 dark:text-gray-400">
					Configure file handling options
				</p>
			</div>

			<!-- Image Compression -->
			<div class="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-4 space-y-3">
				<div class="flex items-center justify-between">
					<div>
						<div class="text-sm font-medium text-gray-900 dark:text-white">
							{$i18n.t('Image Compression')}
						</div>
						<div class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
							Compress images before uploading
						</div>
					</div>
					<button
						class="relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 {imageCompression
							? 'bg-blue-600'
							: 'bg-gray-300 dark:bg-gray-700'}"
						on:click={() => {
							toggleImageCompression();
						}}
						type="button"
					>
						<span
							class="inline-block h-4 w-4 transform rounded-full bg-white transition-transform {imageCompression
								? 'translate-x-6'
								: 'translate-x-1'}"
						/>
					</button>
				</div>

				{#if imageCompression}
					<div class="pt-2 border-t border-gray-200 dark:border-gray-700">
						<div class="flex items-center justify-between">
							<div class="text-xs text-gray-600 dark:text-gray-400">
								{$i18n.t('Image Max Compression Size')}
							</div>
							<div class="flex items-center gap-2">
								<input
									bind:value={imageCompressionSize.width}
									type="number"
									class="w-20 px-2 py-1 text-sm bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 border border-gray-300 dark:border-gray-700 rounded focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none text-center"
									min="0"
									placeholder="Width"
								/>
								<span class="text-gray-500 dark:text-gray-400">×</span>
								<input
									bind:value={imageCompressionSize.height}
									type="number"
									class="w-20 px-2 py-1 text-sm bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 border border-gray-300 dark:border-gray-700 rounded focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none text-center"
									min="0"
									placeholder="Height"
								/>
							</div>
						</div>
					</div>
				{/if}
			</div>
		</div>
	</div>

	<!-- Save Button -->
	<div class="flex justify-end pt-6 border-t border-gray-200 dark:border-gray-700 mt-6">
		<button
			class="px-6 py-2.5 text-sm font-medium bg-orange-600 hover:bg-orange-700 text-white rounded-lg transition-colors shadow-sm hover:shadow-md focus:outline-none focus:ring-2 focus:ring-orange-500 focus:ring-offset-2"
			type="submit"
		>
			{$i18n.t('Save')}
		</button>
	</div>
</form>

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

	/* Hide number input spinners */
	input[type='number']::-webkit-inner-spin-button,
	input[type='number']::-webkit-outer-spin-button {
		-webkit-appearance: none;
		margin: 0;
	}

	input[type='number'] {
		-moz-appearance: textfield;
	}
</style>