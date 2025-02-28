<script lang="ts">
	import Chat from '$lib/components/chat/Chat.svelte';
	import Help from '$lib/components/layout/Help.svelte';
	import Sidebar from '$lib/components/layout/Sidebar.svelte';

	let chat: Chat;
</script>

<Sidebar on:new-chat={() => chat?.newChat()} />
<Help />
<Chat bind:this={chat} />
