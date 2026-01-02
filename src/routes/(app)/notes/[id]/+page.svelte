<script lang="ts">
	import { onMount } from 'svelte';

	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { showSidebar } from '$lib/stores';
	import { SIDEBAR_WIDTH } from '$lib/constants';

	import dayjs from '$lib/dayjs';
	import { createNoteHandler } from '$lib/components/notes/utils';

	import NoteEditor from '$lib/components/notes/NoteEditor.svelte';

	let loaded = false;

	onMount(async () => {
		loaded = true;
	});
</script>

{#if loaded}
	<div
		id="note-container"
		class="w-full h-full"
		style={$showSidebar ? `max-width: calc(100% - ${SIDEBAR_WIDTH}px)` : ''}
	>
		<NoteEditor id={$page.params.id} />
	</div>
{/if}
