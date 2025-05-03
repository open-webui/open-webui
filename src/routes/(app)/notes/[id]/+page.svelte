<script lang="ts">
	import { page } from '$app/stores';
	import NoteEditor from '$lib/components/notes/NoteEditor.svelte';
</script>

<NoteEditor id={$page.params.id} />
