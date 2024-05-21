<script lang="ts">
	import Chat from '$lib/components/chat/Chat.svelte';
	import { page } from '$app/stores';
</script>

<Chat chatIdProp={$page.params.id} />
