<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { onMount, getContext, createEventDispatcher } from 'svelte';
	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	import { showArtifacts, showControls } from '$lib/stores';
	import XMark from '../icons/XMark.svelte';

	export let messages;
	export let overlay = false;

	let contents: Array<{ content: string }> = [];
	let selectedContentIdx = 0;

	let iframeElement: HTMLIFrameElement;

	$: if (messages) {
		getContents();
	}

	function getContents() {
		contents = [];
		messages.forEach((message) => {
			if (message.content) {
				let htmlContent = '';
				let cssContent = '';
				let jsContent = '';

				const codeBlocks = message.content.match(/```[\s\S]*?```/g);
				if (codeBlocks) {
					codeBlocks.forEach((block) => {
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
					contents = [...contents, { content: renderedContent }];
				}
			}
		});

		selectedContentIdx = contents ? contents.length - 1 : 0;
	}

	function navigateContent(direction: 'prev' | 'next') {
		console.log(selectedContentIdx);

		selectedContentIdx =
			direction === 'prev'
				? Math.max(selectedContentIdx - 1, 0)
				: Math.min(selectedContentIdx + 1, contents.length - 1);

		console.log(selectedContentIdx);
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
</script>

<div class=" w-full h-full relative flex flex-col bg-gray-850">
	<div class="w-full h-full flex-1 relative">
		{#if overlay}
			<div class=" absolute top-0 left-0 right-0 bottom-0 z-10"></div>
		{/if}

		<div class=" absolute z-50 w-full flex items-center justify-end p-4 dark:text-gray-100">
			<button
				class="self-center"
				on:click={() => {
					dispatch('close');
					showControls.set(false);
					showArtifacts.set(false);
				}}
			>
				<XMark className="size-4" />
			</button>
		</div>

		<div class="flex-1 w-full h-full">
			<div class=" h-full flex flex-col">
				{#if contents.length > 0}
					<div class="max-w-full w-full h-full">
						<iframe
							bind:this={iframeElement}
							title="Content"
							srcdoc={contents[selectedContentIdx].content}
							class="w-full border-0 h-full rounded-none"
							sandbox="allow-scripts allow-forms allow-same-origin"
							on:load={iframeLoadHandler}
						></iframe>
					</div>
				{:else}
					<div class="m-auto text-xs">No HTML, CSS, or JavaScript content found.</div>
				{/if}
			</div>
		</div>
	</div>

	{#if contents.length > 0}
		<div class="flex justify-between items-center p-2.5 font-primary">
			<div class="flex items-center space-x-2">
				<div class="flex self-center min-w-fit" dir="ltr">
					<button
						class="self-center p-1 hover:bg-black/5 dark:hover:bg-white/5 dark:hover:text-white hover:text-black rounded-md transition disabled:cursor-not-allowed"
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
						Version {selectedContentIdx + 1} of {contents.length}
					</div>

					<button
						class="self-center p-1 hover:bg-black/5 dark:hover:bg-white/5 dark:hover:text-white hover:text-black rounded-md transition disabled:cursor-not-allowed"
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
		</div>
	{/if}
</div>
