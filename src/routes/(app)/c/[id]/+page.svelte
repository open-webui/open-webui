<script lang="ts">
	import { page } from '$app/stores';
	import Chat from '$lib/components/chat/Chat.svelte';
	// Help component removed as functionality now exists in TopRightControls
</script>

<Chat chatIdProp={$page.params.id} />
<Help />
