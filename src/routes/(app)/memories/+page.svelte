<script lang="ts">
	import { toast } from 'svelte-sonner';
	import dayjs from 'dayjs';
	import { getContext, onMount } from 'svelte';
	import { memories, mobile, showArchivedChats, showSidebar, user } from '$lib/stores';
	import {
		deleteMemoriesByUserId,
		deleteMemoryById,
		getMemories
	} from '$lib/apis/memories';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import AddMemoryModal from '$lib/components/chat/Settings/Personalization/AddMemoryModal.svelte';
	import EditMemoryModal from '$lib/components/chat/Settings/Personalization/EditMemoryModal.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import localizedFormat from 'dayjs/plugin/localizedFormat';
	import Sparkles from '$lib/components/icons/Sparkles.svelte';
	import UserMenu from '$lib/components/layout/Sidebar/UserMenu.svelte';
	import SidebarIcon from '$lib/components/icons/Sidebar.svelte';

	const i18n = getContext('i18n');
	dayjs.extend(localizedFormat);

	let loading = false;
	let showAddMemoryModal = false;
	let showEditMemoryModal = false;
	let selectedMemory = null;
	let showClearConfirmDialog = false;

	const loadMemories = async () => {
		loading = true;
		try {
			const data = await getMemories(localStorage.token);
			memories.set(data || []);
		} catch (error) {
			toast.error($i18n.t('Failed to load memories'));
			console.error(error);
		} finally {
			loading = false;
		}
	};

	const onClearConfirmed = async () => {
		const res = await deleteMemoriesByUserId(localStorage.token).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res && $memories.length > 0) {
			toast.success($i18n.t('Memory cleared successfully'));
			memories.set([]);
		}
		showClearConfirmDialog = false;
	};

	const handleDeleteMemory = async (memoryId: string) => {
		const res = await deleteMemoryById(localStorage.token, memoryId).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			toast.success($i18n.t('Memory deleted successfully'));
			await loadMemories();
		}
	};

	onMount(() => {
		loadMemories();
	});
</script>

<div
	class="flex flex-col w-full h-screen max-h-[100dvh] transition-width duration-200 ease-in-out {$showSidebar
		? 'md:max-w-[calc(100%-260px)]'
		: ''} max-w-full"
>
	<!-- Navbar -->
	<nav class="px-2 pt-1.5 backdrop-blur-xl w-full drag-region">
		<div class="flex items-center">
			{#if $mobile}
				<div class="{$showSidebar ? 'md:hidden' : ''} flex flex-none items-center">
					<Tooltip
						content={$showSidebar ? $i18n.t('Close Sidebar') : $i18n.t('Open Sidebar')}
						interactive={true}
					>
						<button
							id="sidebar-toggle-button"
							class="cursor-pointer flex rounded-lg hover:bg-gray-100 dark:hover:bg-gray-850 transition"
							on:click={() => {
								showSidebar.set(!$showSidebar);
							}}
						>
							<div class="self-center p-1.5">
								<SidebarIcon />
							</div>
						</button>
					</Tooltip>
				</div>
			{/if}

			<div class="ml-2 py-0.5 self-center flex items-center justify-between w-full">
				<div class="flex items-center gap-3">
					<div class="p-1.5 bg-gray-100 dark:bg-gray-800 rounded-xl">
						<Sparkles className="size-5" strokeWidth="2" />
					</div>
					<div>
						<h1 class="text-lg font-semibold text-gray-900 dark:text-gray-100">
							{$i18n.t('Memory')}
						</h1>
					</div>
				</div>

				<div class="self-center flex items-center gap-1">
					{#if $user !== undefined && $user !== null}
						<UserMenu
							className="max-w-[240px]"
							role={$user?.role}
							help={true}
							on:show={(e) => {
								if (e.detail === 'archived-chat') {
									showArchivedChats.set(true);
								}
							}}
						>
							<button
								class="select-none flex rounded-xl p-1.5 w-full hover:bg-gray-50 dark:hover:bg-gray-850 transition"
								aria-label="User Menu"
							>
								<div class="self-center">
									<img
										src={$user?.profile_image_url}
										class="size-6 object-cover rounded-full"
										alt="User profile"
										draggable="false"
									/>
								</div>
							</button>
						</UserMenu>
					{/if}
				</div>
			</div>
		</div>
	</nav>

	<!-- Content -->
	<div class="pb-1 flex-1 max-h-full overflow-y-auto">
		<div class="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
			<!-- Action Buttons -->
			<div class="flex items-center justify-between mb-6">
				<p class="text-sm text-gray-500 dark:text-gray-400">
					{$i18n.t('Memories accessible by LLMs will be shown here.')}
				</p>
				<div class="flex items-center gap-2">
					<button
						class="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-xl transition"
						on:click={() => {
							showAddMemoryModal = true;
						}}
					>
						<div class="flex items-center gap-2">
							<svg
								xmlns="http://www.w3.org/2000/svg"
								fill="none"
								viewBox="0 0 24 24"
								stroke-width="2"
								stroke="currentColor"
								class="w-4 h-4"
							>
								<path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
							</svg>
							{$i18n.t('Add Memory')}
						</div>
					</button>
					<!-- <button
						class="px-4 py-2 text-sm font-medium text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-xl transition"
						on:click={() => {
							if ($memories.length > 0) {
								showClearConfirmDialog = true;
							} else {
								toast.error($i18n.t('No memories to clear'));
							}
						}}
					>
						<div class="flex items-center gap-2">
							<svg
								xmlns="http://www.w3.org/2000/svg"
								fill="none"
								viewBox="0 0 24 24"
								stroke-width="2"
								stroke="currentColor"
								class="w-4 h-4"
							>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0"
								/>
							</svg>
							{$i18n.t('Clear memory')}
						</div>
					</button> -->
				</div>
			</div>

			<!-- Memory List -->
			{#if loading}
				<div class="flex items-center justify-center py-20">
					<div class="text-center">
						<div
							class="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-current border-r-transparent align-[-0.125em] motion-reduce:animate-[spin_1.5s_linear_infinite]"
						></div>
						<div class="mt-4 text-sm text-gray-500">{$i18n.t('Loading...')}</div>
					</div>
				</div>
			{:else if $memories.length === 0}
				<div class="flex items-center justify-center py-20">
					<div class="text-center max-w-md">
						<div
							class="mx-auto w-16 h-16 bg-gray-100 dark:bg-gray-800 rounded-full flex items-center justify-center mb-4"
						>
							<Sparkles className="size-8 text-gray-400" strokeWidth="2" />
						</div>
						<h3 class="text-lg font-medium text-gray-900 dark:text-gray-100 mb-2">
							{$i18n.t('No memories yet')}
						</h3>
						<p class="text-sm text-gray-500 dark:text-gray-400 mb-6">
							{$i18n.t('Memories accessible by LLMs will be shown here.')}
						</p>
						<button
							class="px-4 py-2 text-sm font-medium text-white bg-gray-900 dark:bg-white dark:text-gray-900 hover:bg-gray-800 dark:hover:bg-gray-100 rounded-xl transition"
							on:click={() => {
								showAddMemoryModal = true;
							}}
						>
							{$i18n.t('Add your first memory')}
						</button>
					</div>
				</div>
			{:else}
				<div class="grid gap-4 grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
					{#each $memories as memory}
						<div
							class="group relative bg-white dark:bg-gray-850 border border-gray-200 dark:border-gray-800 rounded-xl p-4 hover:shadow-md transition"
						>
							<div class="flex items-start justify-between gap-3">
								<div class="flex-1 min-w-0">
									<p class="text-sm text-gray-800 dark:text-gray-200 break-words whitespace-pre-wrap">
										{memory.content}
									</p>
									<div class="flex items-center gap-2 mt-3 text-xs text-gray-500 dark:text-gray-500">
										<svg
											xmlns="http://www.w3.org/2000/svg"
											fill="none"
											viewBox="0 0 24 24"
											stroke-width="1.5"
											stroke="currentColor"
											class="w-3.5 h-3.5"
										>
											<path
												stroke-linecap="round"
												stroke-linejoin="round"
												d="M12 6v6h4.5m4.5 0a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z"
											/>
										</svg>
										{dayjs(memory.updated_at * 1000).format('ll')}
									</div>
								</div>
								<div class="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition">
									<Tooltip content={$i18n.t('Edit')}>
										<button
											class="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition"
											on:click={() => {
												selectedMemory = memory;
												showEditMemoryModal = true;
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
													d="m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L6.832 19.82a4.5 4.5 0 0 1-1.897 1.13l-2.685.8.8-2.685a4.5 4.5 0 0 1 1.13-1.897L16.863 4.487Zm0 0L19.5 7.125"
												/>
											</svg>
										</button>
									</Tooltip>
									<Tooltip content={$i18n.t('Delete')}>
										<button
											class="p-2 hover:bg-red-50 dark:hover:bg-red-900/20 text-red-500 rounded-lg transition"
											on:click={() => handleDeleteMemory(memory.id)}
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
							</div>
						</div>
					{/each}
				</div>
			{/if}
		</div>
	</div>
</div>

<ConfirmDialog
	title={$i18n.t('Clear Memory')}
	message={$i18n.t('Are you sure you want to clear all memories? This action cannot be undone.')}
	show={showClearConfirmDialog}
	on:confirm={onClearConfirmed}
	on:cancel={() => {
		showClearConfirmDialog = false;
	}}
/>

<AddMemoryModal
	bind:show={showAddMemoryModal}
	on:save={async () => {
		await loadMemories();
	}}
/>

<EditMemoryModal
	bind:show={showEditMemoryModal}
	memory={selectedMemory}
	on:save={async () => {
		await loadMemories();
	}}
/>
