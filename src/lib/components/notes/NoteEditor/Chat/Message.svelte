<script lang="ts">
	import { onMount, getContext } from 'svelte';

	const i18n = getContext('i18n');

	export let message;
	export let idx;

	export let onDelete;

	let textAreaElement: HTMLTextAreaElement;

	onMount(() => {
		textAreaElement.style.height = '';
		textAreaElement.style.height = textAreaElement.scrollHeight + 'px';
	});
</script>

<div class="flex flex-col gap-1 group">
	<div class="flex items-start pt-1">
		<div
			class="px-2 py-1 text-sm font-semibold uppercase min-w-[6rem] text-left rounded-lg transition"
		>
			{$i18n.t(message.role)}
		</div>
	</div>

	<div class="flex-1">
		<!-- $i18n.t('a user') -->
		<!-- $i18n.t('an assistant') -->
		<textarea
			id="{message.role}-{idx}-textarea"
			bind:this={textAreaElement}
			class="w-full bg-transparent outline-hidden rounded-lg px-2 text-sm resize-none overflow-hidden"
			placeholder={$i18n.t(`Enter {{role}} message here`, {
				role: message.role === 'user' ? $i18n.t('a user') : $i18n.t('an assistant')
			})}
			rows="1"
			on:input={(e) => {
				textAreaElement.style.height = '';
				textAreaElement.style.height = textAreaElement.scrollHeight + 'px';
			}}
			on:focus={(e) => {
				textAreaElement.style.height = '';
				textAreaElement.style.height = textAreaElement.scrollHeight + 'px';

				// e.target.style.height = Math.min(e.target.scrollHeight, 200) + 'px';
			}}
			bind:value={message.content}
		/>
	</div>
</div>
