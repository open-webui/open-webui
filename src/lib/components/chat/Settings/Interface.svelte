<script lang="ts">
	import { getBackendConfig } from '$lib/apis';
	import { setDefaultPromptSuggestions } from '$lib/apis/configs';
	import { config, models, settings, user } from '$lib/stores';
	import { createEventDispatcher, onMount, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import { updateUserInfo } from '$lib/apis/users';
	import { getUserPosition } from '$lib/utils';
	import { uploadBackgroundImage } from '$lib/apis/files';

	const dispatch = createEventDispatcher();

	const i18n = getContext('i18n');

	export let saveSettings: Function;

	let backgroundImageUrl = '';
	let random_image_url = '';
	let inputFiles = null;
	let filesInputElement;

	// Addons
	let titleAutoGenerate = true;
	let responseAutoCopy = false;
	let widescreenMode = false;
	let splitLargeChunks = false;
	let scrollOnBranchChange = true;
	let userLocation = false;
	let enableFileUpdateBase64 = false;

	// Interface
	let defaultModelId = '';
	let showUsername = false;

	let chatBubble = true;
	let chatDirection: 'LTR' | 'RTL' = 'LTR';

	let showEmojiInCall = false;
	let voiceInterruption = false;
	let hapticFeedback = false;

	let streamResponse = true;

	const toggleSplitLargeChunks = async () => {
		splitLargeChunks = !splitLargeChunks;
		saveSettings({ splitLargeChunks: splitLargeChunks });
	};

	const toggleStreamResponse = async () => {
		streamResponse = !streamResponse;
		saveSettings({ streamResponse: streamResponse });
	};

	const togglesScrollOnBranchChange = async () => {
		scrollOnBranchChange = !scrollOnBranchChange;
		saveSettings({ scrollOnBranchChange: scrollOnBranchChange });
	};

	const togglewidescreenMode = async () => {
		widescreenMode = !widescreenMode;
		saveSettings({ widescreenMode: widescreenMode });
	};

	const toggleChatBubble = async () => {
		chatBubble = !chatBubble;
		saveSettings({ chatBubble: chatBubble });
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

	const toggleEnableFileUpdateBase64 = async () => {
		enableFileUpdateBase64 = !enableFileUpdateBase64;
		saveSettings({ enableFileUpdateBase64: enableFileUpdateBase64 });
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

	const toggleChangeChatDirection = async () => {
		chatDirection = chatDirection === 'LTR' ? 'RTL' : 'LTR';
		saveSettings({ chatDirection });
	};

	const updateInterfaceHandler = async () => {
		saveSettings({
			models: [defaultModelId]
		});
	};

	onMount(async () => {
		titleAutoGenerate = $settings?.title?.auto ?? true;

		responseAutoCopy = $settings.responseAutoCopy ?? false;
		showUsername = $settings.showUsername ?? false;

		showEmojiInCall = $settings.showEmojiInCall ?? false;
		voiceInterruption = $settings.voiceInterruption ?? false;

		chatBubble = $settings.chatBubble ?? true;
		widescreenMode = $settings.widescreenMode ?? false;
		splitLargeChunks = $settings.splitLargeChunks ?? false;
		scrollOnBranchChange = $settings.scrollOnBranchChange ?? true;
		chatDirection = $settings.chatDirection ?? 'LTR';
		userLocation = $settings.userLocation ?? false;
		enableFileUpdateBase64 = $settings.enableFileUpdateBase64 ?? false;

		hapticFeedback = $settings.hapticFeedback ?? false;
		streamResponse = $settings?.streamResponse ?? true;

		defaultModelId = $settings?.models?.at(0) ?? '';
		if ($config?.default_models) {
			defaultModelId = $config.default_models.split(',')[0];
		}

		backgroundImageUrl = $settings.backgroundImageUrl ?? null;
		random_image_url = $config?.random_image_url ?? '';
	});
</script>

<form
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
		on:change={async () => {
			if (!inputFiles || inputFiles.length === 0) {
				toast.error($i18n.t(`File not found.`));
				return;
			}

			const file = inputFiles[0];
			const validImageTypes = ['image/gif', 'image/webp', 'image/jpeg', 'image/png'];

			if (!validImageTypes.includes(file.type)) {
				toast.error(`文件只支持以下格式：${validImageTypes.join(', ')}`);
				inputFiles = null;
				return;
			}

			const reader = new FileReader();
			reader.onload = async (event) => {
				try {
					const res = await uploadBackgroundImage(localStorage.token, file);
					backgroundImageUrl = res?.filename
						? `/api/v1/files/background/images/${res.filename}`
						: event.target.result;
					saveSettings({ backgroundImageUrl });
				} catch (error) {
					console.error('Error uploading image:', error);
					backgroundImageUrl = event.target.result;
					saveSettings({ backgroundImageUrl });
				}
			};

			reader.readAsDataURL(file);
		}}
	/>

	<div class=" space-y-3 pr-1.5 overflow-y-scroll max-h-[25rem] scrollbar-hidden">
		<div class=" space-y-1 mb-3">
			<div class="mb-2">
				<div class="flex justify-between items-center text-xs">
					<div class=" text-sm font-medium">{$i18n.t('Default Model')}</div>
				</div>
			</div>

			<div class="flex-1 mr-2">
				<select
					class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none"
					bind:value={defaultModelId}
					placeholder="Select a model"
				>
					<option value="" disabled selected>{$i18n.t('Select a model')}</option>
					{#each $models.filter((model) => model.id) as model}
						<option value={model.id} class="bg-gray-100 dark:bg-gray-700">{model.name}</option>
					{/each}
				</select>
			</div>
		</div>
		<hr class=" dark:border-gray-850" />

		<div>
			<div class=" mb-1.5 text-sm font-medium">{$i18n.t('UI')}</div>

			<div>
				<div class=" py-0.5 flex w-full justify-between">
					<div class=" self-center text-xs">{$i18n.t('Chat Bubble UI')}</div>

					<button
						class="p-1 px-3 text-xs flex rounded transition"
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
						<div class=" self-center text-xs">
							{$i18n.t('Display the username instead of You in the Chat')}
						</div>

						<button
							class="p-1 px-3 text-xs flex rounded transition"
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
					<div class=" self-center text-xs">{$i18n.t('Widescreen Mode')}</div>

					<button
						class="p-1 px-3 text-xs flex rounded transition"
						on:click={() => {
							togglewidescreenMode();
						}}
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
					<div class=" self-center text-xs">{$i18n.t('Chat direction')}</div>

					<button
						class="p-1 px-3 text-xs flex rounded transition"
						on:click={toggleChangeChatDirection}
						type="button"
					>
						{#if chatDirection === 'LTR'}
							<span class="ml-2 self-center">{$i18n.t('LTR')}</span>
						{:else}
							<span class="ml-2 self-center">{$i18n.t('RTL')}</span>
						{/if}
					</button>
				</div>
			</div>

			<div>
				<div class=" py-0.5 flex w-full justify-between">
					<div class=" self-center text-xs">
						{$i18n.t('Stream Chat Response')}
					</div>

					<button
						class="p-1 px-3 text-xs flex rounded transition"
						on:click={() => {
							toggleStreamResponse();
						}}
						type="button"
					>
						{#if streamResponse === true}
							<span class="ml-2 self-center">{$i18n.t('On')}</span>
						{:else}
							<span class="ml-2 self-center">{$i18n.t('Off')}</span>
						{/if}
					</button>
				</div>
			</div>

			<div>
				<div class=" py-0.5 flex w-full justify-between">
					<div class=" self-center text-xs">
						{$i18n.t('Fluidly stream large external response chunks')}
					</div>

					<button
						class="p-1 px-3 text-xs flex rounded transition"
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
			</div>

			<div>
				<div class=" py-0.5 flex w-full justify-between">
					<div class=" self-center text-xs">
						{$i18n.t('Random Chat Background Image')}
					</div>

					<button
						class="p-1 px-3 text-xs flex rounded transition"
						on:click={() => {
							if (backgroundImageUrl !== null) {
								backgroundImageUrl = null;
							} else {
								backgroundImageUrl = random_image_url;
								toast.success(
									$i18n.t(
										'Random background image has been enabled, you will get a new background image every time you refresh the page~'
									)
								);
							}
							saveSettings({ backgroundImageUrl });
						}}
						type="button"
					>
						{#if backgroundImageUrl !== null}
							<span class="ml-2 self-center">{$i18n.t('On')}</span>
						{:else}
							<span class="ml-2 self-center">{$i18n.t('Off')}</span>
						{/if}
					</button>
				</div>
			</div>

			<div>
				<div class=" py-0.5 flex w-full justify-between">
					<div class=" self-center text-xs">
						{$i18n.t('Chat Background Image')}
					</div>

					<button
						class="p-1 px-3 text-xs flex rounded transition"
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
					<div class=" self-center text-xs">
						{$i18n.t('Scroll to bottom when switching between branches')}
					</div>

					<button
						class="p-1 px-3 text-xs flex rounded transition"
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

			<div class=" my-1.5 text-sm font-medium">{$i18n.t('Chat')}</div>

			<div>
				<div class=" py-0.5 flex w-full justify-between">
					<div class=" self-center text-xs">{$i18n.t('Enable File-Update Base64')}</div>

					<button
						class="p-1 px-3 text-xs flex rounded transition"
						on:click={() => {
							toggleEnableFileUpdateBase64();
						}}
						type="button"
					>
						{#if enableFileUpdateBase64 === true}
							<span class="ml-2 self-center">{$i18n.t('On')}</span>
						{:else}
							<span class="ml-2 self-center">{$i18n.t('Off')}</span>
						{/if}
					</button>
				</div>
			</div>

			<div>
				<div class=" py-0.5 flex w-full justify-between">
					<div class=" self-center text-xs">{$i18n.t('Title Auto-Generation')}</div>

					<button
						class="p-1 px-3 text-xs flex rounded transition"
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
					<div class=" self-center text-xs">
						{$i18n.t('Response AutoCopy to Clipboard')}
					</div>

					<button
						class="p-1 px-3 text-xs flex rounded transition"
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
					<div class=" self-center text-xs">{$i18n.t('Allow User Location')}</div>

					<button
						class="p-1 px-3 text-xs flex rounded transition"
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
					<div class=" self-center text-xs">{$i18n.t('Haptic Feedback')}</div>

					<button
						class="p-1 px-3 text-xs flex rounded transition"
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

			<div class=" my-1.5 text-sm font-medium">{$i18n.t('Voice')}</div>

			<div>
				<div class=" py-0.5 flex w-full justify-between">
					<div class=" self-center text-xs">{$i18n.t('Allow Voice Interruption in Call')}</div>

					<button
						class="p-1 px-3 text-xs flex rounded transition"
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
					<div class=" self-center text-xs">{$i18n.t('Display Emoji in Call')}</div>

					<button
						class="p-1 px-3 text-xs flex rounded transition"
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
		</div>
	</div>

	<div class="flex justify-end text-sm font-medium">
		<button
			class=" px-4 py-2 bg-emerald-700 hover:bg-emerald-800 text-gray-100 transition rounded-lg"
			type="submit"
		>
			{$i18n.t('Save')}
		</button>
	</div>
</form>
