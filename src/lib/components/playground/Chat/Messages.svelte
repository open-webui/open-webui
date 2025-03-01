<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import Message from './Message.svelte';

	import { getI18nContext } from '$lib/contexts';
const i18n = getContext('i18n');

	let { messages = $bindable([]) } = $props();
</script>

<div class="py-3 space-y-3">
	{#each messages as message, idx}
		<Message
			{idx}
			{message}
			onDelete={() => {
				messages = messages.filter((message, messageIdx) => messageIdx !== idx);
			}}
		/>
	{/each}
</div>
