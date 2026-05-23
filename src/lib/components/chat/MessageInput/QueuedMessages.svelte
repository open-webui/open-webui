<script lang="ts">
	import { getContext, tick } from 'svelte';
	import Tooltip from '../../common/Tooltip.svelte';
	import XMark from '../../icons/XMark.svelte';

	const i18n: any = getContext('i18n');

	export let queue: any[] = [];
	export let editQueuedMessage: (id: string, text: string) => void = () => {};
	export let removeQueuedMessage: (id: string) => void = () => {};

	let editingId: string | null = null;
	let editingText = '';
	let editingTextarea: HTMLTextAreaElement | null = null;

	const startEdit = async (item: any) => {
		editingId = item.id;
		editingText = item.prompt ?? '';
		await tick();
		editingTextarea?.focus();
		// Place caret at end
		const len = editingTextarea?.value.length ?? 0;
		editingTextarea?.setSelectionRange(len, len);
	};

	const commitEdit = () => {
		if (!editingId) return;
		const id = editingId;
		const text = editingText;
		editingId = null;
		editingText = '';
		// Cancel if the user emptied the message — that's effectively unqueueing.
		if (text.trim() === '') {
			removeQueuedMessage(id);
		} else {
			editQueuedMessage(id, text);
		}
	};

	const cancelEdit = () => {
		editingId = null;
		editingText = '';
	};

	const onEditorKeydown = (e: KeyboardEvent) => {
		if (e.key === 'Escape') {
			e.preventDefault();
			cancelEdit();
			return;
		}
		// Cmd/Ctrl+Enter (or just Enter) commits — match the chat input vibe.
		if (e.key === 'Enter' && !e.shiftKey) {
			e.preventDefault();
			commitEdit();
		}
	};

	const preview = (text: string, max = 120) => {
		if (!text) return '';
		const collapsed = text.replace(/\s+/g, ' ').trim();
		return collapsed.length > max ? collapsed.slice(0, max - 1) + '…' : collapsed;
	};
</script>

{#if queue.length > 0}
	<div class="mx-1 mt-2 mb-1 flex flex-col gap-1.5" aria-label={$i18n.t('Queued messages')}>
		{#each queue as item, idx (item.id)}
			<div
				class="group flex items-start gap-2 rounded-2xl border-hairline border-gray-200 dark:border-gray-800 bg-gray-50/80 dark:bg-gray-850/60 px-3 py-2 text-sm"
			>
				<div
					class="mt-0.5 flex size-5 shrink-0 items-center justify-center rounded-full bg-book-cloth/15 text-[10px] font-semibold text-book-cloth dark:bg-manilla-dark dark:text-gray-100"
					aria-hidden="true"
				>
					{idx + 1}
				</div>

				<div class="min-w-0 flex-1">
					{#if editingId === item.id}
						<textarea
							bind:this={editingTextarea}
							bind:value={editingText}
							on:keydown={onEditorKeydown}
							rows="2"
							class="w-full resize-none bg-transparent text-gray-800 dark:text-gray-100 outline-hidden placeholder-gray-400"
							placeholder={$i18n.t('Edit queued message')}
						></textarea>
						<div class="mt-1 flex items-center gap-2">
							<button
								type="button"
								class="rounded-full bg-book-cloth px-3 py-1 text-xs font-medium text-white hover:bg-kraft"
								on:click={commitEdit}
							>
								{$i18n.t('Done')}
							</button>
							<button
								type="button"
								class="rounded-full px-3 py-1 text-xs text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800"
								on:click={cancelEdit}
							>
								{$i18n.t('Cancel')}
							</button>
							<span class="text-[10px] text-gray-400">
								{$i18n.t('Enter to save, Esc to cancel')}
							</span>
						</div>
					{:else}
						<button
							type="button"
							class="block w-full text-left text-gray-800 dark:text-gray-100 line-clamp-2 leading-snug hover:underline decoration-dotted underline-offset-2"
							title={$i18n.t('Click to edit')}
							on:click={() => startEdit(item)}
						>
							{preview(item.prompt)}
						</button>
						{#if (item.files ?? []).length > 0}
							<div class="mt-1 text-[11px] text-gray-500 dark:text-gray-400">
								{$i18n.t('{{count}} attached', { count: item.files.length })}
							</div>
						{/if}
					{/if}
				</div>

				{#if editingId !== item.id}
					<div class="flex shrink-0 items-center gap-1">
						<Tooltip content={$i18n.t('Edit')}>
							<button
								type="button"
								class="rounded-full p-1 text-gray-500 hover:bg-gray-100 hover:text-gray-700 dark:text-gray-400 dark:hover:bg-gray-800 dark:hover:text-gray-200"
								aria-label={$i18n.t('Edit queued message')}
								on:click={() => startEdit(item)}
							>
								<svg
									xmlns="http://www.w3.org/2000/svg"
									viewBox="0 0 20 20"
									fill="currentColor"
									class="size-4"
								>
									<path
										d="M2.695 14.763l-1.262 3.154a.5.5 0 00.65.65l3.155-1.262a4 4 0 001.343-.885L17.5 5.5a2.121 2.121 0 00-3-3L3.58 13.42a4 4 0 00-.885 1.343z"
									/>
								</svg>
							</button>
						</Tooltip>
						<Tooltip content={$i18n.t('Remove from queue')}>
							<button
								type="button"
								class="rounded-full p-1 text-gray-500 hover:bg-gray-100 hover:text-gray-700 dark:text-gray-400 dark:hover:bg-gray-800 dark:hover:text-gray-200"
								aria-label={$i18n.t('Remove queued message')}
								on:click={() => removeQueuedMessage(item.id)}
							>
								<XMark className="size-4" />
							</button>
						</Tooltip>
					</div>
				{/if}
			</div>
		{/each}
	</div>
{/if}
