<script lang="ts">
	import { toast } from 'svelte-sonner';
	import dayjs from 'dayjs';
	import { onMount, getContext } from 'svelte';

	import Modal from '$lib/components/common/Modal.svelte';
	import { getArchivedChatList } from '$lib/apis/chats';

	const i18n = getContext('i18n');

	export let show = false;

	let chats = [];

	onMount(async () => {
		chats = await getArchivedChatList(localStorage.token);
	});
</script>

<Modal size="lg" bind:show>
	<div>
		<div class=" flex justify-between dark:text-gray-300 px-5 py-4">
			<div class=" text-lg font-medium self-center">{$i18n.t('Archived Chats')}</div>
			<button
				class="self-center"
				on:click={() => {
					show = false;
				}}
			>
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
		<hr class=" dark:border-gray-850" />

		<div class="flex flex-col md:flex-row w-full px-5 py-4 md:space-x-4 dark:text-gray-200">
			<div class=" flex flex-col w-full sm:flex-row sm:justify-center sm:space-x-6">
				{#if chats.length > 0}
					<div class="text-left text-sm w-full mb-8">
						{#each chats as chat}
							<div>
								{JSON.stringify(chat)}
							</div>
						{/each}
					</div>
				{:else}
					<div class="text-left text-sm w-full mb-8">You have no archived conversations.</div>
				{/if}
			</div>
		</div>
	</div>
</Modal>
