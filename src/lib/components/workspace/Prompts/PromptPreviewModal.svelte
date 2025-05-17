<script lang="ts">
	import { createEventDispatcher, getContext } from 'svelte';
	import { toast } from 'svelte-sonner'; // Import toast
	import Modal from '$lib/components/common/Modal.svelte';
	import Close from '$lib/components/icons/XMark.svelte';
	import ClipboardDocument from '$lib/components/icons/Clipboard.svelte'; // Import new icon

	export let show: boolean;
	export let prompt: { title: string; command: string; content: string; [key: string]: any };

	const dispatch = createEventDispatcher();
	const i18n = getContext('i18n');

	function closeModal() {
		show = false;
		dispatch('close');
	}

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Escape') {
			closeModal();
		}
	}

	async function copyContentToClipboard() {
		if (!prompt?.content) {
			toast.error($i18n.t('No content to copy.'));
			return;
		}
		try {
			await navigator.clipboard.writeText(prompt.content);
			toast.success($i18n.t('Prompt content copied to clipboard!'));
		} catch (err) {
			toast.error($i18n.t('Failed to copy content.'));
			console.error('Failed to copy: ', err);
		}
	}
</script>

<svelte:window on:keydown={handleKeydown} />

{#if show && prompt}
	<Modal bind:show on:close={closeModal} size="lg">
		<div class="p-5 sm:p-6 flex flex-col gap-4 bg-white dark:bg-gray-900 rounded-lg shadow-xl">
			<div class="flex justify-between items-center">
				<h3 class="text-xl font-semibold text-gray-800 dark:text-gray-100">
					{prompt.title}
				</h3>
				<button
					on:click={closeModal}
					class="p-1 rounded-full text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
					aria-label={$i18n.t('Close')}
				>
					<Close className="size-5" />
				</button>
			</div>

			<div class="text-sm text-gray-600 dark:text-gray-400">
				<span class="font-medium text-gray-700 dark:text-gray-300">{$i18n.t('Command:')}</span> {prompt.command}
			</div>

			<div class="mt-1 border-t border-gray-200 dark:border-gray-700 pt-3">
				<h4 class="text-md font-medium text-gray-700 dark:text-gray-300 mb-2">{$i18n.t('Content:')}</h4>
				<div
					class="relative group max-h-[60vh] overflow-y-auto bg-gray-50 dark:bg-gray-800 p-3 rounded-md text-sm"
				>
					<pre
						class="whitespace-pre-wrap break-words font-sans text-gray-700 dark:text-gray-200 pr-10"
					>{prompt.content || $i18n.t('No content available.')}</pre>
					
					{#if prompt.content}
						<button
							type="button"
							class="absolute top-2 right-2 p-1.5 rounded-md text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 hover:bg-gray-200/70 dark:hover:bg-gray-700/70 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 focus:ring-offset-gray-50 dark:focus:ring-offset-gray-800 transition-all opacity-0 group-hover:opacity-100 focus:opacity-100"
							on:click={copyContentToClipboard}
							title={$i18n.t('Copy content to clipboard')}
							aria-label={$i18n.t('Copy content to clipboard')}
						>
							<ClipboardDocument className="size-4" />
						</button>
					{/if}
				</div>
			</div>

			<div class="flex justify-end mt-3">
				<button
					type="button"
					class="px-4 py-2 text-sm font-medium rounded-lg bg-gray-100 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-200 transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 dark:focus:ring-offset-gray-800"
					on:click={closeModal}
				>
					{$i18n.t('Close')}
				</button>
			</div>
		</div>
	</Modal>
{/if}