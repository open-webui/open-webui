<script lang="ts">
	import { toast } from 'svelte-sonner';
	import dayjs from 'dayjs';
	import { getContext, createEventDispatcher } from 'svelte';

	const dispatch = createEventDispatcher();

	import Modal from '$lib/components/common/Modal.svelte';
	import AddMemoryModal from './AddMemoryModal.svelte';

	const i18n = getContext('i18n');

	export let show = false;

	let memories = [];

	let showAddMemoryModal = false;

	$: if (show) {
		(async () => {
			// chats = await getArchivedChatList(localStorage.token);
		})();
	}
</script>

<Modal size="xl" bind:show>
	<div>
		<div class=" flex justify-between dark:text-gray-300 px-5 pt-4 pb-1">
			<div class=" text-lg font-medium self-center">{$i18n.t('Memory')}</div>
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

		<div class="flex flex-col w-full px-5 pb-5 dark:text-gray-200">
			<div
				class=" flex flex-col w-full sm:flex-row sm:justify-center sm:space-x-6 h-[28rem] max-h-screen outline outline-1 rounded-xl outline-gray-100 dark:outline-gray-800 mb-4 mt-1"
			>
				{#if memories.length > 0}
					<div class="text-left text-sm w-full mb-4 max-h-[22rem] overflow-y-scroll">
						<div class="relative overflow-x-auto">
							<table class="w-full text-sm text-left text-gray-600 dark:text-gray-400 table-auto">
								<thead
									class="text-xs text-gray-700 uppercase bg-transparent dark:text-gray-200 border-b-2 dark:border-gray-800"
								>
									<tr>
										<th scope="col" class="px-3 py-2"> {$i18n.t('Name')} </th>
										<th scope="col" class="px-3 py-2 hidden md:flex"> {$i18n.t('Created At')} </th>
										<th scope="col" class="px-3 py-2 text-right" />
									</tr>
								</thead>
								<tbody>
									{#each memories as memory}
										<tr class="border-b dark:border-gray-800">
											<td class="px-3 py-2"> {memory.name} </td>
											<td class="px-3 py-2 hidden md:flex">
												{dayjs(memory.created_at).format($i18n.t('MMMM DD, YYYY'))}
											</td>
											<td class="px-3 py-2 text-right">
												<button
													class="text-xs text-gray-500 dark:text-gray-400"
													on:click={() => {
														// showMemory(memory);
													}}
												>
													{$i18n.t('View')}
												</button>
											</td>
										</tr>
									{/each}
								</tbody>
							</table>
						</div>
					</div>
				{:else}
					<div class="text-center flex h-full text-sm w-full">
						<div class=" my-auto pb-10 px-4 w-full text-gray-500">
							{$i18n.t(
								'As you chat with LLMs, the details and preferences it remembers will be shown here.'
							)}
						</div>
					</div>
				{/if}
			</div>
			<div class="flex text-sm font-medium gap-1.5">
				<button
					class=" px-3.5 py-1.5 font-medium hover:bg-black/5 dark:hover:bg-white/5 outline outline-1 outline-gray-300 dark:outline-gray-800 rounded-3xl"
					on:click={() => {
						showAddMemoryModal = true;
					}}>Add memory</button
				>
				<!-- <button
					class=" px-3.5 py-1.5 font-medium text-red-500 hover:bg-black/5 dark:hover:bg-white/5 outline outline-1 outline-red-300 dark:outline-red-800 rounded-3xl"
					>Clear memory</button
				> -->
			</div>
		</div>
	</div>
</Modal>

<AddMemoryModal bind:show={showAddMemoryModal} />
