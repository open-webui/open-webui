<script lang="ts">
    import { toast } from 'svelte-sonner';
    import { onMount, tick, getContext } from 'svelte';
    import { openDB, deleteDB } from 'idb';
    import fileSaver from 'file-saver';
    const { saveAs } = fileSaver;
    import mermaid from 'mermaid'; 

    import { goto } from '$app/navigation';
    import { page } from '$app/stores';
    import { fade } from 'svelte/transition';

    import { getKnowledgeBases } from '$lib/apis/knowledge';
    import { getFunctions } from '$lib/apis/functions';
    import { getModels, getToolServersData, getVersionUpdates } from '$lib/apis';
    import { getAllTags } from '$lib/apis/chats';
    import { getPrompts } from '$lib/apis/prompts';
    import { getTools } from '$lib/apis/tools';
    import { getBanners } from '$lib/apis/configs';
    import { getUserSettings } from '$lib/apis/users';

    import { WEBUI_VERSION } from '$lib/constants';
    import { compareVersion } from '$lib/utils';

    import {
        config,
        user,
        settings, 
        models,
        prompts,
        knowledge,
        tools,
        functions, 
        tags,
        banners,
        showSettings,
        showChangelog,
        temporaryChatEnabled,
        toolServers
    } from '$lib/stores';

    import Sidebar from '$lib/components/layout/Sidebar.svelte';
    import SettingsModal from '$lib/components/chat/SettingsModal.svelte';
    import ChangelogModal from '$lib/components/ChangelogModal.svelte';
    import AccountPending from '$lib/components/layout/Overlay/AccountPending.svelte';
    import UpdateInfoToast from '$lib/components/layout/UpdateInfoToast.svelte';
    import { get } from 'svelte/store'; 
    import Spinner from '$lib/components/common/Spinner.svelte';

    const i18n = getContext('i18n');

    let loaded = false;
    let DB = null;
    let localDBChats = [];
    let version;

    // --- BEGIN: New Shortcut Handling Code ---

    const _KEY_DISPLAY_MODIFIER_CTRL = 'Ctrl/⌘';
    const _KEY_DISPLAY_MODIFIER_SHIFT = 'Shift';
    const _KEY_DISPLAY_MODIFIER_ALT = 'Alt'; // Define if Alt is used in shortcuts

    // These definitions should ideally be shared or consistent with your settings component
    const DEFAULT_SHORTCUT_DEFINITIONS = [
        { id: 'openNewChat', labelKey: 'Open new chat', defaultKeys: [_KEY_DISPLAY_MODIFIER_CTRL, _KEY_DISPLAY_MODIFIER_SHIFT, 'O'], maxParts: 3, type: 'keyboard' },
        { id: 'focusChatInput', labelKey: 'Focus chat input', defaultKeys: [_KEY_DISPLAY_MODIFIER_SHIFT, 'Esc'], maxParts: 3, type: 'keyboard' },
        { id: 'copyLastCodeBlock', labelKey: 'Copy last code block', defaultKeys: [_KEY_DISPLAY_MODIFIER_CTRL, _KEY_DISPLAY_MODIFIER_SHIFT, ';'], maxParts: 3, type: 'keyboard' },
        { id: 'copyLastResponse', labelKey: 'Copy last response', defaultKeys: [_KEY_DISPLAY_MODIFIER_CTRL, _KEY_DISPLAY_MODIFIER_SHIFT, 'C'], maxParts: 3, type: 'keyboard' },
        { id: 'toggleSidebar', labelKey: 'Toggle sidebar', defaultKeys: [_KEY_DISPLAY_MODIFIER_CTRL, _KEY_DISPLAY_MODIFIER_SHIFT, 'S'], maxParts: 3, type: 'keyboard' },
        { id: 'deleteChat', labelKey: 'Delete chat', defaultKeys: [_KEY_DISPLAY_MODIFIER_CTRL, _KEY_DISPLAY_MODIFIER_SHIFT, '⌫/Delete'], maxParts: 3, type: 'keyboard' },
        { id: 'toggleSettings', labelKey: 'Toggle settings', defaultKeys: [_KEY_DISPLAY_MODIFIER_CTRL, '.'], maxParts: 3, type: 'keyboard' },
        { id: 'showShortcuts', labelKey: 'Show shortcuts', defaultKeys: [_KEY_DISPLAY_MODIFIER_CTRL, '/'], maxParts: 3, type: 'keyboard' },
        { id: 'toggleTemporaryChat', labelKey: 'Toggle temporary chat', defaultKeys: [_KEY_DISPLAY_MODIFIER_CTRL, _KEY_DISPLAY_MODIFIER_SHIFT, "'"], maxParts: 3, type: 'keyboard' },
    ];

    async function globalShortcutHandler(event: KeyboardEvent) {
        // Ensure settings are loaded before trying to access shortcuts
        const currentSettings = get(settings);
        if (!currentSettings) return; // Settings not yet available

        const userShortcutsFromSettings = currentSettings.shortcuts || {};

        for (const def of DEFAULT_SHORTCUT_DEFINITIONS) {
            const customKeys = userShortcutsFromSettings[def.id];
            const activeKeyConfig = (customKeys && customKeys.length > 0) ? customKeys : def.defaultKeys;

            // Check if activeKeyConfig is valid (array with items)
            if (!Array.isArray(activeKeyConfig) || activeKeyConfig.length === 0) {
                continue;
            }

            const expectsCtrlOrMeta = activeKeyConfig.includes(_KEY_DISPLAY_MODIFIER_CTRL);
            const expectsShift = activeKeyConfig.includes(_KEY_DISPLAY_MODIFIER_SHIFT);
            const expectsAlt = activeKeyConfig.includes(_KEY_DISPLAY_MODIFIER_ALT);

            const mainKeyFromConfig = activeKeyConfig.find(
                k => k !== _KEY_DISPLAY_MODIFIER_CTRL && k !== _KEY_DISPLAY_MODIFIER_SHIFT && k !== _KEY_DISPLAY_MODIFIER_ALT
            );

            if (!mainKeyFromConfig) {
                 // This might occur if a shortcut is defined as only modifiers, or if activeKeyConfig is unexpectedly empty/malformed.
                // Current default definitions all include a non-modifier key.
                continue;
            }

            const pressedCtrlOrMeta = event.ctrlKey || event.metaKey;
            const pressedShift = event.shiftKey;
            const pressedAlt = event.altKey;

            let normalizedEventKey = event.key;
            if (event.key === "Escape") normalizedEventKey = "Esc";
            else if (event.key === "Backspace" || event.key === "Delete") normalizedEventKey = "⌫/Delete";
            else if (event.key === " ") normalizedEventKey = "Space"; 
            else if (event.key === "Tab") normalizedEventKey = "Tab";  
            else if (event.key === "Enter") normalizedEventKey = "Enter"; 
            else if (event.key.length === 1 && event.key.match(/[a-z]/i)) { 
                normalizedEventKey = event.key.toUpperCase();
            }
       

            if (
                expectsCtrlOrMeta === pressedCtrlOrMeta &&
                expectsShift === pressedShift &&
                expectsAlt === pressedAlt &&
                mainKeyFromConfig === normalizedEventKey
            ) {
                event.preventDefault();
                // console.log(`Executing shortcut: ${def.id} using [${activeKeyConfig.join(', ')}]`);

                switch (def.id) {
                    case 'openNewChat':
                        document.getElementById('sidebar-new-chat-button')?.click();
                        break;
                    case 'focusChatInput':
                        document.getElementById('chat-input')?.focus();
                        break;
                    case 'copyLastCodeBlock':
                        (document.querySelector('button.copy-code-button:last-of-type') as HTMLElement)?.click();
                        break;
                    case 'copyLastResponse':
                         (document.querySelector('button.copy-response-button:last-of-type') as HTMLElement)?.click();
                        break;
                    case 'toggleSidebar':
                        document.getElementById('sidebar-toggle-button')?.click();
                        break;
                    case 'deleteChat':
                        document.getElementById('delete-chat-button')?.click();
                        break;
                    case 'toggleSettings':
                        showSettings.update(s => !s);
                        break;
                    case 'showShortcuts':
                        document.getElementById('show-shortcuts-button')?.click();
                        break;
                    case 'toggleTemporaryChat':
                        temporaryChatEnabled.update(t => !t);
                        await goto('/');
                        setTimeout(() => {
                            document.getElementById('new-chat-button')?.click();
                        }, 0);
                        break;
                }
                return; // Shortcut handled, no need to check further
            }
        }
    }

    // --- END: New Shortcut Handling Code ---


    onMount(async () => {
        if ($user === undefined || $user === null) {
            await goto('/auth');
        } else if (['user', 'admin'].includes($user?.role)) {
            try {
                DB = await openDB('Chats', 1);
                if (DB) {
                    const chats = await DB.getAllFromIndex('chats', 'timestamp');
                    localDBChats = chats.map((item, idx) => chats[chats.length - 1 - idx]);
                    if (localDBChats.length === 0) {
                        await deleteDB('Chats');
                    }
                }
                console.log(DB)
            } catch (error) {
                // IndexedDB Not Found
            }

            const userSettings = await getUserSettings(localStorage.token).catch((error) => {
                console.error(error);
                return null;
            });

            if (userSettings) {
                settings.set(userSettings.ui);
            } else {
                let localStorageSettings = {} as Parameters<(typeof settings)['set']>[0];
                try {
                    localStorageSettings = JSON.parse(localStorage.getItem('settings') ?? '{}');
                } catch (e: unknown) {
                    console.error('Failed to parse settings from localStorage', e);
                }
                settings.set(localStorageSettings);
            }

            // Ensure settings are processed before attaching keydown listener that depends on them
            await tick(); // Wait for settings store to potentially update

            models.set(
                await getModels(
                    localStorage.token,
					$config?.features?.enable_direct_connections && ($settings?.directConnections ?? null)
                )
            );

            banners.set(await getBanners(localStorage.token));
            tools.set(await getTools(localStorage.token));
            toolServers.set(await getToolServersData($i18n, $settings?.toolServers ?? []));
            document.addEventListener('keydown', globalShortcutHandler);


            if ($user?.role === 'admin' && (get(settings)?.showChangelog ?? true)) {
                 // Use get(settings) for potentially updated value
                showChangelog.set(get(settings)?.version !== $config.version);
            }

            if ($user?.permissions?.chat?.temporary ?? true) {
                if ($page.url.searchParams.get('temporary-chat') === 'true') {
                    temporaryChatEnabled.set(true);
                }
                if ($user?.permissions?.chat?.temporary_enforced) {
                    temporaryChatEnabled.set(true);
                }
            }

            if ($user?.role === 'admin') {
                if (localStorage.dismissedUpdateToast) {
                    const dismissedUpdateToast = new Date(Number(localStorage.dismissedUpdateToast));
                    const now = new Date();
                    if (now.getTime() - dismissedUpdateToast.getTime() > 24 * 60 * 60 * 1000) {
                        checkForVersionUpdates();
                    }
                } else {
                    checkForVersionUpdates();
                }
            }
            await tick(); // Final tick for any DOM updates related to loaded data
        }
        loaded = true;
    });

    const checkForVersionUpdates = async () => {
        version = await getVersionUpdates(localStorage.token).catch((error) => {
            console.error("Failed to get version updates", error);
            return {
                current: WEBUI_VERSION,
                latest: WEBUI_VERSION
            };
        });
    };
</script>

<SettingsModal bind:show={$showSettings} />
<ChangelogModal bind:show={$showChangelog} />

{#if version && compareVersion(version.latest, version.current) && ($settings?.showUpdateToast ?? true)}
    <div class=" absolute bottom-8 right-8 z-50" in:fade={{ duration: 100 }}>
        <UpdateInfoToast
            {version}
            on:close={() => {
                localStorage.setItem('dismissedUpdateToast', Date.now().toString());
                version = null;
            }}
        />
    </div>
{/if}

{#if $user}
    <div class="app relative">
        <div
            class=" text-gray-700 dark:text-gray-100 bg-white dark:bg-gray-900 h-screen max-h-[100dvh] overflow-auto flex flex-row justify-end"
        >
            {#if !['user', 'admin'].includes($user?.role)}
                <AccountPending />
            {:else if localDBChats.length > 0}
                <div class="fixed w-full h-full flex z-50">
                    <div
                        class="absolute w-full h-full backdrop-blur-md bg-white/20 dark:bg-gray-900/50 flex justify-center"
                    >
                        <div class="m-auto pb-44 flex flex-col justify-center">
                            <div class="max-w-md">
                                <div class="text-center dark:text-white text-2xl font-medium z-50">
                                    Important Update<br /> Action Required for Chat Log Storage
                                </div>

                                <div class=" mt-4 text-center text-sm dark:text-gray-200 w-full">
                                    {$i18n.t(
                                        "Saving chat logs directly to your browser's storage is no longer supported. Please take a moment to download and delete your chat logs by clicking the button below. Don't worry, you can easily re-import your chat logs to the backend through"
                                    )}
                                    <span class="font-semibold dark:text-white"
                                        >{$i18n.t('Settings')} > {$i18n.t('Chats')} > {$i18n.t('Import Chats')}</span
                                    >. {$i18n.t(
                                        'This ensures that your valuable conversations are securely saved to your backend database. Thank you!'
                                    )}
                                </div>

                                <div class=" mt-6 mx-auto relative group w-fit">
                                    <button
                                        class="relative z-20 flex px-5 py-2 rounded-full bg-white border border-gray-100 dark:border-none hover:bg-gray-100 transition font-medium text-sm"
                                        on:click={async () => {
                                            let blob = new Blob([JSON.stringify(localDBChats)], {
                                                type: 'application/json'
                                            });
                                            saveAs(blob, `chat-export-${Date.now()}.json`);

                                            const tx = DB.transaction('chats', 'readwrite');
                                            await Promise.all([tx.store.clear(), tx.done]);
                                            await deleteDB('Chats');

                                            localDBChats = [];
                                        }}
                                    >
                                        Download & Delete
                                    </button>

                                    <button
                                        class="text-xs text-center w-full mt-2 text-gray-400 underline"
                                        on:click={async () => {
                                            localDBChats = [];
                                        }}>{$i18n.t('Close')}</button
                                    >
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            {/if}

            <Sidebar />

            {#if loaded}
                <slot />
            {:else}
                <div class="w-full flex-1 h-full flex items-center justify-center">
                    <Spinner />
                </div>
            {/if}
        </div>
    </div>
{/if}

<style>
	.loading {
		display: inline-block;
		clip-path: inset(0 1ch 0 0);
		animation: l 1s steps(3) infinite;
		letter-spacing: -0.5px;
	}

	@keyframes l {
		to {
			clip-path: inset(0 -1ch 0 0);
		}
	}

	pre[class*='language-'] {
		position: relative;
		overflow: auto;

		/* make space  */
		margin: 5px 0;
		padding: 1.75rem 0 1.75rem 1rem;
		border-radius: 10px;
	}

	pre[class*='language-'] button {
		position: absolute;
		top: 5px;
		right: 5px;

		font-size: 0.9rem;
		padding: 0.15rem;
		background-color: #828282;

		border: ridge 1px #7b7b7c;
		border-radius: 5px;
		text-shadow: #c4c4c4 0 0 2px;
	}

	pre[class*='language-'] button:hover {
		cursor: pointer;
		background-color: #bcbabb;
	}
</style>
