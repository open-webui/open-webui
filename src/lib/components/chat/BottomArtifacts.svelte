<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { onMount, getContext, createEventDispatcher } from 'svelte';
	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	import { showBottomArtifacts, showControls, bottomHistory } from '$lib/stores';
	import XMark from '../icons/XMark.svelte';
	import { copyToClipboard, createMessagesList } from '$lib/utils';
	import ArrowsPointingOut from '../icons/ArrowsPointingOut.svelte';
	import Tooltip from '../common/Tooltip.svelte';
	import SvgPanZoom from '../common/SVGPanZoom.svelte';
	import ArrowLeft from '../icons/ArrowLeft.svelte';

	export let overlay = false;
	let messages = [];

	let contents: Array<{ type: string; content: string }> = [];
	let selectedContentIdx = 0;

	let copied = false;

	$: if ($bottomHistory) {
		messages = createMessagesList($bottomHistory, $bottomHistory.currentId);
		getContents();
	} else {
		messages = [];
		getContents();
	}

	const getContents = () => {
		contents = [];
		messages.forEach((message) => {
			if (message?.role !== 'user' && message?.content) {
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
					contents = [...contents, { type: 'web', content: renderedContent }];
				} else {
					// Check for SVG content
					for (const block of codeBlocks) {
						if (block.lang === 'svg' || (block.lang === 'xml' && block.code.includes('<svg'))) {
							contents = [...contents, { type: 'svg', content: block.code }];
						}
					}
				}
			}
		});

		if (contents.length === 0) {
			showBottomArtifacts.set(false);
			showBottomArtifacts.set(false);
		}

		selectedContentIdx = contents ? contents.length - 1 : 0;
	};

	function navigateContent(direction: 'prev' | 'next') {
		selectedContentIdx =
			direction === 'prev'
				? Math.max(selectedContentIdx - 1, 0)
				: Math.min(selectedContentIdx + 1, contents.length - 1);
	}

	const submitHref = (e: Event) => {
		const chatInput = document.getElementById('chat-input');
		if (chatInput) {
			let textToSet = `Give me more information about: "${e.target.innerHTML.toString()}".`;
			chatInput.innerHTML = textToSet; // Set the innerHTML directly
			setTimeout(() => {
				document.getElementById('send-message-button')?.click();
			}, 400);
		}
	};

	onMount(() => {
		document.getElementById('#BottomArtifact')?.scrollIntoView({ behavior: 'smooth' });
	});

	// Inject event listeners to dynamically rendered HTML content
	onMount(() => {
		// After content is rendered, add event listeners
		const bottomArtifact = document.getElementById('BottomArtifact');
		if (bottomArtifact) {
			const links = bottomArtifact.querySelectorAll(
				'a, tr, td, .nbg__button, .nbg__button__primary, .nbg__button__secondary, .nbg__button__danger, .nbg__button__icon, .nbg__button__primary__no__fill, .nbg__button__secondary__no__fill, .nbg__button__text__link, .nbg__button__copy, .nbg__button__sidebar, .nbg__cta__arrow, .nbg__cta__rounded, .nbg__support__cta__arrow, .nbg__blog__cta__button, .nbg__feature__card__button, .nbg__advantage__card__tag '
			); // Select all links inside BottomArtifact
			links.forEach((link) => {
				link.addEventListener('click', (e) => {
					if ($bottomHistory.messages[$bottomHistory.currentId].done) {
						submitHref(e); // Trigger the function when a link is clicked
					}
				});
			});
		}
	});
	$: {
		const bottomArtifact = document.getElementById('BottomArtifact');
		if (bottomArtifact) {
			const links = bottomArtifact.querySelectorAll('a'); // Select all links inside BottomArtifact
			links.forEach((link) => {
				link.addEventListener('click', (e) => {
					if ($bottomHistory.messages[$bottomHistory.currentId].done) {
						submitHref(e); // Trigger the function when a link is clicked
					}
				});
			});
		}
	}
</script>

<div
	id="bottom-artifact"
	class="absolute bg-gray-50 dark:bg-gray-850 z-50 w-full max-w-full flex flex-col rounded-md shadow-lg"
	style="bottom:5px;left:5px;right:15px;height:380px;overflow-y:auto;padding: 6px;transition: all 0.3s ease-in-out;"
>
	<div class="relative flex flex-col" style="">
		<div class="w-full h-full flex-1 relative">
			{#if overlay}
				<div class="absolute top-0 left-0 right-0 bottom-0 z-10"></div>
			{/if}

			<div class="absolute pointer-events-none z-50 w-full flex items-center justify-start p-4">
				<button
					class="self-center pointer-events-auto p-1 rounded-full bg-white dark:bg-gray-850"
					on:click={() => {
						showBottomArtifacts.set(false);
					}}
				>
					<ArrowLeft className="size-3.5 text-gray-900 dark:text-white" />
				</button>
			</div>

			<div class="absolute pointer-events-none z-50 w-full flex items-center justify-end p-4">
				<button
					class="self-center pointer-events-auto p-1 rounded-full bg-white dark:bg-gray-850"
					on:click={() => {
						dispatch('close');
						showBottomArtifacts.set(false);
					}}
				>
					<XMark className="size-3.5 text-gray-900 dark:text-white" />
				</button>
			</div>

			<div class="flex-1 w-full h-full">
				<div class="h-full flex flex-col">
					{#if contents.length > 0}
						<div
							class="max-w-full w-full h-full"
							role="button"
							tabindex="0"
							on:click={() => {
								dispatch('submit', 'xaxa');
							}}
							on:keydown={(e) => {
								if (e.key === 'Enter' || e.key === ' ') {
									dispatch('submit', 'xaxa');
								}
							}}
						>
							{#if contents[selectedContentIdx].type === 'web'}
								{@html `${contents[selectedContentIdx].content}`}
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
</div>
