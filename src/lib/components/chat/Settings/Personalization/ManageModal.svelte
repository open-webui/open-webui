<script lang="ts">
	import { toast } from 'svelte-sonner';
	import dayjs from 'dayjs';
	import { getContext, createEventDispatcher } from 'svelte';

	const dispatch = createEventDispatcher();

	import Modal from '$lib/components/common/Modal.svelte';
	import AddMemoryModal from './AddMemoryModal.svelte';
	import { deleteMemoriesByUserId, deleteMemoryById, getMemories } from '$lib/apis/memories';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import { error } from '@sveltejs/kit';

	const i18n = getContext('i18n');

	export let show = false;

	let memories = [];

	let showAddMemoryModal = false;

	$: if (show) {
		(async () => {
			memories = await getMemories(localStorage.token);
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
					<div class="text-left text-sm w-full mb-4 overflow-y-scroll">
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
										<tr class="border-b dark:border-gray-800 items-center">
											<td class="px-3 py-1">
												<div class="line-clamp-1">
													{memory.content}
												</div>
											</td>
											<td class=" px-3 py-1 hidden md:flex h-[2.5rem]">
												<div class="my-auto whitespace-nowrap">
													{dayjs(memory.created_at * 1000).format($i18n.t('MMMM DD, YYYY'))}
												</div>
											</td>
											<td class="px-3 py-1">
												<div class="flex justify-end w-full">
													<Tooltip content="Delete">
														<button
															class="self-center w-fit text-sm px-2 py-2 hover:bg-black/5 dark:hover:bg-white/5 rounded-xl"
															on:click={async () => {
																const res = await deleteMemoryById(
																	localStorage.token,
																	memory.id
																).catch((error) => {
																	toast.error(error);
																	return null;
																});

																if (res) {
																	toast.success('Memory deleted successfully');
																	memories = await getMemories(localStorage.token);
																}
															}}
														>
															<svg
																xmlns="http://www.w3.org/2000/svg"
																fill="none"
																viewBox="0 0 24 24"
																stroke-width="1.5"
																stroke="currentColor"
																class="w-4 h-4"
															>
																<path
																	stroke-linecap="round"
																	stroke-linejoin="round"
																	d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0"
																/>
															</svg>
														</button>
													</Tooltip>
												</div>
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
							{$i18n.t('Memories accessible by LLMs will be shown here.')}
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
				<button
					class=" px-3.5 py-1.5 font-medium text-red-500 hover:bg-black/5 dark:hover:bg-white/5 outline outline-1 outline-red-300 dark:outline-red-800 rounded-3xl"
					on:click={async () => {
						const res = await deleteMemoriesByUserId(localStorage.token).catch((error) => {
							toast.error(error);
							return null;
						});

						if (res) {
							toast.success('Memory cleared successfully');
							memories = [];
						}
					}}>Clear memory</button
				>
			</div>
		</div>
	</div>
</Modal>

<AddMemoryModal
	bind:show={showAddMemoryModal}
	on:save={async () => {
		memories = await getMemories(localStorage.token);
	}}
/>
