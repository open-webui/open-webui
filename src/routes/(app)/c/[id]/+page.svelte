<script lang="ts">
	import { page } from '$app/stores';

	import Chat from '$lib/components/chat/Chat.svelte';

	export let data;

	$: preloadedDataPromise =
		data.chatPromise && data.taskResPromise
			? Promise.all([data.chatPromise, data.taskResPromise]).then(([chat, taskRes]) => ({
					chatId: data.chatId,
					chat,
					taskRes
				}))
			: null;
</script>

<Chat chatIdProp={$page.params.id} {preloadedDataPromise} />
