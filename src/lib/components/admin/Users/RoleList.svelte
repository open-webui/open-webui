<script>
	import { onMount, getContext } from 'svelte';

	import dayjs from 'dayjs';
	import relativeTime from 'dayjs/plugin/relativeTime';
	import localizedFormat from 'dayjs/plugin/localizedFormat';

	dayjs.extend(relativeTime);
	dayjs.extend(localizedFormat);

	import { toast } from 'svelte-sonner';

	import { getRoles, updateRole, deleteRole } from '$lib/apis/roles';

	import Tooltip from '$lib/components/common/Tooltip.svelte';

	import EditRoleModal from '$lib/components/admin/Users/Roles/EditRoleModal.svelte';
	import AddRoleModal from '$lib/components/admin/Users/Roles/AddRoleModal.svelte';

	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import ChevronUp from '$lib/components/icons/ChevronUp.svelte';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';

	const i18n = getContext('i18n');

	export let lockedRoles = ['pending', 'user', 'admin'];
	export let roles = [];

	let search = '';
	let selectedRole = null;

	let page = 1;

	let showDeleteConfirmDialog = false;
	let showAddRoleModal = false;
	let showEditRoleModal = false;

	const updateRoleHandler = async (id, role) => {
		const res = await updateRole(localStorage.token, id, role).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			roles = await getRoles(localStorage.token);
		}
	};

	const deleteRoleHandler = async (roleName) => {
		const res = await deleteRole(localStorage.token, roleName).catch((error) => {
			toast.error(`${error}`);
			return null;
		});
		if (res) {
			roles = await getRoles(localStorage.token);
		}
	};

	let sortKey = 'created_at'; // default sort key
	let sortOrder = 'asc'; // default sort order

	function setSortKey(key) {
		if (sortKey === key) {
			sortOrder = sortOrder === 'asc' ? 'desc' : 'asc';
		} else {
			sortKey = key;
			sortOrder = 'asc';
		}
	}

	onMount(async () => {
		roles = await getRoles(localStorage.token).catch((error) => {
			toast.error(`${error}`);
			return [];
		});
	});
</script>

<ConfirmDialog
	bind:show={showDeleteConfirmDialog}
	on:confirm={() => {
		deleteRoleHandler(selectedRole.name);
	}}
/>

{#key selectedRole}
	<EditRoleModal
		bind:show={showEditRoleModal}
		{selectedRole}
		on:save={async () => {
			roles = await getRoles(localStorage.token);
		}}
	/>
{/key}

<AddRoleModal
	bind:show={showAddRoleModal}
	on:save={async () => {
		roles = await getRoles(localStorage.token);
	}}
/>

<div class="mt-0.5 mb-2 gap-1 flex flex-col md:flex-row justify-between">
	<div class="flex md:self-center text-lg font-medium px-0.5">
		<div class="flex-shrink-0">
			{$i18n.t('Roles')}
		</div>
		<div class="flex self-center w-[1px] h-6 mx-2.5 bg-gray-50 dark:bg-gray-850" />
	</div>

	<div class="flex gap-1">
		<div class=" flex w-full space-x-2">
			<div>
				<Tooltip content={$i18n.t('Add Role')}>
					<button
						class=" p-2 rounded-xl hover:bg-gray-100 dark:bg-gray-900 dark:hover:bg-gray-850 transition font-medium text-sm flex items-center space-x-1"
						on:click={() => {
							showAddRoleModal = !showAddRoleModal;
						}}
					>
						<Plus className="size-3.5" />
					</button>
				</Tooltip>
			</div>
		</div>
	</div>
</div>

<div
	class="scrollbar-hidden relative whitespace-nowrap overflow-x-auto max-w-full rounded-sm pt-0.5"
>
	<table
		class="w-full text-sm text-left text-gray-500 dark:text-gray-400 table-auto max-w-full rounded-sm"
	>
		<thead
			class="text-xs text-gray-700 uppercase bg-gray-50 dark:bg-gray-850 dark:text-gray-400 -translate-y-0.5"
		>
			<tr class="">
				<th
					scope="col"
					class="px-3 py-1.5 cursor-pointer select-none"
					on:click={() => setSortKey('role')}
				>
					<div class="flex gap-1.5 items-center">
						{$i18n.t('Identifier')}

						{#if sortKey === 'role'}
							<span class="font-normal"
								>{#if sortOrder === 'asc'}
									<ChevronUp className="size-2" />
								{:else}
									<ChevronDown className="size-2" />
								{/if}
							</span>
						{:else}
							<span class="invisible">
								<ChevronUp className="size-2" />
							</span>
						{/if}
					</div>
				</th>
				<th
					scope="col"
					class="px-3 py-1.5 cursor-pointer select-none"
					on:click={() => setSortKey('name')}
				>
					<div class="flex gap-1.5 items-center">
						{$i18n.t('Name')}

						{#if sortKey === 'name'}
							<span class="font-normal"
								>{#if sortOrder === 'asc'}
									<ChevronUp className="size-2" />
								{:else}
									<ChevronDown className="size-2" />
								{/if}
							</span>
						{:else}
							<span class="invisible">
								<ChevronUp className="size-2" />
							</span>
						{/if}
					</div>
				</th>
				<th
					scope="col"
					class="px-3 py-1.5 cursor-pointer select-none"
					on:click={() => setSortKey('created_at')}
				>
					<div class="flex gap-1.5 items-center">
						{$i18n.t('Created at')}
						{#if sortKey === 'created_at'}
							<span class="font-normal"
								>{#if sortOrder === 'asc'}
									<ChevronUp className="size-2" />
								{:else}
									<ChevronDown className="size-2" />
								{/if}
							</span>
						{:else}
							<span class="invisible">
								<ChevronUp className="size-2" />
							</span>
						{/if}
					</div>
				</th>
				<th scope="col" class="px-3 py-2 text-right" />
			</tr>
		</thead>

		<tbody class="">
			{#each roles as role, roleIdx}
				<tr class="bg-white dark:bg-gray-900 dark:border-gray-850 text-xs">
					<td class="px-3 py-1 min-w-[7rem] w-28">
						<div class=" font-medium self-center">{role.id}</div>
					</td>
					<td class="px-3 py-1 font-medium text-gray-900 dark:text-white w-max">
						<div class="flex flex-row w-max">
							<div class=" font-medium self-center">{role.name}</div>
						</div>
					</td>

					<td class=" px-3 py-1">
						{dayjs(role.created_at * 1000).format('LL')}
					</td>

					<td class="px-3 py-1 text-right">
						<div class="flex justify-end w-full">
							<Tooltip content={$i18n.t('Edit role')}>
								<button
									class="self-center w-fit text-sm px-2 py-2 hover:bg-black/5 dark:hover:bg-white/5 rounded-xl"
									on:click={async () => {
										showEditRoleModal = !showEditRoleModal;
										selectedRole = role;
									}}
								>
									<svg
										xmlns="http://www.w3.org/2000/svg"
										fill="none"
										viewBox="0 0 24 24"
										stroke-width="1.5"
										stroke="currentColor"
										class="w-4 h-4"
									>
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											d="m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L6.832 19.82a4.5 4.5 0 0 1-1.897 1.13l-2.685.8.8-2.685a4.5 4.5 0 0 1 1.13-1.897L16.863 4.487Zm0 0L19.5 7.125"
										/>
									</svg>
								</button>
							</Tooltip>

							{#if !lockedRoles.includes(role.name)}
								<Tooltip content={$i18n.t('Delete role')}>
									<button
										class="self-center w-fit text-sm px-2 py-2 hover:bg-black/5 dark:hover:bg-white/5 rounded-xl"
										on:click={async () => {
											showDeleteConfirmDialog = true;
											selectedRole = role;
										}}
									>
										<svg
											xmlns="http://www.w3.org/2000/svg"
											fill="none"
											viewBox="0 0 24 24"
											stroke-width="1.5"
											stroke="currentColor"
											class="w-4 h-4"
										>
											<path
												stroke-linecap="round"
												stroke-linejoin="round"
												d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0"
											/>
										</svg>
									</button>
								</Tooltip>
							{/if}
						</div>
					</td>
				</tr>
			{/each}
		</tbody>
	</table>
</div>
