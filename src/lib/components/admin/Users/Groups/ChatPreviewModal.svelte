<script lang="ts">
    import { getContext, onMount } from 'svelte';
    import { createEventDispatcher } from 'svelte';
    
    const i18n = getContext('i18n');
    const dispatch = createEventDispatcher();

    export let show = false;
    export let chat = null;

    let modalRef;

    // Sample conversation data for preview
    let conversation = [];
    let loading = false;

    // Generate sample conversation based on chat data
    const generateConversation = (chatData) => {
        if (!chatData) return [];
        
        // Sample conversation based on the chat's questions
        const sampleConversation = [
            {
                id: 1,
                type: 'user',
                message: chatData.questions[0] || "What is 2 + 2?",
                timestamp: "10:15 AM"
            },
            {
                id: 2,
                type: 'assistant',
                message: "2 + 2 equals 4. This is a basic addition problem where we're combining two groups of 2 items each.",
                timestamp: "10:15 AM"
            },
            {
                id: 3,
                type: 'user',
                message: chatData.questions[1] || "Can you explain how you solved that?",
                timestamp: "10:16 AM"
            },
            {
                id: 4,
                type: 'assistant',
                message: "Of course! Addition is the process of combining quantities. When we add 2 + 2, we're taking the first quantity (2) and adding the second quantity (2) to it. You can think of it as counting: start with 2, then count 2 more (3, 4), and you arrive at 4.",
                timestamp: "10:16 AM"
            },
            {
                id: 5,
                type: 'user',
                message: chatData.questions[2] || "Thank you! That makes sense.",
                timestamp: "10:17 AM"
            }
        ];

        return sampleConversation;
    };

    // Load conversation when chat changes
    $: if (chat && show) {
        loading = true;
        // Simulate API call
        setTimeout(() => {
            conversation = generateConversation(chat);
            loading = false;
        }, 300);
    }

    // Handle keyboard events
    const handleKeydown = (event) => {
        if (event.key === 'Escape' || event.key === ' ') {
            event.preventDefault();
            show = false;
        }
    };

    // Handle backdrop click/keyboard
    const handleBackdropClick = (event) => {
        // Only close if clicking directly on the backdrop, not bubbled from modal content
        if (event.target === event.currentTarget) {
            show = false;
        }
    };

    const handleBackdropKeydown = (event) => {
        if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault();
            show = false;
        }
    };

    // Setup event listeners
    onMount(() => {
        const handleGlobalKeydown = (event) => {
            if (show) {
                handleKeydown(event);
            }
        };

        document.addEventListener('keydown', handleGlobalKeydown);

        return () => {
            document.removeEventListener('keydown', handleGlobalKeydown);
        };
    });

    // Close modal function
    const closeModal = () => {
        show = false;
    };
</script>

{#if show}
    <!-- Modal Backdrop as Button -->
    <button
        class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4 border-none cursor-default"
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-title"
        aria-label="Close modal by clicking outside"
        on:click={handleBackdropClick}
        on:keydown={handleBackdropKeydown}
    >
        <!-- Modal Content -->
        <div 
            bind:this={modalRef}
            class="bg-white dark:bg-gray-900 rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col"
            on:click|stopPropagation
            role="document"
        >
            <!-- Header -->
            <div class="flex justify-between items-center p-6 border-b border-gray-200 dark:border-gray-700">
                <div class="flex flex-col">
                    <h2 id="modal-title" class="text-xl font-semibold text-gray-900 dark:text-gray-100">
                        Chat Preview
                    </h2>
                    {#if chat}
                        <div class="text-sm text-gray-500 dark:text-gray-400 mt-1">
                            {chat.name} • {chat.model} • {chat.lastUpdated}
                        </div>
                    {/if}
                </div>
                <button
                    class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 transition"
                    on:click={closeModal}
                    aria-label="Close modal"
                >
                    <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                    </svg>
                </button>
            </div>

            <!-- Content -->
            <div class="flex-1 overflow-hidden flex flex-col">
                {#if loading}
                    <div class="flex-1 flex items-center justify-center">
                        <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                    </div>
                {:else if chat}
                    <!-- Chat Messages -->
                    <div class="flex-1 overflow-y-auto p-6 space-y-4" role="log" aria-label="Chat conversation">
                        {#each conversation as message}
                            <div class="flex {message.type === 'user' ? 'justify-end' : 'justify-start'}">
                                <div 
                                    class="max-w-xs lg:max-w-md px-4 py-2 rounded-lg {message.type === 'user' 
                                        ? 'bg-blue-600 text-white' 
                                        : 'bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-gray-100'}"
                                    role="article"
                                    aria-label="{message.type === 'user' ? 'User message' : 'Assistant message'}"
                                >
                                    <p class="text-sm">{message.message}</p>
                                    <p class="text-xs mt-1 opacity-70">{message.timestamp}</p>
                                </div>
                            </div>
                        {/each}
                    </div>

                    <!-- Chat Stats -->
                    <div class="border-t border-gray-200 dark:border-gray-700 p-6 bg-gray-50 dark:bg-gray-800">
                        <div class="grid grid-cols-4 gap-4 text-center" role="region" aria-label="Chat statistics">
                            <div>
                                <div class="text-lg font-semibold text-gray-900 dark:text-gray-100">
                                    {chat.messageCount}
                                </div>
                                <div class="text-xs text-gray-500 dark:text-gray-400">Messages</div>
                            </div>
                            <div>
                                <div class="text-lg font-semibold text-gray-900 dark:text-gray-100">
                                    {chat.questionsAsked}
                                </div>
                                <div class="text-xs text-gray-500 dark:text-gray-400">Questions</div>
                            </div>
                            <div>
                                <div class="text-lg font-semibold text-gray-900 dark:text-gray-100">
                                    {chat.timeTaken}
                                </div>
                                <div class="text-xs text-gray-500 dark:text-gray-400">Duration</div>
                            </div>
                            <div>
                                <div class="text-lg font-semibold text-gray-900 dark:text-gray-100">
                                    {chat.model}
                                </div>
                                <div class="text-xs text-gray-500 dark:text-gray-400">Model Used</div>
                            </div>
                        </div>
                    </div>
                {:else}
                    <div class="flex-1 flex items-center justify-center text-gray-500 dark:text-gray-400">
                        No chat selected
                    </div>
                {/if}
            </div>

            <!-- Footer -->
            <div class="p-6 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800">
                <div class="flex justify-between items-center">
                    <div class="text-sm text-gray-500 dark:text-gray-400">
                        Press <kbd class="px-2 py-1 bg-gray-200 dark:bg-gray-700 rounded text-xs">Esc</kbd> or 
                        <kbd class="px-2 py-1 bg-gray-200 dark:bg-gray-700 rounded text-xs">Space</kbd> to close
                    </div>
                    <button
                        class="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg transition"
                        on:click={closeModal}
                    >
                        Close
                    </button>
                </div>
            </div>
        </div>
    </button>
{/if}