<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { onMount, getContext } from 'svelte';
	const i18n: any = getContext('i18n');

	import {
		artifactCode,
		chatId,
		config,
		settings,
		showArtifacts,
		artifactContents
	} from '$lib/stores';
	import { copyToClipboard, createMessagesList } from '$lib/utils';
	import { injectCsp } from '$lib/utils/csp';

	import Icon from './FileNav/Icon.svelte';
	import Tooltip from '../common/Tooltip.svelte';
	import SvgPanZoom from '../common/SVGPanZoom.svelte';
	import ArrowLeft from '../icons/ArrowLeft.svelte';

	export let overlay = false;

	let contents: Array<{ type: string; content: string }> = [];
	let selectedContentIdx = 0;

	let copied = false;
	let iframeElement: HTMLIFrameElement;

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
						console.info('External navigation blocked:', url.href);
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

	const downloadArtifact = () => {
		const blob = new Blob([contents[selectedContentIdx].content], { type: 'text/html' });
		const url = URL.createObjectURL(blob);
		const a = document.createElement('a');
		a.href = url;
		a.download = `artifact-${$chatId}-${selectedContentIdx}.html`;
		document.body.appendChild(a);
		a.click();
		document.body.removeChild(a);
		URL.revokeObjectURL(url);
	};

	onMount(() => {
		const unsubscribeArtifactContents = artifactContents.subscribe((value) => {
			const newContents = value ?? [];
			console.log('Artifact contents updated:', newContents);

			if (newContents.length === 0) {
				showArtifacts.set(false);
				selectedContentIdx = 0;
			} else if (newContents.length > contents.length) {
				selectedContentIdx = newContents.length - 1;
			} else if (selectedContentIdx > newContents.length - 1) {
				selectedContentIdx = newContents.length - 1;
			}

			contents = newContents;
		});

		const unsubscribeArtifactCode = artifactCode.subscribe((value) => {
			if (contents && value) {
				const codeIdx = contents.findIndex((content) => content.content.includes(value));
				selectedContentIdx = codeIdx !== -1 ? codeIdx : 0;
			}
		});

		return () => {
			unsubscribeArtifactCode();
			unsubscribeArtifactContents();
			artifactCode.set(null);
		};
	});
</script>

<div class="w-full h-full relative flex flex-col" id="artifacts-container">
	<div class="w-full min-h-0 flex flex-col flex-1 relative">
		{#if contents.length > 0}
			<div
				class="pointer-events-auto z-20 shrink-0 flex items-center justify-between gap-2 px-2 pb-1.5"
			>
				<div class="flex min-w-0 items-center gap-0.5" dir="ltr">
					<button
						aria-label={$i18n.t('Previous version')}
						class="flex h-5 w-5 shrink-0 items-center justify-center rounded text-gray-400 transition-colors duration-100 hover:text-gray-600 disabled:text-gray-200 dark:text-gray-500 dark:hover:text-gray-300 dark:disabled:text-gray-700"
						on:click={() => navigateContent('prev')}
						disabled={selectedContentIdx === 0}
						><Icon name="chevron-left" size={11} strokeWidth={1.5} /></button
					>
					<span class="truncate text-xs text-gray-500 dark:text-gray-400">
						{$i18n.t('Version {{selectedVersion}} of {{totalVersions}}', {
							selectedVersion: selectedContentIdx + 1,
							totalVersions: contents.length
						})}
					</span>
					<button
						aria-label={$i18n.t('Next version')}
						class="flex h-5 w-5 shrink-0 items-center justify-center rounded text-gray-400 transition-colors duration-100 hover:text-gray-600 disabled:text-gray-200 dark:text-gray-500 dark:hover:text-gray-300 dark:disabled:text-gray-700"
						on:click={() => navigateContent('next')}
						disabled={selectedContentIdx === contents.length - 1}
						><Icon name="chevron-right" size={11} strokeWidth={1.5} /></button
					>
				</div>
				<div class="flex shrink-0 items-center gap-0.5">
					<Tooltip content={copied ? $i18n.t('Copied') : $i18n.t('Copy')}>
						<button
							aria-label={copied ? $i18n.t('Copied') : $i18n.t('Copy')}
							class="flex h-5 w-5 items-center justify-center rounded text-gray-400 transition-colors duration-100 hover:text-gray-600 dark:text-gray-500 dark:hover:text-gray-300"
							on:click={() => {
								copyToClipboard(contents[selectedContentIdx].content);
								copied = true;
								setTimeout(() => {
									copied = false;
								}, 2000);
							}}><Icon name={copied ? 'check' : 'copy'} size={11} strokeWidth={1.4} /></button
						>
					</Tooltip>
					<Tooltip content={$i18n.t('Download')}>
						<button
							aria-label={$i18n.t('Download')}
							class="flex h-5 w-5 items-center justify-center rounded text-gray-400 transition-colors duration-100 hover:text-gray-600 dark:text-gray-500 dark:hover:text-gray-300"
							on:click={downloadArtifact}
							><Icon name="download" size={11} strokeWidth={1.4} /></button
						>
					</Tooltip>
					{#if contents[selectedContentIdx].type === 'iframe'}
						<Tooltip content={$i18n.t('Open in full screen')}>
							<button
								aria-label={$i18n.t('Open in full screen')}
								class="flex h-5 w-5 items-center justify-center rounded text-gray-400 transition-colors duration-100 hover:text-gray-600 dark:text-gray-500 dark:hover:text-gray-300"
								on:click={showFullScreen}><Icon name="expand" size={11} strokeWidth={1.4} /></button
							>
						</Tooltip>
					{/if}
				</div>
			</div>
		{/if}

		{#if overlay}
			<div class=" absolute top-0 left-0 right-0 bottom-0 z-10"></div>
		{/if}

		<div class="flex-1 w-full min-h-0 bg-white dark:bg-gray-850">
			<div class=" h-full flex flex-col">
				{#if contents.length > 0}
					<div class="max-w-full w-full h-full">
						{#if contents[selectedContentIdx].type === 'iframe'}
							<iframe
								bind:this={iframeElement}
								title={$i18n.t('Content')}
								srcdoc={injectCsp(
									contents[selectedContentIdx].content,
									$config?.ui?.iframe_csp ?? ''
								)}
								class="w-full border-0 h-full rounded-none"
								sandbox="{($settings?.iframeSandboxAllowScripts ?? true)
									? 'allow-scripts'
									: ''}{($settings?.iframeSandboxAllowDownloads ?? true)
									? ' allow-downloads'
									: ''}{($settings?.iframeSandboxAllowForms ?? true)
									? ' allow-forms'
									: ''}{($settings?.iframeSandboxAllowSameOrigin ?? false)
									? ' allow-same-origin'
									: ''}"
								on:load={iframeLoadHandler}
							></iframe>
						{:else if contents[selectedContentIdx].type === 'svg'}
							<SvgPanZoom
								className=" w-full h-full max-h-full overflow-hidden"
								svg={contents[selectedContentIdx].content}
							/>
						{/if}
					</div>
				{:else}
					<div class="m-auto p-6 text-center font-normal text-xs text-gray-900 dark:text-white">
						{$i18n.t('No HTML, CSS, or JavaScript content found.')}
					</div>
				{/if}
			</div>
		</div>
	</div>
</div>
