<script lang="ts">
    import { prompts, settings, user } from '$lib/stores';
    import {
        extractCurlyBraceWords,
        getUserPosition,
        getFormattedDate,
        getFormattedTime,
        getCurrentDateTime,
        getUserTimezone,
        getWeekday
    } from '$lib/utils';
    import { tick, getContext } from 'svelte';
    import { toast } from 'svelte-sonner';

    const i18n = getContext('i18n');

    export let files; // This is passed down but not directly used in confirmPrompt for content modification

    export let prompt = ''; // This is bind:value from MessageInput's RichTextInput
    export let command = ''; // This is the typed command, e.g. "/myPrompt"

    let selectedPromptIdx = 0;
    let filteredPrompts = [];

    $: filteredPrompts = $prompts
        .filter((p) => p.command.toLowerCase().includes(command.toLowerCase().substring(1))) // Match command without '/'
        .sort((a, b) => a.title.localeCompare(b.title));

    $: if (command) {
        selectedPromptIdx = 0;
    }

    export const selectUp = () => {
        selectedPromptIdx = Math.max(0, selectedPromptIdx - 1);
    };

    export const selectDown = () => {
        selectedPromptIdx = Math.min(selectedPromptIdx + 1, filteredPrompts.length - 1);
    };

    const confirmPrompt = async (selectedLibraryPrompt) => {
        let plainTextPromptContent = selectedLibraryPrompt.content;

        // --- Variable Replacements on plainTextPromptContent ---
        if (plainTextPromptContent.includes('{{CLIPBOARD}}')) {
            const clipboardText = await navigator.clipboard.readText().catch((err) => {
                toast.error($i18n.t('Failed to read clipboard contents'));
                return '{{CLIPBOARD}}'; // Keep placeholder if failed
            });
            plainTextPromptContent = plainTextPromptContent.replaceAll('{{CLIPBOARD}}', clipboardText);
            
            // Logic for pasting images from clipboard into the 'files' array (part of MessageInput)
            // This doesn't directly insert images into the RichTextInput content here.
            if ($settings?.richTextInput ?? true) {
                try {
                    const clipboardItems = await navigator.clipboard.read();
                    for (const item of clipboardItems) {
                        for (const type of item.types) {
                            if (type.startsWith('image/')) {
                                const blob = await item.getType(type);
                                const imageUrl = URL.createObjectURL(blob);
                                if (imageUrl) { // Ensure files is a prop that can be updated
                                    files = [ 
                                        ...files,
                                        { type: 'image', url: imageUrl }
                                    ];
                                }
                                break; // Found an image, no need to check other types for this item
                            }
                        }
                    }
                } catch (err) {
                    // Silently fail if clipboard image reading isn't supported or permission denied
                    // console.warn("Could not read image from clipboard", err);
                }
            }
        }

        if (plainTextPromptContent.includes('{{USER_LOCATION}}')) {
            let location;
            try {
                location = await getUserPosition();
            } catch (error) {
                toast.error($i18n.t('Location access not allowed'));
                location = 'LOCATION_UNKNOWN';
            }
            plainTextPromptContent = plainTextPromptContent.replaceAll('{{USER_LOCATION}}', String(location));
        }

        if (plainTextPromptContent.includes('{{USER_NAME}}')) {
            const name = $user?.name || 'User';
            plainTextPromptContent = plainTextPromptContent.replaceAll('{{USER_NAME}}', name);
        }

        if (plainTextPromptContent.includes('{{USER_LANGUAGE}}')) {
            const language = localStorage.getItem('locale') || 'en-US';
            plainTextPromptContent = plainTextPromptContent.replaceAll('{{USER_LANGUAGE}}', language);
        }

        if (plainTextPromptContent.includes('{{CURRENT_DATE}}')) {
            const date = getFormattedDate();
            plainTextPromptContent = plainTextPromptContent.replaceAll('{{CURRENT_DATE}}', date);
        }

        if (plainTextPromptContent.includes('{{CURRENT_TIME}}')) {
            const time = getFormattedTime();
            plainTextPromptContent = plainTextPromptContent.replaceAll('{{CURRENT_TIME}}', time);
        }

        if (plainTextPromptContent.includes('{{CURRENT_DATETIME}}')) {
            const dateTime = getCurrentDateTime();
            plainTextPromptContent = plainTextPromptContent.replaceAll('{{CURRENT_DATETIME}}', dateTime);
        }

        if (plainTextPromptContent.includes('{{CURRENT_TIMEZONE}}')) {
            const timezone = getUserTimezone();
            plainTextPromptContent = plainTextPromptContent.replaceAll('{{CURRENT_TIMEZONE}}', timezone);
        }

        if (plainTextPromptContent.includes('{{CURRENT_WEEKDAY}}')) {
            const weekday = getWeekday();
            plainTextPromptContent = plainTextPromptContent.replaceAll('{{CURRENT_WEEKDAY}}', weekday);
        }
        // --- End Variable Replacements ---

        const commandTypedInInput = command; // This is the `/theCommandName` string

        if ($settings?.richTextInput ?? true) {
            // Convert the plain text (with newlines) to an HTML string with <p> tags for each line.
            const htmlToInsert = plainTextPromptContent
                .split('\n')
                .map(line => {
                    const escapedLine = line
                        .replace(/&/g, '&amp;')
                        .replace(/</g, '&lt;')
                        .replace(/>/g, '&gt;');
                    // Wrap non-empty lines in <p> tags. For "empty" lines in the prompt,
                    // this will result in <p><br></p> if we want to preserve visible empty lines.
                    // Or, if RichTextInput handles <p></p> as a line break, then just <p>${escapedLine}</p>
                    return `<p>${escapedLine || '<br>'}</p>`; // Use <br> for effectively empty paragraphs to maintain space
                })
                .join('');

            let currentRichText = prompt; // Current HTML content from RichTextInput

            // Attempt to remove the typed command (e.g., "/myPrompt") from the current HTML.
            // This is heuristic. A perfect solution would need to parse HTML or use editor's API.
            // Case 1: Command is at the very end of the content: <p>Some text /cmd</p>
            // Case 2: Command is alone in the last paragraph: <p>Some text</p><p>/cmd</p>
            
            // Try removing if the command is the sole content of the last <p> tag
            const commandInLastP = `<p>${commandTypedInInput}</p>`;
            if (currentRichText.endsWith(commandInLastP)) {
                currentRichText = currentRichText.substring(0, currentRichText.length - commandInLastP.length);
            } else {
                // Try removing if command is at the very end of the string (might be inside another tag)
                // This is less robust. A more specific regex might be needed if the structure varies a lot.
                // For simplicity, we'll assume the command is either in its own <p> or simply at the end of text within a <p>.
                const lastPIndex = currentRichText.lastIndexOf('<p>');
                if (lastPIndex !== -1) {
                    const contentOfLastP = currentRichText.substring(lastPIndex);
                    if (contentOfLastP.includes(commandTypedInInput)) {
                        const cleanedContentOfLastP = contentOfLastP.replace(commandTypedInInput, '');
                        // If removing the command leaves an empty <p></p> or <p> </p>, clean it up or ensure it's valid.
                        if (cleanedContentOfLastP === '<p></p>' || cleanedContentOfLastP === '<p> </p>') {
                            currentRichText = currentRichText.substring(0, lastPIndex); // Remove the empty p tag
                        } else {
                            currentRichText = currentRichText.substring(0, lastPIndex) + cleanedContentOfLastP;
                        }
                    }
                }
            }
            // Ensure that if currentRichText became empty, we don't have an empty string before new content.
            // Also, if currentRichText was `<p></p>` and we removed it, then htmlToInsert should just be set.
            if (currentRichText === '<p><br></p>' || currentRichText === '<p></p>') currentRichText = '';


            prompt = currentRichText + htmlToInsert;

        } else {
            // Plain textarea logic
            let currentText = prompt;
            const lastIndex = currentText.lastIndexOf(commandTypedInInput);
            // Ensure command is at the end or followed by only whitespace
            if (lastIndex !== -1 && (lastIndex + commandTypedInInput.length === currentText.length || currentText.substring(lastIndex + commandTypedInInput.length).match(/^\s*$/))) {
                currentText = currentText.substring(0, lastIndex);
            }
            prompt = currentText + plainTextPromptContent;
        }

        await tick();

        const chatInputElement = document.getElementById('chat-input');
        if (chatInputElement) {
            chatInputElement.focus();
            // Auto-scrolling and variable selection for plain textarea
            if (!($settings?.richTextInput ?? true) && chatInputElement.tagName === 'TEXTAREA') {
                const words = extractCurlyBraceWords(prompt);
                if (words.length > 0) {
                    const word = words.at(0);
                    const fullPromptValue = prompt; // Store before temporary change
                    prompt = prompt.substring(0, word.endIndex + 1); // Temporarily shorten for scroll height calc
                    await tick();
                    (chatInputElement as HTMLTextAreaElement).scrollTop = chatInputElement.scrollHeight;
                    prompt = fullPromptValue; // Restore full prompt
                    await tick();
                    (chatInputElement as HTMLTextAreaElement).setSelectionRange(word.startIndex, word.endIndex + 1);
                } else {
                    (chatInputElement as HTMLTextAreaElement).scrollTop = chatInputElement.scrollHeight;
                }
            }
            // For RichTextInput, complex selection of {{variables}} is harder without editor API.
            // Focusing is sufficient for now.
        }
    };
</script>

{#if filteredPrompts.length > 0}
    <div
        id="commands-container"
        class="px-2 mb-2 text-left w-full absolute bottom-0 left-0 right-0 z-10"
    >
        <div class="flex w-full rounded-xl border border-gray-100 dark:border-gray-850">
            <div
                class="max-h-60 flex flex-col w-full rounded-xl bg-white dark:bg-gray-900 dark:text-gray-100"
            >
                <div class="m-1 overflow-y-auto p-1 space-y-0.5 scrollbar-hidden">
                    {#each filteredPrompts as libPrompt, promptIdx}
                        <button
                            class=" px-3 py-1.5 rounded-xl w-full text-left {promptIdx === selectedPromptIdx
                                ? '  bg-gray-50 dark:bg-gray-850 selected-command-option-button'
                                : ''}"
                            type="button"
                            on:click={() => {
                                confirmPrompt(libPrompt); // Pass the selected library prompt object
                            }}
                            on:mousemove={() => {
                                selectedPromptIdx = promptIdx;
                            }}
                            on:focus={() => {}}
                        >
                            <div class=" font-medium text-black dark:text-gray-100">
                                {libPrompt.command}
                            </div>

                            <div class=" text-xs text-gray-600 dark:text-gray-100">
                                {libPrompt.title}
                            </div>
                        </button>
                    {/each}
                </div>

                <div
                    class=" px-2 pt-0.5 pb-1 text-xs text-gray-600 dark:text-gray-100 bg-white dark:bg-gray-900 rounded-b-xl flex items-center space-x-1"
                >
                    <div>
                        <svg
                            xmlns="http://www.w3.org/2000/svg"
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke-width="1.5"
                            stroke="currentColor"
                            class="w-3 h-3"
                        >
                            <path
                                stroke-linecap="round"
                                stroke-linejoin="round"
                                d="m11.25 11.25.041-.02a.75.75 0 0 1 1.063.852l-.708 2.836a.75.75 0 0 0 1.063.853l.041-.021M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9-3.75h.008v.008H12V8.25Z"
                            />
                        </svg>
                    </div>

                    <div class="line-clamp-1">
                        {$i18n.t(
                            'Tip: Update multiple variable slots consecutively by pressing the tab key in the chat input after each replacement.'
                        )}
                    </div>
                </div>
            </div>
        </div>
    </div>
{/if}
