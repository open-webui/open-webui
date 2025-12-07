<script lang="ts">
	import { toast } from 'svelte-sonner';
	import {
		getUploadTenants,
		uploadDocument,
		ingestUploadedDocument,
		rebuildTenantArtifact,
		rebuildUserArtifact,
		type UploadDocumentResponse,
		type UploadTenant,
		type UploadVisibility
	} from '$lib/apis/uploads';
	import { WEBUI_NAME, user, showArchivedChats, showSidebar, mobile } from '$lib/stores';
	import { onMount } from 'svelte';
	import { browser } from '$app/environment';
	import Files from '$lib/components/upload/Files.svelte';
	import UserMenu from '$lib/components/layout/Sidebar/UserMenu.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Sidebar from '$lib/components/icons/Sidebar.svelte';
	import { getContext } from 'svelte';
	const i18n = getContext('i18n');
	const tabs = [
		{ id: 'upload', label: 'Upload' },
		{ id: 'public', label: 'Public' },
		{ id: 'private', label: 'Private' }
	];
	let activeTab = 'upload';

	let visibility: UploadVisibility = 'public';
	let selectedFile: File | null = null;
	let isUploading = false;
	let uploadResult: UploadDocumentResponse | null = null;
	let fileInput: HTMLInputElement | null = null;
	let tenants: UploadTenant[] = [];
	let tenantsLoading = false;
	let selectedTenantId: string | null = null;
	let tenantsInitialized = false;
	let selectedTenant: UploadTenant | null = null;
	let isRebuildingTenant = false;
	let isRebuildingPrivate = false;

	const loadTenants = async () => {
		if (
			tenantsLoading ||
			tenantsInitialized ||
			!browser ||
			!localStorage.token ||
			$user?.role !== 'admin'
		) {
			return;
		}
		tenantsLoading = true;
		try {
			const list = await getUploadTenants(localStorage.token);
			tenants = list;
			const defaultId = $user?.tenant_id ?? list[0]?.id ?? null;
			selectedTenantId = defaultId;
		} catch (err) {
			const message = typeof err === 'string' ? err : (err?.detail ?? 'Failed to load tenants.');
			toast.error(message);
		} finally {
			tenantsLoading = false;
			tenantsInitialized = true;
		}
	};

	onMount(() => {
		if (browser) {
			loadTenants();
		}
	});

	$: if ($user?.role === 'admin' && browser && !tenantsInitialized) {
		loadTenants();
	}

	const handleFileChange = (event: Event) => {
		const target = event.target as HTMLInputElement;
		selectedFile = target.files?.[0] ?? null;
	};

	const formatBytes = (bytes: number) => {
		if (!bytes) return '0 B';
		const units = ['B', 'KB', 'MB', 'GB', 'TB'];
		const exponent = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
		const value = bytes / Math.pow(1024, exponent);
		return `${value.toFixed(value >= 10 ? 0 : 1)} ${units[exponent]}`;
	};

	const handleSubmit = async (event: SubmitEvent) => {
		event.preventDefault();
		if (!selectedFile) {
			toast.error('Please choose a file to upload.');
			return;
		}

		if (!tenantBucket) {
			toast.error('Your tenant does not have an S3 bucket configured.');
			return;
		}

		if (!localStorage.token) {
			toast.error('You must be signed in to upload files.');
			return;
		}

		isUploading = true;
		uploadResult = null;

		const tenantOverride =
			$user?.role === 'admin' ? (selectedTenantId ?? $user?.tenant_id ?? undefined) : undefined;

		try {
			const result = await uploadDocument(
				localStorage.token,
				selectedFile,
				visibility,
				tenantOverride
			);
			uploadResult = result;
			toast.success('Upload complete.');
			try {
				await ingestUploadedDocument(localStorage.token, result.key);
				toast.success('Ingestion requested.');
			} catch (err) {
				const message =
					typeof err === 'string'
						? err
						: (err?.detail ?? 'Failed to trigger ingestion of the uploaded file.');
				toast.error(message);
			}
			selectedFile = null;
			if (fileInput) {
				fileInput.value = '';
			}
		} catch (err) {
			const message = typeof err === 'string' ? err : (err?.detail ?? 'Failed to upload file.');
			toast.error(message);
		} finally {
			isUploading = false;
		}
	};

	const ensureToken = () => {
		if (!localStorage.token) {
			toast.error('You must be signed in for this action.');
			return null;
		}
		return localStorage.token;
	};

	const handleRebuildTenant = async () => {
		if (!selectedTenant?.s3_bucket) {
			toast.error('Select a tenant to rebuild.');
			return;
		}
		const token = ensureToken();
		if (!token) return;

		isRebuildingTenant = true;
		try {
			await rebuildTenantArtifact(token, selectedTenant.s3_bucket);
			toast.success('Tenant artifact rebuild requested.');
		} catch (err) {
			const message =
				typeof err === 'string'
					? err
					: (err?.detail ?? 'Failed to rebuild tenant artifact.');
			toast.error(message);
		} finally {
			isRebuildingTenant = false;
		}
	};

	const handleRebuildPrivate = async () => {
		if (!tenantBucket || !$user?.id) {
			toast.error('Tenant information unavailable.');
			return;
		}
		const token = ensureToken();
		if (!token) return;

		isRebuildingPrivate = true;
		try {
			await rebuildUserArtifact(token, tenantBucket, $user.id);
			toast.success('Private artifact rebuild requested.');
		} catch (err) {
			const message =
				typeof err === 'string'
					? err
					: (err?.detail ?? 'Failed to rebuild private artifact.');
			toast.error(message);
		} finally {
			isRebuildingPrivate = false;
		}
	};

	$: selectedTenant =
		$user?.role === 'admin'
			? (tenants.find((t) => t.id === (selectedTenantId ?? $user?.tenant_id)) ?? null)
			: null;

	$: tenantBucket =
		$user?.role === 'admin'
			? (selectedTenant?.s3_bucket ?? null)
			: ($user?.tenant_s3_bucket ?? null);

	const joinPath = (base: string, suffix: string) => {
		const normalizedBase = base.endsWith('/') ? base.slice(0, -1) : base;
		const normalizedSuffix = suffix.startsWith('/') ? suffix.slice(1) : suffix;
		return `${normalizedBase}/${normalizedSuffix}`;
	};

	$: publicPath = tenantBucket ?? null;
	$: privatePath = tenantBucket && $user?.id ? joinPath(tenantBucket, `/users/${$user.id}`) : null;
	$: destinationPreview = tenantBucket
		? `${tenantBucket}${visibility === 'private' ? `/users/${$user?.id}` : ''}/${
				selectedFile?.name ?? 'your-file.ext'
			}`
		: null;
</script>

<svelte:head>
	<title>Uploads • {$WEBUI_NAME}</title>
</svelte:head>

<div
	class=" flex flex-col w-full h-screen max-h-[100dvh] transition-width duration-200 ease-in-out {$showSidebar
		? 'md:max-w-[calc(100%-260px)]'
		: ''} max-w-full"
>
	<nav class="   px-2 pt-1.5 backdrop-blur-xl w-full drag-region">
		<div class=" flex items-center">
			{#if $mobile}
				<div class="{$showSidebar ? 'md:hidden' : ''} flex flex-none items-center">
					<Tooltip
						content={$showSidebar ? $i18n.t('Close Sidebar') : $i18n.t('Open Sidebar')}
						interactive={true}
					>
						<button
							id="sidebar-toggle-button"
							class=" cursor-pointer flex rounded-lg hover:bg-gray-100 dark:hover:bg-gray-850 transition cursor-"
							on:click={() => {
								showSidebar.set(!$showSidebar);
							}}
						>
							<div class=" self-center p-1.5">
								<Sidebar />
							</div>
						</button>
					</Tooltip>
				</div>
			{/if}

			<div class="ml-2 py-0.5 self-center flex items-center justify-between w-full">
				<div class="">
					<div
						class="flex gap-1 scrollbar-none overflow-x-auto w-fit text-center text-sm font-medium bg-transparent py-1 touch-auto pointer-events-auto"
					>
						<a class="min-w-fit transition" href="/notes">
							{$i18n.t('Uploads')}
						</a>
					</div>
				</div>

				<div class=" self-center flex items-center gap-1">
					{#if $user !== undefined && $user !== null}
						<UserMenu
							className="max-w-[240px]"
							role={$user?.role}
							help={true}
							on:show={(e) => {
								if (e.detail === 'archived-chat') {
									showArchivedChats.set(true);
								}
							}}
						>
							<button
								class="select-none flex rounded-xl p-1.5 w-full hover:bg-gray-50 dark:hover:bg-gray-850 transition"
								aria-label="User Menu"
							>
								<div class=" self-center">
									<img
										src={$user?.profile_image_url}
										class="size-6 object-cover rounded-full"
										alt="User profile"
										draggable="false"
									/>
								</div>
							</button>
						</UserMenu>
					{/if}
				</div>
			</div>
		</div>
	</nav>
	<div class="mx-auto w-full flex max-w-4xl flex-col gap-6">
		<div class="flex flex-wrap items-start justify-between gap-4">
			<div class="space-y-2">
				<p class="text-sm text-gray-600 dark:text-gray-400">
					Manage tenant documents in S3. Upload new files or inspect public/private folders.
				</p>
			</div>
		</div>

		<div
			class="flex flex-wrap gap-2 rounded-2xl border border-gray-100 bg-white/70 p-2 shadow-sm dark:border-gray-850 dark:bg-gray-900/50"
		>
			{#each tabs as tab}
				<button
					class={`rounded-xl px-4 py-2 text-sm font-medium transition ${
						activeTab === tab.id
							? 'bg-blue-600 text-white shadow'
							: 'text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-850'
					}`}
					type="button"
					on:click={() => {
						activeTab = tab.id;
					}}
				>
					{tab.label}
				</button>
			{/each}
		</div>

		{#if $user?.role === 'admin'}
			<div
				class="rounded-2xl border border-gray-100 bg-white/70 p-5 shadow-sm dark:border-gray-850 dark:bg-gray-900/60"
			>
				<div class="flex flex-col gap-2">
					<label class="text-sm font-medium text-gray-900 dark:text-gray-100" for="tenant-select">
						Target Tenant Bucket
					</label>
					{#if tenantsLoading}
						<p class="text-sm text-gray-600 dark:text-gray-400">Loading tenant list…</p>
					{:else if tenants.length === 0}
						<p class="text-sm text-gray-600 dark:text-gray-400">
							No tenants available. Create one before uploading.
						</p>
					{:else}
						<select
							id="tenant-select"
							class="w-full rounded-xl border border-gray-200 bg-gray-50 px-3 py-2 text-sm text-gray-900 focus:border-blue-500 focus:outline-none dark:border-gray-800 dark:bg-gray-900 dark:text-gray-50"
							bind:value={selectedTenantId}
						>
							{#each tenants as tenant}
								<option value={tenant.id}>
									{tenant.name} ({tenant.s3_bucket})
								</option>
							{/each}
						</select>
						{#if selectedTenant}
							<p class="text-xs text-gray-500 dark:text-gray-400">
								Uploads will be written to
								<code class="rounded bg-gray-100 px-1 py-0.5 text-[11px] dark:bg-gray-850">
									{selectedTenant.s3_bucket}
								</code>
								for this tenant.
							</p>
						{/if}
					{/if}
				</div>
			</div>
		{/if}

		{#if $user?.role === 'admin' && activeTab === 'public'}
			<div class="flex justify-end">
				<button
					class="inline-flex items-center justify-center rounded-xl border border-blue-200 bg-blue-50 px-4 py-2 text-sm font-medium text-blue-700 transition hover:bg-blue-100 dark:border-blue-800 dark:bg-blue-950/30 dark:text-blue-200 disabled:border-gray-200 disabled:bg-gray-100 disabled:text-gray-500"
					type="button"
					on:click={handleRebuildTenant}
					disabled={!selectedTenant?.s3_bucket || isRebuildingTenant}
				>
					{#if isRebuildingTenant}
						<span class="animate-pulse">Rebuilding…</span>
					{:else}
						Rebuild Tenant Artifact
					{/if}
				</button>
			</div>
		{/if}

		{#if activeTab === 'upload'}
			<div class="flex flex-col gap-6">
				{#if !$user}
					<div
						class="rounded-2xl border border-gray-100 bg-white/60 p-5 text-sm shadow-sm dark:border-gray-800 dark:bg-gray-900"
					>
						Loading your profile…
					</div>
				{:else if !tenantBucket}
					<div
						class="rounded-2xl border border-amber-200 bg-amber-50/80 p-5 text-sm text-amber-900 dark:border-amber-500/40 dark:bg-amber-500/10 dark:text-amber-100"
					>
						Your tenant does not have an S3 bucket configured yet. Please contact an administrator
						before using this page.
					</div>
				{:else}
					<div
						class="rounded-2xl border border-gray-100 bg-white/70 p-5 shadow-sm dark:border-gray-850 dark:bg-gray-900/80"
					>
						<div class="space-y-3 text-sm text-gray-700 dark:text-gray-300">
							<p>
								Files are stored inside
								<code class="rounded bg-gray-100 px-1.5 py-0.5 text-xs dark:bg-gray-850">
									{tenantBucket}
								</code>
								in the configured S3 bucket with two destinations:
							</p>
							<ul class="list-disc space-y-1 pl-6">
								<li>
									<span class="font-medium text-gray-900 dark:text-gray-100">Public</span>
									<span class="text-gray-600 dark:text-gray-400">
										→
										<code class="rounded bg-gray-100 px-1 py-0.5 text-xs dark:bg-gray-850">
											{tenantBucket}/&lt;filename&gt;
										</code>
									</span>
								</li>
								<li>
									<span class="font-medium text-gray-900 dark:text-gray-100">Private</span>
									<span class="text-gray-600 dark:text-gray-400">
										→
										<code class="rounded bg-gray-100 px-1 py-0.5 text-xs dark:bg-gray-850">
											{tenantBucket}/users/{$user?.id}/&lt;filename&gt;
										</code>
									</span>
								</li>
							</ul>
						</div>
					</div>

					<form
						class="space-y-5 rounded-2xl border border-gray-100 bg-white/80 p-5 shadow-sm dark:border-gray-850 dark:bg-gray-900/80"
						on:submit|preventDefault={handleSubmit}
					>
						<div class="space-y-2">
							<label class="text-sm font-medium text-gray-900 dark:text-gray-100">Visibility</label>
							<select
								class="w-full rounded-xl border border-gray-200 bg-gray-50 px-3 py-2 text-sm text-gray-900 focus:border-blue-500 focus:outline-none dark:border-gray-800 dark:bg-gray-900 dark:text-gray-50"
								bind:value={visibility}
							>
								<option value="public">Public (shared tenant folder)</option>
								<option value="private">Private (your user folder)</option>
							</select>
						</div>

						<div class="space-y-2">
							<label class="text-sm font-medium text-gray-900 dark:text-gray-100">File</label>
							<input
								class="block w-full rounded-xl border border-dashed border-gray-300 bg-gray-50 px-4 py-3 text-sm text-gray-800 file:mr-4 file:rounded-lg file:border-0 file:bg-blue-600 file:px-4 file:py-2 file:text-sm file:font-medium file:text-white hover:border-gray-400 focus:border-blue-500 focus:outline-none dark:border-gray-800 dark:bg-gray-900 dark:text-gray-100"
								type="file"
								required
								on:change={handleFileChange}
								bind:this={fileInput}
							/>
							{#if selectedFile}
								<p class="text-xs text-gray-500 dark:text-gray-400">
									<span class="font-medium text-gray-700 dark:text-gray-200"
										>{selectedFile.name}</span
									>
									• {formatBytes(selectedFile.size)}
								</p>
							{/if}
						</div>

						{#if destinationPreview}
							<div
								class="rounded-xl bg-gray-50 px-3 py-2 text-xs text-gray-600 dark:bg-gray-900 dark:text-gray-300"
							>
								<div class="text-[11px] uppercase tracking-wide text-gray-400">
									Destination Preview
								</div>
								<code class="break-all">{destinationPreview}</code>
							</div>
						{/if}

						<div class="flex flex-wrap gap-3">
							<button
								type="submit"
								class="inline-flex items-center justify-center rounded-xl bg-blue-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-blue-500 disabled:cursor-not-allowed disabled:bg-blue-400"
								disabled={!selectedFile || isUploading}
							>
								{#if isUploading}
									<span class="animate-pulse">Uploading…</span>
								{:else}
									Upload file
								{/if}
							</button>
							<button
								type="button"
								class="inline-flex items-center justify-center rounded-xl border border-gray-200 px-4 py-2 text-sm font-medium text-gray-700 transition hover:border-gray-300 hover:text-gray-900 dark:border-gray-800 dark:text-gray-200 dark:hover:border-gray-700 dark:hover:text-white"
								on:click={() => {
									selectedFile = null;
									uploadResult = null;
									if (fileInput) {
										fileInput.value = '';
									}
								}}
							>
								Reset
							</button>
						</div>
					</form>
				{/if}

				{#if uploadResult}
					<div
						class="rounded-2xl border border-emerald-200 bg-emerald-50/80 p-5 text-sm text-emerald-900 shadow-sm dark:border-emerald-500/40 dark:bg-emerald-500/10 dark:text-emerald-100"
					>
						<h2 class="text-lg font-semibold text-emerald-900 dark:text-emerald-100">
							Upload complete
						</h2>
						<dl class="mt-3 space-y-2">
							<div>
								<dt
									class="text-xs uppercase tracking-wide text-emerald-700/80 dark:text-emerald-200/80"
								>
									S3 URL
								</dt>
								<dd class="font-mono text-sm text-emerald-900 dark:text-emerald-50 break-all">
									{uploadResult.url}
								</dd>
							</div>
							<div>
								<dt
									class="text-xs uppercase tracking-wide text-emerald-700/80 dark:text-emerald-200/80"
								>
									Object Key
								</dt>
								<dd class="font-mono text-sm text-emerald-900 dark:text-emerald-50 break-all">
									{uploadResult.key}
								</dd>
							</div>
							<div class="flex flex-wrap gap-4">
								<div>
									<dt
										class="text-xs uppercase tracking-wide text-emerald-700/80 dark:text-emerald-200/80"
									>
										Visibility
									</dt>
									<dd class="font-semibold capitalize">{uploadResult.visibility}</dd>
								</div>
								<div>
									<dt
										class="text-xs uppercase tracking-wide text-emerald-700/80 dark:text-emerald-200/80"
									>
										Stored Name
									</dt>
									<dd class="font-mono text-sm text-emerald-900 dark:text-emerald-50">
										{uploadResult.stored_filename}
									</dd>
								</div>
							</div>
						</dl>
					</div>
				{/if}
			</div>
		{:else if activeTab === 'public'}
			{#if publicPath}
				<Files
					path={publicPath}
					tenantId={$user?.role === 'admin'
						? (selectedTenantId ?? $user?.tenant_id ?? null)
						: ($user?.tenant_id ?? null)}
					tenantBucket={tenantBucket}
				/>
			{:else}
				<div
					class="rounded-2xl border border-amber-200 bg-amber-50/80 p-5 text-sm text-amber-900 shadow-sm dark:border-amber-500/40 dark:bg-amber-500/10 dark:text-amber-100"
				>
					Select a tenant to view its public files.
				</div>
			{/if}
		{:else if activeTab === 'private'}
			<div class="flex justify-end">
				<button
					class="inline-flex items-center justify-center rounded-xl border border-blue-200 bg-blue-50 px-4 py-2 text-sm font-medium text-blue-700 transition hover:bg-blue-100 dark:border-blue-800 dark:bg-blue-950/30 dark:text-blue-200 disabled:border-gray-200 disabled:bg-gray-100 disabled:text-gray-500"
					type="button"
					on:click={handleRebuildPrivate}
					disabled={!tenantBucket || !$user?.id || isRebuildingPrivate}
				>
					{#if isRebuildingPrivate}
						<span class="animate-pulse">Rebuilding…</span>
					{:else}
						Rebuild Private Artifact
					{/if}
				</button>
			</div>
			{#if privatePath}
				<Files
					path={privatePath}
					tenantId={$user?.role === 'admin'
						? (selectedTenantId ?? $user?.tenant_id ?? null)
						: ($user?.tenant_id ?? null)}
					tenantBucket={tenantBucket}
				/>
			{:else}
				<div
					class="rounded-2xl border border-amber-200 bg-amber-50/80 p-5 text-sm text-amber-900 shadow-sm dark:border-amber-500/40 dark:bg-amber-500/10 dark:text-amber-100"
				>
					Select a tenant to view private files.
				</div>
			{/if}
		{/if}
	</div>
</div>
