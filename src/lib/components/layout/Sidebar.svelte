<script lang="ts">
    import { toast } from 'svelte-sonner';
    import { v4 as uuidv4 } from 'uuid';

    import { goto } from '$app/navigation';
    import {
        user,
        chats,
        settings,
        showSettings,
        chatId,
        tags,
        folders as _folders,
        showSidebar,
        showSearch,
        mobile,
        showArchivedChats,
        pinnedChats,
        scrollPaginationEnabled,
        currentChatPage,
        temporaryChatEnabled,
        channels,
        socket,
        config,
        isApp,
        models,
        selectedFolder,
        WEBUI_NAME,
        showAnnouncements
    } from '$lib/stores';
    import { onMount, getContext, tick, onDestroy } from 'svelte';

    const i18n = getContext('i18n');

    import {
        getChatList,
        getAllTags,
        getPinnedChatList,
        toggleChatPinnedStatusById,
        getChatById,
        updateChatFolderIdById,
        importChat
    } from '$lib/apis/chats';
    import { createNewFolder, getFolders, updateFolderParentIdById } from '$lib/apis/folders';
    import { WEBUI_BASE_URL } from '$lib/constants';

    import ArchivedChatsModal from './ArchivedChatsModal.svelte';
    import UserMenu from './Sidebar/UserMenu.svelte';
    import ChatItem from './Sidebar/ChatItem.svelte';
    import Spinner from '../common/Spinner.svelte';
    import Loader from '../common/Loader.svelte';
    import Folder from '../common/Folder.svelte';
    import Tooltip from '../common/Tooltip.svelte';
    import Folders from './Sidebar/Folders.svelte';
    import ImportChatsModal from './ImportChatsModal.svelte';
    import { getChannels, createNewChannel } from '$lib/apis/channels';
    import ChannelModal from './Sidebar/ChannelModal.svelte';
    import ChannelItem from './Sidebar/ChannelItem.svelte';
    import PencilSquare from '../icons/PencilSquare.svelte';
    import Search from '../icons/Search.svelte';
    import Sparkles from '../icons/Sparkles.svelte';
    import SearchModal from './SearchModal.svelte';
    import FolderModal from './Sidebar/Folders/FolderModal.svelte';
    import Sidebar from '../icons/Sidebar.svelte';
    import PinnedModelList from './Sidebar/PinnedModelList.svelte';
    import Note from '../icons/Note.svelte';
    import { slide } from 'svelte/transition';
    import { convertDeepseekChats, getImportOrigin } from '$lib/utils';

    const BREAKPOINT = 768;

    let scrollTop = 0;

    let navElement;
    let shiftKey = false;

    let selectedChatId = null;
    let showPinnedChat = true;

    let showCreateChannel = false;

    let showImportChatsModal = false;

    // Pagination variables
    let chatListLoading = false;
    let allChatsLoaded = false;

    let showCreateFolderModal = false;

    let folders = {};
    let folderRegistry = {};

    let newFolderId = null;

    const initFolders = async () => {
        const folderList = await getFolders(localStorage.token).catch((error) => {
            toast.error(`${error}`);
            return [];
        });
        _folders.set(folderList.sort((a, b) => b.updated_at - a.updated_at));

        folders = {};

        // First pass: Initialize all folder entries
        for (const folder of folderList) {
            // Ensure folder is added to folders with its data
            folders[folder.id] = { ...(folders[folder.id] || {}), ...folder };

            if (newFolderId && folder.id === newFolderId) {
                folders[folder.id].new = true;
                newFolderId = null;
            }
        }

        // Second pass: Tie child folders to their parents
        for (const folder of folderList) {
            if (folder.parent_id) {
                // Ensure the parent folder is initialized if it doesn't exist
                if (!folders[folder.parent_id]) {
                    folders[folder.parent_id] = {}; // Create a placeholder if not already present
                }

                // Initialize childrenIds array if it doesn't exist and add the current folder id
                folders[folder.parent_id].childrenIds = folders[folder.parent_id].childrenIds
                    ? [...folders[folder.parent_id].childrenIds, folder.id]
                    : [folder.id];

                // Sort the children by updated_at field
                folders[folder.parent_id].childrenIds.sort((a, b) => {
                    return folders[b].updated_at - folders[a].updated_at;
                });
            }
        }
    };

    const createFolder = async ({ name, data }) => {
        if (name === '') {
            toast.error($i18n.t('Folder name cannot be empty.'));
            return;
        }

        const rootFolders = Object.values(folders).filter((folder) => folder.parent_id === null);
        if (rootFolders.find((folder) => folder.name.toLowerCase() === name.toLowerCase())) {
            // If a folder with the same name already exists, append a number to the name
            let i = 1;
            while (
                rootFolders.find((folder) => folder.name.toLowerCase() === `${name} ${i}`.toLowerCase())
            ) {
                i++;
            }

            name = `${name} ${i}`;
        }

        // Add a dummy folder to the list to show the user that the folder is being created
        const tempId = uuidv4();
        folders = {
            ...folders,
            tempId: {
                id: tempId,
                name: name,
                created_at: Date.now(),
                updated_at: Date.now()
            }
        };

        const res = await createNewFolder(localStorage.token, {
            name,
            data
        }).catch((error) => {
            toast.error(`${error}`);
            return null;
        });

        if (res) {
            // newFolderId = res.id;
            await initFolders();
        }
    };

    const initChannels = async () => {
        await channels.set(await getChannels(localStorage.token));
    };

    const initChatList = async () => {
        // Reset pagination variables
        console.log('initChatList');
        currentChatPage.set(1);
        allChatsLoaded = false;

        initFolders();
        await Promise.all([
            await (async () => {
                console.log('Init tags');
                const _tags = await getAllTags(localStorage.token);
                tags.set(_tags);
            })(),
            await (async () => {
                console.log('Init pinned chats');
                const _pinnedChats = await getPinnedChatList(localStorage.token);
                pinnedChats.set(_pinnedChats);
            })(),
            await (async () => {
                console.log('Init chat list');
                const _chats = await getChatList(localStorage.token, $currentChatPage);
                await chats.set(_chats);
            })()
        ]);

        // Enable pagination
        scrollPaginationEnabled.set(true);
    };

    const loadMoreChats = async () => {
        chatListLoading = true;

        currentChatPage.set($currentChatPage + 1);

        let newChatList = [];

        newChatList = await getChatList(localStorage.token, $currentChatPage);

        // once the bottom of the list has been reached (no results) there is no need to continue querying
        allChatsLoaded = newChatList.length === 0;
        await chats.set([...($chats ? $chats : []), ...newChatList]);

        chatListLoading = false;
    };

    // Helper to convert OpenAI/DeepSeek "mapping" format to OpenWebUI format
    const convertLegacyChat = (convo) => {
        const mapping = convo['mapping'];
        const messages = {};
        let currentId = null;
        let lastId = null; // Fallback to track linear progression

        for (const message_id in mapping) {
            const node = mapping[message_id];
            const message = node.message;

            // Skip empty updates or null messages
            if (!message) continue;

            let content = '';
            let role = message.author?.role === 'assistant' ? 'assistant' : 'user';
            
            // Extract content based on format (OpenAI 'parts' or DeepSeek 'fragments'/'content')
            if (message.content) {
                if (Array.isArray(message.content.parts)) {
                     // OpenAI format
                     content = message.content.parts.join('');
                } else if (typeof message.content === 'string') {
                     // Simple string format
                     content = message.content;
                } else if (Array.isArray(message.fragments)) {
                    // DeepSeek fragments format (if inside content)
                    content = message.fragments.map(f => f.content).join('');
                }
            } 
            // Check top-level fragments (DeepSeek sometimes puts fragments here)
            else if (Array.isArray(message.fragments)) {
                 content = message.fragments.map(f => f.content).join('');
            }

            // Fallback for role inference if missing
            if (role === 'user' && message.author?.role !== 'user' && message.author?.role !== 'system') {
                 // DeepSeek sometimes uses 'author': { 'role': 'tool' } or others
                 role = 'assistant';
            }

            // Skip messages with no content unless strictly necessary (e.g. system instructions, though OpenWebUI handles those differently)
            if (!content && role !== 'system') continue;

            const newChat = {
                id: message_id,
                parentId: node.parent || null,
                childrenIds: node.children || [],
                role: role,
                content: content,
                model: message.model || message.metadata?.model_slug || 'gpt-3.5-turbo',
                done: true,
                context: null,
                timestamp: message.create_time || convo.create_time || Date.now() / 1000
            };
            
            messages[message_id] = newChat;
            
            // Attempt to determine the "current" (latest) node
            // A node with no children is a candidate for being the leaf node
            if (!node.children || node.children.length === 0) {
                // If multiple branches exist, this simple logic takes the last one processed
                // In linear chats, this is correct.
                currentId = message_id;
            }
            lastId = message_id;
        }

        return {
            history: {
                currentId: currentId || lastId,
                messages: messages
            },
            models: Object.values(messages).map(m => m.model).filter((v, i, a) => a.indexOf(v) === i),
            title: convo.title || 'New Chat',
            timestamp: convo.create_time || convo.inserted_at || Date.now() / 1000
        };
    };

    const importChatHandler = async (items, pinned = false, folderId = null) => {
        console.log('importChatHandler', items, pinned, folderId);
        
        for (const item of items) {
            let chatPayload = item.chat;
            let meta = item.meta || {};

            // [NEW] Check if the item is a raw OpenAI/DeepSeek export (has 'mapping')
            // and convert it before processing
            if (item.mapping) {
                console.log("Detected OpenAI/DeepSeek Mapping format, converting...");
                try {
                    chatPayload = convertLegacyChat(item);
                    // Use title from the export if available
                    if (item.title) {
                        chatPayload.title = item.title;
                    }
                } catch (e) {
                    console.error("Conversion failed", e);
                    toast.error(`Format conversion failed for ${item.title || 'chat'}`);
                    continue; 
                }
            } 
            // [NEW] Handle potential nested structure from DeepSeek JSON exports
            // (Where the item itself has 'chat' key but is an array element)
            else if (!chatPayload && item.history) {
                 // If item IS the chat object (OpenWebUI export style)
                 chatPayload = item;
            }

            console.log("Importing:", chatPayload);

            if (chatPayload) {
                await importChat(
                    localStorage.token,
                    chatPayload,
                    meta,
                    pinned,
                    folderId,
                    item?.created_at ?? null,
                    item?.updated_at ?? null
                );
            }
        }

        initChatList();
    };

    const inputFilesHandler = async (files) => {
        console.log(files);

        for (const file of files) {
            const reader = new FileReader();
            reader.onload = async (e) => {
                const content = e.target.result;

                try {
                    const chatItems = JSON.parse(content);
                    // Ensure we handle both single object and array imports
                    const itemsToImport = Array.isArray(chatItems) ? chatItems : [chatItems];
                    importChatHandler(itemsToImport);
                } catch {
                    toast.error($i18n.t(`Invalid file format.`));
                }
            };

            reader.readAsText(file);
        }
    };

    const tagEventHandler = async (type, tagName, chatId) => {
        console.log(type, tagName, chatId);
        if (type === 'delete') {
            initChatList();
        } else if (type === 'add') {
            initChatList();
        }
    };

    let draggedOver = false;

    const onDragOver = (e) => {
        e.preventDefault();

        // Check if a file is being draggedOver.
        if (e.dataTransfer?.types?.includes('Files')) {
            draggedOver = true;
        } else {
            draggedOver = false;
        }
    };

    const onDragLeave = () => {
        draggedOver = false;
    };

    const onDrop = async (e) => {
        e.preventDefault();
        console.log(e); // Log the drop event

        // Perform file drop check and handle it accordingly
        if (e.dataTransfer?.files) {
            const inputFiles = Array.from(e.dataTransfer?.files);

            if (inputFiles && inputFiles.length > 0) {
                console.log(inputFiles); // Log the dropped files
                inputFilesHandler(inputFiles); // Handle the dropped files
            }
        }

        draggedOver = false; // Reset draggedOver status after drop
    };

    let touchstart;
    let touchend;

    function checkDirection() {
        const screenWidth = window.innerWidth;
        const swipeDistance = Math.abs(touchend.screenX - touchstart.screenX);
        if (touchstart.clientX < 40 && swipeDistance >= screenWidth / 8) {
            if (touchend.screenX < touchstart.screenX) {
                showSidebar.set(false);
            }
            if (touchend.screenX > touchstart.screenX) {
                showSidebar.set(true);
            }
        }
    }

    const onTouchStart = (e) => {
        touchstart = e.changedTouches[0];
        console.log(touchstart.clientX);
    };

    const onTouchEnd = (e) => {
        touchend = e.changedTouches[0];
        checkDirection();
    };

    const onKeyDown = (e) => {
        if (e.key === 'Shift') {
            shiftKey = true;
        }
    };

    const onKeyUp = (e) => {
        if (e.key === 'Shift') {
            shiftKey = false;
        }
    };

    const onFocus = () => {};

    const onBlur = () => {
        shiftKey = false;
        selectedChatId = null;
    };

    const importChatsHandler = async (_chats) => {
        let chatsToImport = _chats;

        // [MODIFIED] Logic to intercept DeepSeek/OpenAI imports
        // Check if the input is in OpenAI/DeepSeek export format (has 'mapping')
        // and convert if necessary before passing to the standard import logic.
        if (Array.isArray(chatsToImport)) {
             chatsToImport = chatsToImport.map(item => {
                 if (item.mapping) {
                     return { chat: convertLegacyChat(item), meta: {} };
                 }
                 return item;
             });
        }

        const origin = getImportOrigin(chatsToImport);
        if (origin === 'deepseek') {
            try {
                chatsToImport = convertDeepseekChats(chatsToImport);
            } catch (error) {
                console.error('DeepSeek conversion failed', error);
                toast.error('DeepSeek 聊天转换失败');
                return;
            }
        }

        for (const chat of chatsToImport) {
            console.log(chat);

            if (chat.chat) {
                await importChat(
                    localStorage.token,
                    chat.chat,
                    chat.meta ?? {},
                    false,
                    null,
                    chat?.created_at ?? null,
                    chat?.updated_at ?? null
                );
            } else {
                // Legacy format
                await importChat(localStorage.token, chat, {}, false, null);
            }
        }

        currentChatPage.set(1);
        await chats.set(await getChatList(localStorage.token, $currentChatPage));
        pinnedChats.set(await getPinnedChatList(localStorage.token));
        scrollPaginationEnabled.set(true);
    };

    let unsubscribers = [];
    onMount(async () => {
        showPinnedChat = localStorage?.showPinnedChat ? localStorage.showPinnedChat === 'true' : true;
        await showSidebar.set(!$mobile ? localStorage.sidebar === 'true' : false);

        unsubscribers = [
            mobile.subscribe((value) => {
                if ($showSidebar && value) {
                    showSidebar.set(false);
                }

                if ($showSidebar && !value) {
                    const navElement = document.getElementsByTagName('nav')[0];
                    if (navElement) {
                        navElement.style['-webkit-app-region'] = 'drag';
                    }
                }

                if (!$showSidebar && !value) {
                    showSidebar.set(true);
                }
            }),
            showSidebar.subscribe(async (value) => {
                localStorage.sidebar = value;

                // nav element is not available on the first render
                const navElement = document.getElementsByTagName('nav')[0];

                if (navElement) {
                    if ($mobile) {
                        if (!value) {
                            navElement.style['-webkit-app-region'] = 'drag';
                        } else {
                            navElement.style['-webkit-app-region'] = 'no-drag';
                        }
                    } else {
                        navElement.style['-webkit-app-region'] = 'drag';
                    }
                }

                if (value) {
                    await initChannels();
                    await initChatList();
                }
            })
        ];

        window.addEventListener('keydown', onKeyDown);
        window.addEventListener('keyup', onKeyUp);

        window.addEventListener('touchstart', onTouchStart);
        window.addEventListener('touchend', onTouchEnd);

        window.addEventListener('focus', onFocus);
        window.addEventListener('blur', onBlur);

        const dropZone = document.getElementById('sidebar');

        dropZone?.addEventListener('dragover', onDragOver);
        dropZone?.addEventListener('drop', onDrop);
        dropZone?.addEventListener('dragleave', onDragLeave);
    });

    onDestroy(() => {
        if (unsubscribers && unsubscribers.length > 0) {
            unsubscribers.forEach((unsubscriber) => {
                if (unsubscriber) {
                    unsubscriber();
                }
            });
        }

        window.removeEventListener('keydown', onKeyDown);
        window.removeEventListener('keyup', onKeyUp);

        window.removeEventListener('touchstart', onTouchStart);
        window.removeEventListener('touchend', onTouchEnd);

        window.removeEventListener('focus', onFocus);
        window.removeEventListener('blur', onBlur);

        const dropZone = document.getElementById('sidebar');

        dropZone?.removeEventListener('dragover', onDragOver);
        dropZone?.removeEventListener('drop', onDrop);
        dropZone?.removeEventListener('dragleave', onDragLeave);
    });

    const newChatHandler = async () => {
        selectedChatId = null;
        selectedFolder.set(null);

        if ($user?.role !== 'admin' && $user?.permissions?.chat?.temporary_enforced) {
            await temporaryChatEnabled.set(true);
        } else {
            await temporaryChatEnabled.set(false);
        }

        setTimeout(() => {
            if ($mobile) {
                showSidebar.set(false);
            }
        }, 0);
    };

    const itemClickHandler = async () => {
        selectedChatId = null;
        chatId.set('');

        if ($mobile) {
            showSidebar.set(false);
        }

        await tick();
    };

    const isWindows = /Windows/i.test(navigator.userAgent);
</script>

<ArchivedChatsModal
    bind:show={$showArchivedChats}
    onUpdate={async () => {
        await initChatList();
    }}
/>

<ChannelModal
    bind:show={showCreateChannel}
    onSubmit={async ({ name, access_control }) => {
        const res = await createNewChannel(localStorage.token, {
            name: name,
            access_control: access_control
        }).catch((error) => {
            toast.error(`${error}`);
            return null;
        });

        if (res) {
            $socket.emit('join-channels', { auth: { token: $user?.token } });
            await initChannels();
            showCreateChannel = false;
        }
    }}
/>

<FolderModal
    bind:show={showCreateFolderModal}
    onSubmit={async (folder) => {
        await createFolder(folder);
        showCreateFolderModal = false;
    }}
/>

{#if $showSidebar}
    <div
        class=" {$isApp
            ? ' ml-[4.5rem] md:ml-0'
            : ''} fixed md:hidden z-40 top-0 right-0 left-0 bottom-0 bg-black/60 w-full min-h-screen h-screen flex justify-center overflow-hidden overscroll-contain"
        on:mousedown={() => {
            showSidebar.set(!$showSidebar);
        }}
    />
{/if}

<SearchModal
    bind:show={$showSearch}
    onClose={() => {
        if ($mobile) {
            showSidebar.set(false);
        }
    }}
/>

<button
    id="sidebar-new-chat-button"
    class="hidden"
    on:click={() => {
        goto('/');
        newChatHandler();
    }}
/>

{#if !$mobile && !$showSidebar}
    <div
        class=" py-2 px-1.5 flex flex-col justify-between text-black dark:text-white hover:bg-gray-50/50 dark:hover:bg-gray-950/50 h-full border-e border-gray-50 dark:border-gray-850 z-10 transition-all"
        id="sidebar"
    >
        <button
            class="flex flex-col flex-1 {isWindows ? 'cursor-pointer' : 'cursor-[e-resize]'}"
            on:click={async () => {
                showSidebar.set(!$showSidebar);
            }}
        >
            <div class="pb-1.5">
                <Tooltip
                    content={$showSidebar ? $i18n.t('Close Sidebar') : $i18n.t('Open Sidebar')}
                    placement="right"
                >
                    <button
                        class="flex rounded-xl hover:bg-gray-100 dark:hover:bg-gray-850 transition group {isWindows
                            ? 'cursor-pointer'
                            : 'cursor-[e-resize]'}"
                        aria-label={$showSidebar ? $i18n.t('Close Sidebar') : $i18n.t('Open Sidebar')}
                    >
                        <div class=" self-center flex items-center justify-center size-9">
                            <img
                                crossorigin="anonymous"
                                src="static/favicon.png"
                                class="sidebar-new-chat-icon size-6 rounded-full group-hover:hidden invert"
                                alt=""
                            />

                            <Sidebar className="size-5 hidden group-hover:flex" />
                        </div>
                    </button>
                </Tooltip>
            </div>

            <div>
                <div class="">
                    <Tooltip content={$i18n.t('New Chat')} placement="right">
                        <a
                            class=" cursor-pointer flex rounded-xl hover:bg-gray-100 dark:hover:bg-gray-850 transition group"
                            href="/"
                            draggable="false"
                            on:click={async (e) => {
                                e.stopImmediatePropagation();
                                e.preventDefault();

                                goto('/');
                                newChatHandler();
                            }}
                            aria-label={$i18n.t('New Chat')}
                        >
                            <div class=" self-center flex items-center justify-center size-9">
                                <PencilSquare className="size-4.5" />
                            </div>
                        </a>
                    </Tooltip>
                </div>
                
                <div class="">
                    <Tooltip content={$i18n.t('Memory')} placement="right">
                        <a
                            id="sidebar-memory-button"
                            class=" cursor-pointer flex rounded-xl hover:bg-gray-100 dark:hover:bg-gray-850 transition group"
                            href="/memories"
                            draggable="false"
                            on:click={async (e) => {
                                e.stopImmediatePropagation();
                                e.preventDefault();

                                goto('/memories');
                                itemClickHandler();
                            }}
                            aria-label={$i18n.t('Memory')}
                        >
                            <div class=" self-center flex items-center justify-center size-9">
                                <Sparkles strokeWidth="2" className="size-4.5" />
                            </div>
                        </a>
                    </Tooltip>
                </div>
            </div>
        </button>

        <div>
            <div>
                <div class=" py-0.5">
                    {#if $user !== undefined && $user !== null}
                        <UserMenu
                            role={$user?.role}
                            on:show={(e) => {
                                if (e.detail === 'archived-chat') {
                                    showArchivedChats.set(true);
                                }
                                if (e.detail === 'announcements') {
                                    showAnnouncements.set(true);
                                }
                            }}
                        >
                            <div
                                class=" cursor-pointer flex rounded-xl hover:bg-gray-100 dark:hover:bg-gray-850 transition group"
                            >
                                <div class=" self-center flex items-center justify-center size-9">
                                    <img
                                        src={$user?.profile_image_url}
                                        class=" size-6 object-cover rounded-full"
                                        alt={$i18n.t('Open User Profile Menu')}
                                        aria-label={$i18n.t('Open User Profile Menu')}
                                    />
                                </div>
                            </div>
                        </UserMenu>
                    {/if}
                </div>
            </div>
        </div>
    </div>
{/if}

{#if $showSidebar}
    <div
        bind:this={navElement}
        id="sidebar"
        class="h-screen max-h-[100dvh] min-h-screen select-none {$showSidebar
            ? 'bg-gray-50 dark:bg-gray-950 z-50'
            : ' bg-transparent z-0 '} {$isApp
            ? `ml-[4.5rem] md:ml-0 `
            : ' transition-all duration-300 '} shrink-0 text-gray-900 dark:text-gray-200 text-sm fixed top-0 left-0 overflow-x-hidden
        "
        transition:slide={{ duration: 250, axis: 'x' }}
        data-state={$showSidebar}
    >
        <div
            class=" my-auto flex flex-col justify-between h-screen max-h-[100dvh] w-[260px] overflow-x-hidden scrollbar-hidden z-50 {$showSidebar
                ? ''
                : 'invisible'}"
        >
            <div
                class="sidebar px-2 pt-2 pb-1.5 flex justify-between space-x-1 text-gray-600 dark:text-gray-400 sticky top-0 z-10 -mb-3"
            >
                <a
                    class="flex items-center rounded-xl size-8.5 h-full justify-center hover:bg-gray-100/50 dark:hover:bg-gray-850/50 transition no-drag-region"
                    href="/"
                    draggable="false"
                    on:click={newChatHandler}
                >
                    <img
                        crossorigin="anonymous"
                        src="static/favicon.png"
                        class="sidebar-new-chat-icon size-6 rounded-full invert"
                        alt=""
                    />
                </a>

                <a href="/" class="flex flex-1 px-1.5" on:click={newChatHandler}>
                    <div class=" self-center font-medium text-gray-850 dark:text-white font-primary">
                        {$WEBUI_NAME}
                    </div>
                </a>
                <Tooltip
                    content={$showSidebar ? $i18n.t('Close Sidebar') : $i18n.t('Open Sidebar')}
                    placement="bottom"
                >
                    <button
                        class="flex rounded-xl size-8.5 justify-center items-center hover:bg-gray-100/50 dark:hover:bg-gray-850/50 transition {isWindows
                            ? 'cursor-pointer'
                            : 'cursor-[w-resize]'}"
                        on:click={() => {
                            showSidebar.set(!$showSidebar);
                        }}
                        aria-label={$showSidebar ? $i18n.t('Close Sidebar') : $i18n.t('Open Sidebar')}
                    >
                        <div class=" self-center p-1.5">
                            <Sidebar />
                        </div>
                    </button>
                </Tooltip>

                <div
                    class="{scrollTop > 0
                        ? 'visible'
                        : 'invisible'} sidebar-bg-gradient-to-b bg-linear-to-b from-gray-50 dark:from-gray-950 to-transparent from-50% pointer-events-none absolute inset-0 -z-10 -mb-6"
                ></div>
            </div>

            <div
                class="relative flex flex-col flex-1 overflow-y-auto scrollbar-hidden pt-3 pb-3"
                on:scroll={(e) => {
                    if (e.target.scrollTop === 0) {
                        scrollTop = 0;
                    } else {
                        scrollTop = e.target.scrollTop;
                    }
                }}
            >
                <div class="pb-1.5">
                    <div class="px-[7px] flex justify-center text-gray-800 dark:text-gray-200">
                        <a
                            id="sidebar-new-chat-button"
                            class="grow flex items-center space-x-3 rounded-2xl px-2.5 py-2 hover:bg-gray-100 dark:hover:bg-gray-900 transition outline-none"
                            href="/"
                            draggable="false"
                            on:click={newChatHandler}
                            aria-label={$i18n.t('New Chat')}
                        >
                            <div class="self-center">
                                <PencilSquare className=" size-4.5" strokeWidth="2" />
                            </div>

                            <div class="flex self-center translate-y-[0.5px]">
                                <div class=" self-center text-sm font-primary">{$i18n.t('New Chat')}</div>
                            </div>
                        </a>
                    </div>

                    <div class="px-[7px] flex justify-center text-gray-800 dark:text-gray-200">
                        <a
                            id="sidebar-memory-button"
                            class="grow flex items-center space-x-3 rounded-2xl px-2.5 py-2 hover:bg-gray-100 dark:hover:bg-gray-900 transition outline-none"
                            href="/memories"
                            on:click={itemClickHandler}
                            draggable="false"
                            aria-label={$i18n.t('Memory')}
                        >
                            <div class="self-center">
                                <Sparkles strokeWidth="2" className="size-4.5" />
                            </div>

                            <div class="flex self-center translate-y-[0.5px]">
                                <div class=" self-center text-sm font-primary">{$i18n.t('Memory')}</div>
                            </div>
                        </a>
                    </div>
                </div>

                {#if ($models ?? []).length > 0 && ($settings?.pinnedModels ?? []).length > 0}
                    <PinnedModelList bind:selectedChatId {shiftKey} />
                {/if}

                <Folder
                    className="px-2 mt-0.5"
                    name={$i18n.t('Chats')}
                    chevron={false}
                    on:change={async (e) => {
                        selectedFolder.set(null);
                    }}
                    on:import={(e) => {
                        importChatHandler(e.detail);
                    }}
                    on:drop={async (e) => {
                        const { type, id, item } = e.detail;

                        if (type === 'chat') {
                            let chat = await getChatById(localStorage.token, id).catch((error) => {
                                return null;
                            });
                            if (!chat && item) {
                                chat = await importChat(
                                    localStorage.token,
                                    item.chat,
                                    item?.meta ?? {},
                                    false,
                                    null,
                                    item?.created_at ?? null,
                                    item?.updated_at ?? null
                                );
                            }

                            if (chat) {
                                console.log(chat);
                                if (chat.folder_id) {
                                    const res = await updateChatFolderIdById(localStorage.token, chat.id, null).catch(
                                        (error) => {
                                            toast.error(`${error}`);
                                            return null;
                                        }
                                    );

                                    folderRegistry[chat.folder_id]?.setFolderItems();
                                }

                                if (chat.pinned) {
                                    const res = await toggleChatPinnedStatusById(localStorage.token, chat.id);
                                }

                                await initChatList();
                            }
                        } else if (type === 'folder') {
                            if (folders[id].parent_id === null) {
                                return;
                            }

                            const res = await updateFolderParentIdById(localStorage.token, id, null).catch(
                                (error) => {
                                    toast.error(`${error}`);
                                    return null;
                                }
                            );

                            if (res) {
                                await initFolders();
                            }
                        }
                    }}
                >
                    {#if $pinnedChats.length > 0}
                        <div class="mb-1">
                            <div class="flex flex-col space-y-1 rounded-xl">
                                <Folder
                                    buttonClassName=" text-gray-500"
                                    bind:open={showPinnedChat}
                                    on:change={(e) => {
                                        localStorage.setItem('showPinnedChat', e.detail);
                                        console.log(e.detail);
                                    }}
                                    on:import={(e) => {
                                        importChatHandler(e.detail, true);
                                    }}
                                    on:drop={async (e) => {
                                        const { type, id, item } = e.detail;

                                        if (type === 'chat') {
                                            let chat = await getChatById(localStorage.token, id).catch((error) => {
                                                return null;
                                            });
                                            if (!chat && item) {
                                                chat = await importChat(
                                                    localStorage.token,
                                                    item.chat,
                                                    item?.meta ?? {},
                                                    false,
                                                    null,
                                                    item?.created_at ?? null,
                                                    item?.updated_at ?? null
                                                );
                                            }

                                            if (chat) {
                                                console.log(chat);
                                                if (chat.folder_id) {
                                                    const res = await updateChatFolderIdById(
                                                        localStorage.token,
                                                        chat.id,
                                                        null
                                                    ).catch((error) => {
                                                        toast.error(`${error}`);
                                                        return null;
                                                    });
                                                }

                                                if (!chat.pinned) {
                                                    const res = await toggleChatPinnedStatusById(localStorage.token, chat.id);
                                                }

                                                await initChatList();
                                            }
                                        }
                                    }}
                                    name={$i18n.t('Pinned')}
                                >
                                    <div
                                        class="ml-3 pl-1 mt-[1px] flex flex-col overflow-y-auto scrollbar-hidden border-s border-gray-100 dark:border-gray-900 text-gray-900 dark:text-gray-200"
                                    >
                                        {#each $pinnedChats as chat, idx (`pinned-chat-${chat?.id ?? idx}`)}
                                            <ChatItem
                                                className=""
                                                id={chat.id}
                                                title={chat.title}
                                                {shiftKey}
                                                selected={selectedChatId === chat.id}
                                                on:select={() => {
                                                    selectedChatId = chat.id;
                                                }}
                                                on:unselect={() => {
                                                    selectedChatId = null;
                                                }}
                                                on:change={async () => {
                                                    await initChatList();
                                                }}
                                                on:tag={(e) => {
                                                    const { type, name } = e.detail;
                                                    tagEventHandler(type, name, chat.id);
                                                }}
                                            />
                                        {/each}
                                    </div>
                                </Folder>
                            </div>
                        </div>
                    {/if}

                    <div class=" flex-1 flex flex-col overflow-y-auto scrollbar-hidden">
                        <div class="pt-1.5">
                            {#if $chats}
                                {#each $chats as chat, idx (`chat-${chat?.id ?? idx}`)}
                                    {#if idx === 0 || (idx > 0 && chat.time_range !== $chats[idx - 1].time_range)}
                                        <div
                                            class="w-full pl-2.5 text-xs text-gray-500 dark:text-gray-500 font-medium {idx ===
                                            0
                                                ? ''
                                                : 'pt-5'} pb-1.5"
                                        >
                                            {$i18n.t(chat.time_range)}
                                            </div>
                                    {/if}

                                    <ChatItem
                                        className=""
                                        id={chat.id}
                                        title={chat.title}
                                        {shiftKey}
                                        selected={selectedChatId === chat.id}
                                        on:select={() => {
                                            selectedChatId = chat.id;
                                        }}
                                        on:unselect={() => {
                                            selectedChatId = null;
                                        }}
                                        on:change={async () => {
                                            await initChatList();
                                        }}
                                        on:tag={(e) => {
                                            const { type, name } = e.detail;
                                            tagEventHandler(type, name, chat.id);
                                        }}
                                    />
                                {/each}

                                {#if $scrollPaginationEnabled && !allChatsLoaded}
                                    <Loader
                                        on:visible={(e) => {
                                            if (!chatListLoading) {
                                                loadMoreChats();
                                            }
                                        }}
                                    >
                                        <div
                                            class="w-full flex justify-center py-1 text-xs animate-pulse items-center gap-2"
                                        >
                                            <Spinner className=" size-4" />
                                            <div class=" ">{$i18n.t('Loading...')}</div>
                                        </div>
                                    </Loader>
                                {/if}
                            {:else}
                                <div
                                    class="w-full flex justify-center py-1 text-xs animate-pulse items-center gap-2"
                                >
                                    <Spinner className=" size-4" />
                                    <div class=" ">{$i18n.t('Loading...')}</div>
                                </div>
                            {/if}
                        </div>
                    </div>
                </Folder>
            </div>

            <hr class="border-gray-100 dark:border-gray-850 mx-1.5 my-1.5" />

            <div class="px-1.5 pt-1.5 pb-2 sticky bottom-0 z-10 -mt-3 sidebar">
                <div
                    class=" sidebar-bg-gradient-to-t bg-linear-to-t from-gray-50 dark:from-gray-950 to-transparent from-50% pointer-events-none absolute inset-0 -z-10 -mt-6"
                ></div>

                <button
                    class="flex w-full items-center space-x-3 rounded-2xl px-2.5 py-2 hover:bg-gray-100/50 dark:hover:bg-gray-900 transition outline-none"
                    on:click={() => {
                        showImportChatsModal = true;
                    }}
                    draggable="false"
                    aria-label="导入聊天记录"
                >
                    <div class="self-center">
                        <svg
                            xmlns="http://www.w3.org/2000/svg"
                            viewBox="0 0 16 16"
                            fill="currentColor"
                            class="size-4.5"
                        >
                            <path
                                fill-rule="evenodd"
                                d="M4 2a1.5 1.5 0 0 0-1.5 1.5v9A1.5 1.5 0 0 0 4 14h8a1.5 1.5 0 0 0 1.5-1.5V6.621a1.5 1.5 0 0 0-.44-1.06L9.94 2.439A1.5 1.5 0 0 0 8.878 2H4Zm4 9.5a.75.75 0 0 1-.75-.75V8.06l-.72.72a.75.75 0 0 1-1.06-1.06l2-2a.75.75 0 0 1 1.06 0l2 2a.75.75 0 1 1-1.06 1.06l-.72-.72v2.69a.75.75 0 0 1-.75.75Z"
                                clip-rule="evenodd"
                            />
                        </svg>
                    </div>
                    <div class="flex self-center translate-y-[0.5px]">
                        <div class="self-center text-sm font-primary">导入聊天记录</div>
                    </div>
                </button>

                <div class="flex flex-col font-primary">
                    {#if $user !== undefined && $user !== null}
                        <UserMenu
                            role={$user?.role}
                            on:show={(e) => {
                                if (e.detail === 'archived-chat') {
                                    showArchivedChats.set(true);
                                }
                                if (e.detail === 'announcements') {
                                    showAnnouncements.set(true);
                                }
                            }}
                        >
                            <div
                                class=" flex items-center rounded-2xl py-2 px-1.5 w-full hover:bg-gray-100/50 dark:hover:bg-gray-900/50 transition"
                            >
                                <div class=" self-center mr-3">
                                    <img
                                        src={$user?.profile_image_url}
                                        class=" size-6 object-cover rounded-full"
                                        alt={$i18n.t('Open User Profile Menu')}
                                        aria-label={$i18n.t('Open User Profile Menu')}
                                    />
                                </div>
                                <div class=" self-center font-medium">{$user?.name}</div>
                            </div>
                        </UserMenu>
                    {/if}
                </div>
            </div>
        </div>
    </div>
{/if}

<ImportChatsModal
    bind:show={showImportChatsModal}
    onImport={async (chats) => {
        await importChatsHandler(chats);
    }}
/>