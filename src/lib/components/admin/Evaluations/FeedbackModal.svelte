<script lang="ts">
	import Modal from '$lib/components/common/Modal.svelte';
	import { getContext } from 'svelte';
	const i18n = getContext('i18n');

	export let show = false;
	export let selectedFeedback = null;

	export let onClose: () => void = () => {};

	const close = () => {
		show = false;
		onClose();
	};
</script>

<Modal size="sm" bind:show>
	{#if selectedFeedback}
		<div>
			<div class="flex justify-between dark:text-gray-300 px-5 pt-4 pb-2">
				<div class="text-lg font-medium self-center">
					{$i18n.t('Feedback Details')}
				</div>
				<button class="self-center" on:click={close} aria-label="Close">
					<svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 20 20"
						fill="currentColor"
						class="w-5 h-5"
					>
						<path
							d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z"
						/>
					</svg>
				</button>
			</div>

			<div class="flex flex-col md:flex-row w-full px-5 pb-4 md:space-x-4 dark:text-gray-200">
				<div class="flex flex-col w-full">
					<div class="flex flex-col w-full mb-2">
						<div class=" mb-1 text-xs text-gray-500">{$i18n.t('Rating')}</div>

						<div class="flex-1">
							<span>{selectedFeedback?.data?.details?.rating ?? '-'}</span>
						</div>
					</div>
					<div class="flex flex-col w-full mb-2">
						<div class=" mb-1 text-xs text-gray-500">{$i18n.t('Reason')}</div>

						<div class="flex-1">
							<span>{selectedFeedback?.data?.reason || '-'}</span>
						</div>
					</div>

					<div class="mb-2">
						{#if selectedFeedback?.data?.tags && selectedFeedback?.data?.tags.length}
							<div class="flex flex-wrap gap-1 mt-1">
								{#each selectedFeedback?.data?.tags as tag}
									<span class="px-2 py-0.5 rounded bg-gray-100 dark:bg-gray-800 text-xs">{tag}</span
									>
								{/each}
							</div>
						{:else}
							<span>-</span>
						{/if}
					</div>
					<div class="flex justify-end pt-3">
						<button
							class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full"
							type="button"
							on:click={close}
						>
							{$i18n.t('Close')}
						</button>
					</div>
				</div>
			</div>
		</div>
	{/if}
</Modal>
