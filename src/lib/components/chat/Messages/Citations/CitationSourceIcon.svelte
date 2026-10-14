<script lang="ts">
	import FileTypeIcon from '$lib/components/chat/FileNav/FileTypeIcon.svelte';
	import { getCitationIconInfo, type SourceInfo, type SourceMetadata } from '$lib/utils/citations';

	export let source: SourceInfo | undefined = undefined;
	export let metadata: SourceMetadata | undefined = undefined;
	export let size = 12;
	export let imageClass = 'rounded-sm';

	let failedFaviconUrl: string | null = null;
	$: icon = getCitationIconInfo(source, metadata, undefined, size <= 16 ? 16 : 32);
	$: faviconUrl = icon.faviconUrl !== failedFaviconUrl ? icon.faviconUrl : null;
</script>

{#if icon.documentName}
	<FileTypeIcon name={icon.documentName} {size} />
{:else if faviconUrl}
	<img
		src={faviconUrl}
		alt=""
		referrerpolicy="no-referrer"
		class={`shrink-0 ${imageClass}`}
		style={`width: ${size}px; height: ${size}px;`}
		on:error={(event) => {
			failedFaviconUrl = event.currentTarget.src;
		}}
	/>
{:else}
	<FileTypeIcon name="" {size} />
{/if}
