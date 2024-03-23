<script lang="ts">
	import { onMount, getContext } from 'svelte';

	const i18n = getContext('i18n');

	export let messages = [];
	let textAreaElement: HTMLTextAreaElement;
	onMount(() => {
		messages.forEach((message, idx) => {
			textAreaElement.style.height = '';
			textAreaElement.style.height = textAreaElement.scrollHeight + 'px';
		});
	});
</script>

<div class="py-3 space-y-3">
	{#each messages as message, idx}
		<div class="flex gap-2 group">
			<div class="flex items-start pt-1">
				<button
					class="px-2 py-1 text-sm font-semibold uppercase min-w-[6rem] text-left dark:group-hover:bg-gray-800 rounded-lg transition"
					on:click={() => {
						message.role = message.role === 'user' ? 'assistant' : 'user';
					}}>{$i18n.t(message.role)}</button
				>
			</div>

			<div class="flex-1">
				<!-- $i18n.t('a user') -->
				<!-- $i18n.t('an assistant') -->
				<textarea
					id="{message.role}-{idx}-textarea"
					bind:this={textAreaElement}
					class="w-full bg-transparent outline-none rounded-lg p-2 text-sm resize-none overflow-hidden"
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
						messages = messages.filter((message, messageIdx) => messageIdx !== idx);
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

		<hr class=" dark:border-gray-800" />
	{/each}

	<button
		class="flex items-center gap-2 px-2 py-1"
		on:click={() => {
			console.log(messages.at(-1));
			messages.push({
				role: (messages.at(-1)?.role ?? 'assistant') === 'user' ? 'assistant' : 'user',
				content: ''
			});
			messages = messages;
		}}
	>
		<div>
			<svg
				xmlns="http://www.w3.org/2000/svg"
				fill="none"
				viewBox="0 0 24 24"
				stroke-width="1.5"
				stroke="currentColor"
				class="w-5 h-5"
			>
				<path
					stroke-linecap="round"
					stroke-linejoin="round"
					d="M12 9v6m3-3H9m12 0a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z"
				/>
			</svg>
		</div>

		<div class=" text-sm font-medium">{$i18n.t('Add message')}</div>
	</button>
</div>
