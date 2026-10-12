<script lang="ts">
	import { getContext, onMount } from 'svelte';

	const i18n = getContext<typeof import('$lib/i18n').default>('i18n');

	import { getGroups, getGroupById, getGroupInfoById } from '$lib/apis/groups';
	import { getUserInfoById } from '$lib/apis/users';
	import { WEBUI_API_BASE_URL } from '$lib/constants';
	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import DropdownMenu from '$lib/components/common/DropdownMenu.svelte';
	import LockClosed from '$lib/components/icons/LockClosed.svelte';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import Check from '$lib/components/icons/Check.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import Badge from '$lib/components/common/Badge.svelte';
	import GlobeAlt from '$lib/components/icons/GlobeAlt.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import AddAccessModal from './AddAccessModal.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Switch from '$lib/components/common/Switch.svelte';

	type AccessGrant = {
		id?: string;
		principal_type: 'user' | 'group' | 'anyone';
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
	export let shareOpen = false;
	export let shareUsers = true;
	export let allowGroups = true;
	export let defaultPermission: 'read' | 'write' = 'read';

	let groups: any[] = [];
	const resolvingGroupIds = new Set<string>();
	let userById: Record<string, any> = {};
	const resolvingUserIds = new Set<string>();

	let showAddAccessModal = false;
	$: visibility = getVisibility(accessGrants ?? []);
	$: visibilityOptions = [
		{ value: 'private' as const, label: $i18n.t('Private') },
		...((share && sharePublic) || hasPublicReadGrant(accessGrants ?? [])
			? [{ value: 'public' as const, label: $i18n.t('Public') }]
			: []),
		...((share && shareOpen) || hasAnyoneReadGrant(accessGrants ?? [])
			? [{ value: 'open' as const, label: $i18n.t('Open') }]
			: [])
	];

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

	const hasAnyoneReadGrant = (grants: AccessGrant[]): boolean =>
		grants.some(
			(grant) =>
				grant.principal_type === 'anyone' &&
				grant.principal_id === '*' &&
				grant.permission === 'read'
		);

	const hasPublicWriteGrant = (grants: AccessGrant[]): boolean =>
		grants.some(
			(grant) =>
				grant.principal_type === 'user' &&
				grant.principal_id === '*' &&
				grant.permission === 'write'
		);

	const currentGrants = (grants: AccessGrant[] | any = accessGrants): AccessGrant[] =>
		Array.isArray(grants) ? (grants as AccessGrant[]) : [];

	const getPrincipalIdsByPermission = (
		principalType: 'user' | 'group',
		permission: 'read' | 'write',
		grants: AccessGrant[] | any = accessGrants
	): string[] =>
		Array.from(
			new Set(
				currentGrants(grants)
					.filter(
						(grant) => grant.principal_type === principalType && grant.permission === permission
					)
					.map((grant) => grant.principal_id)
			)
		);

	const hasPrincipalGrant = (
		principalType: 'user' | 'group' | 'anyone',
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

	const getVisibility = (grants: AccessGrant[]): 'private' | 'public' | 'open' => {
		if (hasAnyoneReadGrant(grants)) return 'open';
		if (hasPublicReadGrant(grants)) return 'public';
		return 'private';
	};

	const setVisibility = (visibility: 'private' | 'public' | 'open') => {
		const filtered = currentGrants().filter(
			(grant) =>
				!(
					(grant.principal_type === 'user' || grant.principal_type === 'anyone') &&
					grant.principal_id === '*'
				)
		);
		if (visibility === 'public') {
			filtered.push({
				principal_type: 'user',
				principal_id: '*',
				permission: 'read'
			});
		} else if (visibility === 'open') {
			filtered.push({
				principal_type: 'anyone',
				principal_id: '*',
				permission: 'read'
			});
		}
		commitAccessGrants(filtered);
	};

	const togglePublicWrite = () => {
		let next = [...currentGrants()];
		if (hasPublicWriteGrant(next)) {
			next = next.filter(
				(grant) =>
					!(
						grant.principal_type === 'user' &&
						grant.principal_id === '*' &&
						grant.permission === 'write'
					)
			);
		} else {
			next = upsertPrincipalGrant('user', '*', 'write', next);
		}
		commitAccessGrants(next);
	};

	const upsertPrincipalGrant = (
		principalType: 'user' | 'group' | 'anyone',
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
		principalType: 'user' | 'group' | 'anyone',
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

	const removePrincipal = (principalType: 'user' | 'group' | 'anyone', principalId: string) => {
		let next = [...currentGrants()];
		next = removePrincipalGrant(principalType, principalId, 'read', next);
		next = removePrincipalGrant(principalType, principalId, 'write', next);
		commitAccessGrants(next);
	};

	const togglePrincipalWrite = (
		principalType: 'user' | 'group' | 'anyone',
		principalId: string
	) => {
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
			if (defaultPermission === 'write') {
				next = upsertPrincipalGrant('group', groupId, 'read', next);
			}
			next = upsertPrincipalGrant('group', groupId, defaultPermission, next);
		}
		for (const userId of userIds) {
			if (defaultPermission === 'write') {
				next = upsertPrincipalGrant('user', userId, 'read', next);
			}
			next = upsertPrincipalGrant('user', userId, defaultPermission, next);
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
	$: readGroupIds = getPrincipalIdsByPermission('group', 'read', accessGrants);
	$: writeGroupIds = getPrincipalIdsByPermission('group', 'write', accessGrants);
	$: readUserIds = getPrincipalIdsByPermission('user', 'read', accessGrants).filter(
		(id) => id !== '*'
	);
	$: writeUserIds = getPrincipalIdsByPermission('user', 'write', accessGrants).filter(
		(id) => id !== '*'
	);

	$: selectedUserIds = Array.from(new Set([...readUserIds, ...writeUserIds]));

	$: selectedUsers = selectedUserIds
		.map((id) => {
			return userById[id] ?? { id, name: id, email: '' };
		})
		.sort((a, b) => a.name.localeCompare(b.name));

	$: accessGroups = Array.from(new Set([...readGroupIds, ...writeGroupIds]))
		.map((id) => groups.find((group) => group.id === id) ?? { id, name: id })
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
		const res = await getGroups(localStorage.token, true).catch((error) => {
			console.error(error);
			return [];
		});

		groups = [...groups, ...res].filter(
			(g, index, self) => index === self.findIndex((t) => t.id === g.id)
		);
	});
</script>

<AddAccessModal
	bind:show={showAddAccessModal}
	{shareUsers}
	{allowGroups}
	{accessGrants}
	onAdd={handleAddAccess}
/>

<div class="flex flex-col gap-2">
	<div class="-mx-1 rounded-xl bg-gray-50/60 px-3 py-2 dark:bg-white/[0.03]">
		<Tooltip
			content={!(share && sharePublic) && visibility === 'private'
				? $i18n.t('You do not have permission to make this public')
				: ''}
		>
			<Dropdown closeOnSelect>
				<button
					type="button"
					aria-label={$i18n.t('Visibility')}
					class="flex h-6 items-center gap-2 rounded-md text-[0.8125rem] font-medium text-gray-800 transition hover:text-gray-950 dark:text-gray-200 dark:hover:text-white"
				>
					{#if visibility === 'private'}
						<LockClosed className="size-3.5 text-gray-500 dark:text-gray-400" />
					{:else}
						<GlobeAlt className="size-3.5 text-gray-500 dark:text-gray-400" />
					{/if}
					<span>{visibilityOptions.find((option) => option.value === visibility)?.label}</span>
					<ChevronDown className="size-3 text-gray-400 dark:text-gray-500" strokeWidth="2" />
				</button>
				<div slot="content">
					<DropdownMenu className="min-w-40">
						{#each visibilityOptions as option}
							<button
								type="button"
								role="menuitemradio"
								aria-checked={visibility === option.value}
								on:click={() => {
									if (visibility !== option.value) setVisibility(option.value);
								}}
							>
								{#if option.value === 'private'}<LockClosed className="size-3.5" />
								{:else}<GlobeAlt className="size-3.5" />{/if}
								<span class="flex-1 text-left">{option.label}</span>
								{#if visibility === option.value}<Check className="size-3.5 text-blue-500" />{/if}
							</button>
						{/each}
					</DropdownMenu>
				</div>
			</Dropdown>
		</Tooltip>
		<p class="mt-0.5 text-xs leading-5 text-gray-500 dark:text-gray-400">
			{#if visibility === 'private'}
				{$i18n.t('Only select users and groups with permission can access')}
			{:else if visibility === 'public'}
				{$i18n.t('Accessible to all users')}
			{:else}
				{$i18n.t('Anyone with the link can view')}
			{/if}
		</p>

		{#if hasPublicReadGrant(accessGrants ?? []) && !hasAnyoneReadGrant(accessGrants ?? []) && accessRoles.includes('write')}
			<div
				class="flex w-full items-center justify-between gap-3 border-t border-gray-100/70 pt-2 mt-2 dark:border-white/5"
			>
				<div class="self-center text-xs">
					{$i18n.t('Allow public write access')}
				</div>
				<Switch
					state={hasPublicWriteGrant(accessGrants ?? [])}
					on:change={() => {
						togglePublicWrite();
					}}
				/>
			</div>
		{/if}
	</div>

	<slot />

	{#if share}
		<div class="flex items-center justify-between text-xs font-normal text-gray-500 my-0.5">
			<div>
				{$i18n.t('Access List')}
			</div>
			<div class="flex gap-1">
				<button
					class="px-2 py-1 bg-transparent hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition text-xs font-normal flex items-center gap-1"
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
		<div class="flex flex-col gap-1">
			<!-- Groups -->
			{#each accessGroups as group}
				<div class="flex items-center gap-2 justify-between text-sm w-full transition pb-1">
					<div class="flex items-center gap-2 min-w-0 flex-1">
						<!-- Placeholder for group icon vs user icon -->
						<div
							class="size-5 rounded-full bg-gray-100 dark:bg-gray-850 flex items-center justify-center text-xs"
						>
							{group.name.charAt(0).toUpperCase()}
						</div>

						<div class="truncate text-sm flex items-center gap-2">
							{group.name}
							{#if group.member_count != null}
								<span class="text-xs text-gray-400 font-normal"
									>{group.member_count} {$i18n.t('members')}</span
								>
							{/if}
						</div>
					</div>

					<div class="flex justify-end items-center gap-1.5 shrink-0">
						{#if accessRoles.includes('write')}
							<select
								aria-label={$i18n.t('Access level')}
								class="bg-transparent text-sm outline-none pr-5"
								value={writeGroupIds.includes(group.id) ? 'write' : 'read'}
								on:change={(e) => {
									if (
										((e.target as HTMLSelectElement).value === 'write') !==
										writeGroupIds.includes(group.id)
									) {
										togglePrincipalWrite('group', group.id);
									}
								}}
							>
								<option value="read">{$i18n.t('Read')}</option>
								<option value="write">{$i18n.t('Write')}</option>
							</select>
						{:else}
							<Badge type={'info'} content={$i18n.t('Read')} />
						{/if}

						<button
							class="rounded-full p-1 hover:bg-gray-100 dark:hover:bg-gray-850 transition"
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
			{#if shareUsers}
				{#each selectedUsers as user}
					<div
						class="flex items-center gap-2 justify-between text-sm w-full transition border-b border-gray-50/50 dark:border-gray-850/50 pb-1.5 last:border-0"
					>
						<div class="flex items-center gap-2 min-w-0 flex-1">
							<img
								class="rounded-full size-5 object-cover"
								src={`${WEBUI_API_BASE_URL}/users/${user.id}/profile/image`}
								alt={user.name ?? user.id}
							/>
							<div class="min-w-0 flex-1">
								<Tooltip content={user.email} placement="top-start">
									<div class="truncate text-sm">{user.name ?? user.id}</div>
								</Tooltip>
							</div>
						</div>

						<div class="flex justify-end items-center gap-1.5 shrink-0">
							{#if accessRoles.includes('write')}
								<select
									aria-label={$i18n.t('Access level')}
									class="bg-transparent text-sm outline-none pr-5"
									value={writeUserIds.includes(user.id) ? 'write' : 'read'}
									on:change={(e) => {
										if (
											((e.target as HTMLSelectElement).value === 'write') !==
											writeUserIds.includes(user.id)
										) {
											togglePrincipalWrite('user', user.id);
										}
									}}
								>
									<option value="read">{$i18n.t('Read')}</option>
									<option value="write">{$i18n.t('Write')}</option>
								</select>
							{:else}
								<Badge type={'info'} content={$i18n.t('Read')} />
							{/if}

							<button
								class="rounded-full p-1 hover:bg-gray-100 dark:hover:bg-gray-850 transition"
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
			{/if}

			{#if getVisibility(accessGrants ?? []) === 'private' && accessGroups.length === 0 && selectedUsers.length === 0}
				<div class="text-xs text-gray-500 text-center py-3">
					{$i18n.t('No access grants. Private to you.')}
				</div>
			{/if}
		</div>
	{/if}
</div>
