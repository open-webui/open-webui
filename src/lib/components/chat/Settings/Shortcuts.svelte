
<script lang="ts">
    import { getContext, onMount, createEventDispatcher, tick } from 'svelte';
    import { settings } from '$lib/stores';
    import { toast } from 'svelte-sonner';

    const i18n = getContext('i18n');
    const dispatch = createEventDispatcher();

    export let saveSettings: Function;

    interface ShortcutKeyPart {
        id: string;
        value: string;
    }

    interface ConfigurableShortcut {
        id:string;
        labelKey: string;
        defaultKeys: string[];
        currentKeys: ShortcutKeyPart[];
        maxParts: number;
        type: 'keyboard';
    }

    let configuredShortcuts: ConfigurableShortcut[] = [];

    const shortcutDefinitionsSource: Omit<ConfigurableShortcut, 'currentKeys'>[] = [
        { id: 'openNewChat', labelKey: 'Open new chat', defaultKeys: ['Ctrl/⌘', 'Shift', 'O'], maxParts: 3, type: 'keyboard' },
        { id: 'focusChatInput', labelKey: 'Focus chat input', defaultKeys: ['Shift', 'Esc'], maxParts: 3, type: 'keyboard' },
        { id: 'copyLastCodeBlock', labelKey: 'Copy last code block', defaultKeys: ['Ctrl/⌘', 'Shift', ';'], maxParts: 3, type: 'keyboard' },
        { id: 'copyLastResponse', labelKey: 'Copy last response', defaultKeys: ['Ctrl/⌘', 'Shift', 'C'], maxParts: 3, type: 'keyboard' },
        { id: 'toggleSidebar', labelKey: 'Toggle sidebar', defaultKeys: ['Ctrl/⌘', 'Shift', 'S'], maxParts: 3, type: 'keyboard' },
        { id: 'deleteChat', labelKey: 'Delete chat', defaultKeys: ['Ctrl/⌘', 'Shift', '⌫/Delete'], maxParts: 3, type: 'keyboard' },
        { id: 'toggleSettings', labelKey: 'Toggle settings', defaultKeys: ['Ctrl/⌘', '.'], maxParts: 3, type: 'keyboard' },
        { id: 'showShortcuts', labelKey: 'Show shortcuts', defaultKeys: ['Ctrl/⌘', '/'], maxParts: 3, type: 'keyboard' },
        { id: 'toggleTemporaryChat', labelKey: 'Toggle temporary chat', defaultKeys: ['Ctrl/⌘', 'Shift', "'"], maxParts: 3, type: 'keyboard' },
    ];

    const keyDisplayMap: { [key: string]: string } = {
        Control: 'Ctrl/⌘', Meta: 'Ctrl/⌘', Shift: 'Shift', Alt: 'Alt',
        Escape: 'Esc', " ": 'Space', ArrowUp: '↑', ArrowDown: '↓',
        ArrowLeft: '←', ArrowRight: '→', Enter: 'Enter', Tab: 'Tab',
        Backspace: '⌫/Delete', Delete: '⌫/Delete',
    };

    const allowedFirstKeys: Set<string> = new Set([
        'Ctrl/⌘', 'Shift', 'Alt', 'Esc', 'Space', '↑', '↓', '←', '→',
        'Enter', 'Tab', '⌫/Delete',
        'F1', 'F2', 'F3', 'F4', 'F5', 'F6', 'F7', 'F8', 'F9', 'F10', 'F11', 'F12'
    ]);

    function isAllowedAsFirstKey(key: string): boolean {
        if (!key) return false;
        return allowedFirstKeys.has(key);
    }

    function getInitialDisplayKeys(def: Omit<ConfigurableShortcut, 'currentKeys'>, savedKeys: string[] | undefined): string[] {
        let effectiveKeys = (savedKeys && savedKeys.length > 0) ? savedKeys : def.defaultKeys;
        if (effectiveKeys.length > def.maxParts) {
            effectiveKeys = effectiveKeys.slice(0, def.maxParts);
        }

        let initialKeys: string[] = [];
        if (def.maxParts === 2) {
            initialKeys = [effectiveKeys[0] || '', effectiveKeys[1] || ''];
        } else if (def.maxParts === 3) {
            if (effectiveKeys.length === 3) {
                initialKeys = effectiveKeys;
            } else { 
                initialKeys = [effectiveKeys[0] || '', effectiveKeys[1] || ''];
            }
        } else { 
             initialKeys = effectiveKeys.slice();
             while(initialKeys.length < def.maxParts && initialKeys.length < 2) {
                 initialKeys.push('');
             }
        }
        return initialKeys;
    }

    onMount(() => {
        const savedShortcuts = $settings.shortcuts || {};
        configuredShortcuts = shortcutDefinitionsSource.map(def => {
            const initialDisplayValues = getInitialDisplayKeys(def, savedShortcuts[def.id]);
            const currentKeyParts = initialDisplayValues.map(k => ({ id: crypto.randomUUID(), value: k }));
            return { ...def, currentKeys: currentKeyParts };
        });
    });

    const addKeyInput = async (shortcutId: string) => {
        const shortcutIndex = configuredShortcuts.findIndex(sc => sc.id === shortcutId);
        if (shortcutIndex === -1) return;
        const shortcut = configuredShortcuts[shortcutIndex];

        if (shortcut.currentKeys.length === 2 && shortcut.maxParts > 2) {
            const newKeyIndex = shortcut.currentKeys.length;
            shortcut.currentKeys = [...shortcut.currentKeys, { id: crypto.randomUUID(), value: '' }];
            configuredShortcuts = [...configuredShortcuts];
            await tick();
            const newInputId = `shortcut-input-${shortcutId}-${newKeyIndex}`;
            (document.getElementById(newInputId) as HTMLInputElement | null)?.focus();
        }
    };

    const removeKeyInput = (shortcutId: string, partIndex: number) => {
        const shortcutIndex = configuredShortcuts.findIndex(sc => sc.id === shortcutId);
        if (shortcutIndex === -1) return;
        const shortcut = configuredShortcuts[shortcutIndex];

        if (partIndex === 2 && shortcut.currentKeys.length === 3) {
            shortcut.currentKeys.splice(partIndex, 1);
            shortcut.currentKeys = [...shortcut.currentKeys];
            configuredShortcuts = [...configuredShortcuts];
        }
    };

    const recordKey = (event: KeyboardEvent, shortcutId: string, partIndex: number) => {
        event.preventDefault();
        const shortcut = configuredShortcuts.find(sc => sc.id === shortcutId);
        if (!shortcut || partIndex >= shortcut.currentKeys.length) return;

        const currentKeyValue = shortcut.currentKeys[partIndex].value;
        let keyValueToSet: string | undefined = undefined;
        const pressedKey = event.key;

        if (pressedKey === 'Backspace' || pressedKey === 'Delete') {
            keyValueToSet = (currentKeyValue === keyDisplayMap.Backspace) ? '' : keyDisplayMap.Backspace;
        } else if (pressedKey === 'Escape') {
            keyValueToSet = '';
        } else if (keyDisplayMap[pressedKey]) {
            keyValueToSet = keyDisplayMap[pressedKey];
        } else if (pressedKey.length === 1) {
            keyValueToSet = pressedKey.match(/[a-z]/i) ? pressedKey.toUpperCase() : pressedKey;
        } else if (/^F([1-9]|1[0-2])$/.test(pressedKey)) {
            keyValueToSet = pressedKey;
        }

        if (keyValueToSet !== undefined) {
            if (partIndex === 0 && keyValueToSet !== '' && !isAllowedAsFirstKey(keyValueToSet)) {
                toast.error($i18n.t('The first key of a shortcut must be a modifier (e.g., Ctrl/⌘, Shift, Alt) or a special key (e.g., Esc, F1-F12). "{{key}}" is not allowed as the first key.', { key: keyValueToSet }));
                shortcut.currentKeys[partIndex].value = ''; 
                configuredShortcuts = [...configuredShortcuts]; 
                return; 
            }

            shortcut.currentKeys[partIndex].value = keyValueToSet;
            configuredShortcuts = [...configuredShortcuts];

            if (keyValueToSet !== '' && partIndex < shortcut.currentKeys.length - 1) {
                const nextInputId = `shortcut-input-${shortcutId}-${partIndex + 1}`;
                (document.getElementById(nextInputId) as HTMLInputElement | null)?.focus();
            } else if (keyValueToSet !== '') {
                (event.target as HTMLInputElement).blur();
            }
        }
    };

    const getCleanedKeys = (keyParts: ShortcutKeyPart[]): string[] => {
        return keyParts.map(kp => kp.value.trim()).filter(k => k !== '');
    };

    const normalizeKeyCombination = (keys: string[]): string => {
        return keys.length > 0 ? keys.map(k => k.toLowerCase()).sort().join('+') : '';
    };

    const updateShortcutsHandler = async () => {
        const newSettings: { [key: string]: string[] } = {};
        const keyMap = new Map<string, string>();
        let errorOccurred = false;
        // Create a deep copy for temporary modifications and UI updates if errors occur
        let tempConfigs = JSON.parse(JSON.stringify(configuredShortcuts)) as ConfigurableShortcut[];

        for (let i = 0; i < tempConfigs.length; i++) {
            const currentTempConfig = tempConfigs[i];
            const originalDef = shortcutDefinitionsSource.find(def => def.id === currentTempConfig.id)!;
            const cleanedKeysArray = getCleanedKeys(currentTempConfig.currentKeys);

            let finalKeysToSave: string[];

            if (cleanedKeysArray.length === 0) { // All inputs for this specific shortcut are empty
                // User intends to revert to default.
                finalKeysToSave = [...originalDef.defaultKeys];
                // Update currentKeys display in tempConfigs to reflect default for UI consistency
                const defaultDisplayValues = getInitialDisplayKeys(originalDef, undefined);
                tempConfigs[i].currentKeys = defaultDisplayValues.map(k => ({ id: crypto.randomUUID(), value: k }));
            } else {
                // At least one input for this shortcut is filled.
                // New Validation: Check if ALL displayed inputs for this shortcut are actually filled.
                const hasEmptyVisiblePart = currentTempConfig.currentKeys.some(part => part.value.trim() === '');
                if (hasEmptyVisiblePart) {
                    toast.error($i18n.t('Shortcut "{{label}}" has an unfilled key. Please fill all displayed key parts or clear all of them to use the default.', {
                        label: $i18n.t(originalDef.labelKey)
                    }));
                    errorOccurred = true;
                    break; 
                }

                // All displayed parts are filled. `cleanedKeysArray` now accurately represents all keys.
                // Validation 1 (First key type):
                const firstKey = cleanedKeysArray[0]; // `cleanedKeysArray` is guaranteed non-empty here
                if (!isAllowedAsFirstKey(firstKey)) {
                    toast.error($i18n.t('Shortcut "{{label}}" cannot start with the key "{{key}}". The first key must be a modifier (e.g., Ctrl/⌘, Shift, Alt) or a special key (e.g., Esc, F1-F12).', {
                        label: $i18n.t(originalDef.labelKey),
                        key: firstKey
                    }));
                    errorOccurred = true;
                    break;
                }

                // Validation 2 (Minimum number of keys for these specific shortcuts):
                if (cleanedKeysArray.length < 2) { 
                    toast.error($i18n.t('Shortcut "{{label}}" must have at least 2 keys if partially configured. You provided {{count}} key(s). Clear all inputs to use its default ({{defaultDisplay}}).', {
                        label: $i18n.t(originalDef.labelKey),
                        count: cleanedKeysArray.length,
                        defaultDisplay: originalDef.defaultKeys.join(' + ')
                    }));
                    errorOccurred = true;
                    break;
                }
                finalKeysToSave = cleanedKeysArray;
            }

            newSettings[currentTempConfig.id] = finalKeysToSave;

            if (finalKeysToSave.length > 0) { // Should always be true if we reach here
                const norm = normalizeKeyCombination(finalKeysToSave);
                if (keyMap.has(norm)) {
                    const existingDef = shortcutDefinitionsSource.find(def => def.id === keyMap.get(norm))!;
                    toast.error($i18n.t('Duplicate shortcut: "{{key}}" is used for both "{{action1}}" and "{{action2}}".', {
                        key: finalKeysToSave.join(' + '),
                        action1: $i18n.t(existingDef.labelKey),
                        action2: $i18n.t(originalDef.labelKey)
                    }));
                    errorOccurred = true;
                    break;
                }
                keyMap.set(norm, currentTempConfig.id);
            }
        }
        
        // Update the main configuredShortcuts to reflect any changes made in tempConfigs (e.g., reversion to default display)
        // This ensures UI consistency if an error occurred and we bailed, or on successful save.
        configuredShortcuts = [...tempConfigs];

        if (errorOccurred) return;

        await saveSettings({ shortcuts: newSettings });
        dispatch('save');
        toast.success($i18n.t('Shortcuts saved successfully!'));
    };

    const resetShortcutToDefault = (shortcutId: string) => {
        const index = configuredShortcuts.findIndex(sc => sc.id === shortcutId);
        if (index === -1) return;
        const def = shortcutDefinitionsSource.find(d => d.id === shortcutId)!;

        const initialDisplayValues = getInitialDisplayKeys(def, undefined);
        configuredShortcuts[index].currentKeys = initialDisplayValues.map(k => ({ id: crypto.randomUUID(), value: k }));
        configuredShortcuts = [...configuredShortcuts]; // Trigger Svelte reactivity
        toast.info($i18n.t('Shortcut "{{label}}" reset to default ({{defaultKeysDisplay}}).', {
            label: $i18n.t(def.labelKey),
            defaultKeysDisplay: def.defaultKeys.join(' + ')
        }));
    };

</script>

<form class="flex flex-col h-full justify-between space-y-3 text-sm" on:submit|preventDefault={updateShortcutsHandler}>
    <div class="space-y-6 overflow-y-auto max-h-[28rem] lg:max-h-full pr-2">
        <div>
            <h3 class="text-lg font-medium mb-3 dark:text-gray-300">{$i18n.t('Keyboard shortcuts')}</h3>
            <div class="space-y-3">
                {#each configuredShortcuts as shortcut (shortcut.id)}
                    <div class="w-full flex flex-col sm:flex-row justify-between sm:items-center">
                        <div class="text-sm mb-1 sm:mb-0 dark:text-gray-200 min-w-[180px] sm:mr-2">{$i18n.t(shortcut.labelKey)}</div>
                        <div class="flex items-center space-x-1 text-xs flex-wrap">
                            {#each shortcut.currentKeys as keyPart, i (keyPart.id)}
                                <div class="flex items-center relative mr-1 mb-1"> 
                                    <input
                                        type="text"
                                        readonly
                                        id={`shortcut-input-${shortcut.id}-${i}`}
                                        value={keyPart.value}
                                        on:keydown={(e) => recordKey(e, shortcut.id, i)}
                                        placeholder={$i18n.t('Key {{num}}', {num: i + 1})}
                                        class="h-fit py-1 px-2 w-[5.5rem] text-center rounded-sm border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-200 focus:ring-2 focus:ring-blue-500 outline-none"
                                        aria-label={`Shortcut part ${i+1} for ${$i18n.t(shortcut.labelKey)}`}
                                    />
                                    {#if i === 2 && shortcut.currentKeys.length === 3} 
                                        <button
                                            type="button"
                                            on:click={() => removeKeyInput(shortcut.id, i)}
                                            title={$i18n.t('Remove third key')}
                                            class="p-0.5 rounded-full hover:bg-gray-300 dark:hover:bg-gray-500 transition-colors text-red-500 absolute -top-1.5 -right-1.5 z-10 bg-white dark:bg-gray-800 border dark:border-gray-600 shadow"
                                            aria-label={`Remove third key for ${$i18n.t(shortcut.labelKey)}`}
                                        >
                                            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" class="w-3 h-3">
                                                <path fill-rule="evenodd" d="M3 8a.5.5 0 01.5-.5h9a.5.5 0 010 1H3.5A.5.5 0 013 8z" clip-rule="evenodd" />
                                            </svg>
                                        </button>
                                    {/if}
                                </div>
                            {/each}

                            {#if shortcut.currentKeys.length === 2 && shortcut.maxParts > 2}
                                <button
                                    type="button"
                                    on:click={() => addKeyInput(shortcut.id)}
                                    title={$i18n.t('Add third key')}
                                    class="p-1 rounded hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors text-green-500 mr-1 mb-1 flex items-center justify-center w-7 h-7 border border-gray-300 dark:border-gray-600"
                                    aria-label={`Add third key for ${$i18n.t(shortcut.labelKey)}`}
                                >
                                

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-4 h-4">

<path d="M10.75 4.75a.75.75 0 00-1.5 0v4.5h-4.5a.75.75 0 000 1.5h4.5v4.5a.75.75 0 001.5 0v-4.5h4.5a.75.75 0 000-1.5h-4.5v-4.5z" />

</svg>
                                </button>
                            {/if}
                             <button
                                type="button"
                                on:click={() => resetShortcutToDefault(shortcut.id)}
                                title={$i18n.t('Reset to default')}
                                class="p-1.5 rounded hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors mb-1 flex items-center justify-center w-7 h-7 border border-gray-300 dark:border-gray-600"
                                aria-label={`Reset shortcut for ${$i18n.t(shortcut.labelKey)} to default`}
                            >
                            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" class="w-4 h-4 text-gray-500 dark:text-gray-400">
                                <path d="M20 8c-1.535-2.788-4.467-4.676-7.837-4.676-4.97 0-9 4.03-9 9s4.03 9 9 9c3.97 0 7.337-2.573 8.544-6.141" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
                                <path d="M20 2v6h-6" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
                              </svg>
                            </button>
                        </div>
                    </div>
                {/each}
            </div>
        </div>
    </div>

    <div class="flex justify-end text-sm font-medium mt-4">
        <button
            class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full"
            type="submit"
        >
            {$i18n.t('Save')}
        </button>
    </div>
</form>

<style>
    input::-webkit-outer-spin-button,
    input::-webkit-inner-spin-button {
        -webkit-appearance: none;
        margin: 0;
    }
    input[type='number'] {
        -moz-appearance: textfield; /* Firefox */
    }
</style>
