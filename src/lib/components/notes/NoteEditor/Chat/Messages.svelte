<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import Message from './Message.svelte';

	const i18n = getContext('i18n');

	export let messages = [];
</script>

<div class="space-y-3 pb-12">
	{#each messages as message, idx}
		<Message
			{message}
			{idx}
			onEdit={() => {
				messages = messages.map((msg, messageIdx) => {
					if (messageIdx === idx) {
						return { ...msg, edit: true };
					}
					return msg;
				});
			}}
			onDelete={() => {
				messages = messages.filter((message, messageIdx) => messageIdx !== idx);
			}}
		/>
	{/each}
</div>
