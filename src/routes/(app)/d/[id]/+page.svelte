<script lang="ts">
	import { page } from '$app/stores';
	import CodeAssistChat from '$lib/components/chat/CodeAssistChat.svelte';
	//AXL:김정민 일단 없어서 주석처리
	// import Help from '$lib/components/layout/Help.svelte';
</script>

<!-- <Help /> -->
<CodeAssistChat chatIdProp={$page.params.id} />
