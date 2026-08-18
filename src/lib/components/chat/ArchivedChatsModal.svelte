<script lang="ts">
	import { getContext } from 'svelte';
	import Modal from '$lib/components/common/Modal.svelte';
	import ArchivedChats from '$lib/components/chat/Settings/ArchivedChats.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';

	export let show = false;
	const i18n = getContext('i18n');
</script>

<Modal size="xl" bind:show>
	<div class="text-gray-700 dark:text-gray-100 h-full flex flex-col max-h-[85vh]">
		<div class="flex justify-between items-center pb-3 border-b border-gray-100 dark:border-gray-850 px-6 pt-5">
			<div class="text-lg font-semibold flex items-center gap-2">
				<span>📦</span>
				<span>{$i18n.t('Archived Chats')}</span>
			</div>
			<button
				class="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition cursor-pointer"
				on:click={() => (show = false)}
				aria-label={$i18n.t('Close')}
			>
				<XMark className="size-5" />
			</button>
		</div>

		<div class="flex-1 overflow-y-auto px-6 py-4">
			<ArchivedChats />
		</div>
	</div>
</Modal>
