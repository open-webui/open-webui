<script lang="ts">
	import { getContext, onMount } from 'svelte';

	const i18n = getContext('i18n');

	import { getGroups, getGroupById, getGroupInfoById } from '$lib/apis/groups';
	import { getUserInfoById } from '$lib/apis/users';
	import { WEBUI_API_BASE_URL } from '$lib/constants';
	import XMark from '$lib/components/icons/XMark.svelte';
	import Badge from '$lib/components/common/Badge.svelte';
	import GlobeAlt from '$lib/components/icons/GlobeAlt.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import AddAccessModal from './AddAccessModal.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';

	type AccessGrant = {
		id?: string;
		principal_type: 'user' | 'group';
		principal_id: string;
		permission: 'read' | 'write';
	};

	type LegacyAccessControl = {
		read: { group_ids: string[]; user_ids: string[] };
		write: { group_ids: string[]; user_ids: string[] };
	};

	export let onChange: Function = () => {};

	export let accessRoles = ['read'];
	export let accessGrants: AccessGrant[] | any = [];
	export let accessControl: any = undefined;

	export let share = true;
	export let sharePublic = true;

	let groups: any[] = [];
	const resolvingGroupIds = new Set<string>();
	let userById: Record<string, any> = {};
	const resolvingUserIds = new Set<string>();

	let showAddAccessModal = false;

	const dedupeAccessGrants = (grants: AccessGrant[] | null | undefined): AccessGrant[] => {
		if (!Array.isArray(grants)) return [];
		const map = new Map<string, AccessGrant>();
		for (const grant of grants) {
			if (!grant) continue;
			const key = `${grant.principal_type}:${grant.principal_id}:${grant.permission}`;
			if (!grant.principal_type || !grant.principal_id || !grant.permission) continue;
			map.set(key, {
				id: grant.id,
				principal_type: grant.principal_type,
				principal_id: grant.principal_id,
				permission: grant.permission
			});
		}
		return Array.from(map.values());
	};

	const legacyAccessControlToGrants = (accessControl: any): AccessGrant[] => {
		if (accessControl === null) {
			return [
				{
					principal_type: 'user',
					principal_id: '*',
					permission: 'read'
				}
			];
		}

		if (!accessControl || typeof accessControl !== 'object') {
			return [];
		}

		const grants: AccessGrant[] = [];
		for (const permission of ['read', 'write'] as const) {
			const entry = accessControl?.[permission] ?? {};
			for (const groupId of entry?.group_ids ?? []) {
				grants.push({
					principal_type: 'group',
					principal_id: groupId,
					permission
				});
			}
			for (const userId of entry?.user_ids ?? []) {
				grants.push({
					principal_type: 'user',
					principal_id: userId,
					permission
				});
			}
		}

		return dedupeAccessGrants(grants);
	};

	const grantsToLegacyAccessControl = (grants: AccessGrant[]): null | LegacyAccessControl => {
		const normalized = dedupeAccessGrants(grants);
		if (hasPublicReadGrant(normalized)) {
			return null;
		}

		const result: LegacyAccessControl = {
			read: { group_ids: [], user_ids: [] },
			write: { group_ids: [], user_ids: [] }
		};

		for (const grant of normalized) {
			if (!['read', 'write'].includes(grant.permission)) {
				continue;
			}

			if (grant.principal_type === 'group') {
				if (!result[grant.permission].group_ids.includes(grant.principal_id)) {
					result[grant.permission].group_ids = [
						...result[grant.permission].group_ids,
						grant.principal_id
					];
				}
			} else if (grant.principal_type === 'user' && grant.principal_id !== '*') {
				if (!result[grant.permission].user_ids.includes(grant.principal_id)) {
					result[grant.permission].user_ids = [
						...result[grant.permission].user_ids,
						grant.principal_id
					];
				}
			}
		}

		return result;
	};

	const normalizeInputToGrants = (value: any): AccessGrant[] => {
		if (value === null) {
			return legacyAccessControlToGrants(null);
		}
		if (Array.isArray(value)) {
			return dedupeAccessGrants(value);
		}
		if (value && typeof value === 'object' && ('read' in value || 'write' in value)) {
			return legacyAccessControlToGrants(value);
		}
		return [];
	};

	const stableStringify = (value: any): string => {
		try {
			return JSON.stringify(value ?? null);
		} catch {
			return '';
		}
	};

	const hasPublicReadGrant = (grants: AccessGrant[]): boolean =>
		grants.some(
			(grant) =>
				grant.principal_type === 'user' && grant.principal_id === '*' && grant.permission === 'read'
		);

	const currentGrants = (): AccessGrant[] =>
		Array.isArray(accessGrants) ? (accessGrants as AccessGrant[]) : [];

	const getPrincipalIdsByPermission = (
		principalType: 'user' | 'group',
		permission: 'read' | 'write'
	): string[] =>
		Array.from(
			new Set(
				currentGrants()
					.filter(
						(grant) => grant.principal_type === principalType && grant.permission === permission
					)
					.map((grant) => grant.principal_id)
			)
		);

	const hasPrincipalGrant = (
		principalType: 'user' | 'group',
		principalId: string,
		permission: 'read' | 'write'
	): boolean =>
		currentGrants().some(
			(grant) =>
				grant.principal_type === principalType &&
				grant.principal_id === principalId &&
				grant.permission === permission
		);

	const commitAccessGrants = (nextGrants: AccessGrant[]) => {
		accessGrants = dedupeAccessGrants(nextGrants);
		onChange(accessGrants);
	};

	const setPublic = (isPublic: boolean) => {
		const filtered = currentGrants().filter(
			(grant) =>
				!(
					grant.principal_type === 'user' &&
					grant.principal_id === '*' &&
					grant.permission === 'read'
				)
		);
		if (isPublic) {
			filtered.push({
				principal_type: 'user',
				principal_id: '*',
				permission: 'read'
			});
		}
		commitAccessGrants(filtered);
	};

	const upsertPrincipalGrant = (
		principalType: 'user' | 'group',
		principalId: string,
		permission: 'read' | 'write',
		grants: AccessGrant[]
	): AccessGrant[] => {
		if (
			grants.some(
				(grant) =>
					grant.principal_type === principalType &&
					grant.principal_id === principalId &&
					grant.permission === permission
			)
		) {
			return grants;
		}
		return [
			...grants,
			{
				principal_type: principalType,
				principal_id: principalId,
				permission
			}
		];
	};

	const removePrincipalGrant = (
		principalType: 'user' | 'group',
		principalId: string,
		permission: 'read' | 'write',
		grants: AccessGrant[]
	): AccessGrant[] =>
		grants.filter(
			(grant) =>
				!(
					grant.principal_type === principalType &&
					grant.principal_id === principalId &&
					grant.permission === permission
				)
		);

	const removePrincipal = (principalType: 'user' | 'group', principalId: string) => {
		let next = [...currentGrants()];
		next = removePrincipalGrant(principalType, principalId, 'read', next);
		next = removePrincipalGrant(principalType, principalId, 'write', next);
		commitAccessGrants(next);
	};

	const togglePrincipalWrite = (principalType: 'user' | 'group', principalId: string) => {
		let next = [...currentGrants()];
		const hasWrite = hasPrincipalGrant(principalType, principalId, 'write');
		if (hasWrite) {
			next = removePrincipalGrant(principalType, principalId, 'write', next);
		} else {
			next = upsertPrincipalGrant(principalType, principalId, 'read', next);
			next = upsertPrincipalGrant(principalType, principalId, 'write', next);
		}
		commitAccessGrants(next);
	};

	const ensureUsersByIds = async (userIds: string[]) => {
		const pendingIds = userIds.filter((id) => !userById[id] && !resolvingUserIds.has(id));
		if (!pendingIds.length) return;

		for (const id of pendingIds) {
			resolvingUserIds.add(id);
		}

		const fetched = await Promise.all(
			pendingIds.map(async (id) => {
				const user = await getUserInfoById(localStorage.token, id).catch((error) => {
					console.error(error);
					return null;
				});
				return { id, user };
			})
		);

		const nextUserById = { ...userById };
		for (const item of fetched) {
			if (item.user?.id) {
				nextUserById[item.id] = item.user;
			}
			resolvingUserIds.delete(item.id);
		}
		userById = nextUserById;
	};

	const handleAddAccess = ({ userIds, groupIds }: { userIds: string[]; groupIds: string[] }) => {
		let next = [...currentGrants()];

		for (const groupId of groupIds) {
			next = upsertPrincipalGrant('group', groupId, 'read', next);
		}
		for (const userId of userIds) {
			next = upsertPrincipalGrant('user', userId, 'read', next);
		}
		commitAccessGrants(next);
	};

	// NOTE: We must reference `accessGrants` directly in each reactive
	// expression so Svelte tracks the dependency.
	const ensureGroupsByIds = async (groupIds: string[]) => {
		const pendingIds = groupIds.filter(
			(id) => !groups.find((g) => g.id === id) && !resolvingGroupIds.has(id)
		);
		if (!pendingIds.length) return;

		for (const id of pendingIds) {
			resolvingGroupIds.add(id);
		}

		const fetched = await Promise.all(
			pendingIds.map(async (id) => {
				const group = await getGroupInfoById(localStorage.token, id).catch((error) => {
					console.error(error);
					return null;
				});
				return group;
			})
		);

		const newGroups = fetched.filter((g) => g);
		if (newGroups.length > 0) {
			groups = [...groups, ...newGroups].filter(
				(g, index, self) => index === self.findIndex((t) => t.id === g.id)
			);
		}

		for (const id of pendingIds) {
			resolvingGroupIds.delete(id);
		}
	};

	$: if (readGroupIds.length > 0 || writeGroupIds.length > 0) {
		void ensureGroupsByIds([...readGroupIds, ...writeGroupIds]);
	}
	$: readGroupIds = (accessGrants, getPrincipalIdsByPermission('group', 'read'));
	$: writeGroupIds = (accessGrants, getPrincipalIdsByPermission('group', 'write'));
	$: readUserIds =
		(accessGrants, getPrincipalIdsByPermission('user', 'read').filter((id) => id !== '*'));
	$: writeUserIds =
		(accessGrants, getPrincipalIdsByPermission('user', 'write').filter((id) => id !== '*'));

	$: selectedUserIds = Array.from(new Set([...readUserIds, ...writeUserIds]));

	$: selectedUsers = selectedUserIds
		.map((id) => {
			return userById[id] ?? { id, name: id, email: '' };
		})
		.sort((a, b) => a.name.localeCompare(b.name));

	$: accessGroups = groups
		.filter((group) => readGroupIds.includes(group.id) || writeGroupIds.includes(group.id))
		.sort((a, b) => a.name.localeCompare(b.name));

	$: if (selectedUserIds.length > 0) {
		void ensureUsersByIds(selectedUserIds);
	}

	$: {
		if (accessControl !== undefined) {
			const normalizedGrants = normalizeInputToGrants(accessControl);
			if (stableStringify(normalizedGrants) !== stableStringify(accessGrants)) {
				accessGrants = normalizedGrants;
			}
		}
	}

	$: {
		const normalizedGrants = normalizeInputToGrants(accessGrants);
		if (stableStringify(normalizedGrants) !== stableStringify(accessGrants)) {
			accessGrants = normalizedGrants;
		}

		if (accessControl !== undefined) {
			const nextAccessControl = grantsToLegacyAccessControl(normalizedGrants);
			if (stableStringify(nextAccessControl) !== stableStringify(accessControl)) {
				accessControl = nextAccessControl;
			}
		}
	}

	onMount(async () => {
		console.log('AccessControl mounted', { accessGrants, accessControl });
		const res = await getGroups(localStorage.token, true).catch((error) => {
			console.error(error);
			return [];
		});

		console.log('getGroups res', res);

		groups = [...groups, ...res].filter(
			(g, index, self) => index === self.findIndex((t) => t.id === g.id)
		);
	});

	$: console.log('AccessControl state', {
		accessGrants,
		readGroupIds,
		writeGroupIds,
		selectedUserIds,
		groups,
		accessGroups,
		selectedUsers
	});
</script>

<AddAccessModal bind:show={showAddAccessModal} onAdd={handleAddAccess} />

<div class=" rounded-lg flex flex-col gap-1">
	<div class="py-2">
		<div class="flex gap-2.5 items-center">
			<div>
				<div class=" p-2 bg-black/5 dark:bg-white/5 rounded-full">
					{#if !hasPublicReadGrant(accessGrants ?? [])}
						<svg
							xmlns="http://www.w3.org/2000/svg"
							fill="none"
							viewBox="0 0 24 24"
							stroke-width="1.5"
							stroke="currentColor"
							class="w-5 h-5"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								d="M16.5 10.5V6.75a4.5 4.5 0 10-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 002.25-2.25v-6.75a2.25 2.25 0 00-2.25-2.25H6.75a2.25 2.25 0 00-2.25 2.25v6.75a2.25 2.25 0 002.25 2.25z"
							/>
						</svg>
					{:else}
						<svg
							xmlns="http://www.w3.org/2000/svg"
							fill="none"
							viewBox="0 0 24 24"
							stroke-width="1.5"
							stroke="currentColor"
							class="w-5 h-5"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								d="M6.115 5.19l.319 1.913A6 6 0 008.11 10.36L9.75 12l-.387.775c-.217.433-.132.956.21 1.298l1.348 1.348c.21.21.329.497.329.795v1.089c0 .426.24.815.622 1.006l.153.076c.433.217.956.132 1.298-.21l.723-.723a8.7 8.7 0 002.288-4.042 1.087 1.087 0 00-.358-1.099l-1.33-1.108c-.251-.21-.582-.299-.905-.245l-1.17.195a1.125 1.125 0 01-.98-.314l-.295-.295a1.125 1.125 0 010-1.591l.13-.132a1.125 1.125 0 011.3-.21l.603.302a.809.809 0 001.086-1.086L14.25 7.5l1.256-.837a4.5 4.5 0 001.528-1.732l.146-.292M6.115 5.19A9 9 0 1017.18 4.64M6.115 5.19A8.965 8.965 0 0112 3c1.929 0 3.716.607 5.18 1.64"
							/>
						</svg>
					{/if}
				</div>
			</div>

			<div>
				<Tooltip
					content={!(share && sharePublic) && !hasPublicReadGrant(accessGrants ?? [])
						? $i18n.t('You do not have permission to make this public')
						: ''}
				>
					<select
						id="models"
						class="dark:bg-gray-900 outline-none bg-transparent text-sm font-medium block w-fit pr-10 max-w-full placeholder-gray-400"
						value={!hasPublicReadGrant(accessGrants ?? []) ? 'private' : 'public'}
						on:change={(e) => {
							setPublic((e.target as HTMLSelectElement).value === 'public');
						}}
					>
						<option class=" text-gray-700" value="private">{$i18n.t('Private')}</option>
						{#if (share && sharePublic) || hasPublicReadGrant(accessGrants ?? [])}
							<option class=" text-gray-700" value="public">{$i18n.t('Public')}</option>
						{/if}
					</select>
				</Tooltip>

				<div class=" text-xs text-gray-400 font-medium">
					{#if !hasPublicReadGrant(accessGrants ?? [])}
						{$i18n.t('Only select users and groups with permission can access')}
					{:else}
						{$i18n.t('Accessible to all users')}
					{/if}
				</div>
			</div>
		</div>
	</div>

	{#if share}
		<div class="flex items-center justify-between text-xs font-medium text-gray-500 my-1">
			<div>
				{$i18n.t('Access List')}
			</div>
			<div class="flex gap-1">
				<button
					class="px-2 py-1 bg-transparent hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition text-xs font-medium flex items-center gap-1"
					type="button"
					on:click={() => {
						showAddAccessModal = true;
					}}
				>
					<Plus className="size-3" />
					{$i18n.t('Add Access')}
				</button>
			</div>
		</div>

		<!-- List -->
		<div class="flex flex-col gap-2">
			<!-- Groups -->
			{#each accessGroups as group}
				<div class="flex items-center gap-3 justify-between text-sm w-full transition pb-1">
					<div class="flex items-center gap-2 w-full flex-1">
						<!-- Placeholder for group icon vs user icon -->
						<div
							class="size-5 rounded-full bg-gray-100 dark:bg-gray-850 flex items-center justify-center text-xs"
						>
							{group.name.charAt(0).toUpperCase()}
						</div>

						<div class="truncate text-sm flex items-center gap-2">
							{group.name}
							<span class="text-xs text-gray-400 font-normal"
								>{group?.member_count} {$i18n.t('members')}</span
							>
						</div>
					</div>

					<div class="w-full flex justify-end items-center gap-2">
						<button
							type="button"
							on:click={() => {
								if (accessRoles.includes('write')) {
									togglePrincipalWrite('group', group.id);
								}
							}}
						>
							{#if writeGroupIds.includes(group.id)}
								<Badge type={'success'} content={$i18n.t('Write')} />
							{:else}
								<Badge type={'info'} content={$i18n.t('Read')} />
							{/if}
						</button>

						<button
							class=" rounded-full p-1 hover:bg-gray-100 dark:hover:bg-gray-850 transition"
							type="button"
							on:click={() => {
								removePrincipal('group', group.id);
							}}
						>
							<XMark className="size-4" />
						</button>
					</div>
				</div>
			{/each}

			<!-- Users -->
			{#each selectedUsers as user}
				<div
					class="flex items-center gap-3 justify-between text-sm w-full transition border-b border-gray-50 dark:border-gray-850 pb-2 last:border-0"
				>
					<div class="flex items-center gap-2 w-full flex-1">
						<img
							class="rounded-full size-5 object-cover"
							src={`${WEBUI_API_BASE_URL}/users/${user.id}/profile/image`}
							alt={user.name ?? user.id}
						/>
						<div class="w-full">
							<Tooltip content={user.email} placement="top-start">
								<div class="truncate text-sm">{user.name ?? user.id}</div>
							</Tooltip>
						</div>
					</div>

					<div class="w-full flex justify-end items-center gap-2">
						<button
							type="button"
							on:click={() => {
								if (accessRoles.includes('write')) {
									togglePrincipalWrite('user', user.id);
								}
							}}
						>
							{#if writeUserIds.includes(user.id)}
								<Badge type={'success'} content={$i18n.t('Write')} />
							{:else}
								<Badge type={'info'} content={$i18n.t('Read')} />
							{/if}
						</button>

						<button
							class=" rounded-full p-1 hover:bg-gray-100 dark:hover:bg-gray-850 transition"
							type="button"
							on:click={() => {
								removePrincipal('user', user.id);
							}}
						>
							<XMark className="size-4" />
						</button>
					</div>
				</div>
			{/each}

			{#if !hasPublicReadGrant(accessGrants ?? []) && accessGroups.length === 0 && selectedUsers.length === 0}
				<div class="text-xs text-gray-500 text-center py-4">
					{$i18n.t('No access grants. Private to you.')}
				</div>
			{/if}
		</div>
	{/if}
</div>
