<!-- Company custom: Team Workspaces V1 -->
<script lang="ts">
	import { getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	import { toast } from 'svelte-sonner';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';

	import {
		mobile,
		showSidebar,
		activeWorkspaceId,
		chatId,
		workspaceChatsRefreshKey,
		user,
		governanceCapabilities,
		selectedFolder
	} from '$lib/stores';
	import {
		createWorkspaceFolder,
		deleteWorkspaceFolderById,
		getWorkspaceChatListByFolderId,
		getWorkspaceChats,
		getWorkspaceFolderById,
		getWorkspaceFolders,
		updateWorkspaceFolderById,
		updateWorkspaceFolderIsExpandedById,
		updateWorkspaceFolderParentIdById
	} from '$lib/apis/workspaces';
	import { updateChatFolderIdById } from '$lib/apis/chats';
	import { canManageWorkspace, canWriteWorkspace } from '$lib/utils/governance';

	import Cog6 from '$lib/components/icons/Cog6.svelte';
	import Users from '$lib/components/icons/Users.svelte';
	import Folders from './Folders.svelte';
	import FolderModal from './Folders/FolderModal.svelte';

	const i18n: Writable<i18nType> = getContext('i18n');

	type FolderFormPayload = {
		name?: string;
		data?: Record<string, unknown>;
		meta?: Record<string, unknown>;
		parent_id?: string | null;
	};

	export let workspace: any;
	export let onManage: () => void = () => {};

	export let className = '';

	let open = false;
	let chats: any[] = [];
	let folders: Record<string, any> = {};
	let folderRegistry: Record<string, any> = {};
	let showCreateFolderModal = false;
	let lastRefreshKey = -1;
	let folderApis: Record<string, any>;
	$: canWrite = canWriteWorkspace(workspace, $user, $governanceCapabilities);
	$: canManage = canManageWorkspace(workspace, $user, $governanceCapabilities);

	const openWorkspace = async () => {
		open = !open;
		activeWorkspaceId.set(open ? workspace.id : null);
		selectedFolder.set(null);

		if (open) {
			lastRefreshKey = $workspaceChatsRefreshKey;
			await refreshWorkspace();
		}
	};

	$: if ($activeWorkspaceId === workspace.id && !open) {
		open = true;
	}

	$: if (open && $workspaceChatsRefreshKey !== lastRefreshKey) {
		lastRefreshKey = $workspaceChatsRefreshKey;
		refreshWorkspace();
	}

	const newWorkspaceChat = async () => {
		activeWorkspaceId.set(workspace.id);
		chatId.set('');
		if (!open) open = true;
		await goto(`/workspaces/${workspace.id}`);
		if ($mobile) showSidebar.set(false);
	};

	const buildFolderTree = (folderList: any[]) => {
		const nextFolders: Record<string, any> = {};
		for (const folder of folderList) {
			nextFolders[folder.id] = { ...(nextFolders[folder.id] || {}), ...folder };
		}
		for (const folder of folderList) {
			if (folder.parent_id) {
				if (!nextFolders[folder.parent_id]) {
					nextFolders[folder.parent_id] = {};
				}
				nextFolders[folder.parent_id].childrenIds = nextFolders[folder.parent_id].childrenIds
					? [...nextFolders[folder.parent_id].childrenIds, folder.id]
					: [folder.id];
			}
		}
		return nextFolders;
	};

	const refreshWorkspace = async () => {
		try {
			const [chatResult, folderResult] = await Promise.all([
				getWorkspaceChats(localStorage.token, workspace.id),
				getWorkspaceFolders(localStorage.token, workspace.id)
			]);
			chats = (chatResult ?? []).filter((chat: any) => !chat.folder_id);
			folders = buildFolderTree(folderResult ?? []);
		} catch (e) {
			toast.error(`${e}`);
		}
	};

	const createFolder = async ({ name, data, meta, parent_id }: FolderFormPayload) => {
		name = name?.trim();
		if (!name) {
			toast.error($i18n.t('Folder name cannot be empty.'));
			return;
		}

		await createWorkspaceFolder(localStorage.token, workspace.id, {
			name,
			data,
			meta,
			parent_id
		});
		await refreshWorkspace();
	};

	$: folderApis = {
		createNewFolder: (token: string, form: any) => createWorkspaceFolder(token, workspace.id, form),
		getFolderById: (token: string, folderId: string) =>
			getWorkspaceFolderById(token, workspace.id, folderId),
		updateFolderById: (token: string, folderId: string, form: any) =>
			updateWorkspaceFolderById(token, workspace.id, folderId, form),
		updateFolderParentIdById: (token: string, folderId: string, parentId?: string | null) =>
			updateWorkspaceFolderParentIdById(token, workspace.id, folderId, parentId ?? null),
		updateFolderIsExpandedById: (token: string, folderId: string, isExpanded: boolean) =>
			updateWorkspaceFolderIsExpandedById(token, workspace.id, folderId, isExpanded),
		deleteFolderById: (token: string, folderId: string, deleteContents: boolean) =>
			deleteWorkspaceFolderById(token, workspace.id, folderId, deleteContents),
		getChatListByFolderId: (token: string, folderId: string, page: number = 1) =>
			getWorkspaceChatListByFolderId(token, workspace.id, folderId, page),
		getChatsByFolderId: (token: string, folderId: string) =>
			getWorkspaceChatListByFolderId(token, workspace.id, folderId),
		updateChatFolderIdById
	};
</script>

<FolderModal
	bind:show={showCreateFolderModal}
	onSubmit={async (folder: FolderFormPayload) => {
		await createFolder(folder);
		showCreateFolderModal = false;
	}}
/>

<div class="w-full {className}">
	<!-- Workspace header row -->
	<div
		class="group flex items-center justify-between w-full rounded-xl px-2 py-1 cursor-pointer
		       hover:bg-gray-100 dark:hover:bg-gray-900
		       {$activeWorkspaceId === workspace.id ? 'bg-gray-100 dark:bg-gray-900' : ''}
		       dark:text-gray-400 text-gray-600 select-none"
		role="button"
		tabindex="0"
		on:click={openWorkspace}
		on:keydown={(e) => e.key === 'Enter' && openWorkspace()}
	>
		<div class="flex items-center gap-1.5 overflow-hidden">
			<!-- Workspace icon -->
			<div class="size-4 flex items-center justify-center ml-0.5 shrink-0">
				<Users className="size-3.5" strokeWidth="2" />
			</div>

			<span class="text-sm line-clamp-1 flex-1">{workspace.name}</span>
		</div>

		<div class="flex items-center gap-1 shrink-0">
			<!-- Manage button (hover only) -->
			{#if canManage}
				<button
					type="button"
					class="p-0.5 dark:hover:bg-gray-850 rounded-lg touch-auto invisible group-hover:visible"
					title={$i18n.t('Manage workspace')}
					on:click|stopPropagation={onManage}
				>
					<Cog6 className="size-3.5" />
				</button>
			{/if}

			<!-- Chevron -->
			<svg
				xmlns="http://www.w3.org/2000/svg"
				viewBox="0 0 20 20"
				fill="currentColor"
				class="size-3.5 transition-transform duration-150 {open ? 'rotate-90' : ''}"
			>
				<path
					fill-rule="evenodd"
					d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z"
					clip-rule="evenodd"
				/>
			</svg>
		</div>
	</div>

	<!-- Chat list (shown when workspace is open) -->
	{#if open}
		<div class="ml-2 mt-0.5 flex flex-col gap-0.5">
			{#if canWrite}
				<button
					type="button"
					class="group/chat flex items-center justify-start gap-1.5 w-full rounded-xl px-2 py-1 text-left text-sm
					       hover:bg-gray-100 dark:hover:bg-gray-900 dark:text-gray-400 text-gray-600
					       line-clamp-1 cursor-pointer select-none"
					on:click={newWorkspaceChat}
				>
					<span class="line-clamp-1">+ {$i18n.t('New Chat')}</span>
				</button>
			{/if}
			{#if canManage}
				<button
					type="button"
					class="group/chat flex items-center justify-start gap-1.5 w-full rounded-xl px-2 py-1 text-left text-sm
					       hover:bg-gray-100 dark:hover:bg-gray-900 dark:text-gray-400 text-gray-600
					       line-clamp-1 cursor-pointer select-none"
					on:click={() => (showCreateFolderModal = true)}
				>
					<span class="line-clamp-1">+ {$i18n.t('New Folder')}</span>
				</button>
			{/if}
			<Folders
				bind:folderRegistry
				{folders}
				{folderApis}
				workspaceId={workspace.id}
				folderReadOnly={!canManage}
				selectFolderPath={`/workspaces/${workspace.id}`}
				onDelete={refreshWorkspace}
				on:update={refreshWorkspace}
				on:change={refreshWorkspace}
			/>
			{#if chats.length === 0 && Object.keys(folders).length === 0}
				<div class="px-3 py-1 text-xs text-gray-400 dark:text-gray-600 italic">
					{$i18n.t('No chats yet')}
				</div>
			{:else}
				{#each chats as chat (chat.id)}
					<a
						href="/workspaces/{workspace.id}/c/{chat.id}"
						draggable="false"
						class="group/chat flex items-center gap-1.5 w-full rounded-xl px-2 py-1 text-sm
						       hover:bg-gray-100 dark:hover:bg-gray-900
						       {$page.url.pathname === `/workspaces/${workspace.id}/c/${chat.id}`
							? 'bg-gray-100 dark:bg-gray-900 font-medium dark:text-white text-black'
							: 'dark:text-gray-400 text-gray-600'}
						       line-clamp-1 cursor-pointer select-none"
						on:click={() => {
							activeWorkspaceId.set(workspace.id);
							if ($mobile) showSidebar.set(false);
						}}
					>
						<span class="line-clamp-1 flex-1">{chat.title}</span>
					</a>
				{/each}
			{/if}
		</div>
	{/if}
</div>
