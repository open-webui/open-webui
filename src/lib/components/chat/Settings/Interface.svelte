<script lang="ts">
  import { preventDefault } from 'svelte/legacy';

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

  interface Props {
    saveSettings: Function;
  }

  let { saveSettings }: Props = $props();

  let backgroundImageUrl = $state(null);
  let inputFiles = $state(null);
  let filesInputElement = $state();

  // Addons
  let titleAutoGenerate = $state(true);
  let autoTags = $state(true);

  let responseAutoCopy = $state(false);
  let widescreenMode = $state(false);
  let splitLargeChunks = false;
  let scrollOnBranchChange = $state(true);
  let userLocation = $state(false);

  // Interface
  let defaultModelId = '';
  let showUsername = $state(false);
  let richTextInput = $state(true);
  let largeTextAsFile = $state(false);
  let notificationSound = $state(true);

  let landingPageMode = $state('');
  let chatBubble = $state(true);
  let chatDirection: 'LTR' | 'RTL' = $state('LTR');

  let imageCompression = $state(false);
  let imageCompressionSize = $state({
    width: '',
    height: ''
  });

  // Admin - Show Update Available Toast
  let showUpdateToast = $state(true);
  let showChangelog = $state(true);

  let showEmojiInCall = $state(false);
  let voiceInterruption = $state(false);
  let hapticFeedback = $state(false);

  let webSearch = $state(null);

  const toggleSplitLargeChunks = async () => {
    splitLargeChunks = !splitLargeChunks;
    saveSettings({ splitLargeChunks: splitLargeChunks });
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

  const toggleChangeChatDirection = async () => {
    chatDirection = chatDirection === 'LTR' ? 'RTL' : 'LTR';
    saveSettings({ chatDirection });
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
    autoTags = $settings.autoTags ?? true;

    responseAutoCopy = $settings.responseAutoCopy ?? false;

    showUsername = $settings.showUsername ?? false;
    showUpdateToast = $settings.showUpdateToast ?? true;
    showChangelog = $settings.showChangelog ?? true;

    showEmojiInCall = $settings.showEmojiInCall ?? false;
    voiceInterruption = $settings.voiceInterruption ?? false;

    richTextInput = $settings.richTextInput ?? true;
    largeTextAsFile = $settings.largeTextAsFile ?? false;

    landingPageMode = $settings.landingPageMode ?? '';
    chatBubble = $settings.chatBubble ?? true;
    widescreenMode = $settings.widescreenMode ?? false;
    splitLargeChunks = $settings.splitLargeChunks ?? false;
    scrollOnBranchChange = $settings.scrollOnBranchChange ?? true;
    chatDirection = $settings.chatDirection ?? 'LTR';
    userLocation = $settings.userLocation ?? false;

    notificationSound = $settings.notificationSound ?? true;

    hapticFeedback = $settings.hapticFeedback ?? false;

    imageCompression = $settings.imageCompression ?? false;
    imageCompressionSize = $settings.imageCompressionSize ?? { width: '', height: '' };

    defaultModelId = $settings?.models?.at(0) ?? '';
    if ($config?.default_models) {
      defaultModelId = $config.default_models.split(',')[0];
    }

    backgroundImageUrl = $settings.backgroundImageUrl ?? null;
    webSearch = $settings.webSearch ?? null;
  });
</script>

<form
  class="flex flex-col h-full justify-between space-y-3 text-sm"
  onsubmit={preventDefault(() => {
    updateInterfaceHandler();
    dispatch('save');
  })}
>
  <input
    bind:this={filesInputElement}
    accept="image/*"
    hidden
    type="file"
    bind:files={inputFiles}
    onchange={() => {
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
      <div class=" mb-1.5 text-sm font-medium">{$i18n.t('UI')}</div>

      <div>
        <div class=" py-0.5 flex w-full justify-between">
          <div class=" self-center text-xs">{$i18n.t('Landing Page Mode')}</div>

          <button
            class="p-1 px-3 text-xs flex rounded-sm transition"
            type="button"
            onclick={() => {
              toggleLandingPageMode();
            }}
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
          <div class=" self-center text-xs">{$i18n.t('Chat Bubble UI')}</div>

          <button
            class="p-1 px-3 text-xs flex rounded-sm transition"
            type="button"
            onclick={() => {
              toggleChatBubble();
            }}
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
              class="p-1 px-3 text-xs flex rounded-sm transition"
              type="button"
              onclick={() => {
                toggleShowUsername();
              }}
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
            class="p-1 px-3 text-xs flex rounded-sm transition"
            type="button"
            onclick={() => {
              toggleWidescreenMode();
            }}
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
            class="p-1 px-3 text-xs flex rounded-sm transition"
            type="button"
            onclick={toggleChangeChatDirection}
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
            {$i18n.t('Notification Sound')}
          </div>

          <button
            class="p-1 px-3 text-xs flex rounded-sm transition"
            type="button"
            onclick={() => {
              toggleNotificationSound();
            }}
          >
            {#if notificationSound === true}
              <span class="ml-2 self-center">{$i18n.t('On')}</span>
            {:else}
              <span class="ml-2 self-center">{$i18n.t('Off')}</span>
            {/if}
          </button>
        </div>
      </div>

      {#if $user.role === 'admin'}
        <div>
          <div class=" py-0.5 flex w-full justify-between">
            <div class=" self-center text-xs">
              {$i18n.t('Toast notifications for new updates')}
            </div>

            <button
              class="p-1 px-3 text-xs flex rounded-sm transition"
              type="button"
              onclick={() => {
                toggleShowUpdateToast();
              }}
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
            <div class=" self-center text-xs">
              {$i18n.t(`Show "What's New" modal on login`)}
            </div>

            <button
              class="p-1 px-3 text-xs flex rounded-sm transition"
              type="button"
              onclick={() => {
                toggleShowChangelog();
              }}
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
          <div class=" self-center text-xs">{$i18n.t('Title Auto-Generation')}</div>

          <button
            class="p-1 px-3 text-xs flex rounded-sm transition"
            type="button"
            onclick={() => {
              toggleTitleAutoGenerate();
            }}
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
          <div class=" self-center text-xs">{$i18n.t('Chat Tags Auto-Generation')}</div>

          <button
            class="p-1 px-3 text-xs flex rounded-sm transition"
            type="button"
            onclick={() => {
              toggleAutoTags();
            }}
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
          <div class=" self-center text-xs">
            {$i18n.t('Auto-Copy Response to Clipboard')}
          </div>

          <button
            class="p-1 px-3 text-xs flex rounded-sm transition"
            type="button"
            onclick={() => {
              toggleResponseAutoCopy();
            }}
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
          <div class=" self-center text-xs">
            {$i18n.t('Rich Text Input for Chat')}
          </div>

          <button
            class="p-1 px-3 text-xs flex rounded-sm transition"
            type="button"
            onclick={() => {
              toggleRichTextInput();
            }}
          >
            {#if richTextInput === true}
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
            {$i18n.t('Paste Large Text as File')}
          </div>

          <button
            class="p-1 px-3 text-xs flex rounded-sm transition"
            type="button"
            onclick={() => {
              toggleLargeTextAsFile();
            }}
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
          <div class=" self-center text-xs">
            {$i18n.t('Chat Background Image')}
          </div>

          <button
            class="p-1 px-3 text-xs flex rounded-sm transition"
            type="button"
            onclick={() => {
              if (backgroundImageUrl !== null) {
                backgroundImageUrl = null;
                saveSettings({ backgroundImageUrl });
              } else {
                filesInputElement.click();
              }
            }}
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
          <div class=" self-center text-xs">{$i18n.t('Allow User Location')}</div>

          <button
            class="p-1 px-3 text-xs flex rounded-sm transition"
            type="button"
            onclick={() => {
              toggleUserLocation();
            }}
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
            class="p-1 px-3 text-xs flex rounded-sm transition"
            type="button"
            onclick={() => {
              toggleHapticFeedback();
            }}
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
					<div class=" self-center text-xs">
						{$i18n.t('Fluidly stream large external response chunks')}
					</div>

					<button
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
          <div class=" self-center text-xs">
            {$i18n.t('Scroll to bottom when switching between branches')}
          </div>

          <button
            class="p-1 px-3 text-xs flex rounded-sm transition"
            type="button"
            onclick={() => {
              togglesScrollOnBranchChange();
            }}
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
          <div class=" self-center text-xs">{$i18n.t('Web Search in Chat')}</div>

          <button
            class="p-1 px-3 text-xs flex rounded-sm transition"
            type="button"
            onclick={() => {
              toggleWebSearch();
            }}
          >
            {#if webSearch === 'always'}
              <span class="ml-2 self-center">{$i18n.t('Always')}</span>
            {:else}
              <span class="ml-2 self-center">{$i18n.t('Default')}</span>
            {/if}
          </button>
        </div>
      </div>

      <div class=" my-1.5 text-sm font-medium">{$i18n.t('Voice')}</div>

      <div>
        <div class=" py-0.5 flex w-full justify-between">
          <div class=" self-center text-xs">{$i18n.t('Allow Voice Interruption in Call')}</div>

          <button
            class="p-1 px-3 text-xs flex rounded-sm transition"
            type="button"
            onclick={() => {
              toggleVoiceInterruption();
            }}
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
            class="p-1 px-3 text-xs flex rounded-sm transition"
            type="button"
            onclick={() => {
              toggleEmojiInCall();
            }}
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
          <div class=" self-center text-xs">{$i18n.t('Image Compression')}</div>

          <button
            class="p-1 px-3 text-xs flex rounded-sm transition"
            type="button"
            onclick={() => {
              toggleImageCompression();
            }}
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
            <div class=" self-center text-xs">{$i18n.t('Image Max Compression Size')}</div>

            <div>
              <input
                class="w-20 bg-transparent outline-hidden text-center"
                min="0"
                placeholder="Width"
                type="number"
                bind:value={imageCompressionSize.width}
              />x
              <input
                class="w-20 bg-transparent outline-hidden text-center"
                min="0"
                placeholder="Height"
                type="number"
                bind:value={imageCompressionSize.height}
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
