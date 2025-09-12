<script lang="ts">
	import { page } from '$app/stores';
	import NotePlusEditor from '$lib/components/noteplus/NotePlusEditor.svelte';
</script>

<NotePlusEditor id={$page.params.id} />