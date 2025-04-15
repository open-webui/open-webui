<script lang="ts">
	import Chat from '$lib/components/chat/Chat.svelte';
	import Sidebar from '$lib/components/layout/Sidebar.svelte';
	import KnowledgeManager from '$lib/IONOS/components/knowledge/KnowledgeManager.svelte';

	let chat: Chat;
</script>

<Sidebar on:new-chat={() => chat?.newChat()} />
<Chat bind:this={chat} />
<KnowledgeManager />
