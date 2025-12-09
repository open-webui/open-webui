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
	<div class="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
		<div>
			<h1 class="text-2xl font-semibold text-gray-900 dark:text-gray-100">
				{$i18n.t('Tenants')}
			</h1>
			<p class="text-sm text-gray-500 dark:text-gray-400">
				{$i18n.t('Manage S3-backed tenants and their prompt files.')}
			</p>
		</div>

		<div class="flex gap-2 self-start md:self-center">
			<Tooltip content={$i18n.t('Add Tenant')}>
				<button
					class="inline-flex items-center justify-center rounded-xl border border-gray-300 px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-700 dark:text-gray-200 dark:hover:bg-gray-800"
					on:click={openAddModal}
				>
					<Plus className="size-4 mr-1" />
					<span>{$i18n.t('Add')}</span>
				</button>
			</Tooltip>
		</div>
	</div>

	{#if loading}
		<div class="flex justify-center py-10">
			<Spinner className="size-5" />
		</div>
	{:else if tenants.length === 0}
		<div class="rounded-2xl border border-dashed border-gray-200 bg-white/70 p-8 text-center text-gray-500 dark:border-gray-800 dark:bg-gray-900/70 dark:text-gray-300">
			{$i18n.t('No tenants found. Create one to get started.')}
		</div>
	{:else}
		<div class="overflow-x-auto rounded-2xl border border-gray-100 bg-white/70 shadow-sm dark:border-gray-850 dark:bg-gray-900/70">
			<table class="min-w-full divide-y divide-gray-200 dark:divide-gray-800 text-sm">
				<thead class="bg-gray-50 dark:bg-gray-900/80 text-gray-600 dark:text-gray-300">
					<tr>
						<th class="px-4 py-3 text-left font-semibold">{$i18n.t('Name')}</th>
						<th class="px-4 py-3 text-left font-semibold">{$i18n.t('S3 Bucket')}</th>
						<th class="px-4 py-3 text-left font-semibold">{$i18n.t('Created at')}</th>
						<th class="px-4 py-3 text-right font-semibold">{$i18n.t('Actions')}</th>
					</tr>
				</thead>
				<tbody class="divide-y divide-gray-100 dark:divide-gray-850 text-gray-800 dark:text-gray-100">
					{#each tenants as tenant}
						<tr>
							<td class="px-4 py-3 font-medium">{tenant.name}</td>
							<td class="px-4 py-3 font-mono text-xs sm:text-sm break-all">{tenant.s3_bucket}</td>
							<td class="px-4 py-3">{formatDate(tenant.created_at)}</td>
							<td class="px-4 py-3">
								<div class="flex justify-end gap-2">
									<Tooltip content={$i18n.t('Manage')}>
										<button
											class="rounded-lg border border-gray-300 px-3 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-700 dark:text-gray-200 dark:hover:bg-gray-800"
											on:click={() => openEditModal(tenant)}
										>
											{$i18n.t('Edit')}
										</button>
									</Tooltip>

									<Tooltip content={$i18n.t('Delete')}>
										<button
											class="rounded-lg border border-red-200 px-3 py-1.5 text-xs font-medium text-red-600 hover:bg-red-50 dark:border-red-500/50 dark:text-red-400 dark:hover:bg-red-500/10"
											on:click={() => confirmDeleteTenant(tenant)}
										>
											{$i18n.t('Delete')}
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
