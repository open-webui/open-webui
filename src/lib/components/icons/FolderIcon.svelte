<script lang="ts">
	import Folder from './Folder.svelte';
	import FolderOpen from './FolderOpen.svelte';
	export let open = false;
	export let className = 'size-4';
	export let strokeWidth = '1.5';
</script>

{#if open}
	<FolderOpen {className} {strokeWidth} />
{:else}
	<Folder {className} {strokeWidth} />
{/if}
