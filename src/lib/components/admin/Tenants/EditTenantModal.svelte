<script lang="ts">
	import { createEventDispatcher, getContext } from 'svelte';
	import dayjs from 'dayjs';
	import localizedFormat from 'dayjs/plugin/localizedFormat';
	import { toast } from 'svelte-sonner';
	import { goto } from '$app/navigation';

import Modal from '$lib/components/common/Modal.svelte';
import Files from '$lib/components/upload/Files.svelte';
import Spinner from '$lib/components/common/Spinner.svelte';
import TenantLogoImage from './TenantLogoImage.svelte';
import { uploadTenantPrompt, type TenantInfo, updateTenant, type TenantUpdatePayload } from '$lib/apis/tenants';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();
	dayjs.extend(localizedFormat);

	export let show = false;
	export let tenant: TenantInfo | null = null;

	let uploading = false;
	let saving = false;
	let selectedFile: File | null = null;
	let fileInput: HTMLInputElement | null = null;
	let filesComponent: { refresh?: () => void } | null = null;
let tableName = '';
let systemConfigClientName = '';
let logoImageUrl = '';
let initializedTenantId: string | null = null;

	$: promptsPath = tenant ? `${tenant.s3_bucket}/prompts` : null;
	$: if (!show) {
		tableName = '';
		systemConfigClientName = '';
		logoImageUrl = '';
		initializedTenantId = null;
	} else if (tenant && tenant.id !== initializedTenantId) {
		tableName = tenant.table_name ?? '';
		systemConfigClientName = tenant.system_config_client_name ?? '';
		logoImageUrl = tenant.logo_image_url ?? '';
		initializedTenantId = tenant.id;
	}

	const closeModal = () => {
		show = false;
		dispatch('closed');
	};

	const handleFileChange = (event: Event) => {
		const target = event.target as HTMLInputElement;
		selectedFile = target.files?.[0] ?? null;
	};

	$: if (!show) {
		selectedFile = null;
		if (fileInput) {
			fileInput.value = '';
		}
	}

	const uploadPrompt = async () => {
		if (!tenant) {
			toast.error($i18n.t('Select a tenant first.'));
			return;
		}
		if (!selectedFile) {
			toast.error($i18n.t('Choose a .txt file to upload.'));
			return;
		}
		if (!selectedFile.name.toLowerCase().endsWith('.txt')) {
			toast.error($i18n.t('Only .txt files are allowed.'));
			return;
		}
		if (typeof localStorage === 'undefined' || !localStorage.token) {
			toast.error($i18n.t('You must be signed in for this action.'));
			return;
		}

		uploading = true;
		try {
			await uploadTenantPrompt(localStorage.token, tenant.id, selectedFile);
			toast.success($i18n.t('Prompt uploaded'));
			selectedFile = null;
			if (fileInput) {
				fileInput.value = '';
			}
			filesComponent?.refresh?.();
			dispatch('updated');
		} catch (error) {
			const message = typeof error === 'string' ? error : (error?.detail ?? 'Failed to upload prompt.');
			toast.error(message);
		} finally {
			uploading = false;
		}
	};

	const formatDate = (timestamp?: number) => {
		if (!timestamp) return '—';
		return dayjs(timestamp * 1000).format('LLL');
	};

	const saveTenantDetails = async () => {
		if (!tenant) {
			toast.error($i18n.t('Select a tenant first.'));
			return;
		}
		if (typeof localStorage === 'undefined' || !localStorage.token) {
			toast.error($i18n.t('You must be signed in for this action.'));
			return;
		}

		const trimmedTableName = tableName.trim();
		const trimmedClientName = systemConfigClientName.trim();
		const normalizedLogo = logoImageUrl || '';
		const payload: TenantUpdatePayload = {
			table_name: trimmedTableName ? trimmedTableName : null,
			system_config_client_name: trimmedClientName ? trimmedClientName : null,
			logo_image_url: normalizedLogo || null
		};

		saving = true;
		try {
			const updated = await updateTenant(localStorage.token, tenant.id, payload);
			tenant = updated;
			tableName = updated.table_name ?? '';
			systemConfigClientName = updated.system_config_client_name ?? '';
			logoImageUrl = updated.logo_image_url ?? '';
			toast.success($i18n.t('Tenant updated'));
			dispatch('updated');
		} catch (error) {
			const message = typeof error === 'string' ? error : (error?.detail ?? 'Failed to update tenant.');
			toast.error(message);
		} finally {
			saving = false;
		}
	};
</script>

<Modal size="lg" bind:show>
	<div class="px-6 pt-5 pb-6 space-y-4">
		<div class="flex items-center justify-between">
			<div>
				<h2 class="text-xl font-semibold text-gray-900 dark:text-gray-100">
					{$i18n.t('Tenant Details')}
				</h2>
				<p class="text-sm text-gray-500 dark:text-gray-400">
					{$i18n.t('Manage prompt files for this tenant.')}
				</p>
			</div>

			<button
				class="text-sm text-gray-500 hover:text-gray-800 dark:text-gray-400 dark:hover:text-gray-200"
				on:click={closeModal}
			>
				{$i18n.t('Close')}
			</button>
		</div>

		{#if tenant}
			<div class="grid gap-4 md:grid-cols-2">
				<div class="flex flex-col space-y-1 rounded-2xl border border-gray-100 bg-white/70 p-4 dark:border-gray-800 dark:bg-gray-900/60">
					<span class="text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">
						{$i18n.t('Name')}
					</span>
					<span class="text-base font-medium text-gray-900 dark:text-gray-100">{tenant.name}</span>
				</div>

				<div class="flex flex-col space-y-1 rounded-2xl border border-gray-100 bg-white/70 p-4 dark:border-gray-800 dark:bg-gray-900/60">
					<span class="text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">
						{$i18n.t('S3 Bucket')}
					</span>
					<span class="font-mono text-xs sm:text-sm text-gray-900 dark:text-gray-100">{tenant.s3_bucket}</span>
				</div>
			</div>

			<div class="rounded-2xl border border-gray-100 bg-white/70 p-4 dark:border-gray-800 dark:bg-gray-900/60">
				<h3 class="text-sm font-semibold text-gray-900 dark:text-gray-100">{$i18n.t('Tenant Configuration')}</h3>
				<form
					class="mt-3 space-y-3"
					on:submit|preventDefault={() => {
						saveTenantDetails();
					}}
				>
					<div class="flex flex-col gap-4 sm:flex-row">
						<div class="flex flex-col space-y-1">
							<label class="text-xs font-medium uppercase tracking-wide text-gray-500 dark:text-gray-400">
								{$i18n.t('Tenant Logo')}
							</label>
							<TenantLogoImage
								bind:logoImageUrl
								name={tenant.name}
								imageClassName="max-h-28 w-auto rounded-xl border border-gray-200 object-contain dark:border-gray-700"
							/>
						</div>

						<div class="flex-1 space-y-3">
							<div class="flex flex-col space-y-1">
								<label class="text-xs font-medium uppercase tracking-wide text-gray-500 dark:text-gray-400">
									{$i18n.t('Table Name')}
								</label>
								<input
									class="rounded-xl border border-gray-200 bg-transparent px-3 py-2 text-sm text-gray-900 outline-hidden focus:border-blue-500 dark:border-gray-700 dark:text-gray-100"
									type="text"
									placeholder={$i18n.t('Enter table name')}
									bind:value={tableName}
								/>
							</div>

							<div class="flex flex-col space-y-1">
								<label class="text-xs font-medium uppercase tracking-wide text-gray-500 dark:text-gray-400">
									{$i18n.t('System Config Client Name')}
								</label>
								<input
									class="rounded-xl border border-gray-200 bg-transparent px-3 py-2 text-sm text-gray-900 outline-hidden focus:border-blue-500 dark:border-gray-700 dark:text-gray-100"
									type="text"
									placeholder={$i18n.t('Enter client name')}
									bind:value={systemConfigClientName}
								/>
							</div>

						</div>
					</div>

					<div class="flex justify-end">
						<button
							class="inline-flex items-center rounded-full bg-black px-4 py-2 text-sm font-medium text-white transition hover:bg-gray-900 disabled:cursor-not-allowed disabled:opacity-60 dark:bg-white dark:text-black dark:hover:bg-gray-100"
							type="submit"
							disabled={saving}
						>
							{$i18n.t('Save')}
							{#if saving}
								<span class="ml-2">
									<Spinner className="size-4" />
								</span>
							{/if}
						</button>
					</div>
				</form>
			</div>

			<div class="rounded-2xl border border-gray-100 bg-white/70 p-4 text-sm text-gray-600 dark:border-gray-800 dark:bg-gray-900/60 dark:text-gray-300">
				<strong>{$i18n.t('Created at')}:</strong>
				<span>{formatDate(tenant.created_at)}</span>
			</div>

			<div class="rounded-2xl border border-gray-100 bg-white/70 p-4 dark:border-gray-800 dark:bg-gray-900/60">
				<h3 class="text-sm font-semibold text-gray-900 dark:text-gray-100">{$i18n.t('Upload Prompt')}</h3>
				<p class="text-xs text-gray-500 dark:text-gray-400">
					{$i18n.t('Upload .txt files to populate the tenant prompts directory.')}
				</p>

				<div class="mt-3 flex flex-col gap-3 md:flex-row md:items-center">
					<input
						bind:this={fileInput}
						type="file"
						accept=".txt"
						on:change={handleFileChange}
						class="text-sm text-gray-700 file:mr-3 file:rounded-full file:border file:border-gray-300 file:bg-transparent file:px-3 file:py-1.5 file:text-sm file:font-medium file:text-gray-600 hover:file:bg-gray-100 dark:text-gray-200 dark:file:border-gray-600 dark:file:text-gray-200 dark:hover:file:bg-gray-800"
					/>
					<button
						class="inline-flex items-center rounded-full bg-black px-4 py-2 text-sm font-medium text-white transition hover:bg-gray-900 disabled:cursor-not-allowed disabled:opacity-60 dark:bg-white dark:text-black dark:hover:bg-gray-100"
						type="button"
						on:click={uploadPrompt}
						disabled={uploading}
					>
						{$i18n.t('Upload')}
					</button>
				</div>
			</div>

				<div class="rounded-2xl border border-gray-100 bg-white/70 p-4 dark:border-gray-800 dark:bg-gray-900/60">
					<h3 class="mb-2 text-sm font-semibold text-gray-900 dark:text-gray-100">
						{$i18n.t('Prompt Files')}
					</h3>
					<Files
						bind:this={filesComponent}
						tenantId={tenant.id}
						tenantBucket={tenant.s3_bucket}
						path={promptsPath}
						useTenantPromptApi={true}
					/>
					<div class="mt-4 flex justify-end">
						<button
							type="button"
							class="inline-flex items-center rounded-full border border-gray-200 px-4 py-2 text-sm font-medium text-gray-700 transition hover:bg-gray-50 dark:border-gray-700 dark:text-gray-200 dark:hover:bg-gray-800"
							on:click={() => {
								closeModal();
								goto(`/admin/tenants/${encodeURIComponent(tenant.id)}/help`);
							}}
						>
							{$i18n.t('Edit Help Text')}
						</button>
					</div>
				</div>
		{:else}
			<p class="text-sm text-gray-500 dark:text-gray-400">
				{$i18n.t('Select a tenant to view details.')}
			</p>
		{/if}
	</div>
</Modal>
