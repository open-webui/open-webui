<script lang="ts">
    import { onMount, getContext } from 'svelte';
    import Modal from '../common/Modal.svelte';
    import { showArtifacts, chats, chatId } from '$lib/stores';
    import { getChatById } from '$lib/apis/chats';

    export let show = false;

    const i18n = getContext('i18n');

    let renderedContents: Array<{ content: string, preview: string }> = [];
    let currentRenderIndex = 0;
    let currentChat = null;
    let iframeElement: HTMLIFrameElement;
    let error: string | null = null;
    let viewMode: 'full' | 'preview' = 'full';
    let renderRatio: 'responsive' | 'mobile' | 'desktop' = 'responsive';
    let isFullscreen = false;
    
    async function loadChatMessages(id: string) {
        try {
            const chatData = await getChatById(localStorage.token, id);
            if (chatData?.chat?.messages) {
                updateRenderedContents(chatData.chat.messages);
            } else {
                error = 'No messages found in chat data';
            }
        } catch (err) {
            error = `Error loading chat: ${err.message}`;
        }
    }
    
    $: if (show && $chatId) {
        currentChat = $chats.find(chat => chat.id === $chatId);
        if (currentChat) {
            loadChatMessages($chatId);
            viewMode = 'full'; // Set viewMode to 'full' when opening the modal
        } else {
            error = 'Chat not found';
        }
    }
    
    function processHtml(html: string): string {
        html = html.replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '');
        html = html.replace(/\s(src|href)=["'](?!data:)[^"']+["']/gi, '');
        return html;
    }
    
    function updateRenderedContents(messages) {
        renderedContents = [];
    
        messages.forEach((message) => {
            if (message.content) {
                let htmlContent = '';
                let cssContent = '';
                let jsContent = '';
    
                const codeBlocks = message.content.match(/```[\s\S]*?```/g);
                if (codeBlocks) {
                    codeBlocks.forEach(block => {
                        const lang = block.split('\n')[0].replace('```', '').trim().toLowerCase();
                        const code = block.replace(/```[\s\S]*?\n/, '').replace(/```$/, '');
                        if (lang === 'html') {
                            htmlContent += code + '\n';
                        } else if (lang === 'css') {
                            cssContent += code + '\n';
                        } else if (lang === 'javascript' || lang === 'js') {
                            jsContent += code + '\n';
                        }
                    });
                }
    
                const inlineHtml = message.content.match(/<html>[\s\S]*?<\/html>/gi);
                const inlineCss = message.content.match(/<style>[\s\S]*?<\/style>/gi);
                const inlineJs = message.content.match(/<script>[\s\S]*?<\/script>/gi);
    
                if (inlineHtml) htmlContent += inlineHtml.join('\n');
                if (inlineCss) cssContent += inlineCss.join('\n');
                if (inlineJs) jsContent += inlineJs.join('\n');
    
                if (htmlContent || cssContent || jsContent) {
                    const renderedContent = `
                        <!DOCTYPE html>
                        <html lang="en">
                        <head>
                            <meta charset="UTF-8">
                            <meta name="viewport" content="width=device-width, initial-scale=1.0">
                            <style>${cssContent}</style>
                        </head>
                        <body>
                            ${processHtml(htmlContent)}
                            <script>${jsContent}<\/script>
                        </body>
                        </html>
                    `;
                    renderedContents.unshift({ content: renderedContent, preview: renderedContent });
                }
            }
        });
    
        currentRenderIndex = 0;
    }
    
    function navigateRender(direction: 'prev' | 'next') {
        currentRenderIndex = direction === 'prev'
            ? (currentRenderIndex - 1 + renderedContents.length) % renderedContents.length
            : (currentRenderIndex + 1) % renderedContents.length;
    }
    
    function handleIframeLoad() {
        iframeElement.contentWindow.addEventListener('click', function(e) {
            const target = e.target.closest('a');
            if (target && target.href) {
                e.preventDefault();
                const url = new URL(target.href, iframeElement.baseURI);
                if (url.origin === window.location.origin) {
                    iframeElement.contentWindow.history.pushState(null, '', url.pathname + url.search + url.hash);
                } else {
                    console.log('External navigation blocked:', url.href);
                }
            }
        }, true);
    }
    
    function handleClose() {
        show = false;
        $showArtifacts = false;
        viewMode = 'full';
        if (isFullscreen) {
            exitFullscreen();
        }
    }
    
    function setRenderRatio(ratio: 'responsive' | 'mobile' | 'desktop') {
        renderRatio = ratio;
        if (ratio === 'desktop') {
            requestFullscreen();
        } else if (isFullscreen) {
            exitFullscreen();
        }
    }

    function requestFullscreen() {
        const elem = document.documentElement;
        if (elem.requestFullscreen) {
            elem.requestFullscreen();
        } else if (elem.mozRequestFullScreen) { // Firefox
            elem.mozRequestFullScreen();
        } else if (elem.webkitRequestFullscreen) { // Chrome, Safari and Opera
            elem.webkitRequestFullscreen();
        } else if (elem.msRequestFullscreen) { // IE/Edge
            elem.msRequestFullscreen();
        }
        isFullscreen = true;
    }

    function exitFullscreen() {
        if (document.exitFullscreen) {
            document.exitFullscreen();
        } else if (document.mozCancelFullScreen) { // Firefox
            document.mozCancelFullScreen();
        } else if (document.webkitExitFullscreen) { // Chrome, Safari and Opera
            document.webkitExitFullscreen();
        } else if (document.msExitFullscreen) { // IE/Edge
            document.msExitFullscreen();
        }
        isFullscreen = false;
    }

    function switchViewMode() {
        viewMode = viewMode === 'full' ? 'preview' : 'full';
        if (viewMode === 'full' && renderRatio === 'desktop') {
            exitFullscreen();
            renderRatio = 'responsive';
        }
    }
    
    function selectRender(index: number) {
        currentRenderIndex = index;
        viewMode = 'full';
    }

    onMount(() => {
        document.addEventListener('fullscreenchange', () => {
            isFullscreen = !!document.fullscreenElement;
            if (!isFullscreen && renderRatio === 'desktop') {
                renderRatio = 'responsive';
            }
        });
    });
</script>

<Modal bind:show on:close={handleClose}>
    <div class="text-gray-700 dark:text-gray-100" class:fullscreen={renderRatio === 'desktop'}>
        <div class="flex justify-between items-center dark:text-gray-300 px-5 pt-4 pb-1">
            <div class="text-lg font-medium self-center">{$i18n.t('Artifacts')}</div>
            <div class="flex items-center space-x-2">
                <button
                    class="p-2 rounded-full bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600"
                    on:click={() => navigateRender('prev')}
                    disabled={renderedContents.length <= 1}
                >
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="w-6 h-6">
                        <path d="M15 18l-6-6 6-6" />
                    </svg>
                </button>
                <span>{renderedContents.length - currentRenderIndex} / {renderedContents.length}</span>
                <button
                    class="p-2 rounded-full bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600"
                    on:click={() => navigateRender('next')}
                    disabled={renderedContents.length <= 1}
                >
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="w-6 h-6">
                        <path d="M9 18l6-6-6-6" />
                    </svg>
                </button>
            </div>
            <div class="flex items-center space-x-2">
                <button
                    class={`p-2 rounded ${renderRatio === 'responsive' ? 'bg-blue-500 text-white' : 'bg-gray-200 dark:bg-gray-700'}`}
                    on:click={() => setRenderRatio('responsive')}
                    title="Responsive View"
                >
                    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <rect x="2" y="3" width="20" height="14" rx="2" ry="2"></rect>
                        <line x1="8" y1="21" x2="16" y2="21"></line>
                        <line x1="12" y1="17" x2="12" y2="21"></line>
                    </svg>
                </button>
                <button
                    class={`p-2 rounded ${renderRatio === 'mobile' ? 'bg-blue-500 text-white' : 'bg-gray-200 dark:bg-gray-700'}`}
                    on:click={() => setRenderRatio('mobile')}
                    title="Mobile View"
                >
                    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <rect x="5" y="2" width="14" height="20" rx="2" ry="2"></rect>
                        <line x1="12" y1="18" x2="12.01" y2="18"></line>
                    </svg>
                </button>
                <button
                    class={`p-2 rounded ${renderRatio === 'desktop' ? 'bg-blue-500 text-white' : 'bg-gray-200 dark:bg-gray-700'}`}
                    on:click={() => setRenderRatio('desktop')}
                    title="Desktop View (Fullscreen)"
                >
                    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3"></path>
                    </svg>
                </button>
                <button 
                    class="p-2 rounded-full hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
                    on:click={switchViewMode}
                    title={viewMode === 'full' ? 'Show Previews' : 'Show Full View'}
                >
                    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
                        <line x1="9" y1="3" x2="9" y2="21"></line>
                    </svg>
                </button>
            </div>
        </div>

        <div class="p-4 flex-grow overflow-auto">
            {#if error}
                <div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative mb-4" role="alert">
                    <strong class="font-bold">Error!</strong>
                    <span class="block sm:inline">{error}</span>
                </div>
            {/if}

            <div class="bg-white dark:bg-gray-800 p-4 rounded-lg h-full flex flex-col">
                {#if viewMode === 'full'}
                    {#if renderedContents.length > 0}
                        <div class={`w-full mx-auto flex-grow ${
                            renderRatio === 'responsive' ? 'max-w-full' :
                            renderRatio === 'mobile' ? 'mobile-view' :
                            'w-full h-full'
                        }`}>
                            <iframe
                                bind:this={iframeElement}
                                title="Rendered Content"
                                srcdoc={renderedContents[currentRenderIndex].content}
                                class={`w-full border-0 ${
                                    renderRatio === 'responsive' ? 'h-[500px]' :
                                    renderRatio === 'mobile' ? 'mobile-frame' :
                                    'h-full'
                                }`}
                                sandbox="allow-scripts allow-forms allow-same-origin"
                                on:load={handleIframeLoad}
                            ></iframe>
                        </div>
                    {:else}
                        <p>No HTML, CSS, or JavaScript content found in the current messages.</p>
                    {/if}
                {:else}
                    <div class="grid grid-cols-3 gap-4">
                        {#each renderedContents as content, index}
                            <div 
                                class="aspect-square border rounded overflow-hidden cursor-pointer hover:border-blue-500 transition-colors"
                                on:click={() => selectRender(index)}
                            >
                                <iframe
                                    title={`Preview ${index + 1}`}
                                    srcdoc={content.preview}
                                    class="w-full h-full pointer-events-none"
                                    sandbox="allow-scripts"
                                ></iframe>
                            </div>
                        {/each}
                    </div>
                {/if}
            </div>
        </div>
    </div>
</Modal>

<style>
    input::-webkit-outer-spin-button,
    input::-webkit-inner-spin-button {
        -webkit-appearance: none;
        margin: 0;
    }

    .tabs::-webkit-scrollbar {
        display: none;
    }

    .tabs {
        -ms-overflow-style: none;
        scrollbar-width: none;
    }

    input[type='number'] {
        -moz-appearance: textfield;
    }

    .fullscreen {
        position: fixed;
        top: 0;
        left: 0;
        width: 100vw;
        height: 100vh;
        z-index: 9999;
        background-color: rgb(17 24 39);
        color: white;
        display: flex;
        flex-direction: column;
    }

    iframe {
        max-width: 100%;
        margin: 0 auto;
        flex-grow: 1;
    }

    .mobile-view {
        width: 375px;
        margin-left: auto;
        margin-right: auto;
    }

    .mobile-frame {
        height: 667px;
    }
</style>