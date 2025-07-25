<script lang="ts">
	import PiiAwareText from './PiiAwareText.svelte';

	export let text: string;
	export let id: string;
	export let conversationId: string;
	export let done: boolean;
</script>

<PiiAwareText {text} {id} {conversationId} {done} /> 