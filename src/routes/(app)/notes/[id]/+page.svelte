<script lang="ts">
	import { page } from '$app/stores';
	import { showSidebar } from '$lib/stores';

	import NoteEditor from '$lib/components/notes/NoteEditor.svelte';
</script>

<div id="note-container" class="w-full h-full {$showSidebar ? 'md:max-w-[calc(100%-260px)]' : ''}">
	<NoteEditor id={$page.params.id} />
</div>
