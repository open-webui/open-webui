<script lang="ts">
  import { toast } from 'svelte-sonner';
  import { v4 as uuidv4 } from 'uuid';
  import { createPicker } from '$lib/utils/google-drive-picker';
  import { pickAndDownloadFile } from '$lib/utils/onedrive-file-picker';

  import { onMount, tick, getContext, createEventDispatcher, onDestroy } from 'svelte';
  const dispatch = createEventDispatcher();

  import {
    type Model,
    mobile,
    settings,
    showSidebar,
    models,
    config,
    showCallOverlay,
    tools,
    user as _user,
    showControls,
    TTSWorker
  } from '$lib/stores';

  import { blobToFile, compressImage, createMessagesList, findWordIndices } from '$lib/utils';
  import { transcribeAudio } from '$lib/apis/audio';
  import { uploadFile } from '$lib/apis/files';
  import { generateAutoCompletion } from '$lib/apis';
  import { deleteFileById } from '$lib/apis/files';

  import { WEBUI_BASE_URL, WEBUI_API_BASE_URL, PASTED_TEXT_CHARACTER_LIMIT } from '$lib/constants';

  import InputMenu from './MessageInput/InputMenu.svelte';
  import FilesOverlay from './MessageInput/FilesOverlay.svelte';
  import Commands from './MessageInput/Commands.svelte';
  import RichTextInput from '../common/RichTextInput.svelte';
  import Tooltip from '../common/Tooltip.svelte';
  import FileItem from '../common/FileItem.svelte';
  import Image from '../common/Image.svelte';

  import XMark from '../icons/XMark.svelte';
  import GlobeAlt from '../icons/GlobeAlt.svelte';
  import Photo from '../icons/Photo.svelte';
  import CommandLine from '../icons/CommandLine.svelte';

  const i18n = getContext('i18n');

  export let transparentBackground = false;
  export let onChange: Function = () => {};
  export let createMessagePair: Function = () => {};
  export let stopResponse: Function = () => {};

  export let autoScroll = false;
  export let atSelectedModel: Model | undefined = undefined;
  export let selectedModels: string[] = [''];
  export let history: any;

  export let prompt = '';
  export let files: any[] = [];
  export let selectedToolIds: string[] = [];
  export let imageGenerationEnabled = false;
  export let webSearchEnabled = false;
  export let codeInterpreterEnabled = false;

  $: onChange({ prompt, files, selectedToolIds, imageGenerationEnabled, webSearchEnabled });

  let loaded = false;
  let isComposing = false;
  let chatInputElement: any;
  let filesInputElement: any;
  let commandsElement: any;
  let inputFiles: FileList | null = null;
  let dragged = false;
  export let placeholder = '';

  let selectedModelIds: string[] = [];
  $: selectedModelIds = atSelectedModel !== undefined ? [atSelectedModel.id] : selectedModels;

  let visionCapableModels: string[] = [];
  $: visionCapableModels = [...(atSelectedModel ? [atSelectedModel] : selectedModels)].filter(
    (model) => $models.find((m) => m.id === model.id)?.info?.meta?.capabilities?.vision ?? false
  );

  const scrollToBottom = () => {
    const element = document.getElementById('messages-container');
    if (element) {
      element.scrollTo({ top: element.scrollHeight, behavior: 'smooth' });
    }
  };

  const screenCaptureHandler = async () => {
    try {
      const mediaStream = await navigator.mediaDevices.getDisplayMedia({
        video: { cursor: 'never' },
        audio: false
      });
      const video = document.createElement('video');
      video.srcObject = mediaStream;
      await video.play();
      const canvas = document.createElement('canvas');
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      const context = canvas.getContext('2d');
      if (context) {
        context.drawImage(video, 0, 0, canvas.width, canvas.height);
      }
      mediaStream.getTracks().forEach((track) => track.stop());
      window.focus();
      const imageUrl = canvas.toDataURL('image/png');
      files = [...files, { type: 'image', url: imageUrl }];
      video.srcObject = null;
    } catch (error) {
      console.error('Error capturing screen:', error);
      toast.error($i18n.t('Failed to capture screen. Please check permissions.'));
    }
  };

  const uploadFileHandler = async (file: File, fullContext: boolean = false) => {
    if ($_user?.role !== 'admin' && !($_user?.permissions?.chat?.file_upload ?? true)) {
      toast.error($i18n.t('You do not have permission to upload files.'));
      return;
    }

    const tempItemId = uuidv4();
    const fileItem = {
      type: 'file',
      file: '',
      id: null,
      url: '',
      name: file.name,
      collection_name: '',
      status: 'uploading',
      size: file.size,
      error: '',
      itemId: tempItemId,
      ...(fullContext ? { context: 'full' } : {})
    };

    if (fileItem.size === 0) {
      toast.error($i18n.t('You cannot upload an empty file.'));
      return;
    }

    files = [...files, fileItem];

    try {
      const uploadedFile = await uploadFile(localStorage.token, file);
      if (uploadedFile) {
        fileItem.status = 'uploaded';
        fileItem.file = uploadedFile;
        fileItem.id = uploadedFile.id;
        fileItem.collection_name = uploadedFile?.meta?.collection_name || uploadedFile?.collection_name || '';
        fileItem.url = `${WEBUI_API_BASE_URL}/files/${uploadedFile.id}`;
        files = [...files];
      } else {
        files = files.filter((item) => item?.itemId !== tempItemId);
      }
    } catch (e) {
      console.error('File upload error:', e);
      toast.error($i18n.t('Failed to upload file: {{error}}', { error: e.message }));
      files = files.filter((item) => item?.itemId !== tempItemId);
    }
  };

  const inputFilesHandler = async (inputFiles: File[]) => {
    for (const file of inputFiles) {
      const maxSize = $config?.file?.max_size ?? 0;
      if (maxSize && file.size > maxSize * 1024 * 1024) {
        toast.error($i18n.t(`File size should not exceed {{maxSize}} MB.`, { maxSize }));
        continue;
      }

      if (['image/gif', 'image/webp', 'image/jpeg', 'image/png', 'image/avif'].includes(file.type)) {
        if (visionCapableModels.length === 0) {
          toast.error($i18n.t('Selected model(s) do not support image inputs'));
          continue;
        }
        const reader = new FileReader();
        reader.onload = async (event) => {
          let imageUrl = event.target?.result as string;
          if ($settings?.imageCompression ?? false) {
            const width = $settings?.imageCompressionSize?.width ?? null;
            const height = $settings?.imageCompressionSize?.height ?? null;
            if (width || height) {
              imageUrl = await compressImage(imageUrl, width, height);
            }
          }
          files = [...files, { type: 'image', url: imageUrl }];
        };
        reader.readAsDataURL(file);
      } else {
        await uploadFileHandler(file);
      }
    }
  };

  const handleKeyDown = (event: KeyboardEvent) => {
    if (event.key === 'Escape') {
      dragged = false;
    }
  };

  const onDragOver = (e: DragEvent) => {
    e.preventDefault();
    if (e.dataTransfer?.types?.includes('Files')) {
      dragged = true;
    } else {
      dragged = false;
    }
  };

  const onDragLeave = () => {
    dragged = false;
  };

  const onDrop = (e: DragEvent) => {
    e.preventDefault();
    if (e.dataTransfer?.files) {
      const droppedFiles = Array.from(e.dataTransfer.files);
      if (droppedFiles.length > 0) {
        inputFilesHandler(droppedFiles);
      }
    }
    dragged = false;
  };

  onMount(async () => {
    loaded = true;
    window.setTimeout(() => {
      const chatInput = document.getElementById('chat-input');
      chatInput?.focus();
    }, 0);

    window.addEventListener('keydown', handleKeyDown);
    const dropzoneElement = document.getElementById('chat-container');
    if (dropzoneElement) {
      dropzoneElement.addEventListener('dragover', onDragOver);
      dropzoneElement.addEventListener('drop', onDrop);
      dropzoneElement.addEventListener('dragleave', onDragLeave);
    }
  });

  onDestroy(() => {
    window.removeEventListener('keydown', handleKeyDown);
    const dropzoneElement = document.getElementById('chat-container');
    if (dropzoneElement) {
      dropzoneElement.removeEventListener('dragover', onDragOver);
      dropzoneElement.removeEventListener('drop', onDrop);
      dropzoneElement.removeEventListener('dragleave', onDragLeave);
    }
  });
</script>

<FilesOverlay show={dragged} />

{#if loaded}
  <div class="w-full font-primary">
    <div class="mx-auto inset-x-0 bg-transparent flex justify-center">
      <div class="flex flex-col px-3 {($settings?.widescreenMode ?? null) ? 'max-w-full' : 'max-w-6xl'} w-full">
        <div class="relative">
          {#if autoScroll === false && history?.currentId}
            <div class="absolute -top-12 left-0 right-0 flex justify-center z-30 pointer-events-none">
              <button
                class="bg-white border border-gray-100 dark:border-none dark:bg-white/20 p-1.5 rounded-full pointer-events-auto"
                on:click={() => {
                  autoScroll = true;
                  scrollToBottom();
                }}
              >
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-5 h-5">
                  <path fill-rule="evenodd" d="M10 3a.75.75 0 01.75.75v10.638l3.96-4.158a.75.75 0 111.08 1.04l-5.25 5.5a.75.75 0 01-1.08 0l-5.25-5.5a.75.75 0 111.08-1.04l3.96 4.158V3.75A.75.75 0 0110 3z" clip-rule="evenodd" />
                </svg>
              </button>
            </div>
          {/if}
        </div>

        <div class="w-full relative">
          {#if atSelectedModel !== undefined || selectedToolIds.length > 0 || webSearchEnabled || ($settings?.webSearch ?? false) === 'always' || imageGenerationEnabled || codeInterpreterEnabled}
            <div class="px-3 pb-0.5 pt-1.5 text-left w-full flex flex-col absolute bottom-0 left-0 right-0 bg-linear-to-t from-white dark:from-gray-900 z-10">
              {#if selectedToolIds.length > 0}
                <div class="flex items-center justify-between w-full">
                  <div class="flex items-center gap-2.5 text-sm dark:text-gray-500">
                    <div class="pl-1">
                      <span class="relative flex size-2">
                        <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-yellow-400 opacity-75" />
                        <span class="relative inline-flex rounded-full size-2 bg-yellow-500" />
                      </span>
                    </div>
                    <div class="text-ellipsis line-clamp-1 flex">
                      {#each selectedToolIds.map((id) => $tools?.find((t) => t.id === id) || { id, name: id }) as tool, toolIdx (toolIdx)}
                        <Tooltip content={tool?.meta?.description ?? ''} className="{toolIdx !== 0 ? 'pl-0.5' : ''} shrink-0" placement="top">
                          {tool.name}
                        </Tooltip>
                        {#if toolIdx !== selectedToolIds.length - 1}
                          <span>, </span>
                        {/if}
                      {/each}
                    </div>
                  </div>
                </div>
              {/if}

              {#if webSearchEnabled || ($config?.features?.enable_web_search && ($settings?.webSearch ?? false) === 'always')}
                <div class="flex items-center justify-between w-full">
                  <div class="flex items-center gap-2.5 text-sm dark:text-gray-500">
                    <div class="pl-1">
                      <span class="relative flex size-2">
                        <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75" />
                        <span class="relative inline-flex rounded-full size-2 bg-blue-500" />
                      </span>
                    </div>
                    <div class="translate-y-[0.5px]">{$i18n.t('Search the internet')}</div>
                  </div>
                </div>
              {/if}

              {#if imageGenerationEnabled}
                <div class="flex items-center justify-between w-full">
                  <div class="flex items-center gap-2.5 text-sm dark:text-gray-500">
                    <div class="pl-1">
                      <span class="relative flex size-2">
                        <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-teal-400 opacity-75" />
                        <span class="relative inline-flex rounded-full size-2 bg-teal-500" />
                      </span>
                    </div>
                    <div class="translate-y-[0.5px]">{$i18n.t('Generate an image')}</div>
                  </div>
                </div>
              {/if}

              {#if codeInterpreterEnabled}
                <div class="flex items-center justify-between w-full">
                  <div class="flex items-center gap-2.5 text-sm dark:text-gray-500">
                    <div class="pl-1">
                      <span class="relative flex size-2">
                        <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75" />
                        <span class="relative inline-flex rounded-full size-2 bg-green-500" />
                      </span>
                    </div>
                    <div class="translate-y-[0.5px]">{$i18n.t('Execute code for analysis')}</div>
                  </div>
                </div>
              {/if}

              {#if atSelectedModel !== undefined}
                <div class="flex items-center justify-between w-full">
                  <div class="pl-[1px] flex items-center gap-2 text-sm dark:text-gray-500">
                    <img
                      crossorigin="anonymous"
                      alt="model profile"
                      class="size-3.5 max-w-[28px] object-cover rounded-full"
                      src={$models.find((model) => model.id === atSelectedModel.id)?.info?.meta?.profile_image_url ??
                        ($i18n.language === 'dg-DG' ? `/doge.png` : `${WEBUI_BASE_URL}/static/favicon.png`)}
                    />
                    <div class="translate-y-[0.5px]">
                      Talking to <span class="font-medium">{atSelectedModel.name}</span>
                    </div>
                  </div>
                  <button class="flex items-center dark:text-gray-500" on:click={() => (atSelectedModel = undefined)}>
                    <XMark />
                  </button>
                </div>
              {/if}
            </div>
          {/if}

          <Commands
            bind:this={commandsElement}
            bind:prompt
            bind:files
            on:upload={(e) => dispatch('upload', e.detail)}
            on:select={(e) => {
              const data = e.detail;
              if (data?.type === 'model') {
                atSelectedModel = data.data;
              }
              chatInputElement?.focus();
            }}
          />
        </div>
      </div>
    </div>

    <div class="{transparentBackground ? 'bg-transparent' : 'bg-white dark:bg-gray-900'}">
      <div class="{($settings?.widescreenMode ?? null) ? 'max-w-full' : 'max-w-6xl'} px-2.5 mx-auto inset-x-0">
        <div>
          <input
            bind:this={filesInputElement}
            bind:files={inputFiles}
            type="file"
            hidden
            multiple
            on:change={async () => {
              if (inputFiles && inputFiles.length > 0) {
                await inputFilesHandler(Array.from(inputFiles));
                filesInputElement.value = '';
              } else {
                toast.error($i18n.t('File not found.'));
              }
            }}
          />

          <form
            class="w-full flex gap-1.5"
            on:submit|preventDefault={() => {
              if (prompt !== '' || files.length > 0) {
                dispatch('submit', prompt);
              }
            }}
          >
            <div
              class="flex-1 flex flex-col relative w-full rounded-3xl px-1 bg-gray-600/5 dark:bg-gray-400/5 dark:text-gray-100"
              dir={$settings?.chatDirection ?? 'LTR'}
            >
              {#if files.length > 0}
                <div class="mx-2 mt-2.5 -mb-1 flex items-center flex-wrap gap-2">
                  {#each files as file, fileIdx (file.itemId || file.url)}
                    {#if file.type === 'image'}
                      <div class="relative group">
                        <div class="relative flex items-center">
                          <Image src={file.url} alt="input" imageClassName="size-14 rounded-xl object-cover" />
                          {#if (atSelectedModel ? visionCapableModels.length === 0 : selectedModels.length !== visionCapableModels.length)}
                            <Tooltip
                              className="absolute top-1 left-1"
                              content={$i18n.t('{{ models }}', {
                                models: [...(atSelectedModel ? [atSelectedModel] : selectedModels)]
                                  .filter((model) => !visionCapableModels.includes(model))
                                  .map((m) => m.name || m.id)
                                  .join(', ')
                              })}
                            >
                              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="size-4 fill-yellow-300">
                                <path fill-rule="evenodd" d="M9.401 3.003c1.155-2 4.043-2 5.197 0l7.355 12.748c1.154 2-.29 4.5-2.599 4.5H4.645c-2.309 0-3.752-2.5-2.598-4.5L9.4 3.003ZM12 8.25a.75.75 0 0 1 .75.75v3.75a.75.75 0 0 1-1.5 0V9a.75.75 0 0 1 .75-.75Zm0 8.25a.75.75 0 1 0 0-1.5.75.75 0 0 0 0 1.5Z" clip-rule="evenodd" />
                              </svg>
                            </Tooltip>
                          {/if}
                        </div>
                        <button
                          class="absolute -top-1 -right-1 bg-white text-black border border-white rounded-full group-hover:visible invisible transition"
                          type="button"
                          on:click={() => {
                            files.splice(fileIdx, 1);
                            files = [...files];
                          }}
                        >
                          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="size-4">
                            <path d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z" />
                          </svg>
                        </button>
                      </div>
                    {:else}
                      <FileItem
                        item={file}
                        name={file.name}
                        type={file.type}
                        size={file.size}
                        loading={file.status === 'uploading'}
                        dismissible={true}
                        edit={true}
                        on:dismiss={async () => {
                          if (file.type !== 'collection' && !file?.collection && file.id) {
                            await deleteFileById(localStorage.token, file.id);
                          }
                          files.splice(fileIdx, 1);
                          files = [...files];
                        }}
                        on:click={() => console.log(file)}
                      />
                    {/if}
                  {/each}
                </div>
              {/if}

              <div class="px-2.5">
                {#if $settings?.richTextInput ?? true}
                  <RichTextInput
                    bind:this={chatInputElement}
                    bind:value={prompt}
                    id="chat-input"
                    messageInput={true}
                    shiftEnter={!($settings?.ctrlEnterToSend ?? false) &&
                      (!$mobile || !('ontouchstart' in window || navigator.maxTouchPoints > 0 || navigator.msMaxTouchPoints > 0))}
                    placeholder={placeholder || $i18n.t('Send a Message')}
                    largeTextAsFile={$settings?.largeTextAsFile ?? false}
                    autocomplete={$config?.features?.enable_autocomplete_generation ?? false}
                    generateAutoCompletion={async (text) => {
                      if (selectedModelIds.length === 0 || !selectedModelIds[0]) {
                        toast.error($i18n.t('Please select a model first.'));
                        return null;
                      }
                      try {
                        const res = await generateAutoCompletion(
                          localStorage.token,
                          selectedModelIds[0],
                          text,
                          history?.currentId ? createMessagesList(history, history.currentId) : null
                        );
                        return res;
                      } catch (error) {
                        console.error('Autocomplete error:', error);
                        return null;
                      }
                    }}
                    oncompositionstart={() => (isComposing = true)}
                    oncompositionend={() => (isComposing = false)}
                    on:keydown={(e) => {
                      const event = e.detail.event;
                      const isCtrlPressed = event.ctrlKey || event.metaKey;
                      const commandsContainerElement = document.getElementById('commands-container');

                      if (event.key === 'Escape') {
                        stopResponse();
                        atSelectedModel = undefined;
                        selectedToolIds = [];
                        webSearchEnabled = false;
                        imageGenerationEnabled = false;
                        codeInterpreterEnabled = false;
                      }

                      if (isCtrlPressed && event.key === 'Enter' && event.shiftKey) {
                        event.preventDefault();
                        createMessagePair(prompt);
                      }

                      if (prompt === '' && isCtrlPressed && event.key.toLowerCase() === 'r') {
                        event.preventDefault();
                        const regenerateButton = document.getElementsByClassName('regenerate-response-button')[0];
                        regenerateButton?.click();
                      }

                      if (prompt === '' && event.key === 'ArrowUp') {
                        event.preventDefault();
                        const userMessageElement = document.getElementsByClassName('user-message')[0];
                        if (userMessageElement) {
                          userMessageElement.scrollIntoView({ block: 'center' });
                          const editButton = document.getElementsByClassName('edit-user-message-button')[0];
                          editButton?.click();
                        }
                      }

                      if (commandsContainerElement) {
                        if (event.key === 'ArrowUp') {
                          event.preventDefault();
                          commandsElement?.selectUp();
                          const commandOptionButton = document.getElementsByClassName('selected-command-option-button')[0];
                          commandOptionButton?.scrollIntoView({ block: 'center' });
                        } else if (event.key === 'ArrowDown') {
                          event.preventDefault();
                          commandsElement?.selectDown();
                          const commandOptionButton = document.getElementsByClassName('selected-command-option-button')[0];
                          commandOptionButton?.scrollIntoView({ block: 'center' });
                        } else if (event.key === 'Tab') {
                          event.preventDefault();
                          const commandOptionButton = document.getElementsByClassName('selected-command-option-button')[0];
                          commandOptionButton?.click();
                        } else if (event.key === 'Enter') {
                          event.preventDefault();
                          const commandOptionButton = document.getElementsByClassName('selected-command-option-button')[0];
                          if (commandOptionButton) {
                            commandOptionButton.click();
                          } else {
                            document.getElementById('send-message-button')?.click();
                          }
                        }
                      } else if (!isComposing) {
                        const enterPressed = ($settings?.ctrlEnterToSend ?? false)
                          ? (event.key === 'Enter' || event.keyCode === 13) && isCtrlPressed
                          : (event.key === 'Enter' || event.keyCode === 13) && !event.shiftKey;
                        if (enterPressed) {
                          event.preventDefault();
                          if (prompt !== '' || files.length > 0) {
                            dispatch('submit', prompt);
                          }
                        }
                      }
                    }}
                    on:paste={async (e) => {
                      const clipboardData = e.detail.event.clipboardData || window.clipboardData;
                      if (clipboardData?.items) {
                        for (const item of clipboardData.items) {
                          if (item.type.indexOf('image') !== -1) {
                            const blob = item.getAsFile();
                            const reader = new FileReader();
                            reader.onload = (event) => {
                              files = [...files, { type: 'image', url: event.target?.result }];
                            };
                            reader.readAsDataURL(blob);
                          } else if (item.type === 'text/plain' && ($settings?.largeTextAsFile ?? false)) {
                            const text = clipboardData.getData('text/plain');
                            if (text.length > PASTED_TEXT_CHARACTER_LIMIT) {
                              e.detail.event.preventDefault();
                              const blob = new Blob([text], { type: 'text/plain' });
                              const file = new File([blob], `Pasted_Text_${Date.now()}.txt`, { type: 'text/plain' });
                              await uploadFileHandler(file, true);
                            }
                          }
                        }
                      }
                    }}
                  />
                {:else}
                  <textarea
                    id="chat-input"
                    bind:this={chatInputElement}
                    class="scrollbar-hidden bg-transparent dark:text-gray-100 outline-hidden w-full pt-3 px-1 resize-none"
                    placeholder={placeholder || $i18n.t('Send a Message')}
                    bind:value={prompt}
                    on:compositionstart={() => (isComposing = true)}
                    on:compositionend={() => (isComposing = false)}
                    on:keydown={(e) => {
                      const isCtrlPressed = e.ctrlKey || e.metaKey;
                      const commandsContainerElement = document.getElementById('commands-container');

                      if (e.key === 'Escape') {
                        stopResponse();
                        atSelectedModel = undefined;
                        selectedToolIds = [];
                        webSearchEnabled = false;
                        imageGenerationEnabled = false;
                        codeInterpreterEnabled = false;
                      }

                      if (isCtrlPressed && e.key === 'Enter' && e.shiftKey) {
                        e.preventDefault();
                        createMessagePair(prompt);
                      }

                      if (prompt === '' && isCtrlPressed && e.key.toLowerCase() === 'r') {
                        e.preventDefault();
                        const regenerateButton = document.getElementsByClassName('regenerate-response-button')[0];
                        regenerateButton?.click();
                      }

                      if (prompt === '' && e.key === 'ArrowUp') {
                        e.preventDefault();
                        const userMessageElement = document.getElementsByClassName('user-message')[0];
                        if (userMessageElement) {
                          userMessageElement.scrollIntoView({ block: 'center' });
                          const editButton = document.getElementsByClassName('edit-user-message-button')[0];
                          editButton?.click();
                        }
                      }

                      if (commandsContainerElement) {
                        if (e.key === 'ArrowUp') {
                          e.preventDefault();
                          commandsElement?.selectUp();
                          const commandOptionButton = document.getElementsByClassName('selected-command-option-button')[0];
                          commandOptionButton?.scrollIntoView({ block: 'center' });
                        } else if (e.key === 'ArrowDown') {
                          e.preventDefault();
                          commandsElement?.selectDown();
                          const commandOptionButton = document.getElementsByClassName('selected-command-option-button')[0];
                          commandOptionButton?.scrollIntoView({ block: 'center' });
                        } else if (e.key === 'Enter') {
                          e.preventDefault();
                          const commandOptionButton = document.getElementsByClassName('selected-command-option-button')[0];
                          if (e.shiftKey) {
                            prompt += '\n';
                          } else if (commandOptionButton) {
                            commandOptionButton.click();
                          } else {
                            document.getElementById('send-message-button')?.click();
                          }
                        }
                      } else if (!isComposing) {
                        const enterPressed = ($settings?.ctrlEnterToSend ?? false)
                          ? (e.key === 'Enter' || e.keyCode === 13) && isCtrlPressed
                          : (e.key === 'Enter' || e.keyCode === 13) && !e.shiftKey;
                        if (enterPressed) {
                          e.preventDefault();
                          if (prompt !== '' || files.length > 0) {
                            dispatch('submit', prompt);
                          }
                        }
                      }

                      if (e.key === 'Tab') {
                        const words = findWordIndices(prompt);
                        if (words.length > 0) {
                          const word = words[0];
                          const fullPrompt = prompt;
                          prompt = prompt.substring(0, word.endIndex + 1);
                          e.target.scrollTop = e.target.scrollHeight;
                          prompt = fullPrompt;
                          e.preventDefault();
                          e.target.setSelectionRange(word.startIndex, word.endIndex + 1);
                        }
                        e.target.style.height = Math.min(e.target.scrollHeight, 320) + 'px';
                      }
                    }}
                    rows="1"
                    on:input={(e) => {
                      e.target.style.height = Math.min(e.target.scrollHeight, 320) + 'px';
                    }}
                    on:focus={(e) => {
                      e.target.style.height = Math.min(e.target.scrollHeight, 320) + 'px';
                    }}
                    on:paste={async (e) => {
                      const clipboardData = e.clipboardData || window.clipboardData;
                      if (clipboardData?.items) {
                        for (const item of clipboardData.items) {
                          if (item.type.indexOf('image') !== -1) {
                            const blob = item.getAsFile();
                            const reader = new FileReader();
                            reader.onload = (event) => {
                              files = [...files, { type: 'image', url: event.target?.result }];
                            };
                            reader.readAsDataURL(blob);
                          } else if (item.type === 'text/plain' && ($settings?.largeTextAsFile ?? false)) {
                            const text = clipboardData.getData('text/plain');
                            if (text.length > PASTED_TEXT_CHARACTER_LIMIT) {
                              e.preventDefault();
                              const blob = new Blob([text], { type: 'text/plain' });
                              const file = new File([blob], `Pasted_Text_${Date.now()}.txt`, { type: 'text/plain' });
                              await uploadFileHandler(file, true);
                            }
                          }
                        }
                      }
                    }}
                  />
                {/if}
              </div>

              <div class="flex justify-between mt-1.5 mb-2.5 mx-0.5 max-w-full">
                <div class="ml-1 self-end gap-0.5 flex items-center flex-1 max-w-[80%]">
                  <InputMenu
                    bind:selectedToolIds
                    {screenCaptureHandler}
                    {inputFilesHandler}
                    uploadFilesHandler={() => filesInputElement.click()}
                    uploadGoogleDriveHandler={async () => {
                      try {
                        const fileData = await createPicker();
                        if (fileData) {
                          const file = new File([fileData.blob], fileData.name, { type: fileData.blob.type });
                          await uploadFileHandler(file);
                        }
                      } catch (error) {
                        console.error('Google Drive Error:', error);
                        toast.error($i18n.t('Error accessing Google Drive: {{error}}', { error: error.message }));
                      }
                    }}
                    uploadOneDriveHandler={async () => {
                      try {
                        const fileData = await pickAndDownloadFile();
                        if (fileData) {
                          const file = new File([fileData.blob], fileData.name, { type: fileData.blob.type || 'application/octet-stream' });
                          await uploadFileHandler(file);
                        }
                      } catch (error) {
                        console.error('OneDrive Error:', error);
                        toast.error($i18n.t('Error accessing OneDrive: {{error}}', { error: error.message }));
                      }
                    }}
                    onClose={async () => {
                      await tick();
                      chatInputElement?.focus();
                    }}
                  >
                    <button
                      class="bg-transparent hover:bg-gray-100 text-gray-800 dark:text-white dark:hover:bg-gray-800 transition rounded-full p-1.5 outline-hidden focus:outline-hidden"
                      type="button"
                      aria-label="More"
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="size-5">
                        <path d="M10.75 4.75a.75.75 0 0 0-1.5 0v4.5h-4.5a.75.75 0 0 0 0 1.5h4.5v4.5a.75.75 0 0 0 1.5 0v-4.5h4.5a.75.75 0 0 0 0-1.5h-4.5v-4.5Z" />
                      </svg>
                    </button>
                  </InputMenu>

                  <div class="flex gap-0.5 items-center overflow-x-auto scrollbar-none flex-1">
                    {#if $_user}
                      {#if $config?.features?.enable_web_search && ($_user.role === 'admin' || $_user?.permissions?.features?.web_search)}
                        <Tooltip content={$i18n.t('Search the internet')} placement="top">
                          <button
                            on:click|preventDefault={() => (webSearchEnabled = !webSearchEnabled)}
                            type="button"
                            class="px-1.5 @sm:px-2.5 py-1.5 flex gap-1.5 items-center text-sm rounded-full font-medium transition-colors duration-300 focus:outline-hidden max-w-full overflow-hidden {webSearchEnabled || ($settings?.webSearch ?? false) === 'always' ? 'bg-blue-100 dark:bg-blue-500/20 text-blue-500 dark:text-blue-400' : 'bg-transparent text-gray-600 dark:text-gray-300 border-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800'}"
                          >
                            <GlobeAlt className="size-5" strokeWidth="1.75" />
                            <span class="hidden @sm:block whitespace-nowrap overflow-hidden text-ellipsis translate-y-[0.5px] mr-0.5">{$i18n.t('Web Search')}</span>
                          </button>
                        </Tooltip>
                      {/if}

                      {#if $config?.features?.enable_image_generation && ($_user.role === 'admin' || $_user?.permissions?.features?.image_generation)}
                        <Tooltip content={$i18n.t('Generate an image')} placement="top">
                          <button
                            on:click|preventDefault={() => (imageGenerationEnabled = !imageGenerationEnabled)}
                            type="button"
                            class="px-1.5 @sm:px-2.5 py-1.5 flex gap-1.5 items-center text-sm rounded-full font-medium transition-colors duration-300 focus:outline-hidden max-w-full overflow-hidden {imageGenerationEnabled ? 'bg-gray-100 dark:bg-gray-500/20 text-gray-600 dark:text-gray-400' : 'bg-transparent text-gray-600 dark:text-gray-300 border-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800'}"
                          >
                            <Photo className="size-5" strokeWidth="1.75" />
                            <span class="hidden @sm:block whitespace-nowrap overflow-hidden text-ellipsis translate-y-[0.5px] mr-0.5">{$i18n.t('Image')}</span>
                          </button>
                        </Tooltip>
                      {/if}

                      {#if $config?.features?.enable_code_interpreter && ($_user.role === 'admin' || $_user?.permissions?.features?.code_interpreter)}
                        <Tooltip content={$i18n.t('Execute code for analysis')} placement="top">
                          <button
                            on:click|preventDefault={() => (codeInterpreterEnabled = !codeInterpreterEnabled)}
                            type="button"
                            class="px-1.5 @sm:px-2.5 py-1.5 flex gap-1.5 items-center text-sm rounded-full font-medium transition-colors duration-300 focus:outline-hidden max-w-full overflow-hidden {codeInterpreterEnabled ? 'bg-gray-100 dark:bg-gray-500/20 text-gray-600 dark:text-gray-400' : 'bg-transparent text-gray-600 dark:text-gray-300 border-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800'}"
                          >
                            <CommandLine className="size-5" strokeWidth="1.75" />
                            <span class="hidden @sm:block whitespace-nowrap overflow-hidden text-ellipsis translate-y-[0.5px] mr-0.5">{$i18n.t('Code Interpreter')}</span>
                          </button>
                        </Tooltip>
                      {/if}
                    {/if}
                  </div>
                </div>

                <div class="self-end flex space-x-1 mr-1 shrink-0">
                  {#if !history?.currentId || history.messages[history.currentId]?.done}
                    {#if prompt === '' && files.length === 0}
                      <div class="flex items-center"></div>
                    {:else}
                      <Tooltip content={$i18n.t('Send message')}>
                        <button
                          id="send-message-button"
                          class="{webSearchEnabled || ($settings?.webSearch ?? false) === 'always' ? 'bg-blue-500 text-white hover:bg-blue-400' : 'bg-black text-white hover:bg-gray-900 dark:bg-white dark:text-black dark:hover:bg-gray-100'} transition rounded-full p-1.5 self-center"
                          type="submit"
                          disabled={prompt === '' && files.length === 0}
                        >
                          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" class="size-5">
                            <path fill-rule="evenodd" d="M8 14a.75.75 0 0 1-.75-.75V4.56L4.03 7.78a.75.75 0 0 1-1.06-1.06l4.5-4.5a.75.75 0 0 1 1.06 0l4.5 4.5a.75.75 0 0 1-1.06 1.06L8.75 4.56v8.69A.75.75 0 0 1 8 14Z" clip-rule="evenodd" />
                          </svg>
                        </button>
                      </Tooltip>
                    {/if}
                  {/if}
                </div>
              </div>
            </div>
          </form>
        </div>
      </div>
    </div>
  </div>
{/if}
