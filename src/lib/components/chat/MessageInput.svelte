<script lang="ts">
    import { toast } from 'svelte-sonner';
    import { v4 as uuidv4 } from 'uuid';
    import { createPicker, getAuthToken } from '$lib/utils/google-drive-picker';
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

    import {
        blobToFile,
        compressImage,
        createMessagesList,
        extractCurlyBraceWords
    } from '$lib/utils';
    import { transcribeAudio } from '$lib/apis/audio';
    import { uploadFile as apiUploadFile } from '$lib/apis/files'; // Renamed to avoid conflict with local files variable
    import { generateAutoCompletion as apiGenerateAutoCompletion } from '$lib/apis'; // Renamed
    import { deleteFileById as apiDeleteFileById } from '$lib/apis/files'; // Renamed

    import { WEBUI_BASE_URL, WEBUI_API_BASE_URL, PASTED_TEXT_CHARACTER_LIMIT } from '$lib/constants';

    import InputMenu from './MessageInput/InputMenu.svelte';
    import VoiceRecording from './MessageInput/VoiceRecording.svelte';
    import FilesOverlay from './MessageInput/FilesOverlay.svelte';
    import Commands from './MessageInput/Commands.svelte';

    import RichTextInput from '../common/RichTextInput.svelte';
    import Tooltip from '../common/Tooltip.svelte';
    import FileItem from '../common/FileItem.svelte';
    import Image from '../common/Image.svelte';

    import XMark from '../icons/XMark.svelte';
    import Headphone from '../icons/Headphone.svelte';
    import GlobeAlt from '../icons/GlobeAlt.svelte';
    import PhotoSolid from '../icons/PhotoSolid.svelte';
    import Photo from '../icons/Photo.svelte';
    import CommandLine from '../icons/CommandLine.svelte';
    import { KokoroWorker } from '$lib/workers/KokoroWorker';
    import ToolServersModal from './ToolServersModal.svelte';
    import Wrench from '../icons/Wrench.svelte';

    const i18n = getContext('i18n');

    export let transparentBackground = false;

    export let onChange: Function = () => {};
    export let createMessagePair: Function;
    export let stopResponse: Function;

    export let autoScroll = false;

    export let atSelectedModel: Model | undefined = undefined;
    export let selectedModels: string[] = ['']; // Explicitly typed and initialized

    let selectedModelIds: string[] = []; // Explicitly typed
    $: selectedModelIds = atSelectedModel !== undefined ? [atSelectedModel.id] : selectedModels;

    export let history;
    export let taskIds = null;

    export let prompt = '';
    export let files: any[] = []; // Consider a more specific type for file objects if available

    export let toolServers: any[] = []; // Consider a more specific type
    export let selectedToolIds: string[] = []; // Explicitly typed

    export let imageGenerationEnabled = false;
    export let webSearchEnabled = false;
    export let codeInterpreterEnabled = false;

    $: onChange({
        prompt,
        files,
        selectedToolIds,
        imageGenerationEnabled,
        webSearchEnabled
    });

    let showTools = false;
    let loaded = false;
    let recording = false;
    let isComposing = false; // IME composition state

    // Element bindings
    let chatInputContainerElement: HTMLDivElement;
    let chatInputElement: any; // Bound to RichTextInput or HTMLTextAreaElement
    let filesInputElement: HTMLInputElement;
    let commandsElement: Commands; // Assuming Commands is a Svelte component instance

    let inputFiles: FileList;
    let dragged = false; // Drag-over state for file drop zone

    let user = null; // Subscribed from store: $_user
    $: user = $_user;

    export let placeholder = '';

    let visionCapableModels: string[] = []; // Store IDs of vision-capable models
    $: visionCapableModels = [...(atSelectedModel ? [atSelectedModel.id] : selectedModels)].filter(
        (modelId) => $models.find((m) => m.id === modelId)?.info?.meta?.capabilities?.vision ?? true
    );

    const scrollToBottom = () => {
        const element = document.getElementById('messages-container');
        element?.scrollTo({
            top: element.scrollHeight,
            behavior: 'smooth'
        });
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
            context.drawImage(video, 0, 0, canvas.width, canvas.height);

            mediaStream.getTracks().forEach((track) => track.stop());
            window.focus(); // Bring tab to focus

            const imageUrl = canvas.toDataURL('image/png');
            files = [...files, { type: 'image', url: imageUrl }];
            video.srcObject = null; // Clean up
        } catch (error) {
            console.error('Error capturing screen:', error);
            // Potentially show a user-facing toast notification here
        }
    };

    const uploadFileHandler = async (file: File, fullContext: boolean = false) => {
        if (user?.role !== 'admin' && !(user?.permissions?.chat?.file_upload ?? true)) {
            toast.error($i18n.t('You do not have permission to upload files.'));
            return null;
        }

        const tempItemId = uuidv4();
        const fileItem: any = { // Consider a more specific type for fileItem
            type: 'file',
            file: null, // Will hold the actual File object or response from upload
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
            return null;
        }

        files = [...files, fileItem];

        try {
            const uploadedFile = await apiUploadFile(localStorage.token, file);

            if (uploadedFile) {
                if (uploadedFile.error) {
                    console.warn('File upload warning:', uploadedFile.error);
                    toast.warning(uploadedFile.error);
                }

                const updatedFiles = files.map((item) => {
                    if (item.itemId === tempItemId) {
                        return {
                            ...item,
                            status: 'uploaded',
                            file: uploadedFile, // Store the response from API
                            id: uploadedFile.id,
                            collection_name:
                                uploadedFile?.meta?.collection_name || uploadedFile?.collection_name,
                            url: `${WEBUI_API_BASE_URL}/files/${uploadedFile.id}`
                        };
                    }
                    return item;
                });
                files = updatedFiles;
            } else {
                // Remove file from UI if upload failed or returned no data
                files = files.filter((item) => item?.itemId !== tempItemId);
            }
        } catch (e) {
            toast.error($i18n.t('File upload failed: {{message}}', { message: e.message || String(e) }));
            files = files.filter((item) => item?.itemId !== tempItemId);
        }
    };

    const inputFilesHandler = async (selectedFiles: FileList | File[]) => {
        const filesArray = Array.from(selectedFiles);

        for (const file of filesArray) {
            if (
                ($config?.file?.max_size ?? null) !== null &&
                file.size > ($config?.file?.max_size ?? 0) * 1024 * 1024
            ) {
                toast.error(
                    $i18n.t(`File size should not exceed {{maxSize}} MB.`, {
                        maxSize: $config?.file?.max_size
                    })
                );
                continue; // Skip this file
            }

            if (
                ['image/gif', 'image/webp', 'image/jpeg', 'image/png', 'image/avif'].includes(file.type)
            ) {
                if (visionCapableModels.length === 0 && selectedModels.length > 0) { // Check if any model is selected
                    toast.error($i18n.t('Selected model(s) do not support image inputs'));
                    continue; // Skip this file
                }
                let reader = new FileReader();
                reader.onload = async (event) => {
                    let imageUrl = event.target.result as string;

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
                uploadFileHandler(file);
            }
        }
    };

    // Event listener for Escape key to cancel drag operation
    const handleKeyDown = (event: KeyboardEvent) => {
        if (event.key === 'Escape' && dragged) {
            dragged = false;
        }
        // Other keydown logic for chat input is handled directly on the input elements
    };

    // Drag and drop handlers for file uploads
    const onDragOver = (e: DragEvent) => {
        e.preventDefault();
        if (e.dataTransfer?.types?.includes('Files')) {
            dragged = true;
        }
    };
    const onDragLeave = () => {
        dragged = false;
    };
    const onDrop = async (e: DragEvent) => {
        e.preventDefault();
        dragged = false;
        if (e.dataTransfer?.files && e.dataTransfer.files.length > 0) {
            inputFilesHandler(e.dataTransfer.files);
        }
    };

    onMount(async () => {
        loaded = true;

        // Autofocus chat input
        window.setTimeout(() => {
            const chatInput = document.getElementById('chat-input');
            chatInput?.focus();
        }, 0);

        window.addEventListener('keydown', handleKeyDown); // For global escape on drag

        // Setup dropzone listeners
        await tick(); // Ensure chat-container is rendered
        const dropzoneElement = document.getElementById('chat-container');
        dropzoneElement?.addEventListener('dragover', onDragOver);
        dropzoneElement?.addEventListener('drop', onDrop);
        dropzoneElement?.addEventListener('dragleave', onDragLeave);
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

    // Event handler for RichTextInput and Textarea keydown events
    const commonInputKeydownHandler = async (e: CustomEvent<{event: KeyboardEvent}> | KeyboardEvent) => {
        const keyboardEvent = 'detail' in e ? e.detail.event : e; // Accommodate Svelte's custom event
        const isCtrlPressed = keyboardEvent.ctrlKey || keyboardEvent.metaKey;
        const commandsContainerElement = document.getElementById('commands-container');

        if (keyboardEvent.key === 'Escape') {
            if (commandsContainerElement) {
                // If commands are open, Escape should likely close them or clear command input
                // This might be handled within Commands.svelte or by clearing `prompt` if it's a command
            } else {
                stopResponse(); // Global stop response
                // Clear active model/tool selections on Escape
                atSelectedModel = undefined;
                selectedToolIds = [];
                webSearchEnabled = false;
                imageGenerationEnabled = false;
                codeInterpreterEnabled = false;
            }
        }

        // Ctrl + Shift + Enter to create a message pair
        if (isCtrlPressed && keyboardEvent.key === 'Enter' && keyboardEvent.shiftKey) {
            keyboardEvent.preventDefault();
            createMessagePair(prompt);
            return; // Prevent further processing
        }

        // Ctrl + R to regenerate last response when input is empty
        if (prompt === '' && isCtrlPressed && keyboardEvent.key.toLowerCase() === 'r') {
            keyboardEvent.preventDefault();
            const regenerateButton = document.querySelector('.regenerate-response-button:last-of-type') as HTMLElement;
            regenerateButton?.click();
            return;
        }

        // ArrowUp on empty prompt to edit last user message
        if (prompt === '' && keyboardEvent.key === 'ArrowUp' && !commandsContainerElement) {
            keyboardEvent.preventDefault();
            const userMessageElement = document.querySelector('.user-message:last-of-type') as HTMLElement;
            if (userMessageElement) {
                userMessageElement.scrollIntoView({ block: 'center', behavior: 'smooth' });
                const editButton = userMessageElement.querySelector('.edit-user-message-button') as HTMLElement;
                editButton?.click();
            }
            return;
        }

        // Command palette navigation
        if (commandsContainerElement && commandsElement) {
            if (keyboardEvent.key === 'ArrowUp') {
                keyboardEvent.preventDefault();
                commandsElement.selectUp();
                document.querySelector('.selected-command-option-button')?.scrollIntoView({ block: 'nearest' });
            } else if (keyboardEvent.key === 'ArrowDown') {
                keyboardEvent.preventDefault();
                commandsElement.selectDown();
                document.querySelector('.selected-command-option-button')?.scrollIntoView({ block: 'nearest' });
            } else if (keyboardEvent.key === 'Tab' || keyboardEvent.key === 'Enter') {
                keyboardEvent.preventDefault();
                const selectedButton = document.querySelector('.selected-command-option-button') as HTMLElement;
                if (selectedButton) {
                    selectedButton.click();
                } else if (keyboardEvent.key === 'Enter' && !selectedButton) {
                    // If Enter is pressed and no command is selected, submit message
                    document.getElementById('send-message-button')?.click();
                }
            }
            return; // Command handling takes precedence
        }

        // Submit message on Enter/Ctrl+Enter (based on settings) for non-mobile or when not composing
        const isMobileWithTouch = $mobile && ('ontouchstart' in window || navigator.maxTouchPoints > 0); // Simplified mobile check

        if (!isMobileWithTouch && !isComposing) {
            const enterPressed = ($settings?.ctrlEnterToSend ?? false)
                ? (keyboardEvent.key === 'Enter' || keyboardEvent.keyCode === 13) && isCtrlPressed
                : (keyboardEvent.key === 'Enter' || keyboardEvent.keyCode === 13) && !keyboardEvent.shiftKey;

            if (enterPressed) {
                keyboardEvent.preventDefault();
                if (prompt.trim() !== '' || files.length > 0) {
                    dispatch('submit', prompt);
                }
            }
        }
    };

    // Handle paste event for RichTextInput and Textarea
    const commonInputPasteHandler = async (e: CustomEvent<{event: ClipboardEvent}> | ClipboardEvent) => {
        const clipboardEvent = 'detail' in e ? e.detail.event : e;
        const clipboardData = clipboardEvent.clipboardData;

        if (clipboardData?.items) {
            for (const item of clipboardData.items) {
                if (item.type.includes('image')) {
                    const blob = item.getAsFile();
                    if (blob) {
                        const reader = new FileReader();
                        reader.onload = (loadEvent) => {
                            files = [...files, { type: 'image', url: loadEvent.target.result as string }];
                        };
                        reader.readAsDataURL(blob);
                    }
                } else if (item.type === 'text/plain' && ($settings?.largeTextAsFile ?? false)) {
                    const text = clipboardData.getData('text/plain');
                    if (text.length > PASTED_TEXT_CHARACTER_LIMIT) {
                        clipboardEvent.preventDefault(); // Prevent direct paste into input
                        const blob = new Blob([text], { type: 'text/plain' });
                        const file = new File([blob], `Pasted_Text_${Date.now()}.txt`, { type: 'text/plain' });
                        await uploadFileHandler(file, true); // Upload as a file with full context
                    }
                }
            }
        }
    };

    // Specific for textarea: Tab key for variable highlighting and auto-resize
    const textareaKeydownHandler = async (e: KeyboardEvent) => {
        commonInputKeydownHandler(e); // Common logic

        if (e.key === 'Tab' && !e.ctrlKey && !e.metaKey && !e.altKey) { // Ensure only Tab, not part of a combo
            const textarea = e.target as HTMLTextAreaElement;
            const words = extractCurlyBraceWords(prompt);
            if (words.length > 0) {
                e.preventDefault();
                const word = words.at(0); // Focus first variable
                // Cycle through variables or select the first one
                textarea.setSelectionRange(word.startIndex, word.endIndex + 1);
            }
        }
        // Auto-resize logic is handled by on:input and on:focus for textarea
    };

    const textareaInputHandler = (e: Event) => {
        const textarea = e.target as HTMLTextAreaElement;
        textarea.style.height = 'auto'; // Reset height
        textarea.style.height = `${Math.min(textarea.scrollHeight, 320)}px`;
    };

</script>

<FilesOverlay show={dragged} />

<ToolServersModal bind:show={showTools} bind:selectedToolIds />

{#if loaded}
    <div class="w-full font-primary">
        <div class="mx-auto inset-x-0 bg-transparent flex justify-center">
            <div
                class="flex flex-col px-3 {($settings?.widescreenMode ?? null)
                    ? 'max-w-full'
                    : 'max-w-6xl'} w-full"
            >
                <div class="relative">
                    {#if autoScroll === false && history?.currentId}
                        <div
                            class="absolute -top-12 left-0 right-0 flex justify-center z-30 pointer-events-none"
                        >
                            <button
                                class="bg-white border border-gray-100 dark:border-none dark:bg-white/20 p-1.5 rounded-full pointer-events-auto"
                                title={$i18n.t('Scroll to bottom')}
                                on:click={() => {
                                    autoScroll = true;
                                    scrollToBottom();
                                }}
                            >
                                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-5 h-5">
                                    <path fill-rule="evenodd" d="M10 3a.75.75 0 01.75.75v10.638l3.96-4.158a.75.75 0 111.08 1.04l-5.25 5.5a.75.75 0 01-1.08 0l-5.25-5.5a.75.75 0 111.08-1.04l3.96 4.158V3.75A.75.75 0 0110 3z" clip-rule="evenodd"/>
                                </svg>
                            </button>
                        </div>
                    {/if}
                </div>

                <div class="w-full relative">
                    {#if atSelectedModel !== undefined || selectedToolIds.length > 0 || webSearchEnabled || ($settings?.webSearch ?? false) === 'always' || imageGenerationEnabled || codeInterpreterEnabled}
                        <div class="px-3 pb-0.5 pt-1.5 text-left w-full flex flex-col absolute bottom-0 left-0 right-0 bg-gradient-to-t from-white dark:from-gray-900 z-10">
                            {#if atSelectedModel !== undefined}
                                <div class="flex items-center justify-between w-full">
                                    <div class="pl-[1px] flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
                                        <img
                                            crossorigin="anonymous"
                                            alt={$i18n.t('Model profile image')}
                                            class="size-3.5 max-w-[28px] object-cover rounded-full"
                                            src={$models.find((model) => model.id === atSelectedModel.id)?.info?.meta?.profile_image_url ??
                                                ($i18n.language === 'dg-DG' ? `/doge.png` : `${WEBUI_BASE_URL}/static/favicon.png`)}
                                        />
                                        <div class="translate-y-[0.5px]">
                                            {$i18n.t('Talking to')} <span class="font-medium text-gray-800 dark:text-gray-200">{atSelectedModel.name}</span>
                                        </div>
                                    </div>
                                    <div>
                                        <button
                                            class="flex items-center text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200" /* Added hover effect */
                                            title={$i18n.t('Clear selected model')}
                                            on:click={() => { atSelectedModel = undefined; }}
                                        >
                                            <XMark />
                                        </button>
                                    </div>
                                </div>
                            {/if}
                            <!-- Future: Display selected tools, web search status etc. here if needed -->
                        </div>
                    {/if}

                    <Commands
                        bind:this={commandsElement}
                        bind:prompt
                        bind:files
                        on:upload={(e) => { dispatch('upload', e.detail); }}
                        on:select={(e) => {
                            const data = e.detail;
                            if (data?.type === 'model') {
                                atSelectedModel = data.data;
                            }
                            document.getElementById('chat-input')?.focus();
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
                        accept={($config?.file?.allowed_types ?? ['*']).join(',')} // Added accept attribute
                        on:change={async () => {
                            if (inputFiles && inputFiles.length > 0) {
                                inputFilesHandler(inputFiles);
                            } else {
                                toast.error($i18n.t(`No file selected.`)); // Changed message slightly
                            }
                            filesInputElement.value = ''; // Reset file input
                        }}
                    />

                    {#if recording}
                        <VoiceRecording
                            bind:recording
                            on:cancel={async () => {
                                recording = false;
                                await tick();
                                document.getElementById('chat-input')?.focus();
                            }}
                            on:confirm={async (e) => {
                                const { text } = e.detail; // filename not used here
                                prompt = `${prompt}${text} `;
                                recording = false;
                                await tick();
                                document.getElementById('chat-input')?.focus();
                                if ($settings?.speechAutoSend ?? false) {
                                    dispatch('submit', prompt);
                                }
                            }}
                        />
                    {:else}
                        <form
                            class="w-full flex gap-1.5"
                            on:submit|preventDefault={() => { dispatch('submit', prompt); }}
                        >
                            <div
                                class="flex-1 flex flex-col relative w-full shadow-lg rounded-3xl border border-gray-100 dark:border-gray-800 hover:border-gray-200 focus-within:border-gray-200 dark:hover:border-gray-700 dark:focus-within:border-gray-700 transition-colors px-1 bg-white/90 dark:bg-gray-850/50 dark:text-gray-100" /* Adjusted border and bg colors */
                                dir={$settings?.chatDirection ?? 'auto'}
                            >
                                {#if files.length > 0}
                                    <div class="mx-2 mt-2.5 mb-1 flex items-center flex-wrap gap-2">
                                        {#each files as file, fileIdx (file.itemId || file.url)}
                                            {#if file.type === 'image'}
                                                <div class="relative group">
                                                    <div class="relative flex items-center">
                                                        <Image
                                                            src={file.url}
                                                            alt={$i18n.t('User uploaded image')}
                                                            imageClassName="size-14 rounded-xl object-cover border dark:border-gray-700" /* Added border */
                                                        />
                                                        {#if (atSelectedModel ? !visionCapableModels.includes(atSelectedModel.id) : selectedModels.some(id => !visionCapableModels.includes(id)))}
                                                            <Tooltip
                                                                className="absolute top-1 left-1"
                                                                content={$i18n.t('Model {{modelName}} may not support images.', { modelName: (atSelectedModel ? [atSelectedModel] : selectedModels.map(id => $models.find(m => m.id === id)?.name )).filter(name => name).join(', ') })} /* Improved tooltip content */
                                                            >
                                                                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="size-4 text-yellow-400 dark:text-yellow-500">
                                                                    <path fill-rule="evenodd" d="M9.401 3.003c1.155-2 4.043-2 5.197 0l7.355 12.748c1.154 2-.29 4.5-2.599 4.5H4.645c-2.309 0-3.752-2.5-2.598-4.5L9.4 3.003ZM12 8.25a.75.75 0 0 1 .75.75v3.75a.75.75 0 0 1-1.5 0V9a.75.75 0 0 1 .75-.75Zm0 8.25a.75.75 0 1 0 0-1.5.75.75 0 0 0 0 1.5Z" clip-rule="evenodd"/>
                                                                </svg>
                                                            </Tooltip>
                                                        {/if}
                                                    </div>
                                                    <button
                                                        class="absolute -top-1.5 -right-1.5 bg-gray-700 text-white border border-white dark:bg-gray-300 dark:text-black rounded-full group-hover:opacity-100 opacity-0 transition-opacity focus:opacity-100 p-0.5" /* Adjusted style and visibility */
                                                        type="button"
                                                        title={$i18n.t('Remove image')}
                                                        on:click={() => {
                                                            files = files.filter((_, idx) => idx !== fileIdx);
                                                        }}
                                                    >
                                                        <XMark class="size-3" />
                                                    </button>
                                                </div>
                                            {:else}
                                                <FileItem
                                                    item={file}
                                                    name={file.name}
                                                    type={file.type}
                                                    size={file?.size}
                                                    loading={file.status === 'uploading'}
                                                    error={file.error} /* Pass error to FileItem */
                                                    dismissible={true}
                                                    edit={false} /* Assuming not editable here */
                                                    on:dismiss={async () => {
                                                        if (file.type !== 'collection' && !file?.collection_name && file.id) { // Check collection_name also
                                                            try {
                                                                await apiDeleteFileById(localStorage.token, file.id);
                                                            } catch (err) {
                                                                console.error("Error deleting file:", err);
                                                                toast.error($i18n.t("Failed to delete file from server."));
                                                            }
                                                        }
                                                        files = files.filter((_, idx) => idx !== fileIdx);
                                                    }}
                                                />
                                            {/if}
                                        {/each}
                                    </div>
                                {/if}

                                <div class="px-2.5">
                                    {#if $settings?.richTextInput ?? true}
                                        <div
                                            class="scrollbar-hidden text-left bg-transparent dark:text-gray-100 outline-none w-full pt-3 px-1 resize-none h-fit max-h-80 overflow-auto"
                                            id="chat-input-container"
                                            bind:this={chatInputContainerElement}
                                        >
                                            <RichTextInput
                                                bind:this={chatInputElement}
                                                bind:value={prompt}
                                                id="chat-input"
                                                className="input-prose-sm prose-sm dark:prose-invert max-w-full"
                                                messageInput={true}
                                                shiftEnter={!($settings?.ctrlEnterToSend ?? false) && !isMobileWithTouch}
                                                placeholder={placeholder || $i18n.t('Send a Message')}
                                                largeTextAsFile={$settings?.largeTextAsFile ?? false}
                                                autocomplete={$config?.features?.enable_autocomplete_generation && ($settings?.promptAutocomplete ?? false)}
                                                generateAutoCompletion={async (text) => {
                                                    if (selectedModelIds.length === 0 || !selectedModelIds[0]) {
                                                        toast.error($i18n.t('Please select a model first.'));
                                                        return null;
                                                    }
                                                    try {
                                                        return await apiGenerateAutoCompletion(
                                                            localStorage.token,
                                                            selectedModelIds[0],
                                                            text,
                                                            history?.currentId ? createMessagesList(history, history.currentId) : null
                                                        );
                                                    } catch (error) {
                                                        console.error('Autocomplete error:', error);
                                                        return null;
                                                    }
                                                }}
                                                on:compositionstart={() => (isComposing = true)}
                                                on:compositionend={() => (isComposing = false)}
                                                on:keydown={commonInputKeydownHandler}
                                                on:paste={commonInputPasteHandler}
                                            />
                                        </div>
                                    {:else}
                                        <textarea
                                            id="chat-input"
                                            dir="auto"
                                            bind:this={chatInputElement}
                                            class="scrollbar-hidden bg-transparent dark:text-gray-100 outline-none w-full pt-3 px-1 resize-none min-h-[40px]" /* Added min-h */
                                            placeholder={placeholder || $i18n.t('Send a Message')}
                                            bind:value={prompt}
                                            rows="1"
                                            on:compositionstart={() => (isComposing = true)}
                                            on:compositionend={() => (isComposing = false)}
                                            on:keydown={textareaKeydownHandler}
                                            on:input={textareaInputHandler}
                                            on:focus={textareaInputHandler} /* Also resize on focus */
                                            on:paste={commonInputPasteHandler}
                                        />
                                    {/if}
                                </div>

                                <div class="flex justify-between mt-1 mb-2.5 mx-0.5 max-w-full" dir="ltr">
                                    <div class="ml-1 self-end flex items-center flex-1 max-w-[calc(100%-100px)] gap-0.5">
                                        <InputMenu
                                            bind:selectedToolIds
                                            {screenCaptureHandler}
                                            {inputFilesHandler} /* Pass the correct handler */
                                            uploadFilesHandler={() => { filesInputElement.click(); }}
                                            uploadGoogleDriveHandler={async () => {
                                                try {
                                                    const fileData = await createPicker();
                                                    if (fileData?.blob) { // Check blob existence
                                                        const file = new File([fileData.blob], fileData.name, { type: fileData.blob.type });
                                                        await uploadFileHandler(file);
                                                    }
                                                } catch (error) {
                                                    console.error('Google Drive Error:', error);
                                                    toast.error($i18n.t('Error accessing Google Drive: {{message}}', { message: error.message || String(error) }));
                                                }
                                            }}
                                            uploadOneDriveHandler={async () => {
                                                try {
                                                    const fileData = await pickAndDownloadFile();
                                                    if (fileData?.blob) { // Check blob existence
                                                        const file = new File([fileData.blob], fileData.name, { type: fileData.blob.type || 'application/octet-stream' });
                                                        await uploadFileHandler(file);
                                                    }
                                                } catch (error) {
                                                    console.error('OneDrive Error:', error);
                                                    toast.error($i18n.t('Error accessing OneDrive: {{message}}', { message: error.message || String(error) }));
                                                }
                                            }}
                                            on:close={() => { tick().then(() => document.getElementById('chat-input')?.focus()); }}
                                        >
                                            <button
                                                class="bg-transparent hover:bg-gray-100 text-gray-800 dark:text-white dark:hover:bg-gray-800 transition-colors rounded-full p-1.5 outline-none focus:ring-2 focus:ring-blue-500" /* Improved focus */
                                                type="button"
                                                aria-label={$i18n.t('More options')}
                                            >
                                                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="size-5">
                                                    <path d="M10.75 4.75a.75.75 0 0 0-1.5 0v4.5h-4.5a.75.75 0 0 0 0 1.5h4.5v4.5a.75.75 0 0 0 1.5 0v-4.5h4.5a.75.75 0 0 0 0-1.5h-4.5v-4.5Z"/>
                                                </svg>
                                            </button>
                                        </InputMenu>

                                        <div class="flex gap-1 items-center overflow-x-auto scrollbar-thin flex-1">
                                            {#if toolServers.length > 0 || selectedToolIds.length > 0}
                                                <Tooltip content={$i18n.t('{{count}} Available Tools', { count: toolServers.length + selectedToolIds.length })}>
                                                    <button
                                                        class="translate-y-[0.5px] flex gap-1 items-center text-gray-600 dark:text-gray-300 hover:text-gray-700 dark:hover:text-gray-200 rounded-lg p-1 self-center transition-colors"
                                                        aria-label={$i18n.t('Available Tools')}
                                                        type="button"
                                                        on:click={() => { showTools = !showTools; }}
                                                    >
                                                        <Wrench class="size-4" strokeWidth="1.75" />
                                                        <span class="text-sm font-medium">
                                                            {toolServers.length + selectedToolIds.length}
                                                        </span>
                                                    </button>
                                                </Tooltip>
                                            {/if}

                                            {#if user}
                                                {#if $config?.features?.enable_web_search && (user.role === 'admin' || user?.permissions?.features?.web_search)}
                                                    <Tooltip content={$i18n.t('Search the internet')} placement="top">
                                                        <button
                                                            on:click|preventDefault={() => (webSearchEnabled = !webSearchEnabled)}
                                                            type="button"
                                                            class="px-1.5 @xl:px-2.5 py-1.5 flex gap-1.5 items-center text-sm rounded-full font-medium transition-colors duration-300 focus:outline-none max-w-full overflow-hidden border {(webSearchEnabled || ($settings?.webSearch ?? false) === 'always')
                                                                ? 'bg-blue-100 dark:bg-blue-500/20 border-blue-300 dark:border-blue-500/30 text-blue-600 dark:text-blue-400' /* Adjusted colors */
                                                                : 'bg-transparent border-transparent text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'}"
                                                        >
                                                            <GlobeAlt class="size-5" strokeWidth="1.75" />
                                                            <span class="hidden @xl:block whitespace-nowrap overflow-hidden text-ellipsis translate-y-[0.5px]">{$i18n.t('Web Search')}</span>
                                                        </button>
                                                    </Tooltip>
                                                {/if}
                                                {#if $config?.features?.enable_image_generation && (user.role === 'admin' || user?.permissions?.features?.image_generation)}
                                                    <Tooltip content={$i18n.t('Generate an image')} placement="top">
                                                        <button
                                                            on:click|preventDefault={() => (imageGenerationEnabled = !imageGenerationEnabled)}
                                                            type="button"
                                                            class="px-1.5 @xl:px-2.5 py-1.5 flex gap-1.5 items-center text-sm rounded-full font-medium transition-colors duration-300 focus:outline-none max-w-full overflow-hidden border {imageGenerationEnabled
                                                                ? 'bg-purple-100 dark:bg-purple-500/20 border-purple-300 dark:border-purple-500/30 text-purple-600 dark:text-purple-400' /* Example color change */
                                                                : 'bg-transparent border-transparent text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'}"
                                                        >
                                                            <PhotoSolid class="size-5" />
                                                        </button>
                                                    </Tooltip>
                                                {/if}
                                                {#if $config?.features?.enable_code_interpreter && (user.role === 'admin' || user?.permissions?.features?.code_interpreter)}
                                                    <Tooltip content={$i18n.t('Execute code for analysis')} placement="top">
                                                        <button
                                                            on:click|preventDefault={() => (codeInterpreterEnabled = !codeInterpreterEnabled)}
                                                            type="button"
                                                            class="px-1.5 @xl:px-2.5 py-1.5 flex gap-1.5 items-center text-sm rounded-full font-medium transition-colors duration-300 focus:outline-none max-w-full overflow-hidden border {codeInterpreterEnabled
                                                                ? 'bg-green-100 dark:bg-green-500/20 border-green-300 dark:border-green-500/30 text-green-600 dark:text-green-400' /* Example color change */
                                                                : 'bg-transparent border-transparent text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'}"
                                                        >
                                                            <CommandLine class="size-5" strokeWidth="1.75" />
                                                            <span class="hidden @xl:block whitespace-nowrap overflow-hidden text-ellipsis translate-y-[0.5px]">{$i18n.t('Code Interpreter')}</span>
                                                        </button>
                                                    </Tooltip>
                                                {/if}
                                            {/if}
                                        </div>
                                    </div>

                                    <div class="self-end flex space-x-1 mr-1 shrink-0">
                                        {#if (!history?.currentId || history.messages[history.currentId]?.done == true) && (user?.role === 'admin' || (user?.permissions?.chat?.stt ?? true))}
                                            <Tooltip content={$i18n.t('Record voice')}>
                                                <button
                                                    id="voice-input-button"
                                                    class="text-gray-600 dark:text-gray-300 hover:text-gray-700 dark:hover:text-gray-200 transition-colors rounded-full p-1.5 mr-0.5 self-center focus:outline-none focus:ring-2 focus:ring-blue-500" /* Improved focus */
                                                    type="button"
                                                    on:click={async () => {
                                                        try {
                                                            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                                                            if (stream) {
                                                                recording = true;
                                                                // Stop tracks after confirming recording capability to release mic for VoiceRecording component
                                                                stream.getTracks().forEach((track) => track.stop());
                                                            }
                                                        } catch (err) {
                                                            toast.error($i18n.t(`Microphone access denied: {{message}}`, { message: err.message || String(err) }));
                                                        }
                                                    }}
                                                    aria-label={$i18n.t('Voice Input')}
                                                >
                                                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-5 h-5 translate-y-[0.5px]">
                                                        <path d="M7 4a3 3 0 016 0v6a3 3 0 11-6 0V4z" />
                                                        <path d="M5.5 9.643a.75.75 0 00-1.5 0V10c0 3.06 2.29 5.585 5.25 5.954V17.5h-1.5a.75.75 0 000 1.5h4.5a.75.75 0 000-1.5h-1.5v-1.546A6.001 6.001 0 0016 10v-.357a.75.75 0 00-1.5 0V10a4.5 4.5 0 01-9 0v-.357z"/>
                                                    </svg>
                                                </button>
                                            </Tooltip>
                                        {/if}

                                        {#if (taskIds && taskIds.length > 0) || (history?.currentId && history.messages[history.currentId]?.done !== true)}
                                            <div class="flex items-center">
                                                <Tooltip content={$i18n.t('Stop generation')}>
                                                    <button
                                                        class="bg-red-500 hover:bg-red-600 text-white dark:bg-red-600 dark:hover:bg-red-700 transition-colors rounded-full p-1.5 focus:outline-none focus:ring-2 focus:ring-red-400" /* Stop button styling */
                                                        on:click={() => { stopResponse(); }}
                                                        aria-label={$i18n.t('Stop generation')}
                                                    >
                                                        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="size-5">
                                                            <path fill-rule="evenodd" d="M4.5 7.5a3 3 0 013-3h9a3 3 0 013 3v9a3 3 0 01-3 3h-9a3 3 0 01-3-3v-9z" clip-rule="evenodd" />
                                                        </svg>
                                                    </button>
                                                </Tooltip>
                                            </div>
                                        {:else if prompt.trim() === '' && files.length === 0 && (user?.role === 'admin' || (user?.permissions?.chat?.call ?? true))}
                                            <div class="flex items-center">
                                                <Tooltip content={$i18n.t('Call model (experimental)')}>
                                                    <button
                                                        class="bg-blue-500 text-white hover:bg-blue-600 dark:bg-blue-600 dark:hover:bg-blue-700 transition-colors rounded-full p-1.5 self-center focus:outline-none focus:ring-2 focus:ring-blue-400" /* Call button styling */
                                                        type="button"
                                                        aria-label={$i18n.t('Call')}
                                                        on:click={async () => {
                                                            if (selectedModels.length > 1) {
                                                                toast.error($i18n.t('Select only one model to call.')); return;
                                                            }
                                                            if ($config?.audio?.stt?.engine === 'web') { // Check config path
                                                                toast.error($i18n.t('Call feature is not supported when using Web STT engine.')); return;
                                                            }
                                                            try {
                                                                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                                                                stream.getTracks().forEach((track) => track.stop()); // Release mic

                                                                if ($settings?.audio?.tts?.engine === 'browser-kokoro') {
                                                                    if (!$TTSWorker) {
                                                                        const worker = new KokoroWorker({ dtype: $settings.audio?.tts?.engineConfig?.dtype ?? 'fp32'});
                                                                        await worker.init(); // Init worker first
                                                                        TTSWorker.set(worker);
                                                                    }
                                                                }
                                                                showCallOverlay.set(true);
                                                                showControls.set(true);
                                                            } catch (err) {
                                                                toast.error($i18n.t('Permission denied when accessing media devices.'));
                                                            }
                                                        }}
                                                    >
                                                        <Headphone class="size-5" />
                                                    </button>
                                                </Tooltip>
                                            </div>
                                        {:else}
                                            <div class="flex items-center">
                                                <Tooltip content={prompt.trim() === '' && files.length === 0 ? $i18n.t('Enter a message or add a file') : $i18n.t('Send message')}>
                                                    <button
                                                        id="send-message-button"
                                                        class="transition-colors rounded-full p-1.5 self-center focus:outline-none focus:ring-2 focus:ring-blue-500 {!(prompt.trim() === '' && files.length === 0)
                                                            ? 'bg-blue-500 text-white hover:bg-blue-600 dark:bg-blue-600 dark:hover:blue-700' /* Send button active */
                                                            : 'bg-gray-300 text-gray-500 dark:bg-gray-700 dark:text-gray-500 cursor-not-allowed'}" /* Send button inactive */
                                                        type="submit"
                                                        disabled={prompt.trim() === '' && files.length === 0}
                                                        aria-label={$i18n.t('Send message')}
                                                    >
                                                        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" class="size-5">
                                                            <path fill-rule="evenodd" d="M2 8a.75.75 0 01.75-.75h9.546L8.22 3.182a.75.75 0 111.06-1.06l4.5 4.25a.75.75 0 010 1.06l-4.5 4.25a.75.75 0 11-1.06-1.06L12.296 8.75H2.75A.75.75 0 012 8z" clip-rule="evenodd"/>
                                                        </svg>
                                                    </button>
                                                </Tooltip>
                                            </div>
                                        {/if}
                                    </div>
                                </div>
                            </div>
                        </form>
                    {/if}
                </div>
            </div>
        </div>
    </div>
{/if}
