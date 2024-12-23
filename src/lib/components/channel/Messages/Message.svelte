<script lang="ts">
	import Markdown from '$lib/components/chat/Messages/Markdown.svelte';

	export let message;
</script>

{#if message}
	<div>
		<div>
			<Markdown id={message.id} content={message.content} />
		</div>
	</div>
{/if}
