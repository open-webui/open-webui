<script lang="ts">
	import Modal from '$lib/components/common/Modal.svelte';
	import { getContext } from 'svelte';
	export let show = false;
	export let model = null;
	export let feedbacks = [];
	export let onClose: () => void = () => {};
	const i18n = getContext('i18n');

	const close = () => {
		show = false;
		onClose();
	};

	$: topTags = model ? getTopTagsForModel(model.id, feedbacks) : [];

	const getTopTagsForModel = (modelId: string, feedbacks: any[], topN = 5) => {
		const tagCounts = new Map();
		feedbacks
			.filter((fb) => fb.data.model_id === modelId)
			.forEach((fb) => {
				(fb.data.tags || []).forEach((tag) => {
					tagCounts.set(tag, (tagCounts.get(tag) || 0) + 1);
				});
			});
		return Array.from(tagCounts.entries())
			.sort((a, b) => b[1] - a[1])
			.slice(0, topN)
			.map(([tag, count]) => ({ tag, count }));
	};
</script>

<Modal size="sm" bind:show>
	{#if model}
		<div class="flex justify-between dark:text-gray-300 px-5 pt-4 pb-2">
			<div class="text-lg font-medium self-center">
				{model.name}
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
		<div class="px-5 pb-4 dark:text-gray-200">
			<div class="mb-2">
				{#if topTags.length}
					<div class="flex flex-wrap gap-1 mt-1">
						{#each topTags as tagInfo}
							<span class="px-2 py-0.5 rounded bg-gray-100 dark:bg-gray-800 text-xs">
								{tagInfo.tag} <span class="text-gray-500">({tagInfo.count})</span>
							</span>
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
	{/if}
</Modal>
