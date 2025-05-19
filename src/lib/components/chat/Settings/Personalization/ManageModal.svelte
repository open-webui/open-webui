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
	import EditMemoryModal from './EditMemoryModal.svelte';
	import localizedFormat from 'dayjs/plugin/localizedFormat';
	import EllipsisHorizontal from '$lib/components/icons/EllipsisHorizontal.svelte';
	import MemoriesMenu from './MemoriesMenu.svelte';
	import AddEditMemory from './AddEditMemory.svelte';
	import DeleteConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import DOMPurify from 'dompurify';

	const i18n = getContext('i18n');
	dayjs.extend(localizedFormat);

	export let show = false;

	let memories = [];
	let loading = true;

	let showAddMemoryModal = false;
	let showEditMemoryModal = false;

	let selectedMemory = null;

	$: if (show && memories.length === 0 && loading) {
		(async () => {
			memories = await getMemories(localStorage.token);
			loading = false;
		})();
	}
	let showDeleteConfirm = false;
</script>

<Modal size="md-plus" bind:show className="dark:bg-customGray-800 rounded-2xl" containerClassName="bg-lightGray-250/50 dark:bg-[#1D1A1A]/50 backdrop-blur-[7.44px]">
	<div class="bg-lightGray-550 dark:bg-customGray-800 rounded-xl">
		<div class="px-7">
			<div
				class=" flex justify-between text-lightGray-100 dark:text-white pt-5 pb-4 border-b border-lightGray-400 dark:border-customGray-700"
			>
				<div class="self-center">{$i18n.t('Memory')}</div>
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
		</div>

		<div class="flex flex-col w-full px-5 pb-5 dark:text-gray-200">
			<div
				class=" flex flex-col w-full sm:flex-row sm:justify-center sm:space-x-6 h-[20rem] max-h-screen mb-4 mt-1"
			>
				{#if memories.length > 0}
					<div class="text-left text-sm w-full mb-4 overflow-y-scroll">
						<div class="relative overflow-x-auto">
							{#each memories as memory}
								<div
									id="memory-{memory.id}"
									class="flex justify-between items-center group rounded-md w-full dark:hover:bg-customGray-900 py-2 px-3 cursor-pointer"
								>
									<div class="line-clamp-1 text-sm text-lightGray-100 dark:text-customGray-100">
										{memory.content}
									</div>
									<div class="invisible group-hover:visible">
										<MemoriesMenu
											editHandler={async () => {
												selectedMemory = memory;
												// showEditMemoryModal = true;
											}}
											deleteHandler={async () => {
												const res = await deleteMemoryById(localStorage.token, memory.id).catch(
													(error) => {
														toast.error(`${error}`);
														return null;
													}
												);

												if (res) {
													toast.success($i18n.t('Memory deleted successfully'));
													memories = await getMemories(localStorage.token);
												}
											}}
											onClose={() => {}}
										>
											<button
												class="self-center w-fit text-sm px-0.5 h-[21px] dark:text-white dark:hover:text-white hover:bg-black/5 dark:hover:bg-customGray-900 rounded-md"
												type="button"
												on:click={(e) => {}}
											>
												<EllipsisHorizontal className="size-5" />
											</button>
										</MemoriesMenu>
									</div>
								</div>
							{/each}
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
			<AddEditMemory
				memory={selectedMemory}
				on:save={async () => {
					memories = await getMemories(localStorage.token);
					selectedMemory = null;
				}}
			/>
			<div class="flex justify-end text-sm font-medium border-t border-lightGray-400 dark:border-customGray-700 pt-5">
				<!-- <button
					class=" px-3.5 py-1.5 font-medium hover:bg-black/5 dark:hover:bg-white/5 outline outline-1 outline-gray-300 dark:outline-gray-800 rounded-3xl"
					on:click={() => {
						showAddMemoryModal = true;
					}}>{$i18n.t('Add Memory')}</button
				> -->
				<button
					class=" text-xs h-10 px-4 py-2 transition rounded-lg bg-lightGray-300 border-lightGray-400 text-lightGray-100 font-medium hover:bg-lightGray-700 hover:bg-gray-900 dark:bg-customGray-900 dark:hover:bg-customGray-950 dark:text-customGray-200 border dark:border-customGray-700 flex justify-center items-center"
					on:click={async () => {
						if(memories.length < 1) return;
						showDeleteConfirm = true;
					}}>{$i18n.t('Delete All Memories')}</button
				>
			</div>
		</div>
	</div>
</Modal>

<DeleteConfirmDialog
	bind:show={showDeleteConfirm}
	title={$i18n.t('Are you sure you want to delete everything?')}
	on:confirm={async () => {
		const res = await deleteMemoriesByUserId(localStorage.token).catch((error) => {
			toast.error(`${error}`);
			return null;
		});
		if (res) {
			toast.success($i18n.t('Memory cleared successfully'));
			memories = [];
		}
	}}
	confirmLabel={$i18n.t('Delete All')}
	>
	<div class=" text-sm text-gray-700 dark:text-gray-300 flex-1 line-clamp-3">
		{@html DOMPurify.sanitize(
			$i18n.t('This action is permanent and cannot be undone. All your data will be lost.')
		)}
	</div>
</DeleteConfirmDialog>

<!-- <AddMemoryModal
	bind:show={showAddMemoryModal}
	on:save={async () => {
		memories = await getMemories(localStorage.token);
	}}
/>

<EditMemoryModal
	bind:show={showEditMemoryModal}
	memory={selectedMemory}
	on:save={async () => {
		memories = await getMemories(localStorage.token);
	}}
/> -->
