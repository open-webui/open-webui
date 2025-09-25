<script lang="ts">
	import PiiAwareText from './PiiAwareText.svelte';

	export let token: Token;
	export let id: string;
	export let conversationId: string;
	export let done: boolean;
</script>

<PiiAwareText {token} {id} {conversationId} {done} />
