<script lang="ts">
	import { getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';

	import Spinner from '$lib/components/common/Spinner.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Pencil from '$lib/components/icons/Pencil.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import WrenchSolid from '$lib/components/icons/WrenchSolid.svelte';

	import { createRole, updateRoleById, deleteRoleById, setRoleCapabilities } from '$lib/apis/roles';
	import RoleEditor from './RoleEditor.svelte';

	const i18n = getContext<Writable<i18nType>>('i18n');

	export let roles: any[] | null = null;
	export let availableCapabilities: string[] = [];
	export let onRefresh: () => Promise<void> = async () => {};

	const SYSTEM_ROLES = ['admin', 'user', 'pending'];
	const ROLE_COLORS: Record<string, string> = {
		admin: 'bg-red-100 dark:bg-red-900/20 text-red-700 dark:text-red-400',
		user: 'bg-blue-100 dark:bg-blue-900/20 text-blue-700 dark:text-blue-400',
		pending: 'bg-yellow-100 dark:bg-yellow-900/20 text-yellow-700 dark:text-yellow-400'
	};

	let showCreate = false;
	let selectedRole: any = null;
	let showEdit = false;

	const createHandler = async (role: object) => {
		const res = await createRole(localStorage.token, role).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			const caps = (role as any).capabilities;
			if (caps !== undefined && caps.length > 0) {
				await setRoleCapabilities(localStorage.token, res.id, caps).catch((error) => {
					toast.error(`${error}`);
				});
			}
			toast.success($i18n.t('Role created successfully'));
			await onRefresh();
		}
	};

	const updateHandler = async (role: object) => {
		if (!selectedRole) return;
		const res = await updateRoleById(localStorage.token, selectedRole.id, role).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			const caps = (role as any).capabilities;
			if (caps !== undefined) {
				await setRoleCapabilities(localStorage.token, selectedRole.id, caps).catch((error) => {
					toast.error(`${error}`);
				});
			}
			toast.success($i18n.t('Role updated successfully'));
			await onRefresh();
		}
	};

	const deleteHandler = async () => {
		if (!selectedRole) return;
		const res = await deleteRoleById(localStorage.token, selectedRole.id).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			toast.success($i18n.t('Role deleted successfully'));
			selectedRole = null;
			await onRefresh();
		}
	};
</script>

<RoleEditor bind:show={showCreate} {availableCapabilities} onSubmit={createHandler} />

{#if selectedRole}
	<RoleEditor
		bind:show={showEdit}
		edit
		role={selectedRole}
		{availableCapabilities}
		onSubmit={updateHandler}
		onDelete={deleteHandler}
	/>
{/if}

<div
	class="pt-0.5 pb-1 gap-1 flex flex-col md:flex-row justify-between sticky top-0 z-10 bg-white dark:bg-gray-900"
>
	<div class="flex md:self-center text-lg font-medium px-0.5 gap-2">
		<div class="flex-shrink-0">{$i18n.t('Roles')}</div>
		{#if roles !== null}
			<span class="text-lg font-medium text-gray-500 dark:text-gray-300">{roles.length}</span>
		{/if}
	</div>

	<div class="flex gap-1">
		<Tooltip content={$i18n.t('Create Role')}>
			<button
				class="p-2 rounded-xl hover:bg-gray-100 dark:bg-gray-900 dark:hover:bg-gray-850 transition font-medium text-sm flex items-center space-x-1"
				on:click={() => {
					showCreate = true;
				}}
			>
				<Plus className="size-3.5" />
			</button>
		</Tooltip>
	</div>
</div>

{#if roles === null}
	<div class="my-10">
		<Spinner className="size-5" />
	</div>
{:else if roles.length === 0}
	<div
		class="flex flex-col items-center justify-center py-16 text-sm text-gray-400 dark:text-gray-600"
	>
		<svg
			xmlns="http://www.w3.org/2000/svg"
			viewBox="0 0 24 24"
			fill="none"
			stroke="currentColor"
			stroke-width="1.5"
			stroke-linecap="round"
			stroke-linejoin="round"
			class="size-10 mb-3 opacity-40"
		>
			<path
				d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"
			/>
		</svg>
		<div class="mb-3">{$i18n.t('No roles found')}</div>
		<button
			class="text-xs px-3 py-1.5 rounded-full bg-black/5 dark:bg-white/10 hover:bg-black/10 dark:hover:bg-white/15 transition text-gray-600 dark:text-gray-400"
			on:click={() => {
				showCreate = true;
			}}
		>
			{$i18n.t('Create your first role')}
		</button>
	</div>
{:else}
	<div class="flex flex-col gap-0.5 mt-1">
		{#each roles as role (role.id)}
			{@const isSystemRole = SYSTEM_ROLES.includes(role.name)}
			{@const badgeClass =
				ROLE_COLORS[role.name] ?? 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400'}

			<button
				class="flex items-center gap-3 justify-between px-1 py-2 text-xs w-full transition hover:bg-gray-50 dark:hover:bg-gray-900/20 rounded-lg group"
				on:click={() => {
					selectedRole = role;
					showEdit = true;
				}}
			>
				<div class="flex items-center gap-2.5 flex-1 min-w-0">
					<div class="flex-shrink-0">
						{#if isSystemRole}
						<div class="size-2 rounded-full bg-gray-400 dark:bg-gray-600"></div>
						{:else}
						<div class="size-2 rounded-full bg-emerald-400 dark:bg-emerald-500"></div>
						{/if}
					</div>

					<div class="flex flex-col min-w-0 text-left">
						<div class="flex items-center gap-1.5">
							<span class="font-medium text-gray-800 dark:text-gray-200 truncate">
								{role.name}
							</span>
							{#if isSystemRole}
								<span
									class="text-[9px] uppercase tracking-wider font-semibold px-1.5 py-0.5 rounded {badgeClass} flex-shrink-0"
								>
									{$i18n.t('system')}
								</span>
							{/if}
						</div>
						{#if role.description}
							<span class="text-gray-400 dark:text-gray-500 truncate text-[11px] mt-0.5">
								{role.description}
							</span>
						{/if}
					</div>
				</div>

				<div class="flex items-center gap-2 flex-shrink-0">
					{#if role.capabilities?.length > 0}
						<div class="flex items-center gap-1 text-gray-400 dark:text-gray-500">
							<WrenchSolid className="size-3" />
							<span>{role.capabilities.length}</span>
						</div>
					{/if}

					<div
						class="rounded-lg p-1 opacity-0 group-hover:opacity-100 transition hover:bg-gray-100 dark:hover:bg-gray-850"
					>
						<Pencil className="size-3.5" />
					</div>
				</div>
			</button>
		{/each}
	</div>

	<div class="text-gray-500 text-xs mt-2 text-right">
		ⓘ {$i18n.t('Click on a role to edit its name, description, and capabilities.')}
	</div>
{/if}
