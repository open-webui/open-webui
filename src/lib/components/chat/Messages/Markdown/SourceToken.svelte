<script lang="ts">
	import { getContext } from 'svelte';
	import type { Readable } from 'svelte/store';
	import type { Tokens } from 'marked';
	import { LinkPreview } from 'bits-ui';
	import { decodeString } from '$lib/utils';
	import { getParagraphIds } from '$lib/utils/citations';
	import ArrowLeft from '$lib/components/icons/ArrowLeft.svelte';
	import ArrowRight from '$lib/components/icons/ArrowRight.svelte';
	import Source from './Source.svelte';

	const i18n = getContext<typeof import('$lib/i18n').default>('i18n');
	const citations = getContext<Readable<any[]>>('citations');

	export let token: Tokens.Generic;
	export let onClick: Function = () => {};

	let openPreview = false;
	let sourceIdx = 0;

	$: if (!openPreview) sourceIdx = 0;

	// The sources this marker cites, each under the identifier it is cited by ("2" or "2#page").
	// Paragraphs of one source, as in [1#3][1#4], are one entry cited by "1#3,1#4".
	$: sources = [...new Set<string>(token.citationIdentifiers)]
		.map((id) => ({
			id,
			citation: $citations.find((citation) => citation.number === parseInt(id.split('#')[0]))
		}))
		.filter(({ citation }) => citation && citation.title !== 'N/A')
		.reduce(
			(entries: { id: string; citation: any; paragraphIds: number[] }[], { id, citation }) => {
				const paragraphIds = (citation.paragraphs ?? []).some(
					(paragraphs: any[]) => paragraphs?.length
				)
					? getParagraphIds([id])
					: [];
				const entry = paragraphIds.length
					? entries.find((entry) => entry.citation === citation && entry.paragraphIds.length)
					: null;
				if (entry) {
					entry.id = `${entry.id},${id}`;
					entry.paragraphIds = [...entry.paragraphIds, ...paragraphIds];
				} else {
					entries.push({ id, citation, paragraphIds });
				}
				return entries;
			},
			[]
		);

	$: label = sources.length > 0 ? formattedTitle(decodeString(sources[0].citation.title)) : '';

	// Helper function to return only the domain from a URL
	function getDomain(url: string): string {
		const domain = url.replace('http://', '').replace('https://', '').split(/[/?#]/)[0];

		if (domain.startsWith('www.')) {
			return domain.slice(4);
		}
		return domain;
	}

	// Helper function to check if text is a URL and return the domain
	function formattedTitle(title: string): string {
		if (title.startsWith('http')) {
			return getDomain(title);
		}

		return title;
	}

	const getDisplayTitle = (title: string) => {
		if (!title) return 'N/A';
		if (title.length > 30) {
			return title.slice(0, 15) + '...' + title.slice(-10);
		}
		return title;
	};

	const showSource = (idx: number) => {
		sourceIdx = (idx + sources.length) % sources.length;
	};

	// Left and right page the card wherever the focus is, as the chat input usually holds it.
	const arrowKeys = (_node: HTMLElement) => {
		const keydownHandler = (e: KeyboardEvent) => {
			if (e.metaKey || e.ctrlKey || e.altKey || e.shiftKey || e.isComposing) return;
			if (e.key !== 'ArrowLeft' && e.key !== 'ArrowRight') return;

			e.preventDefault();
			e.stopPropagation();
			showSource(sourceIdx + (e.key === 'ArrowLeft' ? -1 : 1));
		};

		window.addEventListener('keydown', keydownHandler, true);
		return { destroy: () => window.removeEventListener('keydown', keydownHandler, true) };
	};

	let marker: HTMLElement;

	// The answer text this marker follows, back to the marker before it or the start of its block
	const getClaim = () => {
		const block = marker?.closest('p, li, td, th, blockquote, h1, h2, h3, h4, h5, h6');
		if (!block) return '';
		const range = document.createRange();
		range.selectNodeContents(block);
		const previous = [...block.querySelectorAll('[data-citation]')]
			.filter((node) => node.compareDocumentPosition(marker) & Node.DOCUMENT_POSITION_FOLLOWING)
			.pop();
		if (previous) range.setStartAfter(previous);
		range.setEndBefore(marker);
		return range.toString();
	};

	const openSource = (id: string) => {
		openPreview = false;
		onClick(id, getClaim());
	};
</script>

{#if sources.length > 0}
	<LinkPreview.Root openDelay={200} closeDelay={100} bind:open={openPreview}>
		<LinkPreview.Trigger>
			{#snippet child({ props })}
				<button
					{...props}
					bind:this={marker}
					data-citation
					aria-label={sources.length === 1
						? $i18n.t('View source: {{title}}', { title: label })
						: `${getDisplayTitle(label)} +${sources.length - 1} more sources`}
					class="text-[0.625rem] w-fit translate-y-[2px] px-2 py-0.5 dark:bg-base-0/5 dark:text-base-0/80 dark:hover:text-base-0 bg-base-50 text-base-1000/80 hover:text-base-1000 transition rounded-xl"
					on:click={(e) => {
						// From the keyboard, the marker opens the source its card shows.
						if (sources.length === 1 || (openPreview && e.detail === 0)) {
							openSource(sources[sourceIdx].id);
						} else {
							openPreview = !openPreview;
						}
					}}
				>
					<span class="line-clamp-1">
						{getDisplayTitle(label)}
						{#if sources.length > 1}
							<span class="dark:text-base-0/50 text-base-1000/50">+{sources.length - 1}</span>
						{/if}
					</span>
				</button>
			{/snippet}
		</LinkPreview.Trigger>
		<LinkPreview.Portal>
			<LinkPreview.Content
				class="z-[9999] w-[20rem] max-w-[calc(100vw-1.5rem)] overflow-hidden rounded-2xl bg-base-0 shadow-[0_16px_40px_-28px_rgba(0,0,0,0.55)] ring-1 ring-base-1000/5 dark:bg-base-850 dark:text-base-0 dark:ring-base-0/10"
				side="bottom"
				align="start"
				sideOffset={6}
				collisionPadding={12}
			>
				{#if sources.length > 1}
					<!-- Focus stays on the marker, as losing it is what closes the card on touch. -->
					<!-- svelte-ignore a11y-no-static-element-interactions -->
					<div
						use:arrowKeys
						on:mousedown|preventDefault
						class="relative z-10 -mb-1.5 flex items-center gap-1 px-3 pt-2 text-[0.625rem] leading-none text-base-400 dark:text-base-500"
					>
						<button
							type="button"
							aria-label={$i18n.t('Previous')}
							class="p-0.5 transition hover:text-base-900 dark:hover:text-base-100"
							on:click={() => showSource(sourceIdx - 1)}
						>
							<ArrowLeft className="size-3" strokeWidth="2" />
						</button>
						<button
							type="button"
							aria-label={$i18n.t('Next')}
							class="p-0.5 transition hover:text-base-900 dark:hover:text-base-100"
							on:click={() => showSource(sourceIdx + 1)}
						>
							<ArrowRight className="size-3" strokeWidth="2" />
						</button>
						<div class="ml-auto px-0.5 tabular-nums" aria-live="polite">
							{sourceIdx + 1}/{sources.length}
						</div>
					</div>
				{/if}
				<!-- Every source shares one cell, so the card keeps its size while paging. -->
				<div class="grid">
					{#each sources as { id, citation, paragraphIds }, idx (id)}
						<div class="col-start-1 row-start-1 min-w-0 {idx === sourceIdx ? '' : 'invisible'}">
							<Source {citation} {paragraphIds} onClick={() => openSource(id)} />
						</div>
					{/each}
				</div>
			</LinkPreview.Content>
		</LinkPreview.Portal>
	</LinkPreview.Root>
{/if}
