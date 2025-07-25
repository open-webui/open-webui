<!--
	Chat.svelte - Legacy wrapper for backward compatibility
	
	This component has been refactored into smaller, more maintainable components.
	All functionality is now in Chat/Chat.svelte
	
	This file maintains backward compatibility for existing imports.
-->
<script lang="ts">
	import Chat from './Chat/Chat.svelte';
	
	export let chatIdProp = '';
</script>

<Chat {chatIdProp} />