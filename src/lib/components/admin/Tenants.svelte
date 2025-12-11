<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { browser } from '$app/environment';
	import dayjs from 'dayjs';
	import localizedFormat from 'dayjs/plugin/localizedFormat';
	import { toast } from 'svelte-sonner';

	import { getUploadTenants, deleteTenant, type TenantInfo } from '$lib/apis/tenants';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import AddTenantModal from './Tenants/AddTenantModal.svelte';
	import EditTenantModal from './Tenants/EditTenantModal.svelte';

	const i18n = getContext('i18n');
	dayjs.extend(localizedFormat);

	let tenants: TenantInfo[] = [];
	let loading = false;
	let query = '';

	let showAddModal = false;
	let showEditModal = false;
	let selectedTenant: TenantInfo | null = null;

	let showDeleteConfirm = false;
	let tenantToDelete: TenantInfo | null = null;

	const loadTenants = async () => {
		if (!browser || !localStorage.token) {
			toast.error($i18n.t('You must be signed in to view tenants.'));
			return;
		}

		loading = true;
		try {
			tenants = await getUploadTenants(localStorage.token);
		} catch (error) {
			const message = typeof error === 'string' ? error : (error?.detail ?? 'Failed to load tenants.');
			toast.error(message);
			tenants = [];
		} finally {
			loading = false;
		}
	};

	onMount(() => {
		loadTenants();
	});

	$: filteredTenants =
		query.trim().length === 0
			? tenants
			: tenants.filter(
					(tenant) =>
						tenant.name.toLowerCase().includes(query.toLowerCase()) ||
						tenant.s3_bucket.toLowerCase().includes(query.toLowerCase())
				);

	const openAddModal = () => {
		showAddModal = true;
	};

	const openEditModal = (tenant: TenantInfo) => {
		selectedTenant = tenant;
		showEditModal = true;
	};

	const confirmDeleteTenant = (tenant: TenantInfo) => {
		tenantToDelete = tenant;
		showDeleteConfirm = true;
	};

	const deleteTenantHandler = async () => {
		if (!tenantToDelete || !browser || !localStorage.token) {
			showDeleteConfirm = false;
			return;
		}

		try {
			await deleteTenant(localStorage.token, tenantToDelete.id);
			toast.success($i18n.t('Tenant deleted'));
			await loadTenants();
		} catch (error) {
			const message = typeof error === 'string' ? error : (error?.detail ?? 'Failed to delete tenant.');
			toast.error(message);
		} finally {
			showDeleteConfirm = false;
			tenantToDelete = null;
		}
	};

	const formatDate = (timestamp?: number) => {
		if (!timestamp) return '—';
		return dayjs(timestamp * 1000).format('LLL');
	};
</script>

<ConfirmDialog
	bind:show={showDeleteConfirm}
	on:confirm={() => {
		deleteTenantHandler();
	}}
	on:cancel={() => {
		showDeleteConfirm = false;
		tenantToDelete = null;
	}}
/>

<AddTenantModal
	bind:show={showAddModal}
	on:save={() => {
		loadTenants();
	}}
/>

<EditTenantModal
	bind:show={showEditModal}
	tenant={selectedTenant}
	on:closed={() => {
		selectedTenant = null;
	}}
	on:updated={() => {
		loadTenants();
	}}
/>

<div class="flex flex-col w-full h-full pb-2 space-y-3 px-[16px]">
		<div class="pt-0.5 pb-1 gap-1 flex flex-col md:flex-row justify-between sticky top-0 z-10 bg-white dark:bg-gray-900">
			<div class="flex md:self-center text-lg font-medium px-0.5">
				<div class="flex-shrink-0">
					{$i18n.t('Tenants')}
				</div>
				<div class="flex self-center w-[1px] h-6 mx-2.5 bg-gray-50 dark:bg-gray-850" />
				<span class="text-lg font-medium text-gray-500 dark:text-gray-300">{tenants.length}</span>
			</div>

			<div class="flex gap-1">
				<div class=" flex w-full space-x-2">
					<div class="flex flex-1">
						<div class=" self-center ml-1 mr-3">
							<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-4 h-4">
								<path
									fill-rule="evenodd"
									d="M9 3.5a5.5 5.5 0 100 11 5.5 5.5 0 000-11zM2 9a7 7 0 1112.452 4.391l3.328 3.329a.75.75 0 11-1.06 1.06l-3.329-3.328A7 7 0 012 9z"
									clip-rule="evenodd"
								/>
							</svg>
						</div>
						<input
							class=" w-full text-sm pr-4 py-1 rounded-r-xl outline-hidden bg-transparent"
							bind:value={query}
							placeholder={$i18n.t('Search')}
						/>
					</div>

					<div>
						<Tooltip content={$i18n.t('Add Tenant')}>
							<button
								class=" p-2 rounded-xl hover:bg-gray-100 dark:bg-gray-900 dark:hover:bg-gray-850 transition font-medium text-sm flex items-center space-x-1"
								on:click={openAddModal}
							>
								<Plus className="size-3.5" />
							</button>
						</Tooltip>
					</div>
				</div>
			</div>
		</div>

	{#if loading}
		<div class="flex justify-center py-10">
			<Spinner className="size-5" />
		</div>
	{:else if filteredTenants.length === 0}
		<div class="rounded-2xl border border-dashed border-gray-200 bg-white/70 p-8 text-center text-gray-500 dark:border-gray-800 dark:bg-gray-900/70 dark:text-gray-300">
			{$i18n.t('No tenants found. Create one to get started.')}
		</div>
	{:else}
		<div class="scrollbar-hidden relative whitespace-nowrap overflow-x-auto max-w-full">
			<table class="w-full text-sm text-left text-gray-500 dark:text-gray-400 table-auto max-w-full">
				<thead class="text-xs text-gray-800 uppercase bg-transparent dark:text-gray-200">
					<tr class=" border-b-[1.5px] border-gray-50 dark:border-gray-850">
						<th scope="col" class="px-2.5 py-2">
							{$i18n.t('Name')}
						</th>
						<th scope="col" class="px-2.5 py-2">
							{$i18n.t('S3 Bucket')}
						</th>
						<th scope="col" class="px-2.5 py-2">
							{$i18n.t('Created at')}
						</th>
						<th scope="col" class="px-2.5 py-2 text-right" />
					</tr>
				</thead>
				<tbody>
					{#each filteredTenants as tenant}
						<tr class="bg-white dark:bg-gray-900 dark:border-gray-850 text-xs">
							<td class="px-3 py-1 font-medium text-gray-900 dark:text-white">
								{tenant.name}
							</td>
							<td class="px-3 py-1 font-mono text-xs sm:text-sm break-all">
								{tenant.s3_bucket}
							</td>
							<td class="px-3 py-1">
								{formatDate(tenant.created_at)}
							</td>
							<td class="px-3 py-1 text-right">
								<div class="flex justify-end gap-1.5">
									<Tooltip content={$i18n.t('Edit Tenant')}>
										<button
											class="self-center w-fit text-sm px-2 py-2 hover:bg-black/5 dark:hover:bg-white/5 rounded-xl"
											on:click={() => openEditModal(tenant)}
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

									<Tooltip content={$i18n.t('Delete Tenant')}>
										<button
											class="self-center w-fit text-sm px-2 py-2 hover:bg-black/5 dark:hover:bg-white/5 rounded-xl"
											on:click={() => confirmDeleteTenant(tenant)}
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
								</div>
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
	{/if}
</div>
