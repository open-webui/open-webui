<script lang="ts">
	import { page } from '$app/stores';

	import Chat from '$lib/components/chat/Chat.svelte';

	export let data;
</script>

<Chat chatIdProp={$page.params.id} preloadedData={data} />
