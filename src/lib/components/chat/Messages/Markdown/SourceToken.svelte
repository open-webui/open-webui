<script lang="ts">
	import { getContext } from 'svelte';
	import { readable, type Readable } from 'svelte/store';
	import { LinkPreview } from 'bits-ui';
	import { decodeString } from '$lib/utils';
	import {
		buildTextFragmentUrl,
		getSafeCitationUrl,
		parseCitationIdentifier,
		selectCitationEntry,
		type CitationEntry
	} from '$lib/utils/citations';
	import {
		activeCitationHovercard,
		clampCitationIndex,
		closeCitationHovercard,
		openCitationHovercard,
		stepCitationIndex
	} from '$lib/utils/citationHovercard';
	import CitationHovercard from '../Citations/CitationHovercard.svelte';
	import CitationPreview from '../Citations/CitationPreview.svelte';
	import CitationSourceIcon from '../Citations/CitationSourceIcon.svelte';
	import Source from './Source.svelte';

	export let token;
	export let sourceIds: string[] = [];
	export let onClick: (identifier: string | number) => void = () => {};

	let openPreview = false;
	let selectedIndex = 0;
	const hovercardOwner = {};
	const citationEntries =
		getContext<Readable<CitationEntry[]>>('citationEntries') ?? readable<CitationEntry[]>([]);

	$: identifiers = token.citationIdentifiers ?? token.ids ?? [];
	$: selectedIndex = clampCitationIndex(selectedIndex, identifiers.length);
	$: if (openPreview && $activeCitationHovercard !== hovercardOwner) openPreview = false;

	const setOpenPreview = (open: boolean) => {
		openPreview = open;
		if (open) {
			openCitationHovercard(hovercardOwner);
		} else {
			closeCitationHovercard(hovercardOwner);
		}
	};

	const moveSelection = (delta: number) => {
		selectedIndex = stepCitationIndex(selectedIndex, identifiers.length, delta);
	};

	const handleNavigationKey = (event: KeyboardEvent) => {
		if (identifiers.length <= 1 || !['ArrowLeft', 'ArrowRight'].includes(event.key)) return;
		event.preventDefault();
		event.stopPropagation();
		moveSelection(event.key === 'ArrowLeft' ? -1 : 1);
	};

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

	const entryFor = (identifier: string | number) =>
		$citationEntries[parseCitationIdentifier(identifier).sourceIndex];
	const titleFor = (identifier: string | number) =>
		sourceIds[parseCitationIdentifier(identifier).sourceIndex] ?? 'N/A';
	const linkFor = (entry: CitationEntry, identifier: string | number) => {
		const selected = selectCitationEntry(entry, identifier);
		return getSafeCitationUrl(
			buildTextFragmentUrl({
				source: selected.source,
				metadata: selected.metadata[0],
				document: selected.document[0]
			})
		);
	};
</script>

{#if sourceIds}
	{#if (token?.ids ?? []).length == 1}
		{@const identifier = token.citationIdentifiers?.[0] ?? token.ids[0]}
		{@const entry = entryFor(identifier)}
		{#if entry}
			{@const selected = selectCitationEntry(entry, identifier)}
			{@const href = linkFor(entry, identifier)}
			<CitationHovercard
				{entry}
				{identifier}
				title={titleFor(identifier)}
				{href}
				source={selected.source}
				metadata={selected.metadata[0]}
				{onClick}
			/>
		{:else}
			<Source id={identifier} title={titleFor(identifier)} {onClick} />
		{/if}
	{:else}
		{@const firstIdentifier = token.citationIdentifiers?.[0] ?? token.ids[0]}
		{@const firstEntry = entryFor(firstIdentifier)}
		{@const firstSelection = firstEntry
			? selectCitationEntry(firstEntry, firstIdentifier)
			: undefined}
		<LinkPreview.Root
			open={openPreview}
			onOpenChange={setOpenPreview}
			openDelay={200}
			closeDelay={100}
		>
			<LinkPreview.Trigger>
				<button
					aria-label={`${getDisplayTitle(formattedTitle(decodeString(titleFor(token.ids[0]))))} +${(token?.ids ?? []).length - 1} more sources`}
					class="text-[0.625rem] w-fit translate-y-[2px] px-2 py-0.5 dark:bg-white/5 dark:text-white/80 dark:hover:text-white bg-gray-50 text-black/80 hover:text-black transition rounded-xl inline-flex items-center gap-1 !no-underline hover:!no-underline visited:!no-underline focus-visible:!no-underline"
					on:keydown={handleNavigationKey}
					on:click={() => {
						setOpenPreview(!openPreview);
					}}
				>
					<CitationSourceIcon
						source={firstSelection?.source ?? { name: titleFor(firstIdentifier) }}
						metadata={firstSelection?.metadata[0]}
						size={12}
					/>
					<span class="line-clamp-1">
						{getDisplayTitle(formattedTitle(decodeString(titleFor(token.ids[0]))))}
						<span class="dark:text-white/50 text-black/50">+{(token?.ids ?? []).length - 1}</span>
					</span>
				</button>
			</LinkPreview.Trigger>
			<LinkPreview.Portal>
				<LinkPreview.Content class="z-[999]" align="start" sideOffset={6}>
					{@const identifier = identifiers[selectedIndex]}
					{@const entry = entryFor(identifier)}
					<div>
						{#if entry}
							<CitationPreview
								{entry}
								{identifier}
								position={selectedIndex}
								count={identifiers.length}
								onPrevious={() => moveSelection(-1)}
								onNext={() => moveSelection(1)}
								onNavigateKey={handleNavigationKey}
							/>
						{:else}
							<Source id={identifier} title={titleFor(identifier)} {onClick} />
						{/if}
					</div>
				</LinkPreview.Content>
			</LinkPreview.Portal>
		</LinkPreview.Root>
	{/if}
{:else}
	<span>{token.raw}</span>
{/if}
