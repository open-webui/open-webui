<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { toast } from 'svelte-sonner';
	import {
		createCustomRole,
		deleteCustomRole,
		getCustomRoles,
		updateCustomRole
	} from '$lib/apis/users';
	import CustomRoleModal from './CustomRoleModal.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Search from '$lib/components/icons/Search.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import EditPencil from '$lib/components/icons/EditPencil.svelte';
	import Trash from '$lib/components/icons/Trash.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';

	const i18n: any = getContext('i18n');
	let roles: any[] = [];
	let loading = true;
	let query = '';
	let showModal = false;
	let editingRole: any = null;
	let statusMessage = '';
	let loadError = '';
	let pendingRoleId = '';
	let pendingDeactivationRole: any = null;
	let showDeactivateConfirm = false;
	let switchVersion = 0;

	$: filteredRoles = roles.filter((r) =>
		`${r.display_name} ${r.name}`.toLowerCase().includes(query.toLowerCase())
	);

	const load = async () => {
		loading = true;
		loadError = '';
		try {
			const roleResponse = await getCustomRoles(localStorage.token, true);
			roles = roleResponse?.items ?? [];
		} catch (error) {
			statusMessage = `${error}`;
			loadError = statusMessage;
			toast.error(statusMessage);
		} finally {
			loading = false;
		}
	};

	const saveRole = async (data: any) => {
		try {
			if (editingRole)
				await updateCustomRole(localStorage.token, editingRole.id, {
					display_name: data.display_name,
					permissions: data.permissions
				});
			else await createCustomRole(localStorage.token, data);
			statusMessage = $i18n.t('Custom role saved successfully');
			toast.success(statusMessage);
			await load();
		} catch (error) {
			toast.error(`${error}`);
			throw error;
		}
	};

	const deactivate = async (role: any) => {
		if (pendingRoleId) return;
		pendingRoleId = role.id;
		try {
			await updateCustomRole(localStorage.token, role.id, { active: !role.active });
			statusMessage = role.active
				? $i18n.t('Role deactivated; assigned users were reset to user.')
				: $i18n.t('Role reactivated successfully');
			toast.success(statusMessage);
			await load();
		} catch (error) {
			statusMessage = `${error}`;
			toast.error(statusMessage);
		} finally {
			pendingRoleId = '';
		}
	};

	const restoreSwitch = () => {
		switchVersion += 1;
	};

	const toggleRole = (role: any, nextState: boolean) => {
		if (role.active && !nextState) {
			pendingDeactivationRole = role;
			showDeactivateConfirm = true;
			restoreSwitch();
			return;
		}

		deactivate(role);
	};

	const deleteRole = async (role: any) => {
		if (pendingRoleId) return;
		if (
			!confirm(
				$i18n.t('Delete this role? Assigned users will be reset to user and this cannot be undone.')
			)
		)
			return;
		pendingRoleId = role.id;
		try {
			await deleteCustomRole(localStorage.token, role.id);
			statusMessage = $i18n.t('Role deleted; assigned users were reset to user.');
			toast.success(statusMessage);
			await load();
		} catch (error) {
			statusMessage = `${error}`;
			toast.error(statusMessage);
		} finally {
			pendingRoleId = '';
		}
	};

	onMount(load);
</script>

<ConfirmDialog
	bind:show={showDeactivateConfirm}
	title={$i18n.t('Deactivate role')}
	message={$i18n.t(
		'Deactivating this role resets every assigned user to the legacy user role. This cannot be undone for those assignments.'
	)}
	confirmLabel={$i18n.t('Deactivate')}
	on:confirm={() => {
		if (pendingDeactivationRole) deactivate(pendingDeactivationRole);
		pendingDeactivationRole = null;
	}}
	on:cancel={() => {
		pendingDeactivationRole = null;
		restoreSwitch();
	}}
/>

<CustomRoleModal bind:show={showModal} role={editingRole} onSubmit={saveRole} />
<div class="space-y-5">
	<div aria-live="polite" class="sr-only">{statusMessage}</div>
	<div
		class="rounded-lg border border-gray-100 bg-gray-50/70 px-3 py-2 text-xs text-gray-600 dark:border-gray-800 dark:bg-gray-850/50 dark:text-gray-300"
	>
		{$i18n.t('Deactivating or deleting a role resets assigned users to the legacy user role.')}
	</div>
	<div class="sticky top-0 z-10 bg-white dark:bg-gray-900">
		<div class="flex min-h-8 flex-wrap items-center gap-2">
			<div class="flex min-w-[12rem] flex-1 items-center">
				<Search className="mx-3 size-3.5" />
				<input
					class="w-full bg-transparent py-1 text-sm outline-hidden"
					bind:value={query}
					placeholder={$i18n.t('Search roles')}
					aria-label={$i18n.t('Search roles')}
				/>
				{#if query}<button
						class="p-1"
						aria-label={$i18n.t('Clear search')}
						on:click={() => (query = '')}><XMark className="size-3" /></button
					>{/if}
			</div>
			<button
				class="rounded-lg bg-gray-50 px-2.5 py-1 text-xs ring-1 ring-gray-200 hover:bg-gray-100 dark:bg-gray-850 dark:ring-gray-800"
				on:click={() => {
					editingRole = null;
					showModal = true;
				}}>{$i18n.t('New Role')}</button
			>
		</div>
	</div>
	{#if loadError}
		<div
			class="rounded-lg bg-red-50 px-3 py-2 text-xs text-red-700 dark:bg-red-950/30 dark:text-red-300"
			role="alert"
		>
			{$i18n.t('Could not load custom roles')}: {loadError}
		</div>
	{/if}

	{#if loading}<Spinner className="my-10 size-5" />{:else if filteredRoles.length === 0}<div
			class="py-16 text-center text-sm text-gray-500"
		>
			{$i18n.t('No custom roles found')}
		</div>{:else}
		<div class="overflow-x-auto">
			<table class="w-full text-left text-sm">
				<thead class="border-b border-gray-100 text-xs uppercase text-gray-500 dark:border-gray-800"
					><tr
						><th class="px-3 py-2 font-normal">{$i18n.t('Role')}</th><th
							class="px-3 py-2 font-normal">{$i18n.t('Name')}</th
						><th class="px-3 py-2 font-normal">{$i18n.t('Status')}</th><th
							class="px-3 py-2 text-right font-normal">{$i18n.t('Actions')}</th
						></tr
					></thead
				>
				<tbody
					>{#each filteredRoles as role}<tr
							class="border-b border-gray-50 dark:border-gray-850 {role.active
								? ''
								: 'bg-gray-50/70 dark:bg-gray-850/40'}"
							><td
								class="px-3 py-3 font-medium {role.active
									? 'text-gray-900 dark:text-white'
									: 'text-gray-600 dark:text-gray-300'}">{role.display_name}</td
							><td
								class="px-3 py-3 font-mono text-xs {role.active
									? 'text-gray-500'
									: 'text-gray-600 dark:text-gray-400'}">{role.name}</td
							><td class="px-3 py-3"
								><span
									class="rounded-full px-2 py-1 text-xs {role.active
										? 'bg-green-50 text-green-700 dark:bg-green-950/40 dark:text-green-300'
										: 'bg-gray-100 text-gray-500 dark:bg-gray-800'}"
									>{role.active ? $i18n.t('Active') : $i18n.t('Inactive')}</span
								></td
							><td class="px-3 py-3 text-right"
								><div class="flex items-center justify-end gap-1 whitespace-nowrap">
									<Tooltip content={$i18n.t('Edit role')}
										><button
											class="mr-2 rounded-lg p-1.5 hover:bg-black/5 dark:hover:bg-white/5"
											aria-label={$i18n.t('Edit role')}
											on:click={() => {
												editingRole = role;
												showModal = true;
											}}><EditPencil className="size-3.5" /></button
										></Tooltip
									>
									{#key `${role.id}-${role.active}-${switchVersion}`}
										<Switch
											state={role.active}
											ariaLabel={role.active
												? $i18n.t('Deactivate role')
												: $i18n.t('Reactivate role')}
											tooltip={role.active
												? $i18n.t('Deactivate role')
												: $i18n.t('Reactivate role')}
											disabled={pendingRoleId === role.id}
											on:change={(event) => toggleRole(role, event.detail)}
										/>
									{/key}
									<Tooltip content={$i18n.t('Delete role')}
										><button
											class="ml-2 rounded-lg p-1.5 text-red-600 hover:bg-red-50 dark:hover:bg-red-950/30"
											aria-label={$i18n.t('Delete role')}
											disabled={pendingRoleId === role.id}
											on:click={() => deleteRole(role)}><Trash className="size-3.5" /></button
										></Tooltip
									>
								</div></td
							></tr
						>{/each}</tbody
				>
			</table>
		</div>
	{/if}
</div>
