<script lang="ts">
	import { LinkPreview } from 'bits-ui';
	import {
		activeCitationHovercard,
		closeCitationHovercard,
		openCitationHovercard
	} from '$lib/utils/citationHovercard';
	import type { CitationEntry, SourceInfo, SourceMetadata } from '$lib/utils/citations';
	import Source from '../Markdown/Source.svelte';
	import CitationPreview from './CitationPreview.svelte';

	export let entry: CitationEntry;
	export let identifier: string | number;
	export let title: string;
	export let href: string | null = null;
	export let source: SourceInfo | undefined = undefined;
	export let metadata: SourceMetadata | undefined = undefined;
	export let onClick: (identifier: string | number) => void = () => {};

	let open = false;
	const owner = {};

	$: if (open && $activeCitationHovercard !== owner) open = false;

	const handleOpenChange = (nextOpen: boolean) => {
		open = nextOpen;
		if (nextOpen) {
			openCitationHovercard(owner);
		} else {
			closeCitationHovercard(owner);
		}
	};
</script>

<LinkPreview.Root {open} onOpenChange={handleOpenChange} openDelay={200} closeDelay={100}>
	<LinkPreview.Trigger>
		<Source id={identifier} {title} {href} {source} {metadata} {onClick} />
	</LinkPreview.Trigger>
	<LinkPreview.Portal>
		<LinkPreview.Content class="z-[999]" align="start" sideOffset={6}>
			<CitationPreview {entry} {identifier} />
		</LinkPreview.Content>
	</LinkPreview.Portal>
</LinkPreview.Root>
