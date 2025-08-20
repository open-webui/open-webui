<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import {
		getSharedChats,
		deleteSharedChatById,
		revokeAllSharedChats,
		resetChatStatsById,
		resetAllChatStats,
		cloneSharedChatById,
		shareChatById,
		importChat,
		getChatById,
		restoreSharedChat
	} from '$lib/apis/chats';
	import { goto } from '$app/navigation';
	import { toast } from 'svelte-sonner';
	import { page as pageStore } from '$app/stores';
	import dayjs from 'dayjs';
	import {
		config,
		user,
		models,
		sharedChats as sharedChatsStore,
		sharedChatsUpdated,
		selectedSharedChatIds,
		showSidebar,
		chatsUpdated
	} from '$lib/stores';
	import { getModels } from '$lib/apis';
	import { clearRevokedSharedChats } from '$lib/apis/chats';
	import ShareChatModal from '$lib/components/chat/ShareChatModal.svelte';
	import Pagination from '$lib/components/common/Pagination.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import DangerZoneConfirmationModal from '$lib/components/common/DangerZoneConfirmationModal.svelte';
	import MenuLines from '$lib/components/icons/MenuLines.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Clipboard from '$lib/components/icons/Clipboard.svelte';

	let showShareChatModal = false;
	let selectedChatId = '';

	let showConfirmRevokeSelected = false;
	let showConfirmRevokeAll = false;
	let showPrimaryRevokeAllConfirm = false;
	let showConfirmResetSelected = false;
	let showConfirmResetAllStats = false;
	let showPrimaryResetAllStatsConfirm = false;
	let showConfirmClearRevoked = false;
	const i18n = getContext('i18n');

	let showConfirmResetStats = false;
	let chatToResetStats = null;

	let page = 1;
	let total = 0;
	let grandTotal = 0;
	let orderBy = 'updated_at';
	let direction = 'desc';

	let searchTerm = '';
	let startDate = '';
	let endDate = '';
	let publicFilter = null;
	let statusFilter = 'all';
	let totalSelectedCount = 0;

	const publicFilterOptions = [
		{ value: null, label: 'Public: All' },
		{ value: true, label: 'Public: Yes' },
		{ value: false, label: 'Public: No' }
	];

	const statusFilterOptions = [
		{ value: 'all', label: 'Status: All' },
		{ value: 'active', label: 'Status: Active' },
		{ value: 'revoked', label: 'Status: Revoked' }
	];

	$: selectedPublicFilterIndex = publicFilterOptions.findIndex((o) => o.value === publicFilter);
	$: selectedStatusFilterIndex = statusFilterOptions.findIndex((o) => o.value === statusFilter);

	const handlePublicFilterScroll = (event) => {
		event.preventDefault();
		const direction = event.deltaY < 0 ? -1 : 1;
		let newIndex = selectedPublicFilterIndex + direction;

		if (newIndex < 0) {
			newIndex = publicFilterOptions.length - 1;
		} else if (newIndex >= publicFilterOptions.length) {
			newIndex = 0;
		}
		publicFilter = publicFilterOptions[newIndex].value;
		page = 1;
		getSharedChatList();
	};

	const handleStatusFilterScroll = (event) => {
		event.preventDefault();
		const direction = event.deltaY < 0 ? -1 : 1;
		let newIndex = selectedStatusFilterIndex + direction;

		if (newIndex < 0) {
			newIndex = statusFilterOptions.length - 1;
		} else if (newIndex >= statusFilterOptions.length) {
			newIndex = 0;
		}
		statusFilter = statusFilterOptions[newIndex].value;
		page = 1;
		getSharedChatList();
	};
	let dateFilterApplied = false;

	const handleDateFilter = () => {
		if (startDate && endDate) {
			page = 1;
			getSharedChatList();
			dateFilterApplied = true;
		}
	};

	const clearDateFilter = () => {
		startDate = '';
		endDate = '';
		dateFilterApplied = false;
		getSharedChatList();
	};

	const setSortKey = (key) => {
		if (orderBy === key) {
			direction = direction === 'asc' ? 'desc' : 'asc';
		} else {
			orderBy = key;
			direction = 'asc';
		}
	};

	const getSharedChatList = async () => {
		if ($user) {
			const res = await getSharedChats(
				localStorage.token,
				page,
				searchTerm,
				orderBy,
				direction,
				startDate ? dayjs(startDate).startOf('day').unix() : undefined,
				endDate ? dayjs(endDate).endOf('day').unix() : undefined,
				publicFilter,
				statusFilter
			);
			total = res.total;
			grandTotal = res.grand_total;

			sharedChatsStore.set(
				res.chats.map((chat) => ({
					...chat,
					status: chat.revoked_at ? 'revoked' : 'active',
					selected: $selectedSharedChatIds.includes(chat.id)
				}))
			);

			if (res.chats.length === 0 && page > 1) {
				page = 1;
			}
		}
	};

	let previousShowShareChatModal = false;
	onMount(async () => {
		models.set(await getModels(localStorage.token));
		getSharedChatList();
		previousShowShareChatModal = showShareChatModal;

		const interval = setInterval(() => {
			const now = Math.floor(Date.now() / 1000);
			const chatsToProcess = [...$sharedChatsStore];

			chatsToProcess.forEach(async (chat) => {
				const isExpiredByTime = chat.expires_at && chat.expires_at <= now;
				const isExpiredByViews =
					chat.expire_on_views && chat.views >= chat.expire_on_views;

				if ((isExpiredByTime || isExpiredByViews) && chat.status === 'active') {
					const res = await deleteSharedChatById(localStorage.token, chat.id);
					if (res) {
						toast.info(`Expired link for "${chat.title}" was automatically revoked.`);
						getSharedChatList();
					}
				}
			});
		}, 1000);

		return () => {
			clearInterval(interval);
		};
	});

	$: if ($user && !($user.role === 'admin' || $user.permissions?.sharing?.shared_chats)) {
		goto('/');
		toast.error("You don't have permission to access this page.");
	}

	$: if ($sharedChatsUpdated) {
		getSharedChatList();
		sharedChatsUpdated.set(false);
	}

	$: if (previousShowShareChatModal && !showShareChatModal) {
		getSharedChatList();
	}

	$: previousShowShareChatModal = showShareChatModal;

	$: if (page || searchTerm || orderBy || direction) {
		getSharedChatList();
	}
	$: totalSelectedCount = $selectedSharedChatIds.length;

	let headerText = '';
	$: {
		let text = 'Shared Chats | ';

		if (searchTerm || dateFilterApplied) {
			text += `${total}`;

			if (searchTerm) {
				text += ` results`;
			}
			if (dateFilterApplied) {
				text += ` filtered by date`;
			}

			if (totalSelectedCount > 0) {
				text += `, ${totalSelectedCount} selected`;
			}
			text += ` / ${grandTotal} share links`;
		} else {
			if (totalSelectedCount > 0) {
				text += `${totalSelectedCount} selected / ${grandTotal} share links`;
			} else {
				text += `${grandTotal} share links`;
			}
		}
		headerText = text;
	}


	const handleSearch = () => {
		page = 1;
		getSharedChatList();
	};

	const copyLink = (link) => {
		navigator.clipboard.writeText(link);
	};

	const cloneChat = async (chatId) => {
		try {
			const new_chat = await cloneSharedChatById(localStorage.token, chatId);
			if (new_chat) {
				const res = await shareChatById(localStorage.token, new_chat.id);
				if (res) {
					toast.success('Chat cloned and shared');
					getSharedChatList();
					chatsUpdated.set(true);
				} else {
					toast.error('Failed to share cloned chat');
				}
			} else {
				toast.error('Failed to clone chat');
			}
		} catch (e) {
			toast.error('Cannot clone a revoked link.');
		}
	};

	const revokeLink = async (chatId) => {
		const res = await deleteSharedChatById(localStorage.token, chatId);
		if (res) {
			toast.success('Link revoked');
			getSharedChatList();
			selectedSharedChatIds.update((ids) => ids.filter((id) => id !== chatId));
		} else {
			toast.error('Failed to revoke link');
		}
	};

	const restoreLink = async (chatId) => {
		const res = await restoreSharedChat(localStorage.token, chatId);
		if (res) {
			toast.success('Link restored');
			getSharedChatList();
		} else {
			toast.error('Failed to restore link');
		}
	};

	const revokeSelected = async () => {
		showConfirmRevokeSelected = true;
	};

	const revokeAll = async () => {
		showConfirmRevokeAll = true;
	};

	const doRevokeSelected = async () => {
		const idsToRevoke = [...$selectedSharedChatIds];
		let revokedCount = 0;
		for (const chatId of idsToRevoke) {
			const res = await deleteSharedChatById(localStorage.token, chatId);
			if (res) {
				revokedCount++;
			}
		}
		toast.success(`${revokedCount} links revoked`);
		getSharedChatList();
		selectedSharedChatIds.set([]);
		showConfirmRevokeSelected = false;
	};

	const doRevokeAll = async () => {
		const res = await revokeAllSharedChats(localStorage.token);
		if (res) {
			toast.success(`${res.revoked} links revoked`);
			getSharedChatList();
		} else {
			toast.error('Failed to revoke all links');
		}
		showConfirmRevokeAll = false;
	};

	const doResetStats = async () => {
		if (!chatToResetStats) return;

		const res = await resetChatStatsById(localStorage.token, chatToResetStats.id);
		if (res) {
			toast.success('Statistics have been reset.');
			getSharedChatList(); // This will refresh the list with the updated data
		} else {
			toast.error('Failed to reset statistics.');
		}
		showConfirmResetStats = false;
		chatToResetStats = null;
	};

	const doResetSelectedStats = async () => {
		const idsToReset = [...$selectedSharedChatIds];
		let resetCount = 0;

		for (const chatId of idsToReset) {
			const res = await resetChatStatsById(localStorage.token, chatId);
			if (res) {
				resetCount++;
			}
		}

		if (resetCount > 0) {
			toast.success(`${resetCount} chat(s) have had their statistics reset.`);
			getSharedChatList();
			selectedSharedChatIds.set([]);
		} else {
			toast.error('Failed to reset statistics for any selected chats.');
		}

		showConfirmResetSelected = false;
	};

	const doResetAllStats = async () => {
		const res = await resetAllChatStats(localStorage.token);
		if (res) {
			toast.success(`${res.reset} chat(s) have had their statistics reset.`);
			getSharedChatList();
		} else {
			toast.error('Failed to reset all chat statistics.');
		}
		showConfirmResetAllStats = false;
	};

	const doClearRevoked = async () => {
		const res = await clearRevokedSharedChats(localStorage.token);
		if (res) {
			toast.success(`${res.cleared} revoked link(s) cleared.`);
			getSharedChatList();
		} else {
			toast.error('Failed to clear revoked links.');
		}
		showConfirmClearRevoked = false;
	};

	const selectAll = (event) => {
		const checked = event.target.checked;
		sharedChatsStore.update((chats) =>
			chats.map((chat) => ({ ...chat, selected: checked }))
		);

		if (checked) {
			selectedSharedChatIds.update((ids) => [
				...new Set([...ids, ...$sharedChatsStore.map((chat) => chat.id)])
			]);
		} else {
			const chatIdsToUnselect = $sharedChatsStore.map((chat) => chat.id);
			selectedSharedChatIds.update((ids) => ids.filter((id) => !chatIdsToUnselect.includes(id)));
		}
	};
</script>

<style>
	.truncate-text {
		max-width: 250px;
		overflow: hidden;
		white-space: nowrap;
		text-overflow: ellipsis;
	}
</style>

<!-- svelte-ignore a11y-no-static-element-interactions -->
<div
	class="transition-width duration-200 ease-in-out {$showSidebar
		? 'md:max-w-[calc(100%-260px)]'
		: ''} w-full flex flex-col h-full"
	on:dragover={(e) => {
		e.preventDefault();
	}}
	on:drop={async (e) => {
		e.preventDefault();

		const data = e.dataTransfer.getData('text/plain');
		try {
			const { type, id, item } = JSON.parse(data);
			if (type === 'chat') {
				const ownChat = await getChatById(localStorage.token, id).catch(() => null);

				if (ownChat) {
					selectedChatId = id;
					showShareChatModal = true;
				} else {
					const canClone = ($user?.role === 'admin' || $user?.permissions?.chat?.clone) ?? true;
					if (!canClone) {
						toast.error($i18n.t("You don't have permission to clone chats."));
						return;
					}

					const res = await importChat(
						localStorage.token,
						item.chat,
						item.meta,
						item.pinned,
						item.folder_id
					);

					if (res) {
						toast.success('Chat imported successfully');
						chatsUpdated.set(true);
						selectedChatId = res.id;
						showShareChatModal = true;
					}
				}
			}
		} catch (e) {
			toast.error('Failed to share chat.');
			console.error(e);
		}
	}}
>
	<div
		class="flex w-full justify-between items-center p-4 border-b border-gray-100 dark:border-gray-800"
	>
		<div class="flex-1 flex items-center">
			<div class="text-lg font-semibold">{headerText}</div>
		</div>
	</div>

	<div class="p-4 space-y-4 flex-grow flex flex-col">
		<div class="flex justify-between items-center">
			<div class="relative w-full max-w-xs">
				<input
					type="text"
					placeholder="Search by title..."
					class="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg dark:bg-gray-800 dark:border-gray-700"
					bind:value={searchTerm}
					on:change={handleSearch}
				/>
				<div class="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none">
					<svg
						class="w-5 h-5 text-gray-400"
						fill="none"
						stroke="currentColor"
						viewBox="0 0 24 24"
						xmlns="http://www.w3.org/2000/svg"
						><path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
						></path></svg
					>
				</div>
				{#if searchTerm}
					<button
						class="absolute inset-y-0 right-0 flex items-center pr-3"
						on:click={() => {
							searchTerm = '';
						}}
					>
						<svg
							class="w-5 h-5 text-gray-400 hover:text-gray-500"
							fill="none"
							stroke="currentColor"
							viewBox="0 0 24 24"
							xmlns="http://www.w3.org/2000/svg"
							><path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M6 18L18 6M6 6l12 12"
							></path></svg
						>
					</button>
				{/if}
			</div>
			<div class="flex space-x-2">
				<input
					type="date"
					class="px-4 py-2 border border-gray-300 rounded-lg dark:bg-gray-800 dark:border-gray-700"
					value={startDate}
					on:change={(e) => {
						startDate = e.target.value;
						if (endDate && dayjs(startDate).isAfter(dayjs(endDate))) {
							endDate = startDate;
						}
					}}
				/>
				<input
					type="date"
					class="px-4 py-2 border border-gray-300 rounded-lg dark:bg-gray-800 dark:border-gray-700"
					value={endDate}
					on:change={(e) => {
						endDate = e.target.value;
						if (startDate && dayjs(endDate).isBefore(dayjs(startDate))) {
							startDate = endDate;
						}
					}}
				/>
				<button
					class="px-4 py-2 bg-gray-200 dark:bg-gray-700 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap"
					on:click={handleDateFilter}
					disabled={!startDate || !endDate}
				>
					Filter by Date
				</button>
				{#if dateFilterApplied}
					<button
						class="px-4 py-2 bg-gray-200 dark:bg-gray-700 rounded-lg whitespace-nowrap"
						on:click={clearDateFilter}
					>
						Reset
					</button>
				{/if}
			<div class="relative">
				<select
					class="pl-4 pr-10 py-2 border border-gray-300 rounded-lg dark:bg-gray-800 dark:border-gray-700"
					bind:value={publicFilter}
					on:change={() => {
						page = 1;
						getSharedChatList();
					}}
					on:wheel|preventDefault={handlePublicFilterScroll}
				>
					{#each publicFilterOptions as option}
						<option value={option.value}>{option.label}</option>
					{/each}
				</select>
			</div>
			<div class="relative">
				<select
					class="pl-4 pr-10 py-2 border border-gray-300 rounded-lg dark:bg-gray-800 dark:border-gray-700"
					bind:value={statusFilter}
					on:change={() => {
						page = 1;
						getSharedChatList();
					}}
					on:wheel|preventDefault={handleStatusFilterScroll}
				>
					{#each statusFilterOptions as option}
						<option value={option.value}>{option.label}</option>
					{/each}
				</select>
			</div>
				{#if totalSelectedCount > 0}
					<button
						class="px-4 py-2 text-red-500 border border-red-500 rounded-lg whitespace-nowrap hover:bg-red-500 hover:text-white"
						on:click={revokeSelected}
					>
						Revoke Selected
					</button>
					<button
						class="px-4 py-2 text-yellow-500 border border-yellow-500 rounded-lg whitespace-nowrap hover:bg-yellow-500 hover:text-white"
						on:click={() => (showConfirmResetSelected = true)}
					>
						Reset Stats for Selected
					</button>
				{/if}
				<button
					class="px-4 py-2 text-red-500 border border-red-500 rounded-lg whitespace-nowrap hover:bg-red-500 hover:text-white disabled:opacity-50 disabled:cursor-not-allowed"
					on:click={() => {
						showPrimaryRevokeAllConfirm = true;
					}}
					disabled={grandTotal === 0}>Revoke All</button
				>
				<button
					class="px-4 py-2 text-yellow-500 border border-yellow-500 rounded-lg whitespace-nowrap hover:bg-yellow-500 hover:text-white disabled:opacity-50 disabled:cursor-not-allowed"
					on:click={() => (showPrimaryResetAllStatsConfirm = true)}
					disabled={grandTotal === 0}
				>
					Reset All Stats
				</button>
				<button
					class="px-4 py-2 text-red-600 border border-red-600 rounded-lg whitespace-nowrap hover:bg-red-600 hover:text-white disabled:opacity-50 disabled:cursor-not-allowed"
					on:click={() => (showConfirmClearRevoked = true)}
					disabled={grandTotal === 0 || $sharedChatsStore.filter(c => c.status === 'revoked').length === 0}
				>
					Clear Revoked
				</button>
			</div>
		</div>
		<div class="overflow-x-auto flex-grow">
			<table class="min-w-full bg-white dark:bg-gray-900 rounded-lg shadow-md">
				<thead>
					<tr class="w-full h-10 border-b border-gray-200 dark:border-gray-800">
						{#if $sharedChatsStore.length > 0}
							<th
								class="px-6 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider"
							>
								<input
									type="checkbox"
									class="form-checkbox"
									on:change={selectAll}
									checked={$selectedSharedChatIds.length > 0 &&
										$selectedSharedChatIds.length === $sharedChatsStore.length}
									indeterminate={$selectedSharedChatIds.length > 0 &&
										$selectedSharedChatIds.length < $sharedChatsStore.length}
								/>
							</th>
						{/if}
						<th
							class="px-6 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider cursor-pointer"
							on:click={() => setSortKey('title')}
						>
							<div class="flex items-center">
								<span>Title</span>
								{#if orderBy === 'title'}
									<span class="ml-1">
										{#if direction === 'asc'}
											<svg
												xmlns="http://www.w3.org/2000/svg"
												class="h-4 w-4"
												fill="none"
												viewBox="0 0 24 24"
												stroke="currentColor"
											>
												<path
													stroke-linecap="round"
													stroke-linejoin="round"
													stroke-width="2"
													d="M5 15l7-7 7 7"
												/>
											</svg>
										{:else}
											<svg
												xmlns="http://www.w3.org/2000/svg"
												class="h-4 w-4"
												fill="none"
												viewBox="0 0 24 24"
												stroke="currentColor"
											>
												<path
													stroke-linecap="round"
													stroke-linejoin="round"
													stroke-width="2"
													d="M19 9l-7 7-7-7"
												/>
											</svg>
										{/if}
									</span>
								{/if}
							</div>
						</th>
						<th
							class="px-6 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider cursor-pointer"
							on:click={() => setSortKey('created_at')}
						>
							<div class="flex items-center">
								<span>Created On</span>
								{#if orderBy === 'created_at'}
									<span class="ml-1">
										{#if direction === 'asc'}
											<svg
												xmlns="http://www.w3.org/2000/svg"
												class="h-4 w-4"
												fill="none"
												viewBox="0 0 24 24"
												stroke="currentColor"
											>
												<path
													stroke-linecap="round"
													stroke-linejoin="round"
													stroke-width="2"
													d="M5 15l7-7 7 7"
												/>
											</svg>
										{:else}
											<svg
												xmlns="http://www.w3.org/2000/svg"
												class="h-4 w-4"
												fill="none"
												viewBox="0 0 24 24"
												stroke="currentColor"
											>
												<path
													stroke-linecap="round"
													stroke-linejoin="round"
													stroke-width="2"
													d="M19 9l-7 7-7-7"
												/>
											</svg>
										{/if}
									</span>
								{/if}
							</div>
						</th>
						<th
							class="px-6 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider cursor-pointer"
							on:click={() => setSortKey('updated_at')}
						>
							<div class="flex items-center">
								<span>Last Updated</span>
								{#if orderBy === 'updated_at'}
									<span class="ml-1">
										{#if direction === 'asc'}
											<svg
												xmlns="http://www.w3.org/2000/svg"
												class="h-4 w-4"
												fill="none"
												viewBox="0 0 24 24"
												stroke="currentColor"
											>
												<path
													stroke-linecap="round"
													stroke-linejoin="round"
													stroke-width="2"
													d="M5 15l7-7 7 7"
												/>
											</svg>
										{:else}
											<svg
												xmlns="http://www.w3.org/2000/svg"
												class="h-4 w-4"
												fill="none"
												viewBox="0 0 24 24"
												stroke="currentColor"
											>
												<path
													stroke-linecap="round"
													stroke-linejoin="round"
													stroke-width="2"
													d="M19 9l-7 7-7-7"
												/>
											</svg>
										{/if}
									</span>
								{/if}
							</div>
						</th>
						<th
							class="px-6 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider cursor-pointer"
							on:click={() => setSortKey('share_id')}
						>
							<div class="flex items-center">
								<span>Link</span>
								{#if orderBy === 'share_id'}
									<span class="ml-1">
										{#if direction === 'asc'}
											<svg
												xmlns="http://www.w3.org/2000/svg"
												class="h-4 w-4"
												fill="none"
												viewBox="0 0 24 24"
												stroke="currentColor"
											>
												<path
													stroke-linecap="round"
													stroke-linejoin="round"
													stroke-width="2"
													d="M5 15l7-7 7 7"
												/>
											</svg>
										{:else}
											<svg
												xmlns="http://www.w3.org/2000/svg"
												class="h-4 w-4"
												fill="none"
												viewBox="0 0 24 24"
												stroke="currentColor"
											>
												<path
													stroke-linecap="round"
													stroke-linejoin="round"
													stroke-width="2"
													d="M19 9l-7 7-7-7"
												/>
											</svg>
										{/if}
									</span>
								{/if}
							</div>
						</th>
						<th
							class="px-6 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider cursor-pointer whitespace-nowrap"
							on:click={() => setSortKey('is_public')}
						>
							<div class="flex items-center">
								<span>Public</span>
								{#if orderBy === 'is_public'}
									<span class="ml-1">
										{#if direction === 'asc'}
											<svg
												xmlns="http://www.w3.org/2000/svg"
												class="h-4 w-4"
												fill="none"
												viewBox="0 0 24 24"
												stroke="currentColor"
											>
												<path
													stroke-linecap="round"
													stroke-linejoin="round"
													stroke-width="2"
													d="M5 15l7-7 7 7"
												/>
											</svg>
										{:else}
											<svg
												xmlns="http://www.w3.org/2000/svg"
												class="h-4 w-4"
												fill="none"
												viewBox="0 0 24 24"
												stroke="currentColor"
											>
												<path
													stroke-linecap="round"
													stroke-linejoin="round"
													stroke-width="2"
													d="M19 9l-7 7-7-7"
												/>
											</svg>
										{/if}
									</span>
								{/if}
							</div>
						</th>
						<th
							class="px-6 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider cursor-pointer whitespace-nowrap"
							on:click={() => setSortKey('views')}
						>
							<div class="flex items-center">
								<span>Views</span>
								{#if orderBy === 'views'}
									<span class="ml-1">
										{#if direction === 'asc'}
											<svg
												xmlns="http://www.w3.org/2000/svg"
												class="h-4 w-4"
												fill="none"
												viewBox="0 0 24 24"
												stroke="currentColor"
											>
												<path
													stroke-linecap="round"
													stroke-linejoin="round"
													stroke-width="2"
													d="M5 15l7-7 7 7"
												/>
											</svg>
										{:else}
											<svg
												xmlns="http://www.w3.org/2000/svg"
												class="h-4 w-4"
												fill="none"
												viewBox="0 0 24 24"
												stroke="currentColor"
											>
												<path
													stroke-linecap="round"
													stroke-linejoin="round"
													stroke-width="2"
													d="M19 9l-7 7-7-7"
												/>
											</svg>
										{/if}
									</span>
								{/if}
							</div>
						</th>
						<th
							class="px-6 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider cursor-pointer whitespace-nowrap"
							on:click={() => setSortKey('clones')}
						>
							<div class="flex items-center">
								<span>Clones</span>
								{#if orderBy === 'clones'}
									<span class="ml-1">
										{#if direction === 'asc'}
											<svg
												xmlns="http://www.w3.org/2000/svg"
												class="h-4 w-4"
												fill="none"
												viewBox="0 0 24 24"
												stroke="currentColor"
											>
												<path
													stroke-linecap="round"
													stroke-linejoin="round"
													stroke-width="2"
													d="M5 15l7-7 7 7"
												/>
											</svg>
										{:else}
											<svg
												xmlns="http://www.w3.org/2000/svg"
												class="h-4 w-4"
												fill="none"
												viewBox="0 0 24 24"
												stroke="currentColor"
											>
												<path
													stroke-linecap="round"
													stroke-linejoin="round"
													stroke-width="2"
													d="M19 9l-7 7-7-7"
												/>
											</svg>
										{/if}
									</span>
								{/if}
							</div>
						</th>
						<th
							class="px-6 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider cursor-pointer whitespace-nowrap"
							on:click={() => setSortKey('revoked_at')}
						>
							<div class="flex items-center">
								<span>Status</span>
								{#if orderBy === 'revoked_at'}
									<span class="ml-1">
										{#if direction === 'asc'}
											<svg
												xmlns="http://www.w3.org/2000/svg"
												class="h-4 w-4"
												fill="none"
												viewBox="0 0 24 24"
												stroke="currentColor"
											>
												<path
													stroke-linecap="round"
													stroke-linejoin="round"
													stroke-width="2"
													d="M5 15l7-7 7 7"
												/>
											</svg>
										{:else}
											<svg
												xmlns="http://www.w3.org/2000/svg"
												class="h-4 w-4"
												fill="none"
												viewBox="0 0 24 24"
												stroke="currentColor"
											>
												<path
													stroke-linecap="round"
													stroke-linejoin="round"
													stroke-width="2"
													d="M19 9l-7 7-7-7"
												/>
											</svg>
										{/if}
									</span>
								{/if}
							</div>
						</th>
						<th
							class="px-6 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider"
							>Actions</th
						>
					</tr>
				</thead>
				<tbody class="divide-y divide-gray-200 dark:divide-gray-800">
					{#if $sharedChatsStore.length > 0}
						{#each $sharedChatsStore as chat}
							<tr class="hover:bg-gray-50 dark:hover:bg-gray-850">
								{#if $sharedChatsStore.length > 0}
									<td class="px-6 py-3 whitespace-nowrap">
										<input
											type="checkbox"
											class="form-checkbox"
											bind:checked={chat.selected}
											on:change={() => {
												if (chat.selected) {
													selectedSharedChatIds.update((ids) => [...ids, chat.id]);
												} else {
													selectedSharedChatIds.update((ids) =>
														ids.filter((id) => id !== chat.id)
													);
												}
											}}
										/>
									</td>
								{/if}
								<td class="px-6 py-3 text-gray-900 dark:text-gray-100 truncate-text">
									<a href={`/c/${chat.id}`} class="hover:underline">
										{chat.title}
									</a>
								</td>
								<td class="px-6 py-3 whitespace-nowrap text-gray-500 dark:text-gray-400"
									>{dayjs(chat.created_at * 1000).format('YYYY-MM-DD h:mm A')}</td
								>
								<td class="px-6 py-3 whitespace-nowrap text-gray-500 dark:text-gray-400"
									>{dayjs(chat.updated_at * 1000).format('YYYY-MM-DD h:mm A')}</td
								>
								<td class="px-6 py-3 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
									{#if chat.status === 'active'}
										<div class="flex items-center">
											<div class="w-80 truncate">
												<a
													href={`/s/${chat.share_id}`}
													target="_blank"
													class="text-blue-600 dark:text-blue-400 hover:underline"
												>
													/s/{chat.share_id}
												</a>
											</div>
											<Tooltip content="Copy Link" className="ml-2">
												<button
													class="p-1 rounded-md hover:bg-gray-100 dark:hover:bg-gray-800"
													on:click={() => {
														copyLink(`${window.location.origin}/s/${chat.share_id}`);
														toast.success('Link copied to clipboard');
													}}
												>
													<Clipboard class="size-4" />
												</button>
											</Tooltip>
										</div>
									{:else}
										<div class="w-48 truncate">/s/{chat.share_id}</div>
									{/if}
								</td>
								<td class="px-6 py-3 whitespace-nowrap text-gray-500 dark:text-gray-400 whitespace-nowrap"
									>{chat.is_public ? 'Yes' : 'No'}</td
								>
								<td class="px-6 py-3 whitespace-nowrap text-gray-500 dark:text-gray-400 whitespace-nowrap"
									>{chat.views}</td
								>
								<td class="px-6 py-3 whitespace-nowrap text-gray-500 dark:text-gray-400 whitespace-nowrap"
									>{chat.clones}</td
								>
								<td class="px-6 py-3 whitespace-nowrap text-gray-500 dark:text-gray-400 whitespace-nowrap">
									{#if chat.status === 'active'}
										<span
											class="px-2 py-1 text-xs font-semibold leading-5 text-green-800 bg-green-100 rounded-full"
											>Active</span
										>
									{:else}
										<span
											class="px-2 py-1 text-xs font-semibold leading-5 text-red-800 bg-red-100 rounded-full"
											>Revoked</span
										>
									{/if}
								</td>
								<td class="px-6 py-3 whitespace-nowrap text-sm font-medium">
									{#if chat.status === 'active'}
										<Tooltip content="Revoke Link" className="inline-block">
											<button
												class="text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200"
												on:click={() => {
													revokeLink(chat.id);
												}}>Revoke</button
											>
										</Tooltip>
									{:else}
										<Tooltip content="Restore Link" className="inline-block">
											<button
												class="text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200"
												on:click={() => {
													restoreLink(chat.id);
												}}>Restore</button
											>
										</Tooltip>
									{/if}
									<Tooltip content="Modify Share Link" className="inline-block">
										<button
											class="text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 ml-4"
											on:click={() => {
												selectedChatId = chat.id;
												showShareChatModal = true;
											}}>Modify</button
										>
									</Tooltip>
									<Tooltip content="Reset Statistics" className="inline-block">
										<button
											class="text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 ml-4"
											on:click={() => {
												chatToResetStats = chat;
												showConfirmResetStats = true;
											}}>Reset Stats</button
										>
									</Tooltip>
									{#if $user?.role === 'admin' || $user?.permissions?.chat?.clone}
										<Tooltip content="Clone Chat" className="inline-block">
											<button
												class="text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 ml-4"
												on:click={() => {
													cloneChat(chat.share_id);
												}}>Clone</button
											>
										</Tooltip>
									{/if}
								</td>
							</tr>
						{/each}
					{:else}
						<tr>
							<td colspan="6" class="text-center py-4 text-gray-500 dark:text-gray-400"
								>No results found</td
							>
						</tr>
					{/if}
				</tbody>
			</table>
		</div>

		{#if total > 20}
			<div class="mt-auto">
				<Pagination bind:page count={total} perPage={20} />
			</div>
		{/if}
	</div>
</div>
<ShareChatModal bind:show={showShareChatModal} chatId={selectedChatId} closeOnDelete={true} />

<ConfirmDialog
	bind:show={showConfirmRevokeSelected}
	title="Revoke Selected Links"
	message={`Are you sure you want to revoke ${totalSelectedCount} selected shared link(s)?`}
	on:confirm={doRevokeSelected}
/>

<ConfirmDialog
	bind:show={showPrimaryRevokeAllConfirm}
	title="Revoke All Links"
	message={`Are you sure you want to revoke all ${grandTotal} shared links?`}
	on:confirm={() => {
		showConfirmRevokeAll = true;
	}}
/>

<DangerZoneConfirmationModal
	bind:show={showConfirmRevokeAll}
	title="Revoke All Links"
	message={`Are you sure you want to revoke all ${grandTotal} shared links? This action cannot be undone.`}
	confirmText="REVOKE"
	confirmButtonText="Revoke All"
	confirmButtonClass="text-red-500 border-red-500 hover:bg-red-500 hover:text-white"
	on:confirm={doRevokeAll}
/>

<ConfirmDialog
	bind:show={showConfirmResetStats}
	title="Reset Statistics"
	message={`Are you sure you want to reset the stats for "${chatToResetStats?.title}"? This will set Views and Clones to 0.`}
	on:confirm={doResetStats}
/>

<ConfirmDialog
	bind:show={showConfirmResetSelected}
	title="Reset Stats for Selected"
	message={`Are you sure you want to reset the stats for ${totalSelectedCount} selected chat(s)?`}
	on:confirm={doResetSelectedStats}
/>

<ConfirmDialog
	bind:show={showPrimaryResetAllStatsConfirm}
	title="Reset All Stats"
	message={`Are you sure you want to reset the stats for all ${grandTotal} shared chats?`}
	on:confirm={() => {
		showConfirmResetAllStats = true;
	}}
/>

<DangerZoneConfirmationModal
	bind:show={showConfirmResetAllStats}
	title="Reset All Stats"
	message={`Are you sure you want to reset the stats for all ${grandTotal} shared chats? This action cannot be undone.`}
	confirmText="RESET"
	confirmButtonText="Reset All Stats"
	confirmButtonClass="text-yellow-500 border-yellow-500 hover:bg-yellow-500 hover:text-white"
	on:confirm={doResetAllStats}
/>

<ConfirmDialog
	bind:show={showConfirmClearRevoked}
	title="Clear Revoked Links"
	message={`Are you sure you want to clear all revoked shared links? This will permanently remove their sharing information.`}
	on:confirm={doClearRevoked}
/>
