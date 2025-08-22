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

<div class="flex gap-2 group">
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
			class="w-full bg-transparent outline-hidden rounded-lg p-2 text-sm resize-none overflow-hidden"
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

	<div class=" pt-1">
		<button
			class=" group-hover:text-gray-500 dark:text-gray-900 dark:hover:text-gray-300 transition"
			on:click={() => {
				onDelete();
			}}
		>
			<svg
				xmlns="http://www.w3.org/2000/svg"
				fill="none"
				viewBox="0 0 24 24"
				stroke-width="2"
				stroke="currentColor"
				class="w-5 h-5"
			>
				<path
					stroke-linecap="round"
					stroke-linejoin="round"
					d="M15 12H9m12 0a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z"
				/>
			</svg>
		</button>
	</div>
</div>
