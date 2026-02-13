<script lang="ts">
	import { getContext } from 'svelte';
	const i18n = getContext('i18n');
	import { toast } from 'svelte-sonner';
	import { bulkShareThreads } from '$lib/apis/spaces';
	import type { Space } from '$lib/apis/spaces';
	import Modal from '$lib/components/common/Modal.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';

	export let show = false;
	export let space: Space | null = null;
	export let onComplete: () => void = () => {};

	let loading = false;

	const handleBulkShare = async () => {
		if (!space) return;
		loading = true;
		try {
			const result = await bulkShareThreads(localStorage.token, space.id);
			toast.success(
				$i18n.t('{{count}} threads shared with space members', {
					count: result.threads_updated
				})
			);
			show = false;
			onComplete();
		} catch (err) {
			toast.error(String(err));
		}
		loading = false;
	};

	const handleSkip = () => {
		show = false;
	};
</script>

<Modal size="sm" bind:show>
	<div class="px-5 pt-4 pb-5">
		<h3 class="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
			{$i18n.t('Share your threads with members')}
		</h3>
		<p class="text-sm text-gray-500 dark:text-gray-400 leading-relaxed mb-6">
			{$i18n.t(
				'Threads in your Space are private by default. Would you like to share your threads to be seen by all members of this Space?'
			)}
		</p>
		<div class="flex justify-end gap-2">
			<button
				class="px-4 py-2 text-sm font-medium text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition"
				on:click={handleSkip}
				disabled={loading}
			>
				{$i18n.t('Skip')}
			</button>
			<button
				class="px-4 py-2 text-sm font-medium bg-black dark:bg-white text-white dark:text-black hover:bg-gray-800 dark:hover:bg-gray-100 rounded-lg transition flex items-center gap-2"
				on:click={handleBulkShare}
				disabled={loading}
			>
				{#if loading}
					<Spinner className="size-3.5" />
				{/if}
				{$i18n.t('Share all threads')}
			</button>
		</div>
	</div>
</Modal>
