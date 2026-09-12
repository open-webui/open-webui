<script lang="ts">
	import { onMount } from 'svelte';

	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { showSidebar } from '$lib/stores';

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
		class="w-full h-full {$showSidebar ? 'md:max-w-[calc(100%-var(--sidebar-width))]' : ''}"
	>
		<NoteEditor id={$page.params.id} />
	</div>
{/if}
