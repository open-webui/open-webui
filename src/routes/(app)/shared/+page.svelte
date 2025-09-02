<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { tick } from 'svelte';
	import { get } from 'svelte/store';
	import {
		getSharedChats,
		getAllSharedChatsMeta,
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
		chatsUpdated,
		settings,

		WEBUI_NAME

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
	import SortIcon from '$lib/components/icons/SortIcon.svelte';
	import Eye from '$lib/components/icons/Eye.svelte';
	import EyeSlash from '$lib/components/icons/EyeSlash.svelte';
	import Pencil from '$lib/components/icons/Pencil.svelte';
	import DocumentDuplicate from '$lib/components/icons/DocumentDuplicate.svelte';
	import ArrowPath from '$lib/components/icons/ArrowPath.svelte';
	import GlobeAltSolid from '$lib/components/icons/GlobeAltSolid.svelte';
	import User from '$lib/components/icons/User.svelte';
	import LockClosed from '$lib/components/icons/LockClosed.svelte';
	import LockOpen from '$lib/components/icons/LockOpen.svelte';

	let showShareChatModal = false;
	let selectedChatId = '';

	let showConfirmRevokeSelected = false;
	let showConfirmRevokeAll = false;
	let showPrimaryRevokeAllConfirm = false;
	let showConfirmResetSelected = false;
	let showConfirmResetAllStats = false;
	let showPrimaryResetAllStatsConfirm = false;
	let showConfirmClearRevoked = false;
	let showPrimaryClearRevokedConfirm = false;
	let revokedCount = 0;
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
	let passwordFilter = null;
	let statusFilter = 'all';
	let typeFilter = 'all';
	let totalSelectedCount = 0;
	let allSharedChatsMeta = [];
	let hasRevokedChats = false;

	const publicFilterOptions = [
		{ value: null, label: 'Visibility: All' },
		{ value: true, label: 'Visibility: Public' },
		{ value: false, label: 'Visibility: Private' }
	];

	const passwordFilterOptions = [
		{ value: null, label: 'Password: All' },
		{ value: true, label: 'Password: Yes' },
		{ value: false, label: 'Password: No' }
	];

	const statusFilterOptions = [
		{ value: 'all', label: 'Status: All' },
		{ value: 'active', label: 'Status: Active' },
		{ value: 'expired', label: 'Status: Expired' },
		{ value: 'revoked', label: 'Status: Revoked' }
	];

	const typeFilterOptions = [
		{ value: 'all', label: 'Type: All' },
		{ value: 'snapshot', label: 'Type: Snapshot' },
		{ value: 'live', label: 'Type: Live' }
	];

	$: selectedPublicFilterIndex = publicFilterOptions.findIndex((o) => o.value === publicFilter);
	$: selectedPasswordFilterIndex = passwordFilterOptions.findIndex(
		(o) => o.value === passwordFilter
	);
	$: selectedStatusFilterIndex = statusFilterOptions.findIndex((o) => o.value === statusFilter);
	$: selectedTypeFilterIndex = typeFilterOptions.findIndex((o) => o.value === typeFilter);

	let apiTypeFilter = null;
	$: {
		if (typeFilter === 'all') {
			apiTypeFilter = null;
		} else if (typeFilter === 'snapshot') {
			apiTypeFilter = true;
		} else {
			apiTypeFilter = false;
		}
	}

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
	};

	const handlePasswordFilterScroll = (event) => {
		event.preventDefault();
		const direction = event.deltaY < 0 ? -1 : 1;
		let newIndex = selectedPasswordFilterIndex + direction;

		if (newIndex < 0) {
			newIndex = passwordFilterOptions.length - 1;
		} else if (newIndex >= passwordFilterOptions.length) {
			newIndex = 0;
		}
		passwordFilter = passwordFilterOptions[newIndex].value;
		page = 1;
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
	};

	const handleTypeFilterScroll = (event) => {
		event.preventDefault();
		const direction = event.deltaY < 0 ? -1 : 1;
		let newIndex = selectedTypeFilterIndex + direction;

		if (newIndex < 0) {
			newIndex = typeFilterOptions.length - 1;
		} else if (newIndex >= typeFilterOptions.length) {
			newIndex = 0;
		}
		typeFilter = typeFilterOptions[newIndex].value;
		page = 1;
	};

	const handleDateScroll = (event, type) => {
		event.preventDefault();
		const direction = event.deltaY < 0 ? 1 : -1;

		if (type === 'start') {
			if (startDate) {
				const newStartDate = dayjs(startDate).add(direction, 'day');
				startDate = newStartDate.format('YYYY-MM-DD');

				if (endDate && newStartDate.isAfter(dayjs(endDate))) {
					endDate = startDate;
				}
			}
		} else if (type === 'end') {
			if (endDate) {
				const newEndDate = dayjs(endDate).add(direction, 'day');
				endDate = newEndDate.format('YYYY-MM-DD');

				if (startDate && newEndDate.isBefore(dayjs(startDate))) {
					startDate = endDate;
				}
			}
		}
	};
	$: dateFilterApplied = !!(startDate && endDate);

	const clearDateFilter = () => {
		startDate = '';
		endDate = '';
		dateFilterApplied = false;
	};

	const setSortKey = (key) => {
		if (key === 'status') {
			if (orderBy !== 'status') {
				orderBy = 'status';
				direction = 'active';
			} else {
				if (direction === 'active') {
					direction = 'expired';
				} else if (direction === 'expired') {
					direction = 'revoked';
				} else {
					direction = 'active';
				}
			}
		} else {
			if (orderBy === key) {
				direction = direction === 'asc' ? 'desc' : 'asc';
			} else {
				orderBy = key;
				direction = 'asc';
			}
		}
	};

	const getSharedChatList = async (
		_page,
		_searchTerm,
		_orderBy,
		_direction,
		_startDate,
		_endDate,
		_publicFilter,
		_passwordFilter,
		_statusFilter,
		_typeFilter
	) => {
		if ($user) {
			const res = await getSharedChats(
				localStorage.token,
				_page,
				_searchTerm,
				_orderBy,
				_direction,
				_startDate ? dayjs(_startDate).startOf('day').unix() : undefined,
				_endDate ? dayjs(_endDate).endOf('day').unix() : undefined,
				_publicFilter,
				_passwordFilter,
				_statusFilter,
				_typeFilter
			);
			total = res.total;
			grandTotal = res.grand_total;

			sharedChatsStore.set(res.chats);

			if (res.chats.length === 0 && _page > 1) {
				page = 1;
			}

			const revokedRes = await getAllSharedChatsMeta(
				localStorage.token,
				'',
				undefined,
				undefined,
				null,
				null,
				'revoked'
			);
			if (revokedRes) {
				revokedCount = revokedRes.length;
			}
		}
	};

	let previousShowShareChatModal = false;
	onMount(async () => {
		models.set(await getModels(localStorage.token));
		previousShowShareChatModal = showShareChatModal;

		const res = await getAllSharedChatsMeta(
			localStorage.token,
			'',
			undefined,
			undefined,
			null,
			null,
			'revoked'
		);
		if (res) {
			revokedCount = res.length;
		}
	});

	$: if ($user && !($user.role === 'admin' || $user.permissions?.sharing?.shared_chats)) {
		goto('/');
		toast.error("You don't have permission to access this page.");
	}

	$: if ($sharedChatsUpdated) {
		getSharedChatList(page, searchTerm, orderBy, direction, startDate, endDate, publicFilter, passwordFilter, statusFilter, apiTypeFilter);
		sharedChatsUpdated.set(false);
	}

	$: if (previousShowShareChatModal && !showShareChatModal) {
		getSharedChatList(page, searchTerm, orderBy, direction, startDate, endDate, publicFilter, passwordFilter, statusFilter, apiTypeFilter);
	}

	$: previousShowShareChatModal = showShareChatModal;

	$: getSharedChatList(page, searchTerm, orderBy, direction, startDate, endDate, publicFilter, passwordFilter, statusFilter, apiTypeFilter);

	$: (async () => {
		if (
			searchTerm ||
			(startDate && endDate) ||
			publicFilter !== null ||
			passwordFilter !== null ||
			statusFilter !== 'all'
		) {
			const filteredChats = await getAllSharedChatsMeta(
				localStorage.token,
				searchTerm,
				startDate ? dayjs(startDate).startOf('day').unix() : undefined,
				endDate ? dayjs(endDate).endOf('day').unix() : undefined,
				publicFilter,
				passwordFilter,
				statusFilter
			);
			const filteredIdSet = new Set(filteredChats.map((c) => c.id));
			totalSelectedCount = $selectedSharedChatIds.filter((id) => filteredIdSet.has(id)).length;
			allSharedChatsMeta = filteredChats;
		} else {
			totalSelectedCount = $selectedSharedChatIds.length;
			if (selectionLevel === 'all') {
				allSharedChatsMeta = await getAllSharedChatsMeta(localStorage.token);
			} else {
				allSharedChatsMeta = [];
			}
		}

		if (selectionLevel === 'all') {
			hasRevokedChats = allSharedChatsMeta.some((chat) => chat.status === 'revoked');
		} else {
			hasRevokedChats = $sharedChatsStore.some((chat) => chat.status === 'revoked');
		}
	})();

	$: displayedChats = $sharedChatsStore;

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
					sharedChatsUpdated.set(true);
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
			getSharedChatList(page, searchTerm, orderBy, direction, startDate, endDate, publicFilter, passwordFilter, statusFilter);
			selectedSharedChatIds.update((ids) => ids.filter((id) => id !== chatId));
		} else {
			toast.error('Failed to revoke link');
		}
	};

	const restoreLink = async (chatId) => {
		const res = await restoreSharedChat(localStorage.token, chatId);
		if (res) {
			toast.success('Link restored');
			getSharedChatList(page, searchTerm, orderBy, direction, startDate, endDate, publicFilter, passwordFilter, statusFilter);
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
		getSharedChatList(page, searchTerm, orderBy, direction, startDate, endDate, publicFilter, passwordFilter, statusFilter);
		selectedSharedChatIds.set([]);
		showConfirmRevokeSelected = false;
	};

	const doRevokeAll = async () => {
		const res = await revokeAllSharedChats(localStorage.token);
		if (res) {
			toast.success(`${res.revoked} links revoked`);
			getSharedChatList(page, searchTerm, orderBy, direction, startDate, endDate, publicFilter, passwordFilter, statusFilter);
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
			getSharedChatList(page, searchTerm, orderBy, direction, startDate, endDate, publicFilter, passwordFilter, statusFilter); // This will refresh the list with the updated data
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
			getSharedChatList(page, searchTerm, orderBy, direction, startDate, endDate, publicFilter, passwordFilter, statusFilter);
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
			getSharedChatList(page, searchTerm, orderBy, direction, startDate, endDate, publicFilter, passwordFilter, statusFilter);
		} else {
			toast.error('Failed to reset all chat statistics.');
		}
		showConfirmResetAllStats = false;
	};

	const doClearRevoked = async () => {
		const res = await clearRevokedSharedChats(localStorage.token);
		if (res) {
			toast.success(`${res.cleared} revoked link(s) cleared.`);
			getSharedChatList(page, searchTerm, orderBy, direction, startDate, endDate, publicFilter, passwordFilter, statusFilter);
			selectedSharedChatIds.set([]);
		} else {
			toast.error('Failed to clear revoked links.');
		}
		showConfirmClearRevoked = false;
	};

	let selectionLevel = 'none'; // none, page, some, all
	let masterCheckbox;

	const handleMasterCheckboxClick = async () => {
		const currentLevel = selectionLevel;

		if (currentLevel === 'all') {
			selectedSharedChatIds.set([]);
		} else if (currentLevel === 'page') {
			const allChats = await getAllSharedChatsMeta(
				localStorage.token,
				searchTerm,
				startDate ? dayjs(startDate).startOf('day').unix() : undefined,
				endDate ? dayjs(endDate).endOf('day').unix() : undefined,
				publicFilter,
				passwordFilter,
				statusFilter
			);
			selectedSharedChatIds.set(allChats.map((c) => c.id));
		} else {
			const currentPageIds = $sharedChatsStore.map((chat) => chat.id);
			selectedSharedChatIds.update((ids) => [...new Set([...ids, ...currentPageIds])]);
		}

		await tick();

		setTimeout(() => {
			if (masterCheckbox) {
				masterCheckbox.checked = selectionLevel === 'page' || selectionLevel === 'all';
				masterCheckbox.indeterminate = selectionLevel === 'some';
			}
		}, 0);
	};

	$: displayedChats = $sharedChatsStore.map((chat) => ({
		...chat,
		selected: $selectedSharedChatIds.includes(chat.id)
	}));

	$: {
		if (grandTotal > 0) {
			const allSelected = $selectedSharedChatIds.length === total;
			const allOnPage =
				displayedChats.length > 0 && displayedChats.every((c) => c.selected);
			const someOnPage = displayedChats.some((c) => c.selected);

			if (allSelected && total > 0) {
				selectionLevel = 'all';
			} else if (allOnPage) {
				selectionLevel = 'page';
			} else if (someOnPage) {
				selectionLevel = 'some';
			} else {
				selectionLevel = 'none';
			}
		} else {
			selectionLevel = 'none';
		}
	}

	let masterCheckboxTooltip = '';
	$: {
		if (selectionLevel === 'all') {
			masterCheckboxTooltip = 'Deselect All';
		} else if (selectionLevel === 'page') {
			masterCheckboxTooltip = 'Select All';
		} else {
			masterCheckboxTooltip = 'Select Page';
		}
	}
</script>

<style>
	.truncate-text {
		max-width: 250px;
		overflow: hidden;
		white-space: nowrap;
		text-overflow: ellipsis;
	}
</style>

<svelte:head>
	<title>
		{$i18n.t('Shared Chats')} • {$WEBUI_NAME}
	</title>
</svelte:head>

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
			if (data) {
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
			}
		} catch (e) {
			// This is a drag and drop of a non-chat item, so we don't need to show an error
		}
	}}
>
	{#if $settings?.backgroundImageUrl ?? $config?.license_metadata?.background_image_url ?? null}
		<div
			class="absolute {$showSidebar
				? 'md:max-w-[calc(100%-260px)] md:translate-x-[260px]'
				: ''} top-0 left-0 w-full h-full bg-cover bg-center bg-no-repeat"
			style="background-image: url({$settings?.backgroundImageUrl ??
				$config?.license_metadata?.background_image_url})  "
		/>

		<div
			class="absolute top-0 left-0 w-full h-full bg-linear-to-t from-white to-white/85 dark:from-gray-900 dark:to-gray-900/90 z-0"
		/>
	{/if}

	<div
		class="flex w-full justify-between items-center p-4 border-b border-gray-100 dark:border-gray-800 z-10"
	>
		<div class="flex-1 flex items-center">
			<div class="text-lg font-semibold">{headerText}</div>
		</div>
	</div>

	<div class="p-4 space-y-4 flex-grow flex flex-col z-10">
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
					on:wheel|preventDefault={(e) => handleDateScroll(e, 'start')}
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
					on:wheel|preventDefault={(e) => handleDateScroll(e, 'end')}
				/>
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
					bind:value={passwordFilter}
					on:change={() => {
						page = 1;
					}}
					on:wheel|preventDefault={handlePasswordFilterScroll}
				>
					{#each passwordFilterOptions as option}
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
					}}
					on:wheel|preventDefault={handleStatusFilterScroll}
				>
					{#each statusFilterOptions as option}
						<option value={option.value}>{option.label}</option>
					{/each}
				</select>
			</div>
			<div class="relative">
				<select
					class="pl-4 pr-10 py-2 border border-gray-300 rounded-lg dark:bg-gray-800 dark:border-gray-700"
					bind:value={typeFilter}
					on:change={() => {
						page = 1;
					}}
					on:wheel|preventDefault={handleTypeFilterScroll}
				>
					{#each typeFilterOptions as option}
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
					on:click={() => (showPrimaryClearRevokedConfirm = true)}
					disabled={!hasRevokedChats}
				>
					Clear Revoked
				</button>
			</div>
		</div>
		<div class="overflow-x-auto flex-grow">
			<table
				class="min-w-full bg-white/80 dark:bg-gray-900/80 rounded-lg shadow-md backdrop-blur-sm"
			>
				<thead>
					<tr class="w-full h-10 border-b border-gray-200 dark:border-gray-800">
						{#if displayedChats.length > 0}
							<th
								class="px-6 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider"
							>
								<Tooltip content={masterCheckboxTooltip}>
									<input
										type="checkbox"
										class="form-checkbox"
										on:click|preventDefault={handleMasterCheckboxClick}
										bind:this={masterCheckbox}
									/>
								</Tooltip>
							</th>
						{/if}
						<th
							class="px-6 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider cursor-pointer"
							on:click={() => setSortKey('title')}
							on:wheel|preventDefault={() => setSortKey('title')}
						>
							<div class="flex items-center">
								<span>Title</span>
								<SortIcon direction={direction} active={orderBy === 'title'} />
							</div>
						</th>
						<th
							class="px-6 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider cursor-pointer"
							on:click={() => setSortKey('created_at')}
							on:wheel|preventDefault={() => setSortKey('created_at')}
						>
							<div class="flex items-center">
								<span>Created On</span>
								<SortIcon direction={direction} active={orderBy === 'created_at'} />
							</div>
						</th>
						<th
							class="px-6 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider cursor-pointer"
							on:click={() => setSortKey('updated_at')}
							on:wheel|preventDefault={() => setSortKey('updated_at')}
						>
							<div class="flex items-center">
								<span>Last Updated</span>
								<SortIcon direction={direction} active={orderBy === 'updated_at'} />
							</div>
						</th>
						<th
							class="px-6 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider cursor-pointer"
							on:click={() => setSortKey('share_id')}
							on:wheel|preventDefault={() => setSortKey('share_id')}
						>
							<div class="flex items-center">
								<span>Link</span>
								<SortIcon direction={direction} active={orderBy === 'share_id'} />
							</div>
						</th>
						<th
							class="px-6 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider cursor-pointer whitespace-nowrap"
							on:click={() => setSortKey('is_public')}
							on:wheel|preventDefault={() => setSortKey('is_public')}
						>
							<div class="flex items-center">
								<span>Visibility</span>
								<SortIcon direction={direction} active={orderBy === 'is_public'} />
							</div>
						</th>
						<th
							class="px-6 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider cursor-pointer whitespace-nowrap"
							on:click={() => setSortKey('password')}
							on:wheel|preventDefault={() => setSortKey('password')}
						>
							<div class="flex items-center">
								<span>Password</span>
								<SortIcon direction={direction} active={orderBy === 'password'} />
							</div>
						</th>
						<th
							class="px-6 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider cursor-pointer whitespace-nowrap"
							on:click={() => setSortKey('views')}
							on:wheel|preventDefault={() => setSortKey('views')}
						>
							<div class="flex items-center">
								<span>Views</span>
								<SortIcon direction={direction} active={orderBy === 'views'} />
							</div>
						</th>
						<th
							class="px-6 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider cursor-pointer whitespace-nowrap"
							on:click={() => setSortKey('clones')}
							on:wheel|preventDefault={() => setSortKey('clones')}
						>
							<div class="flex items-center">
								<span>Clones</span>
								<SortIcon direction={direction} active={orderBy === 'clones'} />
							</div>
						</th>
						<th
							class="px-6 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider cursor-pointer whitespace-nowrap"
							on:click={() => setSortKey('status')}
							on:wheel|preventDefault={() => setSortKey('status')}
						>
							<div class="flex items-center">
								<span>Status</span>
								<SortIcon direction={direction} active={orderBy === 'status'} />
							</div>
						</th>
						<th
							class="px-6 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider cursor-pointer whitespace-nowrap"
							on:click={() => setSortKey('is_snapshot')}
							on:wheel|preventDefault={() => setSortKey('is_snapshot')}
						>
							<div class="flex items-center">
								<span>Type</span>
								<SortIcon direction={direction} active={orderBy === 'is_snapshot'} />
							</div>
						</th>
						<th
							class="px-6 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider"
							>Actions</th
						>
					</tr>
				</thead>
				<tbody class="divide-y divide-gray-200 dark:divide-gray-800">
					{#if displayedChats.length > 0}
						{#each displayedChats as chat}
							<tr class="hover:bg-gray-50/80 dark:hover:bg-gray-850/80">
								{#if displayedChats.length > 0}
									<td class="px-6 py-3 whitespace-nowrap">
										<input
											type="checkbox"
											class="form-checkbox"
											checked={chat.selected}
											on:change={() => {
												selectedSharedChatIds.update((ids) => {
													const set = new Set(ids);
													if (set.has(chat.id)) {
														set.delete(chat.id);
													} else {
														set.add(chat.id);
													}
													return [...set];
												});
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
								<td
									class="px-6 py-3 whitespace-nowrap text-gray-500 dark:text-gray-400 whitespace-nowrap"
								>
									{#if chat.is_public}
										<Tooltip content="Public">
											<GlobeAltSolid class="size-5" />
										</Tooltip>
									{:else}
										<Tooltip content="Private">
											<User class="size-5" />
										</Tooltip>
									{/if}
								</td>
								<td
									class="px-6 py-3 whitespace-nowrap text-gray-500 dark:text-gray-400 whitespace-nowrap"
								>
									{#if chat.has_password}
										<Tooltip content="Password Protected">
											<LockClosed class="size-5" />
										</Tooltip>
									{:else}
										<Tooltip content="No Password">
											<LockOpen class="size-5" />
										</Tooltip>
									{/if}
								</td>
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
									{:else if chat.status === 'expired'}
										<span
											class="px-2 py-1 text-xs font-semibold leading-5 text-yellow-800 bg-yellow-100 rounded-full"
											>Expired</span
										>
									{:else}
										<span
											class="px-2 py-1 text-xs font-semibold leading-5 text-red-800 bg-red-100 rounded-full"
											>Revoked</span
										>
									{/if}
								</td>
								<td class="px-6 py-3 whitespace-nowrap text-gray-500 dark:text-gray-400 whitespace-nowrap">
									{#if chat.is_snapshot}
										<span
											class="px-2 py-1 text-xs font-semibold leading-5 text-blue-800 bg-blue-100 rounded-full"
											>Snapshot</span
										>
									{:else}
										<span
											class="px-2 py-1 text-xs font-semibold leading-5 text-purple-800 bg-purple-100 rounded-full"
											>Live</span
										>
									{/if}
								</td>
								<td class="px-6 py-3 whitespace-nowrap text-sm font-medium">
									<div class="flex items-center">
										{#if chat.status === 'active'}
											<Tooltip content="Revoke Link" className="inline-block">
												<button
													class="text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 p-1 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800"
													on:click={() => {
														revokeLink(chat.id);
													}}><EyeSlash class="size-4" /></button
												>
											</Tooltip>
										{:else}
											<Tooltip content="Re-activate Link" className="inline-block">
												<button
													class="text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 p-1 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800"
													on:click={() => {
														restoreLink(chat.id);
													}}><Eye class="size-4" /></button
												>
											</Tooltip>
										{/if}
										<Tooltip content="Modify Share Link" className="inline-block">
											<button
												class="text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 p-1 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 ml-2"
												on:click={() => {
													selectedChatId = chat.id;
													showShareChatModal = true;
												}}><Pencil class="size-4" /></button
											>
										</Tooltip>
										{#if $user?.role === 'admin' || $user?.permissions?.chat?.clone}
											<Tooltip content="Clone Chat" className="inline-block">
												<button
													class="text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 p-1 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 ml-2"
													on:click={() => {
														cloneChat(chat.share_id);
													}}><DocumentDuplicate class="size-4" /></button
												>
											</Tooltip>
										{/if}
										<Tooltip content="Reset Statistics" className="inline-block">
											<button
												class="text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 p-1 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 ml-2"
												on:click={() => {
													chatToResetStats = chat;
													showConfirmResetStats = true;
												}}><ArrowPath class="size-4" /></button
											>
										</Tooltip>
									</div>
								</td>
							</tr>
						{/each}
					{:else}
						<tr>
							<td colspan="12" class="text-center py-4 text-gray-500 dark:text-gray-400"
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
	bind:show={showPrimaryClearRevokedConfirm}
	title="Clear Revoked Links"
	message={`Are you sure you want to clear all ${revokedCount} revoked shared links? This will permanently remove their sharing information.`}
	on:confirm={() => {
		showConfirmClearRevoked = true;
	}}
/>

<DangerZoneConfirmationModal
	bind:show={showConfirmClearRevoked}
	title="Clear Revoked Links"
	message={`Are you sure you want to clear all ${revokedCount} revoked shared links? This will permanently remove their sharing information.`}
	confirmText="CLEAR"
	confirmButtonText="Clear Revoked"
	confirmButtonClass="text-red-600 border-red-600 hover:bg-red-600 hover:text-white"
	on:confirm={doClearRevoked}
/>
