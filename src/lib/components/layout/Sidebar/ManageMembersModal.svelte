<!-- Company custom: Team Workspaces V1 -->
<script lang="ts">
	import { getContext } from 'svelte';
	import { toast } from 'svelte-sonner';

	import {
		getWorkspaceMembers,
		addWorkspaceMember,
		updateWorkspaceMember,
		removeWorkspaceMember,
		deleteWorkspace
	} from '$lib/apis/workspaces';
	import { searchUsers } from '$lib/apis/users';
	import { workspaces } from '$lib/stores';

	import Modal from '$lib/components/common/Modal.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';

	const i18n = getContext('i18n');

	export let show = false;
	export let workspace: any = null;
	export let currentUserRole: 'manager' | 'member' | 'viewer' | null = null;
	export let onUpdate: () => void = () => {};
	export let onDeleted: () => void = () => {};

	const ROLES = ['manager', 'member', 'viewer'] as const;

	let members: any[] = [];
	let loadingMembers = false;

	let searchQuery = '';
	let searchResults: any[] = [];
	let searching = false;
	let addingUserId: string | null = null;
	let addRole: 'manager' | 'member' | 'viewer' = 'member';

	let showDeleteConfirm = false;

	// Reload members whenever modal opens
	$: if (show && workspace) {
		loadMembers();
	}

	const loadMembers = async () => {
		loadingMembers = true;
		try {
			members = await getWorkspaceMembers(localStorage.token, workspace.id);
		} catch (e) {
			toast.error(`${e}`);
		} finally {
			loadingMembers = false;
		}
	};

	let searchTimeout: ReturnType<typeof setTimeout>;
	const onSearchInput = () => {
		clearTimeout(searchTimeout);
		if (!searchQuery.trim()) {
			searchResults = [];
			return;
		}
		searchTimeout = setTimeout(async () => {
			searching = true;
			try {
				const res = await searchUsers(localStorage.token, searchQuery.trim());
				const memberIds = new Set(members.map((m) => m.user_id));
				searchResults = (res ?? []).filter((u: any) => !memberIds.has(u.id));
			} catch (e) {
				searchResults = [];
			} finally {
				searching = false;
			}
		}, 300);
	};

	const addMember = async (userId: string) => {
		addingUserId = userId;
		try {
			await addWorkspaceMember(localStorage.token, workspace.id, {
				user_id: userId,
				role: addRole
			});
			toast.success($i18n.t('Member added'));
			searchQuery = '';
			searchResults = [];
			await loadMembers();
		} catch (e) {
			toast.error(`${e}`);
		} finally {
			addingUserId = null;
		}
	};

	const updateRole = async (userId: string, role: string) => {
		try {
			await updateWorkspaceMember(localStorage.token, workspace.id, userId, {
				role: role as any
			});
			members = members.map((m) => (m.user_id === userId ? { ...m, role } : m));
		} catch (e) {
			toast.error(`${e}`);
		}
	};

	const removeMember = async (userId: string) => {
		try {
			await removeWorkspaceMember(localStorage.token, workspace.id, userId);
			members = members.filter((m) => m.user_id !== userId);
			toast.success($i18n.t('Member removed'));
		} catch (e) {
			toast.error(`${e}`);
		}
	};

	const confirmDelete = async () => {
		try {
			await deleteWorkspace(localStorage.token, workspace.id);
			workspaces.update((ws) => ws.filter((w: any) => w.id !== workspace.id));
			toast.success($i18n.t('Workspace deleted'));
			show = false;
			onDeleted();
		} catch (e) {
			toast.error(`${e}`);
		}
	};
</script>

<ConfirmDialog
	bind:show={showDeleteConfirm}
	title={$i18n.t('Delete Workspace')}
	message={$i18n.t('Are you sure? This will permanently delete the workspace and all its chats.')}
	onConfirm={confirmDelete}
/>

<Modal bind:show size="sm">
	<div class="px-5 py-4 flex flex-col gap-4">
		<!-- Header -->
		<div class="flex items-center justify-between">
			<h3 class="text-lg font-semibold dark:text-white line-clamp-1">
				{workspace?.name}
			</h3>
			<button
				type="button"
				class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
				on:click={() => (show = false)}
			>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 20 20"
					fill="currentColor"
					class="size-5"
				>
					<path
						d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z"
					/>
				</svg>
			</button>
		</div>

		<!-- Add member (managers only) -->
		{#if currentUserRole === 'manager'}
			<div class="flex flex-col gap-2">
				<label class="text-sm font-medium dark:text-gray-300">{$i18n.t('Add member')}</label>
				<div class="flex gap-2">
					<div class="relative flex-1">
						<input
							bind:value={searchQuery}
							on:input={onSearchInput}
							class="w-full rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 px-3 py-1.5 text-sm dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
							placeholder={$i18n.t('Search by name or email…')}
						/>
						{#if searching}
							<div class="absolute right-2 top-1/2 -translate-y-1/2">
								<Spinner className="size-3.5" />
							</div>
						{/if}
					</div>
					<select
						bind:value={addRole}
						class="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 px-2 py-1.5 text-sm dark:text-white focus:outline-none"
					>
						{#each ROLES as r}
							<option value={r}>{$i18n.t(r)}</option>
						{/each}
					</select>
				</div>

				{#if searchResults.length > 0}
					<div class="border border-gray-200 dark:border-gray-700 rounded-xl overflow-hidden">
						{#each searchResults as u}
							<button
								type="button"
								class="flex items-center justify-between w-full px-3 py-2 text-sm hover:bg-gray-50 dark:hover:bg-gray-800 dark:text-gray-200"
								disabled={addingUserId === u.id}
								on:click={() => addMember(u.id)}
							>
								<div class="flex items-center gap-2 overflow-hidden">
									<img
										src={u.profile_image_url ?? '/user.png'}
										alt={u.name}
										class="size-6 rounded-full shrink-0"
									/>
									<div class="overflow-hidden text-left">
										<div class="line-clamp-1 font-medium">{u.name}</div>
										<div class="line-clamp-1 text-xs text-gray-400">{u.email}</div>
									</div>
								</div>
								{#if addingUserId === u.id}
									<Spinner className="size-3.5 shrink-0" />
								{:else}
									<span class="text-xs text-blue-500 shrink-0">{$i18n.t('Add')}</span>
								{/if}
							</button>
						{/each}
					</div>
				{/if}
			</div>
		{/if}

		<!-- Members list -->
		<div>
			<label class="text-sm font-medium dark:text-gray-300 mb-2 block">
				{$i18n.t('Members')}
				{#if loadingMembers}
					<Spinner className="size-3.5 inline-block ml-1" />
				{/if}
			</label>

			{#if members.length === 0 && !loadingMembers}
				<p class="text-sm text-gray-400 italic">{$i18n.t('No members yet.')}</p>
			{:else}
				<div class="flex flex-col gap-1 max-h-60 overflow-y-auto">
					{#each members as member (member.user_id)}
						<div class="flex items-center justify-between gap-2 py-1">
							<div class="flex items-center gap-2 overflow-hidden">
								<img
									src={`/api/v1/users/${member.user_id}/profile/image`}
									alt={member.display_name ?? member.user_id}
									class="size-6 rounded-full shrink-0"
									on:error={(e) => {
										(e.target as HTMLImageElement).src = '/user.png';
									}}
								/>
								<div class="overflow-hidden">
									<div class="text-sm dark:text-gray-200 line-clamp-1 font-medium">
										{member.display_name ?? member.user_id}
									</div>
									{#if member.email}
										<div class="text-xs text-gray-400 line-clamp-1">{member.email}</div>
									{/if}
								</div>
							</div>

							<div class="flex items-center gap-1 shrink-0">
								{#if currentUserRole === 'manager'}
									<select
										value={member.role}
										class="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 px-1.5 py-0.5 text-xs dark:text-white focus:outline-none"
										on:change={(e) =>
											updateRole(member.user_id, (e.target as HTMLSelectElement).value)}
									>
										{#each ROLES as r}
											<option value={r}>{$i18n.t(r)}</option>
										{/each}
									</select>
									<button
										type="button"
										title={$i18n.t('Remove')}
										class="p-0.5 text-gray-400 hover:text-red-500 rounded"
										on:click={() => removeMember(member.user_id)}
									>
										<svg
											xmlns="http://www.w3.org/2000/svg"
											viewBox="0 0 20 20"
											fill="currentColor"
											class="size-3.5"
										>
											<path
												d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z"
											/>
										</svg>
									</button>
								{:else}
									<span class="text-xs text-gray-400 capitalize">{$i18n.t(member.role)}</span>
								{/if}
							</div>
						</div>
					{/each}
				</div>
			{/if}
		</div>

		<!-- Danger zone (managers only) -->
		{#if currentUserRole === 'manager'}
			<div class="border-t border-gray-100 dark:border-gray-800 pt-3">
				<button
					type="button"
					class="text-xs text-red-500 hover:text-red-600"
					on:click={() => (showDeleteConfirm = true)}
				>
					{$i18n.t('Delete workspace')}
				</button>
			</div>
		{/if}
	</div>
</Modal>
