<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { onMount, getContext, createEventDispatcher } from 'svelte';
	import { fade, slide } from 'svelte/transition';
	import { quintOut } from 'svelte/easing';
	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	import { chatId, settings, showArtifacts, showControls } from '$lib/stores';
	import XMark from '../icons/XMark.svelte';
	import { copyToClipboard, createMessagesList } from '$lib/utils';
	import ArrowsPointingOut from '../icons/ArrowsPointingOut.svelte';
	import Tooltip from '../common/Tooltip.svelte';
	import SvgPanZoom from '../common/SVGPanZoom.svelte';
	import ArrowLeft from '../icons/ArrowLeft.svelte';

	export let overlay = false;
	export let history;
	let messages = [];

	let contents: Array<{ type: string; content: string }> = [];
	let selectedContentIdx = 0;

	let copied = false;
	let iframeElement: HTMLIFrameElement;

	// Track if we should process artifacts
	let shouldProcessArtifacts = false;

	$: if (history) {
		messages = createMessagesList(history, history.currentId);
		// Check if the last message is done before processing
		const lastMessage = messages[messages.length - 1];
		shouldProcessArtifacts = lastMessage?.done === true;
		
		if (shouldProcessArtifacts) {
			getContents();
		} else {
			// Clear contents if response is not done yet
			if (contents.length > 0) {
				contents = [];
				showControls.set(false);
				showArtifacts.set(false);
			}
		}
	} else {
		messages = [];
		contents = [];
	}

	const getContents = () => {
		const newContents = [];
		
		messages.forEach((message) => {
			// Only process messages that are done (completed responses)
			if (message?.role !== 'user' && message?.content && message?.done === true) {
				const codeBlockContents = message.content.match(/```[\s\S]*?```/g);
				let codeBlocks = [];

				if (codeBlockContents) {
					codeBlockContents.forEach((block) => {
						const lang = block.split('\n')[0].replace('```', '').trim().toLowerCase();
						const code = block.replace(/```[\s\S]*?\n/, '').replace(/```$/, '');
						codeBlocks.push({ lang, code });
					});
				}

				let htmlContent = '';
				let cssContent = '';
				let jsContent = '';

				codeBlocks.forEach((block) => {
					const { lang, code } = block;

					if (lang === 'html') {
						htmlContent += code + '\n';
					} else if (lang === 'css') {
						cssContent += code + '\n';
					} else if (lang === 'javascript' || lang === 'js') {
						jsContent += code + '\n';
					}
				});

				const inlineHtml = message.content.match(/<html>[\s\S]*?<\/html>/gi);
				const inlineCss = message.content.match(/<style>[\s\S]*?<\/style>/gi);
				const inlineJs = message.content.match(/<script>[\s\S]*?<\/script>/gi);

				if (inlineHtml) {
					inlineHtml.forEach((block) => {
						const content = block.replace(/<\/?html>/gi, ''); // Remove <html> tags
						htmlContent += content + '\n';
					});
				}
				if (inlineCss) {
					inlineCss.forEach((block) => {
						const content = block.replace(/<\/?style>/gi, ''); // Remove <style> tags
						cssContent += content + '\n';
					});
				}
				if (inlineJs) {
					inlineJs.forEach((block) => {
						const content = block.replace(/<\/?script>/gi, ''); // Remove <script> tags
						jsContent += content + '\n';
					});
				}

				if (htmlContent || cssContent || jsContent) {
					const renderedContent = `
                        <!DOCTYPE html>
                        <html lang="en">
                        <head>
                            <meta charset="UTF-8">
                            <meta name="viewport" content="width=device-width, initial-scale=1.0">
							<${''}style>
								body {
									background-color: white; /* Ensure the iframe has a white background */
								}

								${cssContent}
							</${''}style>
                        </head>
                        <body>
                            ${htmlContent}

							<${''}script>
                            	${jsContent}
							</${''}script>
                        </body>
                        </html>
                    `;
					newContents.push({ type: 'iframe', content: renderedContent });
				} else {
					// Check for SVG content
					for (const block of codeBlocks) {
						if (block.lang === 'svg' || (block.lang === 'xml' && block.code.includes('<svg'))) {
							newContents.push({ type: 'svg', content: block.code });
						}
					}
				}
			}
		});

		// Only update contents if there's a change
		if (JSON.stringify(newContents) !== JSON.stringify(contents)) {
			contents = newContents;
			
			if (contents.length === 0) {
				showControls.set(false);
				showArtifacts.set(false);
			} else {
				// Only auto-show artifacts if response is complete
				if (shouldProcessArtifacts) {
					showArtifacts.set(true);
				}
			}

			selectedContentIdx = contents.length > 0 ? contents.length - 1 : 0;
		}
	};

	function navigateContent(direction: 'prev' | 'next') {
		selectedContentIdx =
			direction === 'prev'
				? Math.max(selectedContentIdx - 1, 0)
				: Math.min(selectedContentIdx + 1, contents.length - 1);
	}

	const iframeLoadHandler = () => {
		iframeElement.contentWindow.addEventListener(
			'click',
			function (e) {
				const target = e.target.closest('a');
				if (target && target.href) {
					e.preventDefault();
					const url = new URL(target.href, iframeElement.baseURI);
					if (url.origin === window.location.origin) {
						iframeElement.contentWindow.history.pushState(
							null,
							'',
							url.pathname + url.search + url.hash
						);
					} else {
						console.log('External navigation blocked:', url.href);
					}
				}
			},
			true
		);

		// Cancel drag when hovering over iframe
		iframeElement.contentWindow.addEventListener('mouseenter', function (e) {
			e.preventDefault();
			iframeElement.contentWindow.addEventListener('dragstart', (event) => {
				event.preventDefault();
			});
		});
	};

	const showFullScreen = () => {
		if (iframeElement.requestFullscreen) {
			iframeElement.requestFullscreen();
		} else if (iframeElement.webkitRequestFullscreen) {
			iframeElement.webkitRequestFullscreen();
		} else if (iframeElement.msRequestFullscreen) {
			iframeElement.msRequestFullscreen();
		}
	};

	onMount(() => {});
</script>

<div class="artifacts-container w-full h-full relative flex flex-col bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-850" in:fade={{ duration: 200 }}>
	<div class="w-full h-full flex flex-col flex-1 relative">
		{#if contents.length > 0}
			<div
				class="header-bar pointer-events-auto z-20 flex justify-between items-center px-4 py-3 bg-white/80 dark:bg-gray-900/80 backdrop-blur-md border-b border-gray-200 dark:border-gray-700 shadow-sm"
				in:slide={{ duration: 300, easing: quintOut }}
			>
				<!-- Left Section: Back Button -->
				<div class="flex items-center gap-3">
					<Tooltip content={$i18n.t('Back to chat')} placement="bottom">
						<button
							class="action-button p-2 rounded-lg bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 transition-all duration-200 hover:scale-105 active:scale-95"
							on:click={() => {
								showArtifacts.set(false);
							}}
						>
							<ArrowLeft className="size-4 text-gray-700 dark:text-gray-300" />
						</button>
					</Tooltip>

					<!-- Version Navigator (only show if multiple versions) -->
					{#if contents.length > 1}
						<div class="flex items-center gap-1 px-3 py-1.5 bg-gray-100 dark:bg-gray-800 rounded-lg" in:fade={{ duration: 200 }}>
							<button
								class="p-1 hover:bg-gray-200 dark:hover:bg-gray-700 rounded transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
								on:click={() => navigateContent('prev')}
								disabled={selectedContentIdx === 0}
								aria-label="Previous version"
							>
								<svg
									xmlns="http://www.w3.org/2000/svg"
									fill="none"
									viewBox="0 0 24 24"
									stroke="currentColor"
									stroke-width="2.5"
									class="size-3.5 text-gray-600 dark:text-gray-400"
								>
									<path
										stroke-linecap="round"
										stroke-linejoin="round"
										d="M15.75 19.5 8.25 12l7.5-7.5"
									/>
								</svg>
							</button>

							<div class="text-xs font-medium text-gray-600 dark:text-gray-400 min-w-[60px] text-center">
								<span class="text-gray-900 dark:text-gray-200">{selectedContentIdx + 1}</span>
								<span class="mx-1">/</span>
								<span>{contents.length}</span>
							</div>

							<button
								class="p-1 hover:bg-gray-200 dark:hover:bg-gray-700 rounded transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
								on:click={() => navigateContent('next')}
								disabled={selectedContentIdx === contents.length - 1}
								aria-label="Next version"
							>
								<svg
									xmlns="http://www.w3.org/2000/svg"
									fill="none"
									viewBox="0 0 24 24"
									stroke="currentColor"
									stroke-width="2.5"
									class="size-3.5 text-gray-600 dark:text-gray-400"
								>
									<path
										stroke-linecap="round"
										stroke-linejoin="round"
										d="m8.25 4.5 7.5 7.5-7.5 7.5"
									/>
								</svg>
							</button>
						</div>
					{/if}
				</div>

				<!-- Center Section: Title -->
				<div class="flex-1 flex justify-center">
					<div class="flex items-center gap-2 px-4 py-1.5 bg-gradient-to-r from-blue-50 to-purple-50 dark:from-blue-900/20 dark:to-purple-900/20 rounded-lg border border-blue-200/50 dark:border-blue-700/50">
						<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="size-4 text-blue-600 dark:text-blue-400">
							<path stroke-linecap="round" stroke-linejoin="round" d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09ZM18.259 8.715 18 9.75l-.259-1.035a3.375 3.375 0 0 0-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 0 0 2.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 0 0 2.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 0 0-2.456 2.456ZM16.894 20.567 16.5 21.75l-.394-1.183a2.25 2.25 0 0 0-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 0 0 1.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 0 0 1.423 1.423l1.183.394-1.183.394a2.25 2.25 0 0 0-1.423 1.423Z" />
						</svg>
						<span class="text-sm font-semibold text-gray-700 dark:text-gray-300">
							{$i18n.t('Artifact Preview')}
						</span>
					</div>
				</div>

				<!-- Right Section: Action Buttons -->
				<div class="flex items-center gap-2">
					<Tooltip content={copied ? $i18n.t('Copied!') : $i18n.t('Copy code')} placement="bottom">
						<button
							class="action-button px-3 py-1.5 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 transition-all duration-200 hover:scale-105 active:scale-95 rounded-lg text-xs font-medium text-gray-700 dark:text-gray-300 flex items-center gap-1.5"
							on:click={() => {
								copyToClipboard(contents[selectedContentIdx].content);
								copied = true;
								setTimeout(() => {
									copied = false;
								}, 2000);
							}}
						>
							{#if copied}
								<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="size-3.5 text-green-600 dark:text-green-400">
									<path stroke-linecap="round" stroke-linejoin="round" d="m4.5 12.75 6 6 9-13.5" />
								</svg>
								<span class="text-green-600 dark:text-green-400">{$i18n.t('Copied')}</span>
							{:else}
								<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="size-3.5">
									<path stroke-linecap="round" stroke-linejoin="round" d="M15.666 3.888A2.25 2.25 0 0 0 13.5 2.25h-3c-1.03 0-1.9.693-2.166 1.638m7.332 0c.055.194.084.4.084.612v0a.75.75 0 0 1-.75.75H9a.75.75 0 0 1-.75-.75v0c0-.212.03-.418.084-.612m7.332 0c.646.049 1.288.11 1.927.184 1.1.128 1.907 1.077 1.907 2.185V19.5a2.25 2.25 0 0 1-2.25 2.25H6.75A2.25 2.25 0 0 1 4.5 19.5V6.257c0-1.108.806-2.057 1.907-2.185a48.208 48.208 0 0 1 1.927-.184" />
								</svg>
								<span>{$i18n.t('Copy')}</span>
							{/if}
						</button>
					</Tooltip>

					{#if contents[selectedContentIdx].type === 'iframe'}
						<Tooltip content={$i18n.t('Open in full screen')} placement="bottom">
							<button
								class="action-button p-2 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 transition-all duration-200 hover:scale-105 active:scale-95 rounded-lg"
								on:click={showFullScreen}
							>
								<ArrowsPointingOut className="size-3.5 text-gray-700 dark:text-gray-300" />
							</button>
						</Tooltip>
					{/if}

					<Tooltip content={$i18n.t('Close')} placement="bottom">
						<button
							class="action-button p-2 rounded-lg bg-red-50 dark:bg-red-900/20 hover:bg-red-100 dark:hover:bg-red-900/30 transition-all duration-200 hover:scale-105 active:scale-95"
							on:click={() => {
								dispatch('close');
								showControls.set(false);
								showArtifacts.set(false);
							}}
						>
							<XMark className="size-4 text-red-600 dark:text-red-400" />
						</button>
					</Tooltip>
				</div>
			</div>
		{/if}

		{#if overlay}
			<div class="absolute top-0 left-0 right-0 bottom-0 z-10 bg-black/5 dark:bg-black/20" in:fade={{ duration: 150 }}></div>
		{/if}

		<!-- Content Area -->
		<div class="flex-1 w-full h-full overflow-hidden">
			<div class="h-full flex flex-col">
				{#if contents.length > 0}
					<div class="content-wrapper max-w-full w-full h-full" in:fade={{ duration: 300, delay: 100 }}>
						{#if contents[selectedContentIdx].type === 'iframe'}
							<div class="iframe-container h-full w-full p-4">
								<div class="iframe-wrapper h-full w-full rounded-xl overflow-hidden shadow-2xl border-2 border-gray-200 dark:border-gray-700 bg-white">
									<iframe
										bind:this={iframeElement}
										title="Artifact Content"
										srcdoc={contents[selectedContentIdx].content}
										class="w-full h-full border-0"
										sandbox="allow-scripts{($settings?.iframeSandboxAllowForms ?? false)
											? ' allow-forms'
											: ''}{($settings?.iframeSandboxAllowSameOrigin ?? false)
											? ' allow-same-origin'
											: ''}"
										on:load={iframeLoadHandler}
									></iframe>
								</div>
							</div>
						{:else if contents[selectedContentIdx].type === 'svg'}
							<div class="svg-container h-full w-full p-4">
								<div class="svg-wrapper h-full w-full rounded-xl overflow-hidden shadow-2xl border-2 border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
									<SvgPanZoom
										className="w-full h-full"
										svg={contents[selectedContentIdx].content}
									/>
								</div>
							</div>
						{/if}
					</div>
				{:else}
					<div class="flex items-center justify-center h-full">
	<div class="text-center p-8 max-w-md" in:fade={{ duration: 300 }}>
		<!-- Icon with animated gradient background -->
		<div class="mb-6 relative inline-block">
			<div class="absolute inset-0 bg-gradient-to-br from-blue-100 to-purple-100 dark:from-blue-900/30 dark:to-purple-900/30 rounded-2xl blur-xl opacity-50"></div>
			<div class="relative bg-gradient-to-br from-blue-50 to-purple-50 dark:from-blue-900/20 dark:to-purple-900/20 p-6 rounded-2xl border border-blue-200/50 dark:border-blue-700/30">
				<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-12 h-12 mx-auto text-blue-500 dark:text-blue-400">
					<path stroke-linecap="round" stroke-linejoin="round" d="M6 6.878V6a2.25 2.25 0 0 1 2.25-2.25h7.5A2.25 2.25 0 0 1 18 6v.878m-12 0c.235-.083.487-.128.75-.128h10.5c.263 0 .515.045.75.128m-12 0A2.25 2.25 0 0 0 4.5 9v.878m13.5-3A2.25 2.25 0 0 1 19.5 9v.878m0 0a2.246 2.246 0 0 0-.75-.128H5.25c-.263 0-.515.045-.75.128m15 0A2.25 2.25 0 0 1 21 12v6a2.25 2.25 0 0 1-2.25 2.25H5.25A2.25 2.25 0 0 1 3 18v-6c0-.98.626-1.813 1.5-2.122" />
				</svg>
			</div>
		</div>
		
		<!-- Text content -->
		<h3 class="text-xl font-semibold text-gray-800 dark:text-gray-200 mb-2">
			{$i18n.t('No artifacts found')}
		</h3>
		<p class="text-sm text-gray-600 dark:text-gray-400 leading-relaxed">
			{$i18n.t('No HTML, CSS, or JavaScript content found.')}
		</p>
		
		<!-- Optional subtle hint -->
		<div class="mt-6 pt-6 border-t border-gray-200 dark:border-gray-700">
			<p class="text-xs text-gray-500 dark:text-gray-500">
				{$i18n.t('Code artifacts will appear here when generated')}
			</p>
		</div>
	</div>
</div>
				{/if}
			</div>
		</div>
	</div>
</div>

	<!-- /* Smooth transitions for all elements */
	:global(.artifacts-container) * {
		transition-timing-function: cubic-bezier(0.4, 0, 0.2, 1);
	}

	/* Content wrapper slide up animation */
	:global(.content-wrapper) {
		animation: slideUp 0.3s cubic-bezier(0.4, 0, 0.2, 1);
	}

	@keyframes slideUp {
		from {
			opacity: 0;
			transform: translateY(10px);
		}
		to {
			opacity: 1;
			transform: translateY(0);
		}
	}

	/* Iframe and SVG wrapper hover effects */
	:global(.iframe-wrapper),
	:global(.svg-wrapper) {
		transition: transform 0.2s ease, box-shadow 0.2s ease;
	}

	:global(.iframe-wrapper:hover),
	:global(.svg-wrapper:hover) {
		transform: translateY(-2px);
		box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
	}

	/* Responsive adjustments */
	@media (max-width: 768px) {
		:global(.header-bar) {
			padding: 0.75rem;
		}

		:global(.iframe-container),
		:global(.svg-container) {
			padding: 0.5rem;
		}
	}

	/* Accessibility: Reduce motion */
	@media (prefers-reduced-motion: reduce) {
		:global(.artifacts-container) *,
		:global(.artifacts-container) *::before,
		:global(.artifacts-container) *::after {
			animation-duration: 0.01ms !important;
			animation-iteration-count: 1 !important;
			transition-duration: 0.01ms !important;
		}
	} -->

