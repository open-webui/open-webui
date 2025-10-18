<script lang="ts">
	import { page } from '$app/stores';
	import { onMount } from 'svelte';
	import { showSidebar } from '$lib/stores';
	import Chat from '$lib/components/chat/Chat.svelte';
</script>

<!-- Match other (app) pages: render Chat directly inside the (app) layout slot -->
<Chat />