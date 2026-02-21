<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';

	import {
		getMessageLimits,
		upsertMessageLimit,
		deleteMessageLimit,
		type MessageLimit,
		type MessageLimitForm
	} from '$lib/apis/message-limits';
	import { getRoles } from '$lib/apis/roles';
	import { getAllUsers } from '$lib/apis/users';

	import Spinner from '$lib/components/common/Spinner.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';

	const i18n = getContext('i18n');

	export let saveHandler: Function;

	let loading = true;
	let limits: MessageLimit[] = [];
	let roles: { id: string; name: string; is_system: boolean }[] = [];
	let users: { id: string; name: string; email: string; role: string }[] = [];

	// System default
	let systemLimit: number = -1;
	let systemLimitId: string | null = null;
	let savingSystem = false;

	// Role limits
	let roleLimits: Map<string, { limit: number; id: string }> = new Map();
	let showAddRole = false;
	let newRoleId = '';
	let newRoleLimit: number = 200;
	let savingRole = false;

	// User overrides
	let userOverrides: Map<string, { limit: number; id: string; name: string; email: string }> =
		new Map();
	let showAddUser = false;
	let newUserId = '';
	let newUserLimit: number = 200;
	let savingUser = false;
	let userSearch = '';

	$: nonAdminRoles = roles.filter((r) => r.name !== 'admin');
	$: availableRoles = nonAdminRoles.filter((r) => !roleLimits.has(r.id));
	$: nonAdminUsers = users.filter((u) => u.role !== 'admin');
	$: filteredUsers = userSearch
		? nonAdminUsers.filter(
				(u) =>
					!userOverrides.has(u.id) &&
					(u.name.toLowerCase().includes(userSearch.toLowerCase()) ||
						u.email.toLowerCase().includes(userSearch.toLowerCase()))
			)
		: nonAdminUsers.filter((u) => !userOverrides.has(u.id));

	const fetchData = async () => {
		loading = true;
		try {
			const [limitsRes, rolesRes, usersRes] = await Promise.all([
				getMessageLimits(localStorage.token),
				getRoles(localStorage.token),
				getAllUsers(localStorage.token)
			]);

			limits = limitsRes ?? [];
			const rolesArr = Array.isArray(rolesRes) ? rolesRes : (rolesRes?.items ?? []);
			roles = rolesArr.map((r: any) => ({
				id: r.id,
				name: r.name,
				is_system: r.is_system
			}));
			const usersArr = Array.isArray(usersRes) ? usersRes : (usersRes?.items ?? []);
			users = usersArr.map((u: any) => ({
				id: u.id,
				name: u.name,
				email: u.email,
				role: u.role
			}));

			// Parse limits into sections
			systemLimitId = null;
			systemLimit = -1;
			roleLimits = new Map();
			userOverrides = new Map();

			for (const l of limits) {
				if (l.scope_type === 'system') {
					systemLimit = l.max_messages_per_day;
					systemLimitId = l.id;
				} else if (l.scope_type === 'role' && l.role_id) {
					roleLimits.set(l.role_id, { limit: l.max_messages_per_day, id: l.id });
				} else if (l.scope_type === 'user' && l.user_id) {
					const u = users.find((u) => u.id === l.user_id);
					userOverrides.set(l.user_id, {
						limit: l.max_messages_per_day,
						id: l.id,
						name: u?.name ?? 'Unknown',
						email: u?.email ?? ''
					});
				}
			}
			// Trigger reactivity
			roleLimits = roleLimits;
			userOverrides = userOverrides;
		} catch (err) {
			toast.error(`Failed to load message limits: ${err}`);
		}
		loading = false;
	};

	const saveSystemDefault = async () => {
		savingSystem = true;
		try {
			const form: MessageLimitForm = {
				scope_type: 'system',
				max_messages_per_day: systemLimit
			};
			const res = await upsertMessageLimit(localStorage.token, form);
			if (res) {
				systemLimitId = res.id;
				toast.success('System default saved');
			}
		} catch (err) {
			toast.error(`${err}`);
		}
		savingSystem = false;
	};

	const saveRoleLimit = async (roleId: string, limit: number) => {
		savingRole = true;
		try {
			const form: MessageLimitForm = {
				scope_type: 'role',
				role_id: roleId,
				max_messages_per_day: limit
			};
			const res = await upsertMessageLimit(localStorage.token, form);
			if (res) {
				roleLimits.set(roleId, { limit: res.max_messages_per_day, id: res.id });
				roleLimits = roleLimits;
				toast.success('Role limit saved');
			}
		} catch (err) {
			toast.error(`${err}`);
		}
		savingRole = false;
	};

	const addRoleLimit = async () => {
		if (!newRoleId) return;
		await saveRoleLimit(newRoleId, newRoleLimit);
		showAddRole = false;
		newRoleId = '';
		newRoleLimit = 200;
	};

	const removeRoleLimit = async (roleId: string) => {
		const entry = roleLimits.get(roleId);
		if (!entry) return;
		try {
			await deleteMessageLimit(localStorage.token, entry.id);
			roleLimits.delete(roleId);
			roleLimits = roleLimits;
			toast.success('Role limit removed');
		} catch (err) {
			toast.error(`${err}`);
		}
	};

	const saveUserOverride = async (userId: string, limit: number) => {
		savingUser = true;
		try {
			const form: MessageLimitForm = {
				scope_type: 'user',
				user_id: userId,
				max_messages_per_day: limit
			};
			const res = await upsertMessageLimit(localStorage.token, form);
			if (res) {
				const u = users.find((u) => u.id === userId);
				userOverrides.set(userId, {
					limit: res.max_messages_per_day,
					id: res.id,
					name: u?.name ?? 'Unknown',
					email: u?.email ?? ''
				});
				userOverrides = userOverrides;
				toast.success('User override saved');
			}
		} catch (err) {
			toast.error(`${err}`);
		}
		savingUser = false;
	};

	const addUserOverride = async () => {
		if (!newUserId) return;
		await saveUserOverride(newUserId, newUserLimit);
		showAddUser = false;
		newUserId = '';
		newUserLimit = 200;
		userSearch = '';
	};

	const removeUserOverride = async (userId: string) => {
		const entry = userOverrides.get(userId);
		if (!entry) return;
		try {
			await deleteMessageLimit(localStorage.token, entry.id);
			userOverrides.delete(userId);
			userOverrides = userOverrides;
			toast.success('User override removed');
		} catch (err) {
			toast.error(`${err}`);
		}
	};

	onMount(() => {
		fetchData();
	});
</script>

<div class="space-y-3">
	{#if loading}
		<div class="flex justify-center py-8">
			<Spinner />
		</div>
	{:else}
		<!-- System Default -->
		<div>
			<div class="text-sm font-semibold mb-2">Default Daily Message Limit</div>
			<div class="text-xs text-gray-500 dark:text-gray-400 mb-3">
				Maximum messages per day for all non-admin users. Set to -1 for unlimited. Per-role and
				per-user overrides take priority.
			</div>

			<div class="flex items-center gap-3">
				<input
					type="number"
					bind:value={systemLimit}
					min="-1"
					class="w-32 rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
					placeholder="-1"
				/>
				<button
					class="px-4 py-2 text-xs rounded-lg bg-gray-900 hover:bg-gray-850 text-white dark:bg-white dark:text-gray-900 dark:hover:bg-gray-100 transition"
					on:click={saveSystemDefault}
					disabled={savingSystem}
				>
					{savingSystem ? 'Saving...' : 'Save'}
				</button>
				<span class="text-xs text-gray-400">
					{systemLimit === -1 ? 'Unlimited' : `${systemLimit} messages/day`}
				</span>
			</div>
		</div>

		<hr class="border-gray-50 dark:border-gray-850 my-2" />

		<!-- Per-Role Limits -->
		<div>
			<div class="text-sm font-semibold mb-2">Per-Role Limits</div>
			<div class="text-xs text-gray-500 dark:text-gray-400 mb-3">
				Set different daily limits for each role. Overrides the system default.
			</div>

			{#if roleLimits.size > 0}
				<div class="space-y-2 mb-3">
					{#each [...roleLimits.entries()] as [roleId, entry]}
						{@const role = roles.find((r) => r.id === roleId)}
						<div class="flex items-center gap-3 px-3 py-2 rounded-lg bg-gray-50 dark:bg-gray-850">
							<div class="flex-1 text-sm font-medium">
								{role?.name ?? roleId}
							</div>
							<input
								type="number"
								value={entry.limit}
								min="-1"
								class="w-24 rounded-lg py-1.5 px-3 text-sm bg-white dark:text-gray-300 dark:bg-gray-900 outline-hidden"
								on:change={(e) => {
									const val = parseInt(e.currentTarget.value);
									if (!isNaN(val)) saveRoleLimit(roleId, val);
								}}
							/>
							<span class="text-xs text-gray-400 w-24">
								{entry.limit === -1 ? 'Unlimited' : `${entry.limit}/day`}
							</span>
							<button
								class="text-red-500 hover:text-red-700 text-xs"
								on:click={() => removeRoleLimit(roleId)}
							>
								Remove
							</button>
						</div>
					{/each}
				</div>
			{/if}

			{#if showAddRole}
				<div
					class="flex items-center gap-3 px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700"
				>
					<select
						bind:value={newRoleId}
						class="flex-1 rounded-lg py-1.5 px-3 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
					>
						<option value="">Select role...</option>
						{#each availableRoles as role}
							<option value={role.id}>{role.name}</option>
						{/each}
					</select>
					<input
						type="number"
						bind:value={newRoleLimit}
						min="-1"
						class="w-24 rounded-lg py-1.5 px-3 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
					/>
					<button
						class="px-3 py-1.5 text-xs rounded-lg bg-gray-900 hover:bg-gray-850 text-white dark:bg-white dark:text-gray-900 dark:hover:bg-gray-100 transition"
						on:click={addRoleLimit}
						disabled={!newRoleId || savingRole}
					>
						Add
					</button>
					<button
						class="text-gray-400 hover:text-gray-600 text-xs"
						on:click={() => {
							showAddRole = false;
						}}
					>
						Cancel
					</button>
				</div>
			{:else if availableRoles.length > 0}
				<button
					class="text-xs text-blue-500 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300"
					on:click={() => {
						showAddRole = true;
					}}
				>
					+ Add Role Limit
				</button>
			{/if}
		</div>

		<hr class="border-gray-50 dark:border-gray-850 my-2" />

		<!-- Per-User Overrides -->
		<div>
			<div class="text-sm font-semibold mb-2">Per-User Overrides</div>
			<div class="text-xs text-gray-500 dark:text-gray-400 mb-3">
				Override the limit for specific users. Takes highest priority.
			</div>

			{#if userOverrides.size > 0}
				<div class="space-y-2 mb-3">
					{#each [...userOverrides.entries()] as [userId, entry]}
						<div class="flex items-center gap-3 px-3 py-2 rounded-lg bg-gray-50 dark:bg-gray-850">
							<div class="flex-1">
								<div class="text-sm font-medium">{entry.name}</div>
								<div class="text-xs text-gray-400">{entry.email}</div>
							</div>
							<input
								type="number"
								value={entry.limit}
								min="-1"
								class="w-24 rounded-lg py-1.5 px-3 text-sm bg-white dark:text-gray-300 dark:bg-gray-900 outline-hidden"
								on:change={(e) => {
									const val = parseInt(e.currentTarget.value);
									if (!isNaN(val)) saveUserOverride(userId, val);
								}}
							/>
							<span class="text-xs text-gray-400 w-24">
								{entry.limit === -1 ? 'Unlimited' : `${entry.limit}/day`}
							</span>
							<button
								class="text-red-500 hover:text-red-700 text-xs"
								on:click={() => removeUserOverride(userId)}
							>
								Remove
							</button>
						</div>
					{/each}
				</div>
			{/if}

			{#if showAddUser}
				<div
					class="flex items-center gap-3 px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700"
				>
					<div class="flex-1 relative">
						<input
							type="text"
							bind:value={userSearch}
							placeholder="Search users..."
							class="w-full rounded-lg py-1.5 px-3 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
							on:input={() => {
								newUserId = '';
							}}
						/>
						{#if userSearch && !newUserId}
							<div
								class="absolute z-10 mt-1 w-full max-h-40 overflow-y-auto rounded-lg bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 shadow-lg"
							>
								{#each filteredUsers.slice(0, 10) as u}
									<button
										class="w-full text-left px-3 py-2 text-sm hover:bg-gray-50 dark:hover:bg-gray-850"
										on:click={() => {
											newUserId = u.id;
											userSearch = `${u.name} (${u.email})`;
										}}
									>
										<div class="font-medium">{u.name}</div>
										<div class="text-xs text-gray-400">{u.email}</div>
									</button>
								{/each}
								{#if filteredUsers.length === 0}
									<div class="px-3 py-2 text-sm text-gray-400">No users found</div>
								{/if}
							</div>
						{/if}
					</div>
					<input
						type="number"
						bind:value={newUserLimit}
						min="-1"
						class="w-24 rounded-lg py-1.5 px-3 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
					/>
					<button
						class="px-3 py-1.5 text-xs rounded-lg bg-gray-900 hover:bg-gray-850 text-white dark:bg-white dark:text-gray-900 dark:hover:bg-gray-100 transition"
						on:click={addUserOverride}
						disabled={!newUserId || savingUser}
					>
						Add
					</button>
					<button
						class="text-gray-400 hover:text-gray-600 text-xs"
						on:click={() => {
							showAddUser = false;
							userSearch = '';
						}}
					>
						Cancel
					</button>
				</div>
			{:else}
				<button
					class="text-xs text-blue-500 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300"
					on:click={() => {
						showAddUser = true;
					}}
				>
					+ Add User Override
				</button>
			{/if}
		</div>

		<hr class="border-gray-50 dark:border-gray-850 my-2" />

		<!-- Info -->
		<div class="text-xs text-gray-400 dark:text-gray-500 space-y-1">
			<div>Resolution order: User override > Role limit > System default > Unlimited</div>
			<div>Admins are always unlimited regardless of settings.</div>
			<div>Limits reset daily at midnight UTC.</div>
		</div>
	{/if}
</div>
