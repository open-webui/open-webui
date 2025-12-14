<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { onMount, getContext, createEventDispatcher } from 'svelte';
	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	import { getGroupManagers, updateGroupManagers } from '$lib/apis/groups';
	import { getUsers } from '$lib/apis/users';

	import Spinner from '$lib/components/common/Spinner.svelte';
	import Search from '$lib/components/icons/Search.svelte';
	import UserCircleSolid from '$lib/components/icons/UserCircleSolid.svelte';

	export let groupId: string = '';

	let loading = true;
	let saving = false;
	let search = '';

	let users: any[] = [];
	let managerIds: string[] = [];

	$: filteredUsers = users.filter((user) => {
		if (search === '') {
			return true;
		}
		const query = search.toLowerCase();
		return (
			user.name.toLowerCase().includes(query) || user.email.toLowerCase().includes(query)
		);
	});

	const loadData = async () => {
		loading = true;
		try {
			// Load all users
			const usersRes = await getUsers(localStorage.token);
			users = usersRes?.users || usersRes || [];

			// Load current managers for this group
			if (groupId) {
				managerIds = (await getGroupManagers(localStorage.token, groupId)) || [];
			}
		} catch (error) {
			console.error('Error loading managers data:', error);
			toast.error($i18n.t('Failed to load managers'));
		}
		loading = false;
	};

	const toggleManager = async (userId: string) => {
		// Store previous state for rollback on error
		const previousManagerIds = [...managerIds];
		
		if (managerIds.includes(userId)) {
			managerIds = managerIds.filter((id) => id !== userId);
		} else {
			managerIds = [...managerIds, userId];
		}

		// Auto-save when toggling
		const success = await saveManagers();
		if (!success) {
			// Rollback on failure
			managerIds = previousManagerIds;
		}
	};

	const saveManagers = async (): Promise<boolean> => {
		if (!groupId) return false;

		saving = true;
		try {
			await updateGroupManagers(localStorage.token, groupId, managerIds);
			toast.success($i18n.t('Managers updated successfully'));
			dispatch('managersUpdated', { managerIds });
			return true;
		} catch (error) {
			console.error('Error saving managers:', error);
			toast.error($i18n.t('Failed to update managers'));
			return false;
		} finally {
			saving = false;
		}
	};

	onMount(() => {
		loadData();
	});
</script>

<div class="flex flex-col h-full">
	<div class="mb-3">
		<div class="text-sm text-gray-500 dark:text-gray-400 mb-2">
			{$i18n.t('Group managers can rename the group and add/remove users, but cannot modify permissions or delete the group.')}
		</div>

		<div class="flex items-center gap-2 bg-gray-50 dark:bg-gray-900 rounded-lg px-3 py-2">
			<Search className="size-4 text-gray-400" />
			<input
				type="text"
				class="flex-1 bg-transparent outline-none text-sm"
				placeholder={$i18n.t('Search users...')}
				bind:value={search}
			/>
		</div>
	</div>

	{#if loading}
		<div class="flex items-center justify-center py-8">
			<Spinner />
		</div>
	{:else}
		<div class="flex-1 overflow-y-auto space-y-1">
			{#if filteredUsers.length === 0}
				<div class="text-center py-8 text-gray-500 dark:text-gray-400">
					{$i18n.t('No users found')}
				</div>
			{:else}
				{#each filteredUsers as user}
					<button
						class="w-full flex items-center gap-3 p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition {managerIds.includes(user.id)
							? 'bg-blue-50 dark:bg-blue-900/20'
							: ''}"
						on:click={() => toggleManager(user.id)}
						disabled={saving}
					>
						<div class="flex-shrink-0">
							{#if user.profile_image_url}
								<img
									src={user.profile_image_url}
									alt={user.name}
									class="size-8 rounded-full object-cover"
								/>
							{:else}
								<UserCircleSolid className="size-8 text-gray-400" />
							{/if}
						</div>

						<div class="flex-1 text-left">
							<div class="text-sm font-medium">{user.name}</div>
							<div class="text-xs text-gray-500 dark:text-gray-400">{user.email}</div>
						</div>

						<div class="flex-shrink-0">
							<input
								type="checkbox"
								class="size-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
								checked={managerIds.includes(user.id)}
								disabled={saving}
							/>
						</div>
					</button>
				{/each}
			{/if}
		</div>

		<div class="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700">
			<div class="text-sm text-gray-500 dark:text-gray-400">
				{$i18n.t('Selected managers')}: {managerIds.length}
			</div>
		</div>
	{/if}
</div>
