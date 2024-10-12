<script lang="ts">
    import { onMount, onDestroy, getContext, createEventDispatcher } from 'svelte';
    import { chatId, showArtifacts, showControls } from '$lib/stores';
    import XMark from '../icons/XMark.svelte';
    import { copyToClipboard, createMessagesList } from '$lib/utils';
    import ArrowsPointingOut from '../icons/ArrowsPointingOut.svelte';
    import Tooltip from '../common/Tooltip.svelte';
    import SvgPanZoom from '../common/SVGPanZoom.svelte';
	import { goto } from '$app/navigation';

    const i18n = getContext('i18n');
    const dispatch = createEventDispatcher();

    export let overlay = false;
    export let history;
    let messages = [];

    let contents: Array<{ type: string; content: string }> = [];
    let selectedContentIdx = 0;

    let copied = false;
    let iframeElement: HTMLIFrameElement | null = null;
    let iframeWrapper: HTMLDivElement;

    let cleanup: (() => void) | null = null;

    $: if (history) {
        messages = createMessagesList(history, history.currentId);
        getContents();
    } else {
        messages = [];
        getContents();
    }

    $: if (iframeElement) {
        if (cleanup) cleanup();
        cleanup = setupIframeListener();
    }

	function isNewProject(prevContent: string, newContent: string): boolean {
		// Simple heuristic: if less than 20% of the content matches, consider it a new project
		const similarity = stringSimilarity(prevContent, newContent);
		return similarity < 0.2;
	}

	function stringSimilarity(s1: string, s2: string): number {
		const longer = s1.length > s2.length ? s1 : s2;
		const shorter = s1.length > s2.length ? s2 : s1;
		const longerLength = longer.length;
		if (longerLength === 0) {
			return 1.0;
		}
		return (longerLength - editDistance(longer, shorter)) / longerLength;
	}

	function editDistance(s1: string, s2: string): number {
		s1 = s1.toLowerCase();
		s2 = s2.toLowerCase();
		const costs = [];
		for (let i = 0; i <= s1.length; i++) {
			let lastValue = i;
			for (let j = 0; j <= s2.length; j++) {
				if (i === 0) {
					costs[j] = j;
				} else if (j > 0) {
					let newValue = costs[j - 1];
					if (s1.charAt(i - 1) !== s2.charAt(j - 1)) {
						newValue = Math.min(Math.min(newValue, lastValue), costs[j]) + 1;
					}
					costs[j - 1] = lastValue;
					lastValue = newValue;
				}
			}
			if (i > 0) {
				costs[s2.length] = lastValue;
			}
		}
		return costs[s2.length];
	}

	function cleanCodeContent(content: string): string {
		// Split the content into lines
		const lines = content.split('\n');
		
		// Find the minimum indentation
		const minIndent = lines.reduce((min, line) => {
			if (line.trim().length === 0) return min; // Skip empty lines
			const indent = line.match(/^\s*/)[0].length;
			return Math.min(min, indent);
		}, Infinity);

		// Remove the minimum indentation from each line and trim
		return lines
			.map(line => line.slice(minIndent).trimRight())
			.join('\n')
			.trim();
	}

	async function downloadCurrentArtifact() {
		if (contents.length === 0 || selectedContentIdx < 0) return;

		const content = contents[selectedContentIdx].content;
		const parser = new DOMParser();
		const doc = parser.parseFromString(content, 'text/html');

		// Extract CSS content
		const cssContent = cleanCodeContent(doc.querySelector('style')?.textContent || '');

		// Extract JavaScript content
		const jsContent = cleanCodeContent(doc.querySelector('script')?.textContent || '');

		// Remove style and script tags from the HTML
		doc.querySelectorAll('style').forEach(el => el.remove());
		doc.querySelectorAll('script').forEach(el => el.remove());

		// Update HTML to link external CSS and JS files
		const head = doc.head || doc.getElementsByTagName('head')[0];

		// Remove existing CSP meta tag if present
		const existingCSP = head.querySelector('meta[http-equiv="Content-Security-Policy"]');
		if (existingCSP) existingCSP.remove();

		// Add the correct Content Security Policy
		const cspMeta = doc.createElement('meta');
		cspMeta.httpEquiv = 'Content-Security-Policy';
		cspMeta.content = "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline';";
		head.insertBefore(cspMeta, head.firstChild);

		const cssLink = doc.createElement('link');
		cssLink.rel = 'stylesheet';
		cssLink.href = 'styles.css';
		head.appendChild(cssLink);

		const jsScript = doc.createElement('script');
		jsScript.src = 'app.js';
		doc.body.appendChild(jsScript);

		// Get the updated HTML content and clean it
		let htmlContent = doc.documentElement.outerHTML;
		htmlContent = cleanCodeContent(htmlContent);

		// Ensure proper DOCTYPE and formatting
		htmlContent = `<!DOCTYPE html>\n${htmlContent}`;

		const files = [
			{ name: 'index.html', content: htmlContent, type: 'text/html' },
			{ name: 'styles.css', content: cssContent, type: 'text/css' },
			{ name: 'app.js', content: jsContent, type: 'text/javascript' }
		];

		if ('showDirectoryPicker' in window) {
			try {
				const dirHandle = await window.showDirectoryPicker();
				for (const file of files) {
					const fileHandle = await dirHandle.getFileHandle(file.name, { create: true });
					const writable = await fileHandle.createWritable();
					await writable.write(file.content);
					await writable.close();
				}
				alert('Files saved successfully!');
			} catch (err) {
				console.error('Error saving files:', err);
				fallbackDownload(files);
			}
		} else {
			fallbackDownload(files);
		}
	}

    function fallbackDownload(files) {
        files.forEach(file => {
            const blob = new Blob([file.content], { type: file.type });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = file.name;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        });
    }

    const sanitizeAndValidateJs = (jsContent: string): string => {
        jsContent = jsContent.replace(/\beval\b|\bFunction\b|\bsetTimeout\b|\bsetInterval\b/g, '');
        
        try {
            new Function(jsContent);
            return jsContent;
        } catch (error) {
            console.error('Invalid JavaScript:', error);
            return '';
        }
    };


    const getContents = () => {
		contents = [];
		let latestHtmlContent = '';
		let latestCssContent = '';
		let latestJsContent = '';
		let isNewProjectStarted = false;

		messages.forEach((message, index) => {
			if (message?.role !== 'user' && message?.content) {
				let newHtmlContent = '';
				let newCssContent = '';
				let newJsContent = '';

                const codeBlockContents = message.content.match(/```[\s\S]*?```/g);
                if (codeBlockContents) {
                    codeBlockContents.forEach((block) => {
                        const lang = block.split('\n')[0].replace('```', '').trim().toLowerCase();
                        const code = block.replace(/```[\s\S]*?\n/, '').replace(/```$/, '');
                        if (lang === 'html') {
                            newHtmlContent += code + '\n';
                        } else if (lang === 'css') {
                            newCssContent += code + '\n';
                        } else if (lang === 'javascript' || lang === 'js') {
                            newJsContent += code + '\n';
                        }
                    });
                }

                const inlineHtml = message.content.match(/<html>[\s\S]*?<\/html>/gi);
                const inlineCss = message.content.match(/<style>[\s\S]*?<\/style>/gi);
                const inlineJs = message.content.match(/<script>[\s\S]*?<\/script>/gi);

                if (inlineHtml) {
                    inlineHtml.forEach((block) => {
                        newHtmlContent += block.replace(/<\/?html>/gi, '') + '\n';
                    });
                }
                if (inlineCss) {
                    inlineCss.forEach((block) => {
                        newCssContent += block.replace(/<\/?style>/gi, '') + '\n';
                    });
                }
                if (inlineJs) {
                    inlineJs.forEach((block) => {
                        newJsContent += block.replace(/<\/?script>/gi, '') + '\n';
                    });
                }

                latestHtmlContent = newHtmlContent || latestHtmlContent;
                latestCssContent = newCssContent || latestCssContent;
                latestJsContent = newJsContent || latestJsContent;

                latestJsContent = sanitizeAndValidateJs(latestJsContent);

				// Check if this is a new project
				if (index > 0) {
					const prevContent = messages[index - 1]?.content || '';
					isNewProjectStarted = isNewProject(prevContent, message.content);
				}

				if (isNewProjectStarted) {
					// If it's a new project, reset the latest content
					latestHtmlContent = '';
					latestCssContent = '';
					latestJsContent = '';
				}

				// Update content
				latestHtmlContent = newHtmlContent || latestHtmlContent;
				latestCssContent = newCssContent || latestCssContent;
				latestJsContent = newJsContent || latestJsContent;

				latestJsContent = sanitizeAndValidateJs(latestJsContent);

                const renderedContent = `
					<!DOCTYPE html>
					<html lang="en">
					<head>
						<meta charset="UTF-8">
						<meta name="viewport" content="width=device-width, initial-scale=1.0">
						<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline';">
						<${''}style>
							body {
								background-color: white;
							}
							${latestCssContent}
						</${''}style>
					</head>
					<body>
						${latestHtmlContent}
						<${''}script>
							(function() {
								window.onerror = function(message, source, lineno, colno, error) {
									console.error('JavaScript error:', message, 'at', source, lineno, colno);
								};
								${latestJsContent}

								document.addEventListener('click', function(e) {
									if (e.target.tagName === 'A' && e.target.href) {
										e.preventDefault();
										window.parent.postMessage({ type: 'navigation', url: e.target.href }, '*');
									}
								});
							})();
						</${''}script>
					</body>
					</html>
				`;

				contents.push({ type: 'iframe', content: renderedContent });
			}
		});

		selectedContentIdx = contents ? contents.length - 1 : 0;
	};

    function navigateContent(direction: 'prev' | 'next') {
        selectedContentIdx =
            direction === 'prev'
                ? Math.max(selectedContentIdx - 1, 0)
                : Math.min(selectedContentIdx + 1, contents.length - 1);
    }

    const setupIframeListener = () => {
		const handler = (event: MessageEvent) => {
			if (event.source === iframeElement?.contentWindow) {
				if (event.data.type === 'navigation') {
					console.log('Received navigation request:', event.data.url);
					handleNavigation(event.data.url);
				}
			}
		};

		window.addEventListener('message', handler);

		return () => {
			window.removeEventListener('message', handler);
		};
	};

    const handleNavigation = async (url: string) => {
		// Function to safely join paths
		const joinPaths = (...parts: string[]) => 
			parts.join('/').replace(/\/+/g, '/').replace(/\/$/, '');

		try {
			let fullUrl: URL;

			// Check if the URL is absolute
			if (url.startsWith('http://') || url.startsWith('https://')) {
				fullUrl = new URL(url);
			} else {
				// Handle relative URLs
				const basePath = window.location.pathname.split('/').slice(0, -1).join('/');
				const absolutePath = url.startsWith('/') ? url : joinPaths(basePath, url);
				fullUrl = new URL(absolutePath, window.location.origin);
			}

			if (fullUrl.origin === window.location.origin) {
				// Internal navigation
				const newPath = fullUrl.pathname + fullUrl.search + fullUrl.hash;
				console.log('Internal navigation to:', newPath);
				await goto(newPath, { replaceState: false });
			} else {
				// External navigation
				console.log('External navigation to:', fullUrl.href);
				window.open(fullUrl.href, '_blank');
			}
		} catch (error) {
			console.error('Error handling navigation:', error, 'URL:', url);
			// Fallback: treat as relative path
			const newPath = url.startsWith('/') ? url : joinPaths(window.location.pathname, url);
			console.log('Fallback navigation to:', newPath);
			await goto(newPath, { replaceState: false });
		}
	};

    const showFullScreen = () => {
        if (iframeWrapper.requestFullscreen) {
            iframeWrapper.requestFullscreen();
        } else if (iframeWrapper.webkitRequestFullscreen) {
            iframeWrapper.webkitRequestFullscreen();
        } else if (iframeWrapper.msRequestFullscreen) {
            iframeWrapper.msRequestFullscreen();
        }
    };

    onDestroy(() => {
        if (cleanup) cleanup();
    });
</script>

<div class="w-full h-full relative flex flex-col bg-gray-50 dark:bg-gray-850">
    <!-- New top spacing div -->
    <div class="h-12 flex-shrink-0 relative">
        <div class="absolute top-0 right-0 p-2">
            <button
                class="p-1 rounded-full bg-white dark:bg-gray-850 shadow-md hover:bg-gray-100 dark:hover:bg-gray-800 transition"
                on:click={() => {
                    dispatch('close');
                    showControls.set(false);
                    showArtifacts.set(false);
                }}
            >
                <XMark className="size-4 text-gray-900 dark:text-white" />
            </button>
        </div>
    </div>

    <!-- Main content area -->
    <div class="flex-grow overflow-hidden">
        <div class="w-full h-full relative">
            {#if overlay}
                <div class="absolute top-0 left-0 right-0 bottom-0 z-10"></div>
            {/if}

            <div class="flex-1 w-full h-full">
                <div class="h-full flex flex-col">
                    {#if contents.length > 0}
                        <div bind:this={iframeWrapper} class="max-w-full w-full h-full">
                            {#if contents[selectedContentIdx].type === 'iframe'}
                                <iframe
                                    bind:this={iframeElement}
                                    title="Content"
                                    srcdoc={contents[selectedContentIdx].content}
                                    class="w-full border-0 h-full rounded-none"
                                    sandbox="allow-scripts allow-forms allow-popups"
                                ></iframe>
                            {:else if contents[selectedContentIdx].type === 'svg'}
                                <SvgPanZoom
                                    className="w-full h-full max-h-full overflow-hidden"
                                    svg={contents[selectedContentIdx].content}
                                />
                            {/if}
                        </div>
                    {:else}
                        <div class="m-auto font-medium text-xs text-gray-900 dark:text-white">
                            {$i18n.t('No HTML, CSS, or JavaScript content found.')}
                        </div>
                    {/if}
                </div>
            </div>
        </div>
    </div>

    <!-- Navigation controls -->
    {#if contents.length > 0}
        <div class="flex justify-between items-center p-2.5 font-primar text-gray-900 dark:text-white">
            <div class="flex items-center space-x-2">
                <div class="flex items-center gap-0.5 self-center min-w-fit" dir="ltr">
                    <button
                        class="self-center p-1 hover:bg-black/5 dark:hover:bg:white/5 dark:hover:text:white hover:text:black rounded-md transition disabled:cursor-not-allowed"
                        on:click={() => navigateContent('prev')}
                        disabled={contents.length <= 1}
                    >
                        <svg
                            xmlns="http://www.w3.org/2000/svg"
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke="currentColor"
                            stroke-width="2.5"
                            class="size-3.5"
                        >
                            <path
                                stroke-linecap="round"
                                stroke-linejoin="round"
                                d="M15.75 19.5 8.25 12l7.5-7.5"
                            />
                        </svg>
                    </button>

                    <div class="text-xs self-center dark:text-gray-100 min-w-fit">
                        {$i18n.t('Version {{selectedVersion}} of {{totalVersions}}', {
                            selectedVersion: selectedContentIdx + 1,
                            totalVersions: contents.length
                        })}
                    </div>

                    <button
                        class="self-center p-1 hover:bg-black/5 dark:hover:bg:white/5 dark:hover:text:white hover:text:black rounded-md transition disabled:cursor-not-allowed"
                        on:click={() => navigateContent('next')}
                        disabled={contents.length <= 1}
                    >
                        <svg
                            xmlns="http://www.w3.org/2000/svg"
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke="currentColor"
                            stroke-width="2.5"
                            class="size-3.5"
                        >
                            <path stroke-linecap="round" stroke-linejoin="round" d="m8.25 4.5 7.5 7.5-7.5 7.5" />
                        </svg>
                    </button>
                </div>
            </div>

            <div class="flex items-center gap-1">
                <button
                    class="copy-code-button bg-none border-none text-xs bg-gray-50 hover:bg-gray-100 dark:bg-gray-850 dark:hover:bg-gray-800 transition rounded-md px-1.5 py-0.5"
                    on:click={() => {
                        copyToClipboard(contents[selectedContentIdx].content);
                        copied = true;

                        setTimeout(() => {
                            copied = false;
                        }, 2000);
                    }}>{copied ? $i18n.t('Copied') : $i18n.t('Copy')}</button
                >

                <button
					class="bg-none border-none text-xs bg-gray-50 hover:bg-gray-100 dark:bg-gray-850 dark:hover:bg-gray-800 transition rounded-md px-1.5 py-0.5"
					on:click={downloadCurrentArtifact}
				>
					{$i18n.t('Download')}
				</button>

                {#if contents[selectedContentIdx].type === 'iframe'}
                    <Tooltip content={$i18n.t('Open in full screen')}>
                        <button
                            class="bg-none border-none text-xs bg-gray-50 hover:bg-gray-100 dark:bg-gray-850 dark:hover:bg-gray-800 transition rounded-md p-0.5"
                            on:click={showFullScreen}
                        >
                            <ArrowsPointingOut className="size-3.5" />
                        </button>
                    </Tooltip>
                {/if}
            </div>
        </div>
    {/if}
</div>