<script lang="ts">
	import { onMount, onDestroy, getContext, tick } from 'svelte';
	const i18n = getContext('i18n');

	import { goto } from '$app/navigation';
	import { toast } from 'svelte-sonner';

	import {
		showSidebar,
		sidebarPinned,
		user,
		currentSpaceId,
		models,
		toolServers,
		socket,
		WEBUI_NAME
	} from '$lib/stores';
	import {
		getSpaceBySlug,
		getSpaceKnowledge,
		updateSpaceById,
		uploadFileToSpace,
		getSpaceFiles,
		removeFileFromSpace,
		addLinkToSpace,
		getSpaceLinks,
		removeLinkFromSpace,
		linkExistingFileToSpace,
		addBookmark,
		removeBookmark,
		getBookmarkedSpaces,
		cloneTemplate,
		updateThreadAccess,
		subscribeToSpace,
		unsubscribeFromSpace,
		getSubscriptionStatus,
		syncSharePointFiles
	} from '$lib/apis/spaces';
	import type { Space, SpaceLink, SpaceCloneForm } from '$lib/apis/spaces';
	import { getChatListBySpaceId } from '$lib/apis/chats';

	import Spinner from '$lib/components/common/Spinner.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Folder from '$lib/components/common/Folder.svelte';
	import SpaceSettingsModal from '$lib/components/layout/Sidebar/SpaceSettingsModal.svelte';
	import SpaceShareModal from '$lib/components/space/SpaceShareModal.svelte';
	import SharePointFilePicker from '$lib/components/chat/SharePointFilePicker.svelte';
	import SocialShareLinks from '$lib/components/space/SocialShareLinks.svelte';
	import { respondToInvitation, SpacePermission } from '$lib/apis/spaces';
	import ChevronLeft from '$lib/components/icons/ChevronLeft.svelte';
	import ChevronRight from '$lib/components/icons/ChevronRight.svelte';
	import PencilSquare from '$lib/components/icons/PencilSquare.svelte';
	import BookOpen from '$lib/components/icons/BookOpen.svelte';
	import GlobeAlt from '$lib/components/icons/GlobeAlt.svelte';
	import ChatBubbleOval from '$lib/components/icons/ChatBubbleOval.svelte';
	import Cog6 from '$lib/components/icons/Cog6.svelte';
	import EllipsisHorizontal from '$lib/components/icons/EllipsisHorizontal.svelte';
	import MessageInput from '$lib/components/chat/MessageInput.svelte';

	export let slug: string = '';

	let space: Space | null = null;
	let knowledgeBases: any[] = [];
	let threads: Array<{ title: string; id: string; updated_at: number; unread?: boolean }> = [];
	let loading = true;
	let error: string | null = null;
	let threadsLoading = false;
	let threadsPage = 1;
	let hasMoreThreads = true;

	let showSettingsModal = false;
	let showShareModal = false;
	let hasPendingInvitation = false;
	let invitationResponding = false;

	let files: any[] = [];
	let links: SpaceLink[] = [];
	let uploading = false;
	let addingLink = false;
	let newLinkUrl = '';
	let newLinkTitle = '';
	let fileInputEl: HTMLInputElement;
	let showFileDropdown = false;
	let showSharePointPicker = false;

	let isBookmarked = false;
	let isSubscribed = false;
	let threadAccessDropdown: string | null = null;
	let syncingSharePoint = false;

	$: hasPendingInvitation =
		space != null &&
		space.user_permission == null &&
		space.contributors?.some((c) => c.email === $user?.email && !c.accepted) === true;

	// Group files by SharePoint site, then by folder for nested display
	interface FolderGroup {
		folderId: string;
		folderName: string;
		files: any[];
	}

	interface SiteGroup {
		siteName: string;
		folders: FolderGroup[];
		totalFiles: number;
	}

	// Individual files not from SharePoint folders
	$: individualFiles = files.filter(
		(f) => !f.meta?.sharepoint_folder_id || f.meta?.source !== 'sharepoint'
	);

	// SharePoint files grouped by site, then folder
	$: siteGroups = (() => {
		const sites: Map<string, Map<string, FolderGroup>> = new Map();

		for (const file of files) {
			if (file.meta?.source !== 'sharepoint' || !file.meta?.sharepoint_folder_id) continue;

			const siteName = file.meta?.sharepoint_site_name || 'SharePoint';
			const folderId = file.meta.sharepoint_folder_id;
			const folderName = file.meta?.sharepoint_folder_name || 'Folder';

			if (!sites.has(siteName)) {
				sites.set(siteName, new Map());
			}

			const siteFolders = sites.get(siteName)!;
			if (!siteFolders.has(folderId)) {
				siteFolders.set(folderId, {
					folderId,
					folderName,
					files: []
				});
			}
			siteFolders.get(folderId)!.files.push(file);
		}

		// Convert to array and sort
		const result: SiteGroup[] = [];
		for (const [siteName, foldersMap] of sites) {
			const folders = Array.from(foldersMap.values()).sort((a, b) =>
				a.folderName.localeCompare(b.folderName)
			);
			const totalFiles = folders.reduce((sum, f) => sum + f.files.length, 0);
			result.push({ siteName, folders, totalFiles });
		}

		return result.sort((a, b) => a.siteName.localeCompare(b.siteName));
	})();

	// Check if we have any SharePoint files for sync button visibility
	$: hasSharePointFiles = files.some((f) => f.meta?.source === 'sharepoint');

	// Inline editing
	let editingTitle = false;
	let editingDescription = false;
	let editTitle = '';
	let editDescription = '';
	let titleInputEl: HTMLInputElement;
	let descInputEl: HTMLTextAreaElement;

	// Chat input (MessageInput state)
	let chatInput = '';
	let chatTextareaEl: HTMLTextAreaElement;
	let chatFiles: any[] = [];
	let selectedModels: [''] = [''];
	let chatHistory = { messages: {}, currentId: null };
	let autoScroll = false;
	let selectedToolIds: string[] = [];
	let selectedFilterIds: string[] = [];
	let imageGenerationEnabled = false;
	let webSearchEnabled = false;
	let codeInterpreterEnabled = false;

	// Derive selectedModels from space model_id when space loads
	$: if (space?.model_id) {
		selectedModels = [space.model_id];
	}

	// Instructions expand
	let instructionsExpanded = false;

	$: if (slug) {
		loadSpace();
	}

	const loadSpace = async () => {
		loading = true;
		error = null;
		threads = [];
		threadsPage = 1;
		hasMoreThreads = true;

		try {
			space = await getSpaceBySlug(localStorage.token, slug);

			if (space) {
				const kb = await getSpaceKnowledge(localStorage.token, space.id).catch(() => null);
				knowledgeBases = kb ?? [];
				files = await getSpaceFiles(localStorage.token, space.id).catch(() => []);
				links = await getSpaceLinks(localStorage.token, space.id).catch(() => []);
				const bookmarks = await getBookmarkedSpaces(localStorage.token).catch(() => []);
				isBookmarked = bookmarks.some((b: Space) => b.id === space?.id);
				const subStatus = await getSubscriptionStatus(localStorage.token, space.id).catch(
					() => null
				);
				isSubscribed = subStatus?.subscribed ?? false;
				await loadThreads();
			} else {
				error = 'Space not found';
			}
		} catch (err) {
			error = String(err);
		}

		loading = false;
	};

	const loadThreads = async () => {
		if (!space || threadsLoading) return;
		threadsLoading = true;

		try {
			const result = await getChatListBySpaceId(localStorage.token, space.id, threadsPage);
			if (result && Array.isArray(result)) {
				if (result.length === 0) {
					hasMoreThreads = false;
				} else {
					threads = [...threads, ...result];
					threadsPage += 1;
					if (result.length < 20) {
						hasMoreThreads = false;
					}
				}
			} else {
				hasMoreThreads = false;
			}
		} catch (err) {
			console.error('Failed to load threads:', err);
			hasMoreThreads = false;
		}

		threadsLoading = false;
	};

	const startChat = () => {
		if (space) {
			currentSpaceId.set(space.id);
		}
		goto('/');
	};

	// handleChatSubmit is now inline in the MessageInput on:submit handler

	const getRelativeTime = (timestamp: number): string => {
		const now = Date.now() / 1000;
		const diff = now - timestamp;

		if (diff < 60) return $i18n.t('just now');
		if (diff < 3600) {
			const mins = Math.floor(diff / 60);
			return mins === 1 ? $i18n.t('1 min ago') : $i18n.t('{{count}} min ago', { count: mins });
		}
		if (diff < 86400) {
			const hrs = Math.floor(diff / 3600);
			return hrs === 1 ? $i18n.t('1 hr ago') : $i18n.t('{{count}} hrs ago', { count: hrs });
		}
		if (diff < 172800) return $i18n.t('yesterday');
		if (diff < 604800) {
			const days = Math.floor(diff / 86400);
			return $i18n.t('{{count}} days ago', { count: days });
		}
		const date = new Date(timestamp * 1000);
		return date.toLocaleDateString();
	};

	const startEditTitle = async () => {
		if (!space?.write_access) return;
		editTitle = space?.name ?? '';
		editingTitle = true;
		await tick();
		titleInputEl?.focus();
		titleInputEl?.select();
	};

	const saveTitle = async () => {
		if (!space || !editTitle.trim()) {
			editingTitle = false;
			return;
		}
		if (editTitle.trim() === space.name) {
			editingTitle = false;
			return;
		}
		try {
			const updated = await updateSpaceById(localStorage.token, space.id, {
				name: editTitle.trim()
			});
			if (updated) {
				space = updated;
				toast.success($i18n.t('Title updated'));
			}
		} catch (err) {
			toast.error(String(err));
		}
		editingTitle = false;
	};

	const startEditDescription = async () => {
		if (!space?.write_access) return;
		editDescription = space?.description ?? '';
		editingDescription = true;
		await tick();
		descInputEl?.focus();
	};

	const saveDescription = async () => {
		if (!space) {
			editingDescription = false;
			return;
		}
		const newDesc = editDescription.trim();
		if (newDesc === (space.description ?? '')) {
			editingDescription = false;
			return;
		}
		try {
			const updated = await updateSpaceById(localStorage.token, space.id, {
				description: newDesc || null
			});
			if (updated) {
				space = updated;
				toast.success($i18n.t('Description updated'));
			}
		} catch (err) {
			toast.error(String(err));
		}
		editingDescription = false;
	};

	const handleTitleKeydown = (e: KeyboardEvent) => {
		if (e.key === 'Enter') {
			e.preventDefault();
			saveTitle();
		}
		if (e.key === 'Escape') {
			editingTitle = false;
		}
	};

	const handleDescKeydown = (e: KeyboardEvent) => {
		if (e.key === 'Escape') {
			editingDescription = false;
		}
	};

	const handleFileUpload = async (e: Event) => {
		const target = e.target as HTMLInputElement;
		const selectedFiles = target.files;
		if (!selectedFiles || !space) return;

		uploading = true;
		try {
			for (let i = 0; i < selectedFiles.length; i++) {
				await uploadFileToSpace(localStorage.token, space.id, selectedFiles[i]);
			}
			files = await getSpaceFiles(localStorage.token, space.id).catch(() => []);
			toast.success($i18n.t('File uploaded'));
		} catch (err) {
			toast.error(String(err));
		}
		uploading = false;
		if (fileInputEl) fileInputEl.value = '';
	};

	const handleRemoveFile = async (fileId: string) => {
		if (!space) return;
		try {
			await removeFileFromSpace(localStorage.token, space.id, fileId);
			files = files.filter((f: any) => f.id !== fileId);
			toast.success($i18n.t('File removed'));
		} catch (err) {
			toast.error(String(err));
		}
	};

	const handleSharePointFileDownloaded = async (e: CustomEvent) => {
		if (!space) return;
		const result = e.detail;
		if (!result?.id) {
			toast.error('SharePoint download returned no file ID');
			return;
		}
		try {
			// Check if file was imported via bulk folder import (already linked to space)
			const isBulkImport = result.meta?.sharepoint_folder_id !== undefined;
			if (!isBulkImport) {
				// Individual file download - need to link to space
				await linkExistingFileToSpace(localStorage.token, space.id, result.id);
			}
			// Refresh files list
			files = await getSpaceFiles(localStorage.token, space.id).catch(() => []);
		} catch (err) {
			toast.error(String(err));
		}
	};

	const handleSyncSharePoint = async () => {
		if (!space) return;
		const sharepointFiles = files.filter((f: any) => f.meta?.source === 'sharepoint');
		if (sharepointFiles.length === 0) {
			toast.info($i18n.t('No SharePoint files to sync'));
			return;
		}

		syncingSharePoint = true;
		try {
			const result = await syncSharePointFiles(localStorage.token, space.id);
			if (result.updated > 0) {
				toast.success($i18n.t('Updated {{count}} file(s)', { count: result.updated }));
				files = await getSpaceFiles(localStorage.token, space.id).catch(() => []);
			} else {
				toast.success($i18n.t('All files are up to date'));
			}
		} catch (err) {
			toast.error(String(err));
		} finally {
			syncingSharePoint = false;
		}
	};

	const handleAddLink = async () => {
		if (!space || !newLinkUrl.trim()) return;
		try {
			const link = await addLinkToSpace(
				localStorage.token,
				space.id,
				newLinkUrl.trim(),
				newLinkTitle.trim() || undefined
			);
			if (link) {
				links = [...links, link];
			}
			newLinkUrl = '';
			newLinkTitle = '';
			addingLink = false;
			toast.success($i18n.t('Link added'));
		} catch (err) {
			toast.error(String(err));
		}
	};

	const handleRemoveLink = async (linkId: string) => {
		if (!space) return;
		try {
			await removeLinkFromSpace(localStorage.token, space.id, linkId);
			links = links.filter((l) => l.id !== linkId);
			toast.success($i18n.t('Link removed'));
		} catch (err) {
			toast.error(String(err));
		}
	};

	// Real-time space thread updates via Socket.IO
	const spaceEventHandler = (event: any) => {
		if (!space || event.space_id !== space.id) return;

		const type = event?.data?.type;
		const data = event?.data?.data;

		if (type === 'thread:created') {
			// Avoid duplicates (e.g. if the current user created the thread)
			if (!threads.find((t) => t.id === data.id)) {
				threads = [
					{
						id: data.id,
						title: data.title || 'New Thread',
						updated_at: data.updated_at
					},
					...threads
				];
			}
		} else if (type === 'thread:deleted') {
			threads = threads.filter((t) => t.id !== data.id);
		} else if (type === 'thread:updated') {
			threads = threads.map((t) =>
				t.id === data.id
					? { ...t, title: data.title ?? t.title, updated_at: data.updated_at ?? t.updated_at }
					: t
			);
		}
	};

	onMount(() => {
		$socket?.on('events:space', spaceEventHandler);
	});

	onDestroy(() => {
		$socket?.off('events:space', spaceEventHandler);
	});
</script>

<svelte:head>
	<title>{space?.name ?? 'Space'} | {$WEBUI_NAME}</title>
</svelte:head>

{#if loading}
	<div
		class="h-screen max-h-[100dvh] w-full flex items-center justify-center {$sidebarPinned
			? 'md:max-w-[calc(100%-var(--sidebar-width))]'
			: ''}"
	>
		<div class="flex flex-col items-center gap-3">
			<Spinner className="size-6" />
			<span class="text-sm text-gray-400 dark:text-gray-500">{$i18n.t('Loading space...')}</span>
		</div>
	</div>
{:else if error || !space}
	<div
		class="h-screen max-h-[100dvh] w-full flex flex-col items-center justify-center gap-4 {$sidebarPinned
			? 'md:max-w-[calc(100%-var(--sidebar-width))]'
			: ''}"
	>
		<div class="text-center space-y-3">
			<div class="text-6xl opacity-20">404</div>
			<div class="text-lg font-medium text-gray-700 dark:text-gray-300">
				{$i18n.t('Space not found')}
			</div>
			<p class="text-sm text-gray-500 dark:text-gray-400 max-w-sm">
				{error ?? $i18n.t("The space you're looking for doesn't exist or you don't have access.")}
			</p>
		</div>
		<button
			class="mt-2 px-4 py-2 text-sm font-medium bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-xl transition"
			on:click={() => goto('/')}
		>
			<div class="flex items-center gap-1.5">
				<ChevronLeft className="size-4" />
				{$i18n.t('Back to Home')}
			</div>
		</button>
	</div>
{:else}
	<div
		class="h-screen max-h-[100dvh] w-full flex flex-col {$sidebarPinned
			? 'md:max-w-[calc(100%-var(--sidebar-width))]'
			: ''}"
	>
		<!-- Sticky Header -->
		<div
			class="sticky top-0 z-20 backdrop-blur-xl bg-white/80 dark:bg-gray-900/80 border-b border-gray-100 dark:border-gray-800/50"
		>
			<div class="max-w-6xl mx-auto px-4 sm:px-6 py-2.5 flex items-center justify-between">
				<div class="flex items-center gap-1.5 min-w-0">
					<Tooltip content={$i18n.t('Back')}>
						<button
							class="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition flex-shrink-0"
							on:click={() => goto('/')}
						>
							<ChevronLeft className="size-5" />
						</button>
					</Tooltip>

					<span class="text-sm text-gray-400 dark:text-gray-500 hidden sm:inline">/</span>

					<div class="flex items-center gap-1.5 min-w-0">
						{#if space.emoji}
							<span class="text-base flex-shrink-0">{space.emoji}</span>
						{/if}
						<h1 class="text-sm font-semibold text-gray-900 dark:text-gray-100 truncate">
							{space.name}
						</h1>
					</div>
				</div>

				<div class="flex items-center gap-1 flex-shrink-0">
					<Tooltip
						content={isSubscribed ? $i18n.t('Unsubscribe') : $i18n.t('Subscribe for notifications')}
					>
						<button
							class="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition {isSubscribed
								? 'text-accent-500'
								: 'text-gray-400 hover:text-accent-500'}"
							on:click={async () => {
								if (!space) return;
								try {
									if (isSubscribed) {
										await unsubscribeFromSpace(localStorage.token, space.id);
										isSubscribed = false;
									} else {
										await subscribeToSpace(localStorage.token, space.id);
										isSubscribed = true;
										toast.success(
											$i18n.t('You will be notified when threads are published in this Space')
										);
									}
								} catch (err) {
									toast.error(String(err));
								}
							}}
						>
							<svg class="size-4" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									d="M14.857 17.082a23.848 23.848 0 0 0 5.454-1.31A8.967 8.967 0 0 1 18 9.75V9A6 6 0 0 0 6 9v.75a8.967 8.967 0 0 1-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 0 1-5.714 0m5.714 0a3 3 0 1 1-5.714 0"
									fill={isSubscribed ? 'currentColor' : 'none'}
									stroke="currentColor"
									stroke-width="1.5"
								/>
							</svg>
						</button>
					</Tooltip>

					<Tooltip content={isBookmarked ? $i18n.t('Remove bookmark') : $i18n.t('Bookmark')}>
						<button
							class="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition {isBookmarked
								? 'text-amber-500'
								: 'text-gray-400 hover:text-amber-500'}"
							on:click={async () => {
								if (!space) return;
								try {
									if (isBookmarked) {
										await removeBookmark(localStorage.token, space.id);
										isBookmarked = false;
										toast.success($i18n.t('Bookmark removed'));
									} else {
										await addBookmark(localStorage.token, space.id);
										isBookmarked = true;
										toast.success($i18n.t('Bookmarked'));
									}
								} catch (err) {
									toast.error(String(err));
								}
							}}
						>
							<svg class="size-4" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									d="M17.593 3.322c1.1.128 1.907 1.077 1.907 2.185V21L12 17.25 4.5 21V5.507c0-1.108.806-2.057 1.907-2.185a48.507 48.507 0 0 1 11.186 0Z"
									fill={isBookmarked ? 'currentColor' : 'none'}
									stroke="currentColor"
									stroke-width="1.5"
								/>
							</svg>
						</button>
					</Tooltip>

					{#if space.write_access}
						<Tooltip content={$i18n.t('Share')}>
							<button
								class="px-3 py-1.5 rounded-lg bg-black dark:bg-white text-white dark:text-black hover:bg-gray-800 dark:hover:bg-gray-100 transition text-xs font-medium flex items-center gap-1.5"
								on:click={() => {
									showShareModal = true;
								}}
							>
								<svg
									class="size-3.5"
									viewBox="0 0 24 24"
									fill="none"
									stroke="currentColor"
									stroke-width="2"
								>
									<path
										stroke-linecap="round"
										stroke-linejoin="round"
										d="M7.217 10.907a2.25 2.25 0 1 0 0 2.186m0-2.186c.18.324.283.696.283 1.093s-.103.77-.283 1.093m0-2.186 9.566-5.314m-9.566 7.5 9.566 5.314m0 0a2.25 2.25 0 1 0 3.935 2.186 2.25 2.25 0 0 0-3.935-2.186Zm0-12.814a2.25 2.25 0 1 0 3.933-2.185 2.25 2.25 0 0 0-3.933 2.185Z"
									/>
								</svg>
								{$i18n.t('Share')}
							</button>
						</Tooltip>

						<Tooltip content={$i18n.t('Edit Space')}>
							<button
								class="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition"
								on:click={() => {
									showSettingsModal = true;
								}}
							>
								<PencilSquare className="size-4" />
							</button>
						</Tooltip>
					{/if}

					<Tooltip content={$i18n.t('More')}>
						<button
							class="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition"
							on:click={() => {
								showSettingsModal = true;
							}}
						>
							<EllipsisHorizontal className="size-4" />
						</button>
					</Tooltip>
				</div>
			</div>
		</div>

		{#if hasPendingInvitation}
			<div class="bg-blue-50 dark:bg-blue-900/20 border-b border-blue-100 dark:border-blue-800/40">
				<div class="max-w-6xl mx-auto px-4 sm:px-6 py-3 flex items-center justify-between gap-4">
					<div class="flex items-center gap-2 min-w-0">
						<svg
							class="size-5 text-blue-500 flex-shrink-0"
							viewBox="0 0 24 24"
							fill="none"
							stroke="currentColor"
							stroke-width="1.5"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								d="M21.75 6.75v10.5a2.25 2.25 0 0 1-2.25 2.25h-15a2.25 2.25 0 0 1-2.25-2.25V6.75m19.5 0A2.25 2.25 0 0 0 19.5 4.5h-15a2.25 2.25 0 0 0-2.25 2.25m19.5 0v.243a2.25 2.25 0 0 1-1.07 1.916l-7.5 4.615a2.25 2.25 0 0 1-2.36 0L3.32 8.91a2.25 2.25 0 0 1-1.07-1.916V6.75"
							/>
						</svg>
						<span class="text-sm font-medium text-blue-800 dark:text-blue-200 truncate">
							{$i18n.t("You've been invited to contribute to this space")}
						</span>
					</div>
					<div class="flex items-center gap-2 flex-shrink-0">
						<button
							class="px-3 py-1.5 text-xs font-medium bg-blue-600 hover:bg-blue-700 text-white rounded-full transition"
							disabled={invitationResponding}
							on:click={async () => {
								if (!space) return;
								invitationResponding = true;
								try {
									await respondToInvitation(localStorage.token, space.id, true);
									toast.success($i18n.t('Invitation accepted'));
									await loadSpace();
								} catch (err) {
									toast.error(String(err));
								}
								invitationResponding = false;
							}}
						>
							{$i18n.t('Accept')}
						</button>
						<button
							class="px-3 py-1.5 text-xs font-medium text-blue-700 dark:text-blue-300 hover:bg-blue-100 dark:hover:bg-blue-800/40 rounded-full transition"
							disabled={invitationResponding}
							on:click={async () => {
								if (!space) return;
								invitationResponding = true;
								try {
									await respondToInvitation(localStorage.token, space.id, false);
									toast.success($i18n.t('Invitation declined'));
									goto('/');
								} catch (err) {
									toast.error(String(err));
								}
								invitationResponding = false;
							}}
						>
							{$i18n.t('Decline')}
						</button>
					</div>
				</div>
			</div>
		{/if}

		<!-- Main Content Area -->
		<div class="flex-1 overflow-y-auto">
			<div class="max-w-6xl mx-auto px-4 sm:px-6 py-6">
				<div class="flex flex-col md:flex-row gap-6 md:gap-8">
					<!-- Left Column: Main Content -->
					<div class="flex-1 min-w-0">
						<!-- Hero: Emoji + Title + Description -->
						<div class="mb-6">
							{#if space.emoji}
								<div
									class="w-14 h-14 rounded-2xl bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-800 dark:to-gray-800/60 flex items-center justify-center text-3xl mb-4 ring-1 ring-gray-200/60 dark:ring-gray-700/40 shadow-sm"
								>
									{space.emoji}
								</div>
							{/if}

							<!-- Editable Title -->
							{#if editingTitle}
								<input
									bind:this={titleInputEl}
									bind:value={editTitle}
									on:blur={saveTitle}
									on:keydown={handleTitleKeydown}
									class="text-2xl font-bold text-gray-900 dark:text-gray-50 bg-transparent border-b-2 border-accent-500 outline-none w-full mb-1 pb-0.5"
									maxlength="128"
								/>
							{:else}
								<div class="flex items-center gap-2 mb-1">
									<h2
										class="text-2xl font-bold text-gray-900 dark:text-gray-50 {space.write_access
											? 'cursor-pointer hover:text-gray-700 dark:hover:text-gray-200 transition-colors'
											: ''}"
										on:click={startEditTitle}
										on:keydown={(e) => e.key === 'Enter' && startEditTitle()}
										role={space.write_access ? 'button' : undefined}
										tabindex={space.write_access ? 0 : undefined}
									>
										{space.name}
									</h2>
									{#if space.is_template}
										<span
											class="px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider rounded-full bg-violet-100 dark:bg-violet-900/30 text-violet-700 dark:text-violet-300"
										>
											{$i18n.t('Template')}
										</span>
									{/if}
								</div>
							{/if}

							<!-- Editable Description -->
							{#if editingDescription}
								<textarea
									bind:this={descInputEl}
									bind:value={editDescription}
									on:blur={saveDescription}
									on:keydown={handleDescKeydown}
									class="text-base text-gray-500 dark:text-gray-400 bg-transparent border-b-2 border-accent-500 outline-none w-full leading-relaxed resize-none"
									rows="2"
									placeholder={$i18n.t('Add a description...')}
								/>
							{:else if space.description}
								<p
									class="text-base text-gray-500 dark:text-gray-400 leading-relaxed {space.write_access
										? 'cursor-pointer hover:text-gray-600 dark:hover:text-gray-300 transition-colors'
										: ''}"
									on:click={startEditDescription}
									on:keydown={(e) => e.key === 'Enter' && startEditDescription()}
									role={space.write_access ? 'button' : undefined}
									tabindex={space.write_access ? 0 : undefined}
								>
									{space.description}
								</p>
							{:else if space.write_access}
								<p
									class="text-base text-gray-400 dark:text-gray-600 italic cursor-pointer hover:text-gray-500 dark:hover:text-gray-500 transition-colors"
									on:click={startEditDescription}
									on:keydown={(e) => e.key === 'Enter' && startEditDescription()}
									role="button"
									tabindex={0}
								>
									{$i18n.t('Add a description...')}
								</p>
							{/if}
						</div>

						{#if space.is_template}
							<div class="mb-6">
								<button
									class="px-4 py-2 text-sm font-medium bg-violet-600 hover:bg-violet-700 text-white rounded-xl transition flex items-center gap-2"
									on:click={async () => {
										if (!space) return;
										try {
											const cloned = await cloneTemplate(localStorage.token, space.id, {
												name: space.name + ' (copy)',
												description: space.description,
												emoji: space.emoji
											});
											toast.success($i18n.t('Space created from template'));
											goto('/spaces/' + cloned.slug);
										} catch (err) {
											toast.error(String(err));
										}
									}}
								>
									<svg
										class="size-4"
										viewBox="0 0 24 24"
										fill="none"
										stroke="currentColor"
										stroke-width="1.5"
									>
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											d="M15.75 17.25v3.375c0 .621-.504 1.125-1.125 1.125h-9.5a1.125 1.125 0 0 1-1.125-1.125V7.875c0-.621.504-1.125 1.125-1.125H6.75a9.06 9.06 0 0 1 1.5.124m7.5 10.376h3.375c.621 0 1.125-.504 1.125-1.125V11.25c0-4.46-3.243-8.161-7.5-8.876a9.06 9.06 0 0 0-1.5-.124H9.375c-.621 0-1.125.504-1.125 1.125v3.5m7.5 10.375H9.375a1.125 1.125 0 0 1-1.125-1.125v-9.25m12 6.625v-1.875a3.375 3.375 0 0 0-3.375-3.375h-1.5a1.125 1.125 0 0 1-1.125-1.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H9.75"
										/>
									</svg>
									{$i18n.t('Use this template')}
								</button>
							</div>
						{/if}

						<!-- Chat Input Area -->
						<div class="mb-8">
							<MessageInput
								history={chatHistory}
								{selectedModels}
								bind:files={chatFiles}
								bind:prompt={chatInput}
								bind:autoScroll
								bind:selectedToolIds
								bind:selectedFilterIds
								bind:imageGenerationEnabled
								bind:codeInterpreterEnabled
								bind:webSearchEnabled
								toolServers={$toolServers}
								generating={false}
								stopResponse={() => {}}
								createMessagePair={() => {}}
								placeholder={$i18n.t('Ask anything in {{name}}...', { name: space.name })}
								on:submit={async (e) => {
									const msg = e.detail?.trim() || chatInput.trim();
									if (!msg || !space) return;

									currentSpaceId.set(space.id);

									const params = new URLSearchParams();
									params.set('q', msg);
									params.set('submit', 'true');
									goto(`/?${params.toString()}`);
								}}
							/>
						</div>

						<!-- Threads Section -->
						<div class="mt-8 bg-white/60 dark:bg-gray-900/60 backdrop-blur-md rounded-2xl ring-1 ring-inset ring-white/20 dark:ring-white/10 p-4">
							<div class="flex items-center gap-2 mb-4">
								<ChatBubbleOval className="size-4 text-accent-500 dark:text-accent-400" />
								<h3
									class="text-xs font-semibold uppercase tracking-wider text-accent-500 dark:text-accent-400"
								>
									{$i18n.t('My threads')}
								</h3>
							</div>

							{#if threads.length === 0 && !threadsLoading}
								<div
									class="rounded-xl border border-dashed border-gray-200 dark:border-gray-800 p-8 text-center"
								>
									<div class="text-3xl mb-3 opacity-40">
										<ChatBubbleOval className="size-8 mx-auto text-gray-300 dark:text-gray-600" />
									</div>
									<p
										class="text-sm text-gray-500 dark:text-gray-400 max-w-xs mx-auto leading-relaxed"
									>
										{$i18n.t(
											'Your conversations in this space will appear here. Ask anything above to get started.'
										)}
									</p>
								</div>
							{:else}
								<div class="space-y-0.5">
									{#each threads as thread (thread.id)}
										<button
											class="w-full text-left px-3.5 py-3 rounded-xl hover:bg-gray-50 dark:hover:bg-gray-800/50 transition group flex items-center justify-between gap-3"
											on:click={() => goto(`/c/${thread.id}`)}
										>
											<div class="min-w-0 flex-1">
												<div
													class="text-sm font-medium text-gray-800 dark:text-gray-200 truncate group-hover:text-gray-900 dark:group-hover:text-white transition"
												>
													{thread.title || $i18n.t('Untitled')}
												</div>
											</div>
											<div class="flex items-center gap-2 flex-shrink-0">
												{#if thread.unread}
													<div class="shrink-0 size-2 rounded-full bg-accent-500"></div>
												{/if}
												<span class="text-xs text-gray-400 dark:text-gray-500 whitespace-nowrap">
													{getRelativeTime(thread.updated_at)}
												</span>
												{#if space.write_access}
													<!-- svelte-ignore a11y-click-events-have-key-events -->
													<!-- svelte-ignore a11y-no-static-element-interactions -->
													<div class="relative">
														<button
															class="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-800 transition"
															on:click|stopPropagation={() => {
																threadAccessDropdown =
																	threadAccessDropdown === thread.id ? null : thread.id;
															}}
														>
															<svg
																class="size-3.5 text-gray-400"
																viewBox="0 0 24 24"
																fill="none"
																stroke="currentColor"
																stroke-width="1.5"
															>
																<path
																	stroke-linecap="round"
																	stroke-linejoin="round"
																	d="M12 21a9.004 9.004 0 0 0 8.716-6.747M12 21a9.004 9.004 0 0 1-8.716-6.747M12 21c2.485 0 4.5-4.03 4.5-9S14.485 3 12 3m0 18c-2.485 0-4.5-4.03-4.5-9S9.515 3 12 3m0 0a8.997 8.997 0 0 1 7.843 4.582M12 3a8.997 8.997 0 0 0-7.843 4.582m15.686 0A11.953 11.953 0 0 1 12 10.5c-2.998 0-5.74-1.1-7.843-2.918m15.686 0A8.959 8.959 0 0 1 21 12c0 .778-.099 1.533-.284 2.253m0 0A17.919 17.919 0 0 1 12 16.5c-3.162 0-6.133-.815-8.716-2.247m0 0A9.015 9.015 0 0 1 3 12c0-1.605.42-3.113 1.157-4.418"
																/>
															</svg>
														</button>
														{#if threadAccessDropdown === thread.id}
															<div
																class="fixed inset-0 z-30"
																on:click|stopPropagation={() => {
																	threadAccessDropdown = null;
																}}
															/>
															<div
																class="absolute right-0 top-full mt-1 z-40 w-36 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-850 shadow-lg py-1"
															>
																{#each [{ value: 'private', label: 'Private', icon: 'M16.5 10.5V6.75a4.5 4.5 0 1 0-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 0 0 2.25-2.25v-6.75a2.25 2.25 0 0 0-2.25-2.25H6.75a2.25 2.25 0 0 0-2.25 2.25v6.75a2.25 2.25 0 0 0 2.25 2.25Z' }, { value: 'space', label: 'Space', icon: 'M18 18.72a9.094 9.094 0 0 0 3.741-.479 3 3 0 0 0-4.682-2.72m.94 3.198.001.031c0 .225-.012.447-.037.666A11.944 11.944 0 0 1 12 21c-2.17 0-4.207-.576-5.963-1.584A6.062 6.062 0 0 1 6 18.719m12 0a5.971 5.971 0 0 0-.941-3.197m0 0A5.995 5.995 0 0 0 12 12.75a5.995 5.995 0 0 0-5.058 2.772m0 0a3 3 0 0 0-4.681 2.72 8.986 8.986 0 0 0 3.74.477m.94-3.197a5.971 5.971 0 0 0-.94 3.197M15 6.75a3 3 0 1 1-6 0 3 3 0 0 1 6 0Zm6 3a2.25 2.25 0 1 1-4.5 0 2.25 2.25 0 0 1 4.5 0Zm-13.5 0a2.25 2.25 0 1 1-4.5 0 2.25 2.25 0 0 1 4.5 0Z' }, { value: 'org', label: 'Organization', icon: 'M3.75 21h16.5M4.5 3h15M5.25 3v18m13.5-18v18M9 6.75h1.5m-1.5 3h1.5m-1.5 3h1.5m3-6H15m-1.5 3H15m-1.5 3H15M9 21v-3.375c0-.621.504-1.125 1.125-1.125h3.75c.621 0 1.125.504 1.125 1.125V21' }, { value: 'public', label: 'Public', icon: 'M12 21a9.004 9.004 0 0 0 8.716-6.747M12 21a9.004 9.004 0 0 1-8.716-6.747M12 21c2.485 0 4.5-4.03 4.5-9S14.485 3 12 3m0 18c-2.485 0-4.5-4.03-4.5-9S9.515 3 12 3m0 0a8.997 8.997 0 0 1 7.843 4.582M12 3a8.997 8.997 0 0 0-7.843 4.582m15.686 0A11.953 11.953 0 0 1 12 10.5c-2.998 0-5.74-1.1-7.843-2.918m15.686 0A8.959 8.959 0 0 1 21 12c0 .778-.099 1.533-.284 2.253m0 0A17.919 17.919 0 0 1 12 16.5c-3.162 0-6.133-.815-8.716-2.247m0 0A9.015 9.015 0 0 1 3 12c0-1.605.42-3.113 1.157-4.418' }] as opt}
																	<button
																		class="w-full text-left px-3 py-1.5 text-xs text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition flex items-center gap-2"
																		on:click|stopPropagation={async () => {
																			if (!space) return;
																			try {
																				await updateThreadAccess(
																					localStorage.token,
																					space.id,
																					thread.id,
																					opt.value
																				);
																				toast.success($i18n.t('Thread access updated'));
																			} catch (err) {
																				toast.error(String(err));
																			}
																			threadAccessDropdown = null;
																		}}
																	>
																		<svg
																			class="size-3.5 text-gray-400 flex-shrink-0"
																			viewBox="0 0 24 24"
																			fill="none"
																			stroke="currentColor"
																			stroke-width="1.5"
																		>
																			<path
																				stroke-linecap="round"
																				stroke-linejoin="round"
																				d={opt.icon}
																			/>
																		</svg>
																		{$i18n.t(opt.label)}
																	</button>
																{/each}
															</div>
														{/if}
													</div>
												{/if}
												<ChevronRight
													className="size-3.5 text-gray-300 dark:text-gray-600 opacity-0 group-hover:opacity-100 transition"
												/>
											</div>
										</button>
									{/each}
								</div>

								{#if hasMoreThreads}
									<div class="mt-3 flex justify-center">
										<button
											class="px-4 py-2 text-xs font-medium text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition flex items-center gap-1.5"
											on:click={loadThreads}
											disabled={threadsLoading}
										>
											{#if threadsLoading}
												<Spinner className="size-3" />
											{/if}
											{$i18n.t('Load more')}
										</button>
									</div>
								{/if}
							{/if}
						</div>
					</div>

					<!-- Right Sidebar -->
					<div class="w-full md:w-60 flex-shrink-0">
						<div class="md:sticky md:top-24 space-y-6 bg-white/60 dark:bg-gray-900/60 backdrop-blur-md rounded-2xl ring-1 ring-inset ring-white/20 dark:ring-white/10 p-4">
							<!-- Knowledge Bases -->
							<div>
								<div class="flex items-center gap-2 mb-3">
									<BookOpen className="size-3.5 text-accent-500 dark:text-accent-400" />
									<h3
										class="text-xs font-semibold uppercase tracking-wider text-accent-500 dark:text-accent-400"
									>
										{$i18n.t('Knowledge Bases')}
									</h3>
								</div>

								{#if knowledgeBases.length === 0}
									<p class="text-xs text-gray-400 dark:text-gray-600 italic pl-5">
										{$i18n.t('None attached')}
									</p>
								{:else}
									<div class="space-y-0.5">
										{#each knowledgeBases as kb}
											<button
												class="w-full text-left px-2.5 py-2 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800/50 transition group flex items-center gap-2.5"
												on:click={() => {
													if (kb?.id) {
														goto(`/workspace/knowledge/${kb.id}`);
													}
												}}
											>
												<div
													class="w-7 h-7 rounded-md bg-amber-50 dark:bg-amber-900/20 flex items-center justify-center flex-shrink-0"
												>
													<BookOpen className="size-3.5 text-amber-600 dark:text-amber-400" />
												</div>
												<span
													class="text-sm text-gray-700 dark:text-gray-300 truncate group-hover:text-gray-900 dark:group-hover:text-white transition"
												>
													{kb?.name ?? $i18n.t('Untitled')}
												</span>
											</button>
										{/each}
									</div>
								{/if}
							</div>

							<!-- Files -->
							<div>
								<div class="flex items-center justify-between mb-3">
									<div class="flex items-center gap-2">
										<svg
											class="size-3.5 text-accent-500 dark:text-accent-400"
											viewBox="0 0 24 24"
											fill="none"
											stroke="currentColor"
											stroke-width="1.5"
										>
											<path
												stroke-linecap="round"
												stroke-linejoin="round"
												d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z"
											/>
										</svg>
										<h3
											class="text-xs font-semibold uppercase tracking-wider text-accent-500 dark:text-accent-400"
										>
											{$i18n.t('Files')}
										</h3>
									</div>
									<div class="flex items-center gap-1">
										{#if files.some((f) => f.meta?.source === 'sharepoint') && space.write_access}
											<Tooltip content={$i18n.t('Sync SharePoint files')}>
												<button
													class="p-0.5 rounded hover:bg-gray-100 dark:hover:bg-gray-800 transition"
													on:click={handleSyncSharePoint}
													disabled={syncingSharePoint}
												>
													{#if syncingSharePoint}
														<Spinner className="size-3.5" />
													{:else}
														<svg
															class="size-3.5 text-sky-500 hover:text-sky-600 dark:text-sky-400 dark:hover:text-sky-300"
															viewBox="0 0 24 24"
															fill="none"
															stroke="currentColor"
															stroke-width="2"
														>
															<path
																stroke-linecap="round"
																stroke-linejoin="round"
																d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0 3.181 3.183a8.25 8.25 0 0 0 13.803-3.7M4.031 9.865a8.25 8.25 0 0 1 13.803-3.7l3.181 3.182m0-4.991v4.99"
															/>
														</svg>
													{/if}
												</button>
											</Tooltip>
										{/if}
										{#if space.write_access}
											<div class="relative">
												<button
													class="p-0.5 rounded hover:bg-gray-100 dark:hover:bg-gray-800 transition"
													on:click={() => {
														showFileDropdown = !showFileDropdown;
													}}
													disabled={uploading}
												>
													{#if uploading}
														<Spinner className="size-3.5" />
													{:else}
														<svg
															class="size-3.5 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
															viewBox="0 0 24 24"
															fill="none"
															stroke="currentColor"
															stroke-width="2"
														>
															<path
																stroke-linecap="round"
																stroke-linejoin="round"
																d="M12 4.5v15m7.5-7.5h-15"
															/>
														</svg>
													{/if}
												</button>
												{#if showFileDropdown}
													<!-- svelte-ignore a11y-click-events-have-key-events -->
													<!-- svelte-ignore a11y-no-static-element-interactions -->
													<div
														class="fixed inset-0 z-30"
														on:click={() => {
															showFileDropdown = false;
														}}
													/>
													<div
														class="absolute right-0 top-full mt-1 z-40 w-44 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-850 shadow-lg py-1"
													>
														<button
															class="w-full text-left px-3 py-2 text-xs text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition flex items-center gap-2"
															on:click={() => {
																showFileDropdown = false;
																fileInputEl?.click();
															}}
														>
															<svg
																class="size-3.5 text-gray-400"
																viewBox="0 0 24 24"
																fill="none"
																stroke="currentColor"
																stroke-width="1.5"
															>
																<path
																	stroke-linecap="round"
																	stroke-linejoin="round"
																	d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5m-13.5-9L12 3m0 0 4.5 4.5M12 3v13.5"
																/>
															</svg>
															{$i18n.t('Upload files')}
														</button>
														<button
															class="w-full text-left px-3 py-2 text-xs text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition flex items-center gap-2"
															on:click={() => {
																showFileDropdown = false;
																showSharePointPicker = true;
															}}
														>
															<svg
																class="size-3.5 text-blue-500"
																viewBox="0 0 24 24"
																fill="currentColor"
															>
																<path
																	d="M11.5 3C7.36 3 4 6.36 4 10.5c0 .71.1 1.39.28 2.04A6.002 6.002 0 0 0 6 24h13a5 5 0 0 0 .95-9.91A7.5 7.5 0 0 0 11.5 3Z"
																	opacity="0.2"
																/>
																<path
																	d="M17.5 8a5.5 5.5 0 0 1 5.5 5.5 5.5 5.5 0 0 1-5.5 5.5H7a4 4 0 0 1-4-4 4 4 0 0 1 2.5-3.71A5.5 5.5 0 0 1 11 6a5.5 5.5 0 0 1 5.21 3.73A5.5 5.5 0 0 1 17.5 8Z"
																	fill="none"
																	stroke="currentColor"
																	stroke-width="1.5"
																	stroke-linecap="round"
																	stroke-linejoin="round"
																/>
															</svg>
															{$i18n.t('SharePoint')}
														</button>
													</div>
												{/if}
											</div>
											<input
												bind:this={fileInputEl}
												type="file"
												multiple
												class="hidden"
												on:change={handleFileUpload}
											/>
										{/if}
									</div>
								</div>

								{#if files.length === 0}
									<p class="text-xs text-gray-400 dark:text-gray-600 italic pl-5">
										{$i18n.t('None attached')}
									</p>
								{:else}
									<div class="space-y-1">
										<!-- Individual files (not from SharePoint folders) -->
										{#each individualFiles as file (file.id)}
											<div
												class="w-full text-left px-2.5 py-2 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800/50 transition group flex items-center gap-2.5"
											>
												<div
													class="w-7 h-7 rounded-md bg-blue-50 dark:bg-blue-900/20 flex items-center justify-center flex-shrink-0"
												>
													<svg
														class="size-3.5 text-blue-600 dark:text-blue-400"
														viewBox="0 0 24 24"
														fill="none"
														stroke="currentColor"
														stroke-width="1.5"
													>
														<path
															stroke-linecap="round"
															stroke-linejoin="round"
															d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z"
														/>
													</svg>
												</div>
												<span
													class="text-sm text-gray-700 dark:text-gray-300 truncate flex-1 group-hover:text-gray-900 dark:group-hover:text-white transition"
												>
													{file.filename ?? file.meta?.name ?? $i18n.t('Untitled')}
												</span>
												{#if space.write_access}
													<button
														class="opacity-0 group-hover:opacity-100 p-0.5 rounded hover:bg-gray-200 dark:hover:bg-gray-700 transition"
														on:click|stopPropagation={() => handleRemoveFile(file.id)}
													>
														<svg
															class="size-3 text-gray-400"
															viewBox="0 0 24 24"
															fill="none"
															stroke="currentColor"
															stroke-width="2"
														>
															<path
																stroke-linecap="round"
																stroke-linejoin="round"
																d="M6 18 18 6M6 6l12 12"
															/>
														</svg>
													</button>
												{/if}
											</div>
										{/each}

										<!-- SharePoint files grouped by Site, then Folder -->
										{#each siteGroups as site (site.siteName)}
											<Folder
												id="sp-site-{site.siteName}"
												name="{site.siteName} ({site.totalFiles})"
												open={false}
												dragAndDrop={false}
												className="ml-0"
												buttonClassName="text-sky-600 dark:text-sky-400 hover:text-sky-700 dark:hover:text-sky-300"
											>
												<div class="space-y-0.5 pl-2">
													{#each site.folders as folder (folder.folderId)}
														<Folder
															id="sp-folder-{folder.folderId}"
															name="{folder.folderName} ({folder.files.length})"
															open={false}
															dragAndDrop={false}
															className="ml-0"
															buttonClassName="text-gray-600 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300"
														>
															<div class="space-y-0.5 pl-2">
																{#each folder.files as file (file.id)}
																	<div
																		class="w-full text-left px-2.5 py-1.5 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800/50 transition group flex items-center gap-2.5"
																	>
																		<div
																			class="w-6 h-6 rounded-md bg-sky-50 dark:bg-sky-900/20 flex items-center justify-center flex-shrink-0"
																			title={$i18n.t('SharePoint')}
																		>
																			<svg
																				class="size-3 text-sky-600 dark:text-sky-400"
																				viewBox="0 0 24 24"
																				fill="none"
																				stroke="currentColor"
																				stroke-width="1.5"
																			>
																				<path
																					stroke-linecap="round"
																					stroke-linejoin="round"
																					d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z"
																				/>
																			</svg>
																		</div>
																		<span
																			class="text-sm text-gray-700 dark:text-gray-300 truncate flex-1 group-hover:text-gray-900 dark:group-hover:text-white transition"
																		>
																			{file.filename ?? file.meta?.name ?? $i18n.t('Untitled')}
																		</span>
																		{#if space.write_access}
																			<button
																				class="opacity-0 group-hover:opacity-100 p-0.5 rounded hover:bg-gray-200 dark:hover:bg-gray-700 transition"
																				on:click|stopPropagation={() => handleRemoveFile(file.id)}
																			>
																				<svg
																					class="size-3 text-gray-400"
																					viewBox="0 0 24 24"
																					fill="none"
																					stroke="currentColor"
																					stroke-width="2"
																				>
																					<path
																						stroke-linecap="round"
																						stroke-linejoin="round"
																						d="M6 18 18 6M6 6l12 12"
																					/>
																				</svg>
																			</button>
																		{/if}
																	</div>
																{/each}
															</div>
														</Folder>
													{/each}
												</div>
											</Folder>
										{/each}
									</div>
								{/if}
							</div>

							<!-- Links -->
							<div>
								<div class="flex items-center justify-between mb-3">
									<div class="flex items-center gap-2">
										<svg
											class="size-3.5 text-accent-500 dark:text-accent-400"
											viewBox="0 0 24 24"
											fill="none"
											stroke="currentColor"
											stroke-width="1.5"
										>
											<path
												stroke-linecap="round"
												stroke-linejoin="round"
												d="M13.19 8.688a4.5 4.5 0 0 1 1.242 7.244l-4.5 4.5a4.5 4.5 0 0 1-6.364-6.364l1.757-1.757m13.35-.622 1.757-1.757a4.5 4.5 0 0 0-6.364-6.364l-4.5 4.5a4.5 4.5 0 0 0 1.242 7.244"
											/>
										</svg>
										<h3
											class="text-xs font-semibold uppercase tracking-wider text-accent-500 dark:text-accent-400"
										>
											{$i18n.t('Links')}
										</h3>
									</div>
									{#if space.write_access}
										<button
											class="p-0.5 rounded hover:bg-gray-100 dark:hover:bg-gray-800 transition"
											on:click={() => {
												addingLink = !addingLink;
											}}
										>
											<svg
												class="size-3.5 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
												viewBox="0 0 24 24"
												fill="none"
												stroke="currentColor"
												stroke-width="2"
											>
												<path
													stroke-linecap="round"
													stroke-linejoin="round"
													d="M12 4.5v15m7.5-7.5h-15"
												/>
											</svg>
										</button>
									{/if}
								</div>

								{#if addingLink}
									<div class="mb-3 space-y-2 pl-0.5">
										<input
											type="url"
											bind:value={newLinkUrl}
											class="w-full text-xs bg-transparent border border-gray-200 dark:border-gray-700 rounded-lg px-2.5 py-1.5 outline-none focus:border-gray-300 dark:focus:border-gray-600 text-gray-700 dark:text-gray-300 placeholder:text-gray-400"
											placeholder={$i18n.t('URL')}
											on:keydown={(e) => {
												if (e.key === 'Enter') handleAddLink();
												if (e.key === 'Escape') addingLink = false;
											}}
										/>
										<input
											type="text"
											bind:value={newLinkTitle}
											class="w-full text-xs bg-transparent border border-gray-200 dark:border-gray-700 rounded-lg px-2.5 py-1.5 outline-none focus:border-gray-300 dark:focus:border-gray-600 text-gray-700 dark:text-gray-300 placeholder:text-gray-400"
											placeholder={$i18n.t('Title (optional)')}
											on:keydown={(e) => {
												if (e.key === 'Enter') handleAddLink();
												if (e.key === 'Escape') addingLink = false;
											}}
										/>
										<div class="flex gap-1.5">
											<button
												class="px-2.5 py-1 text-xs font-medium bg-black dark:bg-white text-white dark:text-black rounded-lg hover:bg-gray-800 dark:hover:bg-gray-100 transition"
												on:click={handleAddLink}
												disabled={!newLinkUrl.trim()}
											>
												{$i18n.t('Add')}
											</button>
											<button
												class="px-2.5 py-1 text-xs text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition"
												on:click={() => {
													addingLink = false;
													newLinkUrl = '';
													newLinkTitle = '';
												}}
											>
												{$i18n.t('Cancel')}
											</button>
										</div>
									</div>
								{/if}

								{#if links.length === 0 && !addingLink}
									<p class="text-xs text-gray-400 dark:text-gray-600 italic pl-5">
										{$i18n.t('None attached')}
									</p>
								{:else}
									<div class="space-y-0.5">
										{#each links as link (link.id)}
											<div
												class="w-full text-left px-2.5 py-2 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800/50 transition group flex items-center gap-2.5"
											>
												<div
													class="w-7 h-7 rounded-md bg-gray-50 dark:bg-gray-800/40 flex items-center justify-center flex-shrink-0"
												>
													<svg
														class="size-3.5 text-gray-400 dark:text-gray-500"
														viewBox="0 0 24 24"
														fill="none"
														stroke="currentColor"
														stroke-width="1.5"
													>
														<path
															stroke-linecap="round"
															stroke-linejoin="round"
															d="M13.19 8.688a4.5 4.5 0 0 1 1.242 7.244l-4.5 4.5a4.5 4.5 0 0 1-6.364-6.364l1.757-1.757m13.35-.622 1.757-1.757a4.5 4.5 0 0 0-6.364-6.364l-4.5 4.5a4.5 4.5 0 0 0 1.242 7.244"
														/>
													</svg>
												</div>
												<a
													href={link.url}
													target="_blank"
													rel="noopener noreferrer"
													class="text-sm text-gray-700 dark:text-gray-300 truncate flex-1 group-hover:text-accent-500 dark:group-hover:text-accent-400 transition"
													title={link.url}
												>
													{link.title || link.url}
												</a>
												{#if space.write_access}
													<button
														class="opacity-0 group-hover:opacity-100 p-0.5 rounded hover:bg-gray-200 dark:hover:bg-gray-700 transition"
														on:click|stopPropagation={() => handleRemoveLink(link.id)}
													>
														<svg
															class="size-3 text-gray-400"
															viewBox="0 0 24 24"
															fill="none"
															stroke="currentColor"
															stroke-width="2"
														>
															<path
																stroke-linecap="round"
																stroke-linejoin="round"
																d="M6 18 18 6M6 6l12 12"
															/>
														</svg>
													</button>
												{/if}
											</div>
										{/each}
									</div>
								{/if}
							</div>

							<!-- Instructions -->
							{#if space.instructions}
								<div>
									<div class="flex items-center gap-2 mb-3">
										<svg
											class="size-3.5 text-accent-500 dark:text-accent-400"
											viewBox="0 0 24 24"
											fill="none"
											stroke="currentColor"
											stroke-width="1.5"
										>
											<path
												stroke-linecap="round"
												stroke-linejoin="round"
												d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z"
											/>
										</svg>
										<h3
											class="text-xs font-semibold uppercase tracking-wider text-accent-500 dark:text-accent-400"
										>
											{$i18n.t('Instructions')}
										</h3>
									</div>

									<div
										class="rounded-lg border border-gray-100 dark:border-gray-800/60 bg-gray-50/50 dark:bg-gray-800/20 p-3"
									>
										<p
											class="text-xs text-gray-600 dark:text-gray-400 leading-relaxed whitespace-pre-wrap"
										>
											{#if instructionsExpanded}
												{space.instructions}
											{:else}
												{space.instructions.length > 100
													? space.instructions.slice(0, 100) + '...'
													: space.instructions}
											{/if}
										</p>
										{#if space.instructions.length > 100}
											<button
												class="mt-2 text-xs font-medium text-accent-500 dark:text-accent-400 hover:text-accent-600 dark:hover:text-accent-300 transition"
												on:click={() => {
													instructionsExpanded = !instructionsExpanded;
												}}
											>
												{instructionsExpanded ? $i18n.t('Show less') : $i18n.t('View all')}
											</button>
										{/if}
									</div>
								</div>
							{/if}

							<!-- Settings Summary -->
							<div>
								<div class="flex items-center gap-2 mb-3">
									<Cog6 className="size-3.5 text-accent-500 dark:text-accent-400" />
									<h3
										class="text-xs font-semibold uppercase tracking-wider text-accent-500 dark:text-accent-400"
									>
										{$i18n.t('Settings')}
									</h3>
								</div>

								<div class="space-y-2.5 pl-0.5">
									{#if space.model_id}
										<div class="flex items-start gap-2">
											<svg
												class="size-3.5 text-gray-400 dark:text-gray-500 mt-0.5 flex-shrink-0"
												viewBox="0 0 24 24"
												fill="none"
												stroke="currentColor"
												stroke-width="1.5"
											>
												<path
													stroke-linecap="round"
													stroke-linejoin="round"
													d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09ZM18.259 8.715 18 9.75l-.259-1.035a3.375 3.375 0 0 0-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 0 0 2.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 0 0 2.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 0 0-2.456 2.456ZM16.894 20.567 16.5 21.75l-.394-1.183a2.25 2.25 0 0 0-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 0 0 1.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 0 0 1.423 1.423l1.183.394-1.183.394a2.25 2.25 0 0 0-1.423 1.423Z"
												/>
											</svg>
											<div class="min-w-0">
												<div class="text-xs text-gray-500 dark:text-gray-400">
													{$i18n.t('Model')}
												</div>
												<div
													class="text-xs font-medium text-gray-700 dark:text-gray-300 truncate mt-0.5"
												>
													{space.model_id}
												</div>
											</div>
										</div>
									{/if}

									<div class="flex items-center gap-2">
										<GlobeAlt
											className="size-3.5 {space.enable_web_by_default
												? 'text-accent-500 dark:text-accent-400'
												: 'text-gray-400 dark:text-gray-500'} flex-shrink-0"
										/>
										<div class="flex items-center gap-1.5">
											<span class="text-xs text-gray-500 dark:text-gray-400">
												{$i18n.t('Web Search')}
											</span>
											<span
												class="text-xs font-medium {space.enable_web_by_default
													? 'text-accent-500 dark:text-accent-400'
													: 'text-gray-400 dark:text-gray-500'}"
											>
												{space.enable_web_by_default ? $i18n.t('On') : $i18n.t('Off')}
											</span>
										</div>
									</div>

									{#if space.write_access}
										<button
											class="w-full mt-2 px-3 py-2 text-xs font-medium text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition flex items-center justify-center gap-1.5"
											on:click={() => {
												showSettingsModal = true;
											}}
										>
											<Cog6 className="size-3.5" />
											{$i18n.t('Edit Settings')}
										</button>
									{/if}
								</div>
							</div>

							{#if space.access_level === 'public'}
								<div>
									<div class="flex items-center gap-2 mb-3">
										<svg
											class="size-3.5 text-gray-400 dark:text-gray-500"
											viewBox="0 0 24 24"
											fill="none"
											stroke="currentColor"
											stroke-width="1.5"
										>
											<path
												stroke-linecap="round"
												stroke-linejoin="round"
												d="M7.217 10.907a2.25 2.25 0 1 0 0 2.186m0-2.186c.18.324.283.696.283 1.093s-.103.77-.283 1.093m0-2.186 9.566-5.314m-9.566 7.5 9.566 5.314m0 0a2.25 2.25 0 1 0 3.935 2.186 2.25 2.25 0 0 0-3.935-2.186Zm0-12.814a2.25 2.25 0 1 0 3.933-2.185 2.25 2.25 0 0 0-3.933 2.185Z"
											/>
										</svg>
										<h3
											class="text-xs font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500"
										>
											{$i18n.t('Share')}
										</h3>
									</div>
									<SocialShareLinks
										url={`${window.location.origin}/spaces/${space.slug}`}
										title={space.name}
										compact={true}
									/>
								</div>
							{/if}
						</div>
					</div>
				</div>
			</div>
		</div>
	</div>

	<SpaceSettingsModal
		bind:show={showSettingsModal}
		{space}
		edit={true}
		onUpdate={async () => {
			await loadSpace();
		}}
	/>

	<SpaceShareModal
		bind:show={showShareModal}
		{space}
		onUpdate={async () => {
			await loadSpace();
		}}
	/>

	<SharePointFilePicker
		bind:show={showSharePointPicker}
		token={localStorage.token}
		spaceId={space?.id ?? null}
		on:fileDownloaded={handleSharePointFileDownloaded}
		on:close={() => {
			showSharePointPicker = false;
		}}
	/>
{/if}
