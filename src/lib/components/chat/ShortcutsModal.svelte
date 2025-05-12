<script lang="ts">
    import { getContext } from 'svelte';
    import Modal from '../common/Modal.svelte';
    import { settings } from '$lib/stores'; // <<< ADDED: Import the settings store

    const i18n = getContext('i18n');

    export let show = false;

    // ---VVV--- ADD THIS DYNAMIC LOGIC ---VVV---

    // Consistent modifier key display strings.
    // These should match the values stored in your settings and default definitions.
    const _KEY_DISPLAY_MODIFIER_CTRL = 'Ctrl/⌘';
    const _KEY_DISPLAY_MODIFIER_SHIFT = 'Shift';
    // const _KEY_DISPLAY_MODIFIER_ALT = 'Alt'; // Define if you use Alt consistently

    // Definitions for all shortcuts to be displayed in this modal.
    // - 'id' must match the ID used in $settings.shortcuts and your global shortcut handler.
    // - 'labelKey' is for i18n translation.
    // - 'defaultKeys' is the fallback if the user hasn't customized it.
    // - 'column' helps in organizing the display into two columns as per your original layout.
    const SHORTCUT_DEFINITIONS_FOR_DISPLAY = [
        // Column 1
        { id: 'openNewChat', labelKey: 'Open new chat', defaultKeys: [_KEY_DISPLAY_MODIFIER_CTRL, _KEY_DISPLAY_MODIFIER_SHIFT, 'O'], column: 1 },
        { id: 'focusChatInput', labelKey: 'Focus chat input', defaultKeys: [_KEY_DISPLAY_MODIFIER_SHIFT, 'Esc'], column: 1 },
        { id: 'copyLastCodeBlock', labelKey: 'Copy last code block', defaultKeys: [_KEY_DISPLAY_MODIFIER_CTRL, _KEY_DISPLAY_MODIFIER_SHIFT, ';'], column: 1 },
        { id: 'copyLastResponse', labelKey: 'Copy last response', defaultKeys: [_KEY_DISPLAY_MODIFIER_CTRL, _KEY_DISPLAY_MODIFIER_SHIFT, 'C'], column: 1 },
        { id: 'generatePromptPair', labelKey: 'Generate prompt pair', defaultKeys: [_KEY_DISPLAY_MODIFIER_CTRL, _KEY_DISPLAY_MODIFIER_SHIFT, 'Enter'], column: 1 },

        // Column 2
        { id: 'toggleSettings', labelKey: 'Toggle settings', defaultKeys: [_KEY_DISPLAY_MODIFIER_CTRL, '.'], column: 2 },
        { id: 'toggleSidebar', labelKey: 'Toggle sidebar', defaultKeys: [_KEY_DISPLAY_MODIFIER_CTRL, _KEY_DISPLAY_MODIFIER_SHIFT, 'S'], column: 2 },
        { id: 'deleteChat', labelKey: 'Delete chat', defaultKeys: [_KEY_DISPLAY_MODIFIER_CTRL, _KEY_DISPLAY_MODIFIER_SHIFT, '⌫/Delete'], column: 2 },
        { id: 'showShortcuts', labelKey: 'Show shortcuts', defaultKeys: [_KEY_DISPLAY_MODIFIER_CTRL, '/'], column: 2 },
        { id: 'toggleTemporaryChat', labelKey: 'Toggle temporary chat', defaultKeys: [_KEY_DISPLAY_MODIFIER_CTRL, _KEY_DISPLAY_MODIFIER_SHIFT, "'"], column: 2 },
    ];

    let column1Shortcuts: { id: string, label: string, keys: string[] }[] = [];
    let column2Shortcuts: { id: string, label: string, keys: string[] }[] = [];

    // This is a Svelte reactive statement. It will re-run whenever $settings changes.
    $: {
        const currentCustomShortcuts = $settings.shortcuts || {}; // Get user's custom shortcuts
        
        const allProcessedShortcuts = SHORTCUT_DEFINITIONS_FOR_DISPLAY.map(def => {
            const customKeysArray = currentCustomShortcuts[def.id];
            
            // Use custom keys if they are a valid array with content; otherwise, use default keys.
            const effectiveKeys = (Array.isArray(customKeysArray) && customKeysArray.length > 0) 
                                  ? customKeysArray 
                                  : def.defaultKeys;
            return {
                id: def.id, // Pass id for keyed #each
                label: $i18n.t(def.labelKey), // Translate the label
                keys: effectiveKeys,
                column: def.column
            };
        });

        column1Shortcuts = allProcessedShortcuts.filter(s => s.column === 1);
        column2Shortcuts = allProcessedShortcuts.filter(s => s.column === 2);
    }
    // ---^^^--- END OF DYNAMIC LOGIC ---^^^---
</script>

<Modal bind:show>
    <div class="text-gray-700 dark:text-gray-100">
        <div class=" flex justify-between dark:text-gray-300 px-5 pt-4">
            <div class=" text-lg font-medium self-center">{$i18n.t('Keyboard shortcuts')}</div>
            <button
                class="self-center"
                on:click={() => {
                    show = false;
                }}
            >
                <svg
                    xmlns="http://www.w3.org/2000/svg"
                    viewBox="0 0 20 20"
                    fill="currentColor"
                    class="w-5 h-5"
                >
                    <path
                        d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z"
                    />
                </svg>
            </button>
        </div>

        <div class="flex flex-col md:flex-row w-full p-5 md:space-x-4 dark:text-gray-200">
            <div class="flex flex-col space-y-3 w-full self-start mb-4 md:mb-0">
                {#each column1Shortcuts as shortcut (shortcut.id)}
                    <div class="w-full flex justify-between items-center">
                        <div class="text-sm">{shortcut.label}</div>
                        <div class="flex space-x-1 text-xs">
                            {#each shortcut.keys as keyPart, i (shortcut.id + '-' + i)}
                                <div
                                    class="h-fit py-1 px-2 flex items-center justify-center rounded-sm border border-black/10 capitalize text-gray-600 dark:border-white/10 dark:text-gray-300"
                                >
                                    {keyPart}
                                </div>
                            {/each}
                        </div>
                    </div>
                {/each}
            </div>

            <div class="flex flex-col space-y-3 w-full self-start">
                {#each column2Shortcuts as shortcut (shortcut.id)}
                    <div class="w-full flex justify-between items-center">
                        <div class="text-sm">{shortcut.label}</div>
                        <div class="flex space-x-1 text-xs">
                            {#each shortcut.keys as keyPart, i (shortcut.id + '-' + i)} 
                                <div
                                    class="h-fit py-1 px-2 flex items-center justify-center rounded-sm border border-black/10 capitalize text-gray-600 dark:border-white/10 dark:text-gray-300"
                                >
                                    {keyPart}
                                </div>
                            {/each}
                        </div>
                    </div>
                {/each}
            </div>
        </div>

        <div class=" flex justify-between dark:text-gray-300 px-5">
            <div class=" text-lg font-medium self-center">{$i18n.t('Input commands')}</div>
        </div>

        <div class="flex flex-col md:flex-row w-full p-5 md:space-x-4 dark:text-gray-200">
            <div class=" flex flex-col w-full sm:flex-row sm:justify-center sm:space-x-6">
                <div class="flex flex-col space-y-3 w-full self-start">
                    <div class="w-full flex justify-between items-center">
                        <div class=" text-sm">
                            {$i18n.t('Attach file from knowledge')}
                        </div>
                        <div class="flex space-x-1 text-xs">
                            <div class="h-fit py-1 px-2 flex items-center justify-center rounded-sm border border-black/10 capitalize text-gray-600 dark:border-white/10 dark:text-gray-300">#</div>
                        </div>
                    </div>
                    <div class="w-full flex justify-between items-center">
                        <div class=" text-sm">
                            {$i18n.t('Add custom prompt')}
                        </div>
                        <div class="flex space-x-1 text-xs">
                            <div class="h-fit py-1 px-2 flex items-center justify-center rounded-sm border border-black/10 capitalize text-gray-600 dark:border-white/10 dark:text-gray-300">/</div>
                        </div>
                    </div>
                    <div class="w-full flex justify-between items-center">
                        <div class=" text-sm">
                            {$i18n.t('Talk to model')}
                        </div>
                        <div class="flex space-x-1 text-xs">
                            <div class="h-fit py-1 px-2 flex items-center justify-center rounded-sm border border-black/10 capitalize text-gray-600 dark:border-white/10 dark:text-gray-300">@</div>
                        </div>
                    </div>
                    <div class="w-full flex justify-between items-center">
                        <div class=" text-sm">
                            {$i18n.t('Accept autocomplete generation / Jump to prompt variable')}
                        </div>
                        <div class="flex space-x-1 text-xs">
                            <div class="h-fit py-1 px-2 flex items-center justify-center rounded-sm border border-black/10 capitalize text-gray-600 dark:border-white/10 dark:text-gray-300">TAB</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</Modal>

<style>
    input::-webkit-outer-spin-button,
    input::-webkit-inner-spin-button {
        /* display: none; <- Crashes Chrome on hover */
        -webkit-appearance: none;
        margin: 0; /* <-- Apparently some margin are still there even though it's hidden */
    }

    .tabs::-webkit-scrollbar {
        display: none; /* for Chrome, Safari and Opera */
    }

    .tabs {
        -ms-overflow-style: none; /* IE and Edge */
        scrollbar-width: none; /* Firefox */
    }

    input[type='number'] {
        -moz-appearance: textfield; /* Firefox */
    }
</style>