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

    export let files;

    export let prompt = ''; // Bound value from MessageInput's RichTextInput (HTML string)
    export let command = ''; // Typed command from Commands.svelte (e.g., "/myPrompt" or "/myPrompt</p>")

    let selectedPromptIdx = 0;
    let filteredPrompts = [];

    // Filter prompts based on the command name (text after the initial /, #, or @)
    $: {
        if (command && command.length > 1) {
            const commandName = command.substring(1).toLowerCase();
            // Handle cases where command might have trailing HTML (e.g. "/mycmd</p>")
            const cleanedCommandName = commandName.replace(/<\/?p>/gi, '').trim();

            filteredPrompts = $prompts
                .filter((p) => p.command.toLowerCase().includes(cleanedCommandName))
                .sort((a, b) => a.title.localeCompare(b.title));
        } else {
            filteredPrompts = [];
        }
    }

    $: if (command) {
        selectedPromptIdx = 0; // Reset selection when command changes
    }

    export const selectUp = () => {
        selectedPromptIdx = Math.max(0, selectedPromptIdx - 1);
    };

    export const selectDown = () => {
        selectedPromptIdx = Math.min(selectedPromptIdx + 1, filteredPrompts.length - 1);
    };

    const confirmPrompt = async (selectedLibraryPrompt) => {
        let plainTextPromptContent = selectedLibraryPrompt.content;

        // --- Variable Replacements ---
        if (plainTextPromptContent.includes('{{CLIPBOARD}}')) {
            const clipboardText = await navigator.clipboard.readText().catch((err) => {
                toast.error($i18n.t('Failed to read clipboard contents'));
                return '{{CLIPBOARD}}'; // Retain placeholder if read fails
            });
            plainTextPromptContent = plainTextPromptContent.replaceAll('{{CLIPBOARD}}', clipboardText);

            if ($settings?.richTextInput ?? true) {
                try {
                    const clipboardItems = await navigator.clipboard.read();
                    for (const item of clipboardItems) {
                        for (const type of item.types) {
                            if (type.startsWith('image/')) {
                                const blob = await item.getType(type);
                                const imageUrl = URL.createObjectURL(blob);
                                if (imageUrl) {
                                    files = [...files, { type: 'image', url: imageUrl }];
                                }
                                break; // Processed one image item
                            }
                        }
                    }
                } catch (err) {
                    // console.warn("Could not read image from clipboard", err); // Optional: Log for debugging
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
            plainTextPromptContent = plainTextPromptContent.replaceAll('{{USER_NAME}}', $user?.name || 'User');
        }
        if (plainTextPromptContent.includes('{{USER_LANGUAGE}}')) {
            plainTextPromptContent = plainTextPromptContent.replaceAll(
                '{{USER_LANGUAGE}}',
                localStorage.getItem('locale') || 'en-US'
            );
        }
        if (plainTextPromptContent.includes('{{CURRENT_DATE}}')) {
            plainTextPromptContent = plainTextPromptContent.replaceAll(
                '{{CURRENT_DATE}}',
                getFormattedDate()
            );
        }
        if (plainTextPromptContent.includes('{{CURRENT_TIME}}')) {
            plainTextPromptContent = plainTextPromptContent.replaceAll(
                '{{CURRENT_TIME}}',
                getFormattedTime()
            );
        }
        if (plainTextPromptContent.includes('{{CURRENT_DATETIME}}')) {
            plainTextPromptContent = plainTextPromptContent.replaceAll(
                '{{CURRENT_DATETIME}}',
                getCurrentDateTime()
            );
        }
        if (plainTextPromptContent.includes('{{CURRENT_TIMEZONE}}')) {
            plainTextPromptContent = plainTextPromptContent.replaceAll(
                '{{CURRENT_TIMEZONE}}',
                getUserTimezone()
            );
        }
        if (plainTextPromptContent.includes('{{CURRENT_WEEKDAY}}')) {
            plainTextPromptContent = plainTextPromptContent.replaceAll(
                '{{CURRENT_WEEKDAY}}',
                getWeekday()
            );
        }
        // --- End Variable Replacements ---

        const typedCommandString = command; // Raw command string from input, may include HTML fragments

        if ($settings?.richTextInput ?? true) {
            // Convert plain text prompt content to HTML, wrapping each line in <p> tags
            const htmlToInsert = plainTextPromptContent
                .split('\n')
                .map((line) => {
                    const escapedLine = line
                        .replace(/&/g, '&amp;')
                        .replace(/</g, '&lt;')
                        .replace(/>/g, '&gt;');
                    return `<p>${escapedLine || '<br>'}</p>`; // Use <br> for empty lines to preserve space
                })
                .join('');

            let currentRichText = prompt; // Current HTML content from RichTextInput

            // Remove the typed command string from the RichTextInput's HTML content.
            // Normalizes the command and attempts various patterns for robust removal.
            let textToReplace = typedCommandString;
            if (textToReplace.charAt(0).match(/[\/\#\@]/)) {
                // Extract the core command (e.g., "/cmd") stripping any HTML
                let coreCommand =
                    textToReplace.charAt(0) +
                    textToReplace.substring(1).replace(/<[^>]*>?/gm, '').trim();

                const patterns = [
                    `<p>${coreCommand}</p>`, // e.g., <p>/cmd</p>
                    coreCommand + '</p>', // e.g., /cmd</p> (part of a larger paragraph)
                    coreCommand // e.g., /cmd (plain text or at the end of non-p content)
                ];

                let replaced = false;
                for (const pattern of patterns) {
                    if (currentRichText.endsWith(pattern)) {
                        currentRichText = currentRichText.substring(0, currentRichText.length - pattern.length);
                        replaced = true;
                        break;
                    }
                }

                // More general removal if the command is within the last <p> tag's content
                if (!replaced) {
                    const lastPTagOpenIndex = currentRichText.lastIndexOf('<p>');
                    if (lastPTagOpenIndex !== -1) {
                        let contentAfterLastP = currentRichText.substring(lastPTagOpenIndex);
                        if (contentAfterLastP.includes(coreCommand)) {
                            contentAfterLastP = contentAfterLastP.replace(coreCommand, '');
                            currentRichText = currentRichText.substring(0, lastPTagOpenIndex) + contentAfterLastP;
                            replaced = true;
                        }
                    }
                }
                // Final attempt if currentRichText is just the core command without HTML
                if (!replaced && currentRichText === coreCommand) {
                    currentRichText = '';
                    replaced = true;
                }
            } else {
                // Fallback for commands not starting with /#@ (should be rare if Prompts.svelte is visible)
                if (currentRichText.endsWith(typedCommandString)) {
                    currentRichText = currentRichText.substring(
                        0,
                        currentRichText.length - typedCommandString.length
                    );
                } else {
                    // Broader replacement, use with caution as it might affect unintended parts
                    currentRichText = currentRichText.replace(typedCommandString, '');
                }
            }

            // Clean up any remaining empty/placeholder HTML paragraphs
            if (
                currentRichText === '<p></p>' ||
                currentRichText === '<p><br></p>' ||
                currentRichText === '<p>&nbsp;</p>' ||
                currentRichText === '<p>' // Dangling open <p> tag
            ) {
                currentRichText = '';
            } else {
                // Remove trailing empty paragraphs that might have been left after command removal
                while (
                    currentRichText.endsWith('<p></p>') ||
                    currentRichText.endsWith('<p><br></p>') ||
                    currentRichText.endsWith('<p>&nbsp;</p>')
                ) {
                    if (currentRichText.endsWith('<p></p>'))
                        currentRichText = currentRichText.substring(0, currentRichText.length - '<p></p>'.length);
                    else if (currentRichText.endsWith('<p><br></p>'))
                        currentRichText = currentRichText.substring(
                            0,
                            currentRichText.length - '<p><br></p>'.length
                        );
                    else if (currentRichText.endsWith('<p>&nbsp;</p>'))
                        currentRichText = currentRichText.substring(
                            0,
                            currentRichText.length - '<p>&nbsp;</p>'.length
                        );
                    else break;
                }
            }

            prompt = currentRichText + htmlToInsert;
        } else {
            // Plain textarea logic
            let currentText = prompt;
            const lastIndex = currentText.lastIndexOf(typedCommandString);
            if (
                lastIndex !== -1 &&
                (lastIndex + typedCommandString.length === currentText.length ||
                    currentText.substring(lastIndex + typedCommandString.length).match(/^\s*$/))
            ) {
                currentText = currentText.substring(0, lastIndex);
            }
            prompt = currentText + plainTextPromptContent;
        }

        await tick();
        const chatInputElement = document.getElementById('chat-input');
        if (chatInputElement) {
            chatInputElement.focus();

            // Handle variable selection for plain textareas after content insertion
            if (!($settings?.richTextInput ?? true) && chatInputElement.tagName === 'TEXTAREA') {
                const words = extractCurlyBraceWords(prompt);
                if (words.length > 0) {
                    const word = words.at(0);
                    const fullPromptValue = prompt;
                    // Temporarily adjust prompt for scroll height calculation and then restore
                    prompt = prompt.substring(0, word.endIndex + 1);
                    await tick();
                    (chatInputElement as HTMLTextAreaElement).scrollTop = chatInputElement.scrollHeight;
                    prompt = fullPromptValue;
                    await tick();
                    (chatInputElement as HTMLTextAreaElement).setSelectionRange(
                        word.startIndex,
                        word.endIndex + 1
                    );
                } else {
                    (chatInputElement as HTMLTextAreaElement).scrollTop = chatInputElement.scrollHeight;
                }
            }
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
                                ? 'bg-gray-50 dark:bg-gray-850 selected-command-option-button'
                                : ''}"
                            type="button"
                            on:click={() => {
                                confirmPrompt(libPrompt);
                            }}
                            on:mousemove={() => {
                                selectedPromptIdx = promptIdx;
                            }}
                            on:focus={() => {
                                // Explicit empty on:focus to prevent default browser focus styling interfering with selection
                            }}
                        >
                            <div class="font-medium text-black dark:text-gray-100">
                                {libPrompt.command} {/* Clean command name like "myPrompt" */}
                            </div>
                            <div class="text-xs text-gray-600 dark:text-gray-100">
                                {libPrompt.title}
                            </div>
                        </button>
                    {/each}
                </div>
                <div
                    class="px-2 pt-0.5 pb-1 text-xs text-gray-600 dark:text-gray-100 bg-white dark:bg-gray-900 rounded-b-xl flex items-center space-x-1"
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
