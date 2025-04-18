<script lang="ts">
	import { page } from '$app/stores';
	import CodeAssistChat from '$lib/components/chat/CodeAssistChat.svelte';
	import Help from '$lib/components/layout/Help.svelte';
</script>

<Help />
<CodeAssistChat chatIdProp={$page.params.id} />
