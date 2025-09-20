<script lang="ts">
	import { onMount, getContext } from 'svelte';

	const i18n = getContext('i18n');

	import Skeleton from '$lib/components/chat/Messages/Skeleton.svelte';
	import Markdown from '$lib/components/chat/Messages/Markdown.svelte';
	import Pencil from '$lib/components/icons/Pencil.svelte';
	import Textarea from '$lib/components/common/Textarea.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import ArrowUpLeft from '$lib/components/icons/ArrowUpLeft.svelte';

	export let message;
	export let idx;

	export let onDelete;
	export let onEdit;
	export let onInsert;

	let textAreaElement: HTMLTextAreaElement;
</script>

<div class="flex flex-col gap-1 group">
	<div class="flex items-center justify-between pt-1">
		<div class="py-1 text-sm font-semibold uppercase min-w-[6rem] text-left rounded-lg transition">
			{$i18n.t(message.role)}
		</div>

		<div class="flex items-center gap-2">
			<Tooltip placement="top" content={$i18n.t('Insert')}>
				<button
					class=" text-transparent group-hover:text-gray-500 dark:hover:text-gray-300 transition"
					on:click={() => {
						onInsert();
					}}
				>
					<ArrowUpLeft className="size-3.5" strokeWidth="2" />
				</button>
			</Tooltip>

			<Tooltip placement="top" content={$i18n.t('Edit')}>
				<button
					class=" text-transparent group-hover:text-gray-500 dark:hover:text-gray-300 transition"
					on:click={() => {
						onEdit();
					}}
				>
					<Pencil className="size-3.5" strokeWidth="2" />
				</button>
			</Tooltip>

			<Tooltip placement="top" content={$i18n.t('Delete')}>
				<button
					class=" text-transparent group-hover:text-gray-500 dark:hover:text-gray-300 transition"
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
						class="size-4"
					>
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							d="M15 12H9m12 0a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z"
						/>
					</svg>
				</button>
			</Tooltip>
		</div>
	</div>

	<div class="flex-1">
		<!-- $i18n.t('a user') -->
		<!-- $i18n.t('an assistant') -->

		{#if !(message?.done ?? true) && message?.content === ''}
			<div class="">
				<Skeleton size="sm" />
			</div>
		{:else if message?.edit === true}
			<Textarea
				className="w-full bg-transparent outline-hidden text-sm resize-none overflow-hidden"
				placeholder={$i18n.t(`Enter {{role}} message here`, {
					role: message.role === 'user' ? $i18n.t('a user') : $i18n.t('an assistant')
				})}
				bind:value={message.content}
				onBlur={() => {
					message.edit = false;
				}}
			/>
		{:else}
			<div class=" markdown-prose-sm text-sm">
				<Markdown id={`note-message-${idx}`} content={message.content} />
			</div>
		{/if}
	</div>
</div>
