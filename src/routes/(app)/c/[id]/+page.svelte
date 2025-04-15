<script lang="ts">
	import { page } from '$app/stores';

	import Chat from '$lib/components/chat/Chat.svelte';
	import Sidebar from '$lib/components/layout/Sidebar.svelte';

	let chat: Chat;
</script>

<Sidebar on:new-chat={() => chat?.newChat()} />
<Chat bind:this={chat} chatIdProp={$page.params.id} />
